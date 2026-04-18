import base64
import json
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate, TokenResponse, TokenRefresh
from app.services.audit import log_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    allowed_roles = {"patient", "doctor", "admin"}
    role = body.role if body.role in allowed_roles else "patient"

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=role,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        blood_group=body.blood_group,
        allergies=body.allergies,
        phone=body.phone,
        weight_kg=body.weight_kg,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await log_audit(db, action="register", resource_type="user", resource_id=str(user.id),
                    user_id=user.id, user_email=user.email, request=request)
    await db.commit()

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.oauth_provider:
        raise HTTPException(status_code=401, detail=f"This account uses {user.oauth_provider.title()} sign-in. Use the SSO button.")
    if not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    await log_audit(db, action="login", resource_type="user", resource_id=str(user.id),
                    user_id=user.id, user_email=user.email, request=request)
    await db.commit()

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: TokenRefresh,
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id), User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile (for onboarding completion)."""
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.date_of_birth is not None:
        current_user.date_of_birth = body.date_of_birth
    if body.gender is not None:
        current_user.gender = body.gender
    if body.blood_group is not None:
        current_user.blood_group = body.blood_group
    if body.allergies is not None:
        current_user.allergies = body.allergies
    if body.phone is not None:
        current_user.phone = body.phone
    if body.weight_kg is not None:
        current_user.weight_kg = body.weight_kg
    if body.onboarding_completed is not None:
        current_user.onboarding_completed = body.onboarding_completed
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


# --- Google SSO ---

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Google OAuth consent screen."""
    settings = get_settings()
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google SSO is not configured")

    state = secrets.token_urlsafe(32)
    # Store state in session/cookie for CSRF check (simplified: we rely on state in redirect)
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Exchange code for tokens, fetch user info, create/update user, redirect to frontend with JWT."""
    settings = get_settings()
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google SSO is not configured")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            err = token_resp.json() if token_resp.headers.get("content-type", "").startswith("application/json") else {}
            raise HTTPException(status_code=400, detail=err.get("error_description", "Failed to exchange code"))

        tokens = token_resp.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token from Google")

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")

        info = userinfo_resp.json()
        email = info.get("email")
        name = info.get("name") or info.get("email", "").split("@")[0]
        google_id = info.get("id")

        if not email:
            raise HTTPException(status_code=400, detail="Google did not provide email")

    result = await db.execute(
        select(User).where(User.oauth_provider == "google", User.oauth_id == google_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.oauth_provider = "google"
            user.oauth_id = google_id
            user.full_name = user.full_name or name
            await db.commit()
            await db.refresh(user)
        else:
            user = User(
                email=email,
                hashed_password=None,
                full_name=name,
                role="patient",
                oauth_provider="google",
                oauth_id=google_id,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    await log_audit(db, action="login", resource_type="user", resource_id=str(user.id),
                    user_id=user.id, user_email=user.email, request=request)
    await db.commit()

    jwt_access = create_access_token({"sub": str(user.id), "role": user.role})
    jwt_refresh = create_refresh_token({"sub": str(user.id)})

    frontend = settings.FRONTEND_URL.rstrip("/")
    params = f"access_token={jwt_access}&refresh_token={jwt_refresh}"
    if not getattr(user, "onboarding_completed", True):
        params += "&onboarding=1"
    redirect_url = f"{frontend}/login?{params}"
    return RedirectResponse(url=redirect_url)


# --- Keycloak OIDC ---

def _get_keycloak_client(settings, client_type: str) -> tuple[str, str]:
    """Get (client_id, client_secret) for admin|doctor|patient."""
    if client_type == "admin":
        return settings.KEYCLOAK_ADMIN_CLIENT_ID, settings.KEYCLOAK_ADMIN_CLIENT_SECRET
    if client_type == "doctor":
        return settings.KEYCLOAK_DOCTOR_CLIENT_ID, settings.KEYCLOAK_DOCTOR_CLIENT_SECRET
    return settings.KEYCLOAK_PATIENT_CLIENT_ID, settings.KEYCLOAK_PATIENT_CLIENT_SECRET


@router.get("/keycloak/login")
async def keycloak_login(
    request: Request,
    client: str = "patient",  # admin | doctor | patient
    register: bool = False,  # if True, show Keycloak registration form
):
    """Redirect to Keycloak login. Use ?client=admin|doctor|patient for portal-specific login.
    Use ?register=1 to show registration form (patient/doctor only)."""
    settings = get_settings()
    if not all([settings.KEYCLOAK_URL, settings.KEYCLOAK_REALM]):
        raise HTTPException(status_code=503, detail="Keycloak is not configured")

    client_type = client.lower() if client in ("admin", "doctor", "patient") else "patient"
    client_id, _ = _get_keycloak_client(settings, client_type)

    base = settings.KEYCLOAK_URL.rstrip("/")
    realm = settings.KEYCLOAK_REALM
    auth_url = f"{base}/realms/{realm}/protocol/openid-connect/auth"
    state = f"{client_type}:{secrets.token_urlsafe(24)}"
    params = {
        "client_id": client_id,
        "redirect_uri": settings.KEYCLOAK_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    if register and client_type in ("patient", "doctor"):
        params["kc_action"] = "register"
    url = f"{auth_url}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/keycloak/callback")
async def keycloak_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Exchange Keycloak code for tokens, create/update user, redirect to frontend with JWT."""
    settings = get_settings()
    if not all([settings.KEYCLOAK_URL, settings.KEYCLOAK_REALM]):
        raise HTTPException(status_code=503, detail="Keycloak is not configured")

    client_type = "patient"
    if ":" in state:
        client_type, _ = state.split(":", 1)
        if client_type not in ("admin", "doctor", "patient"):
            client_type = "patient"
    client_id, client_secret = _get_keycloak_client(settings, client_type)

    base = settings.KEYCLOAK_URL.rstrip("/")
    realm = settings.KEYCLOAK_REALM
    token_url = f"{base}/realms/{realm}/protocol/openid-connect/token"
    userinfo_url = f"{base}/realms/{realm}/protocol/openid-connect/userinfo"

    async with httpx.AsyncClient() as client:
        token_data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.KEYCLOAK_REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        token_resp = await client.post(
            token_url,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            err = token_resp.json() if token_resp.headers.get("content-type", "").startswith("application/json") else {}
            raise HTTPException(status_code=400, detail=err.get("error_description", "Failed to exchange code"))

        tokens = token_resp.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token from Keycloak")

        userinfo_resp = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info from Keycloak")

        info = userinfo_resp.json()
        email = info.get("email") or info.get("preferred_username")
        name = info.get("name") or info.get("given_name", "") + " " + (info.get("family_name") or "")
        name = name.strip() or (email or "").split("@")[0]
        keycloak_sub = info.get("sub")

        if not email:
            raise HTTPException(status_code=400, detail="Keycloak did not provide email")

        # Decode JWT payload to get realm roles (no signature verify - we just got it from Keycloak)
        realm_roles = []
        try:
            payload_b64 = access_token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            realm_roles = payload.get("realm_access", {}).get("roles", [])
        except Exception:
            pass

    # Map Keycloak role to app role (admin > doctor > patient)
    app_role = "patient"
    if "admin" in realm_roles:
        app_role = "admin"
    elif "doctor" in realm_roles:
        app_role = "doctor"
    elif "patient" in realm_roles:
        app_role = "patient"

    result = await db.execute(
        select(User).where(User.oauth_provider == "keycloak", User.oauth_id == keycloak_sub)
    )
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.oauth_provider = "keycloak"
            user.oauth_id = keycloak_sub
            user.full_name = user.full_name or name
            user.role = app_role
            await db.commit()
            await db.refresh(user)
        else:
            user = User(
                email=email,
                hashed_password=None,
                full_name=name,
                role=app_role,
                oauth_provider="keycloak",
                oauth_id=keycloak_sub,
                onboarding_completed=False,
            )
            db.add(user)
            await db.flush()
            # Many-to-one: link patient to doctor if linked_doctor_email in Keycloak user attributes
            attrs = info.get("attributes") or {}
            linked_email = attrs.get("linked_doctor_email")
            if app_role == "patient" and linked_email:
                if isinstance(linked_email, list):
                    linked_email = linked_email[0] if linked_email else None
                if linked_email:
                    doc_row = await db.execute(select(User).where(User.email == linked_email, User.role == "doctor"))
                    doctor = doc_row.scalar_one_or_none()
                    if doctor:
                        user.linked_doctor_id = doctor.id
            await db.commit()
            await db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    await log_audit(db, action="login", resource_type="user", resource_id=str(user.id),
                    user_id=user.id, user_email=user.email, request=request)
    await db.commit()

    jwt_access = create_access_token({"sub": str(user.id), "role": user.role})
    jwt_refresh = create_refresh_token({"sub": str(user.id)})

    frontend = settings.FRONTEND_URL.rstrip("/")
    params = f"access_token={jwt_access}&refresh_token={jwt_refresh}"
    if not getattr(user, "onboarding_completed", True):
        params += "&onboarding=1"
    redirect_url = f"{frontend}/login?{params}"
    return RedirectResponse(url=redirect_url)

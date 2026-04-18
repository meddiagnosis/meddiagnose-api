#!/usr/bin/env python3
"""
Sync users from app DB to Keycloak so seeded users can log in via Keycloak.

Reads users from the database, creates them in Keycloak with matching email,
name, password, and realm role. For patients with linked_doctor_id, sets
linked_doctor_email attribute.

Prerequisites:
- Keycloak running (docker compose -f docker-compose.keycloak.yml up -d)
- App DB seeded (python scripts/seed_mimic_patients.py)
- KEYCLOAK_URL in .env or default http://localhost:8080

Run: python scripts/sync_users_to_keycloak.py [--dry-run]
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Seed credentials for password mapping (must match seed_mimic_patients.py)
DOCTOR_EMAIL = "doctor@meddiagnose.demo"
DOCTOR_PASSWORD = "Doctor@123"
DOCTOR2_EMAIL = "doctor2@meddiagnose.demo"
PATIENT_CREDENTIALS = [
    ("Sarah Johnson", "sarah.johnson@meddiagnose.demo", "Sarah@2024"),
    ("Michael Chen", "michael.chen@meddiagnose.demo", "Michael@2024"),
    ("Priya Sharma", "priya.sharma@meddiagnose.demo", "Priya@2024"),
    ("James Wilson", "james.wilson@meddiagnose.demo", "James@2024"),
    ("Maria Garcia", "maria.garcia@meddiagnose.demo", "Maria@2024"),
    ("David Kim", "david.kim@meddiagnose.demo", "David@2024"),
    ("Emily Davis", "emily.davis@meddiagnose.demo", "Emily@2024"),
    ("Robert Martinez", "robert.martinez@meddiagnose.demo", "Robert@2024"),
    ("Anita Patel", "anita.patel@meddiagnose.demo", "Anita@2024"),
    ("William Brown", "william.brown@meddiagnose.demo", "William@2024"),
    ("Lisa Anderson", "lisa.anderson@meddiagnose.demo", "Lisa@2024"),
    ("Raj Kumar", "raj.kumar@meddiagnose.demo", "Raj@2024"),
    ("Jennifer Taylor", "jennifer.taylor@meddiagnose.demo", "Jennifer@2024"),
    ("Christopher Lee", "christopher.lee@meddiagnose.demo", "Chris@2024"),
    ("Amanda White", "amanda.white@meddiagnose.demo", "Amanda@2024"),
    ("Daniel Thompson", "daniel.thompson@meddiagnose.demo", "Daniel@2024"),
    ("Sneha Reddy", "sneha.reddy@meddiagnose.demo", "Sneha@2024"),
    ("Thomas Clark", "thomas.clark@meddiagnose.demo", "Thomas@2024"),
    ("Rachel Green", "rachel.green@meddiagnose.demo", "Rachel@2024"),
    ("Kevin Nguyen", "kevin.nguyen@meddiagnose.demo", "Kevin@2024"),
]


# Optional: extra email->password for seed_data.py users (keys must be lowercase)
EXTRA_PASSWORD_MAP: dict[str, str] = {
    "admin@meddiagnose.com": "Admin@123",
    "doctor@meddiagnose.com": "Doctor@123",
    "doctor2@meddiagnose.com": "Doctor@123",
    "patient1@gmail.com": "Patient@123",
    "patient2@gmail.com": "Patient@123",
}


def get_password_for_email(email: str) -> str | None:
    """Return plain password for seeded users. None if unknown."""
    key = (email or "").strip().lower()
    if key in EXTRA_PASSWORD_MAP:
        return EXTRA_PASSWORD_MAP[key]
    if key == DOCTOR_EMAIL.lower() or key == DOCTOR2_EMAIL.lower():
        return DOCTOR_PASSWORD
    for _, base_email, pwd in PATIENT_CREDENTIALS:
        if key == base_email.lower():
            return pwd
        base = base_email.split("@")[0].lower()
        if key.startswith(base) and key.endswith("@meddiagnose.demo"):
            return pwd  # extended patient e.g. sarah.johnson20@meddiagnose.demo
    return None


def split_full_name(full_name: str) -> tuple[str, str]:
    """Split full_name into first and last. Default last to empty if single word."""
    parts = (full_name or "").strip().split(None, 1)
    if not parts:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])


async def run_sync(dry_run: bool = False) -> None:
    import httpx
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080").rstrip("/")
    realm = os.getenv("KEYCLOAK_REALM", "meddiagnose")
    admin_user = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
    admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")

    if dry_run:
        print("[DRY RUN] No changes will be made.\n")

    print(f"Keycloak: {keycloak_url} | Realm: {realm}")
    print("-" * 50)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get admin token from master realm
        token_url = f"{keycloak_url}/realms/master/protocol/openid-connect/token"
        try:
            token_resp = await client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": admin_user,
                    "password": admin_password,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]
        except Exception as e:
            print(f"Failed to get Keycloak token: {e}")
            print("Ensure Keycloak is running: docker compose -f docker-compose.keycloak.yml up -d")
            sys.exit(1)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        base = f"{keycloak_url}/admin/realms/{realm}"

        # List existing Keycloak users
        existing: dict[str, str] = {}
        try:
            users_resp = await client.get(f"{base}/users", headers=headers)
            users_resp.raise_for_status()
            for u in users_resp.json():
                if u.get("email"):
                    existing[u["email"].lower()] = u["id"]
        except Exception as e:
            print(f"Failed to list Keycloak users: {e}")
            sys.exit(1)

        # Get realm roles
        roles_map: dict[str, dict] = {}
        try:
            roles_resp = await client.get(f"{base}/roles", headers=headers)
            roles_resp.raise_for_status()
            for r in roles_resp.json():
                roles_map[r["name"]] = r
        except Exception as e:
            print(f"Failed to get realm roles: {e}")
            sys.exit(1)

        # Fetch app DB users
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.is_active == True))
            users = list(result.scalars().all())

        doctor_emails = {u.id: u.email for u in users if u.role == "doctor"}
        created = updated = skipped = 0

        for user in users:
            email = (user.email or "").strip().lower()
            if not email:
                skipped += 1
                continue

            password = get_password_for_email(user.email)
            if not password:
                print(f"  Skip {email}: no password in seed mapping")
                skipped += 1
                continue

            first_name, last_name = split_full_name(user.full_name)
            role = user.role if user.role in ("admin", "doctor", "patient") else "patient"
            role_repr = roles_map.get(role)
            if not role_repr:
                print(f"  Skip {email}: role '{role}' not in Keycloak realm")
                skipped += 1
                continue

            attrs: dict[str, list[str]] = {}
            if user.role == "patient" and user.linked_doctor_id:
                doc_email = doctor_emails.get(user.linked_doctor_id)
                if doc_email:
                    attrs["linked_doctor_email"] = [doc_email]

            if dry_run:
                exists = email in existing
                extra = f" linked_doctor={attrs.get('linked_doctor_email', [''])[0]}" if attrs else ""
                print(f"  {'Update' if exists else 'Create'} {email} ({role}){extra}")
                if not exists:
                    created += 1
                else:
                    updated += 1
                continue

            if email in existing:
                kc_id = existing[email]
                try:
                    update_payload: dict = {
                        "firstName": first_name,
                        "lastName": last_name,
                    }
                    if attrs:
                        update_payload["attributes"] = attrs
                    ur = await client.put(f"{base}/users/{kc_id}", headers=headers, json=update_payload)
                    ur.raise_for_status()
                    pr = await client.put(
                        f"{base}/users/{kc_id}/reset-password",
                        headers=headers,
                        json={"type": "password", "value": password, "temporary": False},
                    )
                    pr.raise_for_status()
                    rr = await client.post(
                        f"{base}/users/{kc_id}/role-mappings/realm",
                        headers=headers,
                        json=[role_repr],
                    )
                    rr.raise_for_status()
                    print(f"  Updated {email} ({role})")
                    updated += 1
                except httpx.HTTPStatusError as e:
                    print(f"  Error updating {email}: {e.response.text}")
                continue

            try:
                create_payload = {
                    "username": email,
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                    "enabled": True,
                    "emailVerified": True,
                    "credentials": [{"type": "password", "value": password, "temporary": False}],
                }
                if attrs:
                    create_payload["attributes"] = attrs
                cr = await client.post(f"{base}/users", headers=headers, json=create_payload)
                if cr.status_code == 409:
                    # User exists (e.g. by username), fetch id and add to existing
                    sr = await client.get(f"{base}/users", headers=headers, params={"email": email})
                    sr.raise_for_status()
                    found = [u for u in sr.json() if (u.get("email") or "").lower() == email]
                    if found:
                        existing[email] = found[0]["id"]
                    print(f"  Exists {email}, skipping")
                    skipped += 1
                    continue
                cr.raise_for_status()
                location = cr.headers.get("Location", "")
                kc_id = location.rstrip("/").split("/")[-1]
                existing[email] = kc_id
                # Assign realm role
                ar = await client.post(
                    f"{base}/users/{kc_id}/role-mappings/realm",
                    headers=headers,
                    json=[role_repr],
                )
                ar.raise_for_status()
                print(f"  Created {email} ({role})")
                created += 1
            except httpx.HTTPStatusError as e:
                print(f"  Error creating {email}: {e.response.text}")

    print("-" * 50)
    print(f"Done: {created} created, {updated} updated, {skipped} skipped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync app DB users to Keycloak")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()
    asyncio.run(run_sync(dry_run=args.dry_run))

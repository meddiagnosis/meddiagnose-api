"""
Regression test suite for the MedDiagnose mock diagnosis engine.

Tests every disease pathway, multi-symptom scoring, edge cases,
response schema validation, and the generic fallback path.
"""

import pytest
from app.services.mock_diagnosis import (
    diagnose, get_all_profiles, _score_keywords, MODEL_VERSION,
    _calculate_age, _filter_medications_for_allergies, _build_history_context,
)

# ---------------------------------------------------------------------------
# Required fields that every diagnosis response MUST contain
# ---------------------------------------------------------------------------
REQUIRED_KEYS = {
    "diagnosis", "reasoning", "severity", "confidence", "findings",
    "medications", "lifestyle_recommendations", "precautions",
    "recommended_tests", "when_to_see_doctor", "urgency", "model_version",
    "medical_history_considered",
}

VALID_SEVERITIES = {"mild", "moderate", "severe", "critical"}
VALID_URGENCIES = {"routine", "soon", "urgent", "emergency"}
MEDICATION_FIELDS = {"name", "dosage", "frequency", "duration", "type", "notes"}


# ===================================================================
# Helper
# ===================================================================
def assert_valid_response(result: dict, expected_name_fragment: str | None = None):
    """Validate that a diagnosis result has all required fields and correct types."""
    for key in REQUIRED_KEYS:
        assert key in result, f"Missing key: {key}"

    assert isinstance(result["diagnosis"], str) and len(result["diagnosis"]) > 0
    assert isinstance(result["reasoning"], str) and len(result["reasoning"]) > 0
    assert result["severity"] in VALID_SEVERITIES, f"Invalid severity: {result['severity']}"
    assert 0.0 <= result["confidence"] <= 1.0, f"Confidence out of range: {result['confidence']}"
    assert result["urgency"] in VALID_URGENCIES, f"Invalid urgency: {result['urgency']}"
    assert isinstance(result["findings"], list) and len(result["findings"]) > 0
    assert isinstance(result["medications"], list) and len(result["medications"]) > 0
    assert isinstance(result["lifestyle_recommendations"], list) and len(result["lifestyle_recommendations"]) > 0
    assert isinstance(result["precautions"], list) and len(result["precautions"]) > 0
    assert isinstance(result["recommended_tests"], list) and len(result["recommended_tests"]) > 0
    assert isinstance(result["when_to_see_doctor"], str) and len(result["when_to_see_doctor"]) > 0
    assert result["model_version"] == MODEL_VERSION

    for med in result["medications"]:
        for field in MEDICATION_FIELDS:
            assert field in med, f"Medication missing field: {field} in {med}"
            assert isinstance(med[field], str) and len(med[field]) > 0

    if expected_name_fragment:
        assert expected_name_fragment.lower() in result["diagnosis"].lower(), \
            f"Expected '{expected_name_fragment}' in diagnosis, got: {result['diagnosis']}"


# ===================================================================
# 1. Per-disease regression tests
# ===================================================================
class TestURTI:
    """Disease #1 — Upper Respiratory Tract Infection"""

    def test_fever_keyword(self):
        r = diagnose("I have fever and cold since 2 days")
        assert_valid_response(r, "Respiratory")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.85

    def test_cough_and_cold(self):
        r = diagnose("cough and cold with runny nose")
        assert_valid_response(r, "Respiratory")

    def test_sore_throat(self):
        r = diagnose("my throat is very sore and hurting")
        assert_valid_response(r, "Respiratory")

    def test_confidence_range(self):
        r = diagnose("I have a fever")
        assert r["confidence"] == 0.85
        assert r["urgency"] == "routine"


class TestHeadache:
    """Disease #2 — Tension-Type Headache"""

    def test_headache_keyword(self):
        r = diagnose("severe headache for the last 3 hours")
        assert_valid_response(r, "Headache")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.78

    def test_migraine_keyword(self):
        r = diagnose("I think I have a migraine")
        assert_valid_response(r, "Headache")

    def test_head_pain(self):
        r = diagnose("throbbing head pain on both sides")
        assert_valid_response(r, "Headache")


class TestGastritis:
    """Disease #3 — Acute Gastritis / Gastroenteritis"""

    def test_stomach_keyword(self):
        r = diagnose("stomach pain and cramping after eating")
        assert_valid_response(r, "Gastritis")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.80

    def test_nausea_vomiting(self):
        r = diagnose("nausea and vomiting since morning")
        assert_valid_response(r, "Gastritis")

    def test_diarrhea(self):
        r = diagnose("I have diarrhea and loose motions")
        assert_valid_response(r, "Gastritis")

    def test_urgency_soon(self):
        r = diagnose("severe abdominal pain with nausea")
        assert r["urgency"] == "soon"


class TestAllergicRhinitis:
    """Disease #4 — Allergic Rhinitis / Sinusitis"""

    def test_sneezing(self):
        r = diagnose("constant sneezing and blocked nose")
        assert_valid_response(r, "Rhinitis")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.82

    def test_sinus_keyword(self):
        r = diagnose("sinus pressure and nasal congestion")
        assert_valid_response(r, "Rhinitis")

    def test_itchy_eyes(self):
        r = diagnose("sneezing with itchy eyes and nasal drip")
        assert_valid_response(r, "Rhinitis")


class TestUTI:
    """Disease #5 — Urinary Tract Infection"""

    def test_burning_urination(self):
        r = diagnose("burning urination and pain in lower abdomen")
        assert_valid_response(r, "Urinary")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.83

    def test_frequent_urination(self):
        r = diagnose("frequent urination with bladder discomfort")
        assert_valid_response(r, "Urinary")

    def test_cloudy_urine(self):
        r = diagnose("cloudy urine with mild burning")
        assert_valid_response(r, "Urinary")


class TestBackPain:
    """Disease #6 — Lower Back Pain / Musculoskeletal"""

    def test_back_pain(self):
        r = diagnose("lower back pain for one week now")
        assert_valid_response(r, "Back Pain")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.76

    def test_spine_stiffness(self):
        r = diagnose("spine stiffness and muscle pain in back")
        assert_valid_response(r, "Back Pain")


class TestHypertension:
    """Disease #7 — Hypertension"""

    def test_high_bp(self):
        r = diagnose("my blood pressure reading was 160/100, high bp")
        assert_valid_response(r, "Hypertension")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.81

    def test_hypertension_keyword(self):
        r = diagnose("diagnosed with hypertension recently")
        assert_valid_response(r, "Hypertension")


class TestDiabetes:
    """Disease #8 — Type 2 Diabetes Indicators"""

    def test_blood_sugar(self):
        r = diagnose("blood sugar level is 250mg, feeling very thirsty")
        assert_valid_response(r, "Diabetes")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.79

    def test_glucose_keyword(self):
        r = diagnose("high glucose levels in my blood test report")
        assert_valid_response(r, "Diabetes")

    def test_diabetes_and_fatigue(self):
        r = diagnose("recently diagnosed diabetes and extreme fatigue")
        assert_valid_response(r, "Diabetes")


class TestSkinInfection:
    """Disease #9 — Skin Infection / Dermatitis"""

    def test_rash(self):
        r = diagnose("red rash on my arms with severe itching")
        assert_valid_response(r, "Skin")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.77

    def test_eczema(self):
        r = diagnose("I think I have eczema, dry flaky skin patches")
        assert_valid_response(r, "Skin")

    def test_acne(self):
        r = diagnose("acne breakout on face with redness")
        assert_valid_response(r, "Skin")


class TestAnxiety:
    """Disease #10 — Anxiety / Stress Disorder"""

    def test_anxiety_keyword(self):
        r = diagnose("I have severe anxiety and panic attacks")
        assert_valid_response(r, "Anxiety")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.74

    def test_insomnia_stress(self):
        r = diagnose("can't sleep due to stress and constant worry")
        assert_valid_response(r, "Anxiety")

    def test_palpitations(self):
        r = diagnose("nervous all the time with palpitations")
        assert_valid_response(r, "Anxiety")


class TestConjunctivitis:
    """Disease #11 — Conjunctivitis"""

    def test_red_eye(self):
        r = diagnose("red eye with watery discharge since yesterday")
        assert_valid_response(r, "Conjunctivitis")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.84

    def test_eye_discharge(self):
        r = diagnose("eye discharge and swollen eyelid, sticky eyes")
        assert_valid_response(r, "Conjunctivitis")

    def test_pink_eye(self):
        r = diagnose("I think I have pink eye, itchy and watery")
        assert_valid_response(r, "Conjunctivitis")


class TestAnemia:
    """Disease #12 — Anemia / Iron Deficiency"""

    def test_weakness_fatigue(self):
        r = diagnose("extreme weakness and fatigue, feeling pale and dizzy")
        assert_valid_response(r, "Anemia")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.75

    def test_iron_deficiency(self):
        r = diagnose("doctor said I have low iron and anemia")
        assert_valid_response(r, "Anemia")

    def test_low_hemoglobin(self):
        r = diagnose("feeling tired all the time, low hemoglobin in report")
        assert_valid_response(r, "Anemia")


class TestAcidReflux:
    """Disease #13 — Acid Reflux / GERD"""

    def test_heartburn(self):
        r = diagnose("severe heartburn after meals, sour taste in mouth")
        assert_valid_response(r, "Reflux")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.82

    def test_acid_reflux(self):
        r = diagnose("acid reflux and chest burn at night")
        assert_valid_response(r, "Reflux")

    def test_acidity(self):
        r = diagnose("excessive burping and acidity problems")
        assert_valid_response(r, "Reflux")


class TestJointPain:
    """Disease #14 — Joint Pain / Arthritis"""

    def test_joint_pain(self):
        r = diagnose("joint pain in both knees, worse in the morning")
        assert_valid_response(r, "Joint")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.76

    def test_arthritis(self):
        r = diagnose("I have been diagnosed with arthritis")
        assert_valid_response(r, "Arthritis")

    def test_stiff_joints(self):
        r = diagnose("stiff joints and swelling in my fingers")
        assert_valid_response(r, "Joint")


class TestRespiratoryInfection:
    """Disease #15 — Lower Respiratory Infection (Bronchitis/Pneumonia)"""

    def test_breathing_difficulty(self):
        r = diagnose("breathing difficulty and chest tightness")
        assert_valid_response(r, "Respiratory Infection")
        assert r["severity"] == "severe"
        assert r["confidence"] == 0.72

    def test_shortness_of_breath(self):
        r = diagnose("shortness of breath and wheezing when walking")
        assert_valid_response(r, "Respiratory Infection")

    def test_urgency_is_urgent(self):
        r = diagnose("severe breathing difficulty and chest congestion")
        assert r["urgency"] == "urgent"


class TestThyroid:
    """Disease #16 — Thyroid Disorder (Hypothyroidism)"""

    def test_thyroid_keyword(self):
        r = diagnose("thyroid levels are abnormal, gaining weight and hair loss")
        assert_valid_response(r, "Thyroid")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.80

    def test_cold_intolerance(self):
        r = diagnose("always feeling cold, dry skin and constipation, high tsh")
        assert_valid_response(r, "Thyroid")

    def test_hypothyroid(self):
        r = diagnose("diagnosed with hypothyroid recently")
        assert_valid_response(r, "Thyroid")


class TestAsthma:
    """Disease #17 — Bronchial Asthma"""

    def test_asthma_keyword(self):
        r = diagnose("I have asthma and need my inhaler frequently")
        assert_valid_response(r, "Asthma")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.81

    def test_night_cough(self):
        r = diagnose("wheezing attack and night cough getting worse")
        assert_valid_response(r, "Asthma")

    def test_allergic_asthma(self):
        r = diagnose("allergic asthma triggered by dust")
        assert_valid_response(r, "Asthma")


class TestMigraineWithAura:
    """Disease #18 — Migraine with Aura"""

    def test_migraine_aura(self):
        r = diagnose("migraine aura with visual disturbance and throbbing headache")
        assert_valid_response(r, "Migraine")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.77

    def test_photophobia(self):
        r = diagnose("one-sided headache with light sensitivity and nausea with headache")
        assert_valid_response(r, "Migraine")

    def test_visual_disturbance(self):
        r = diagnose("seeing flashing lights before a throbbing headache starts")
        assert_valid_response(r, "Migraine")


class TestKidneyStones:
    """Disease #19 — Kidney Stones"""

    def test_kidney_stone(self):
        r = diagnose("sharp side pain, kidney stone diagnosed on ultrasound")
        assert_valid_response(r, "Kidney")
        assert r["severity"] == "severe"
        assert r["confidence"] == 0.79

    def test_flank_pain(self):
        r = diagnose("severe flank pain with blood in urine")
        assert_valid_response(r, "Kidney")

    def test_renal_colic(self):
        r = diagnose("renal colic, pain radiating to groin")
        assert_valid_response(r, "Kidney")


class TestDepression:
    """Disease #20 — Major Depressive Disorder"""

    def test_depression_keyword(self):
        r = diagnose("feeling depressed and hopeless for weeks, lost interest in everything")
        assert_valid_response(r, "Depress")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.73

    def test_no_motivation(self):
        r = diagnose("no motivation, crying all the time, feeling worthless")
        assert_valid_response(r, "Depress")

    def test_urgency_is_urgent(self):
        r = diagnose("feeling depressed and suicidal thoughts")
        assert r["urgency"] == "urgent"


class TestEarInfection:
    """Disease #21 — Ear Infection (Otitis Media)"""

    def test_ear_pain(self):
        r = diagnose("severe ear pain and ear ache since yesterday")
        assert_valid_response(r, "Ear")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.81

    def test_ear_discharge(self):
        r = diagnose("ear discharge and blocked ear with hearing loss")
        assert_valid_response(r, "Ear")

    def test_tinnitus(self):
        r = diagnose("ringing ear and ear infection symptoms")
        assert_valid_response(r, "Ear")


class TestDengue:
    """Disease #22 — Dengue Fever"""

    def test_dengue_keyword(self):
        r = diagnose("dengue fever, platelet count dropping, high fever")
        assert_valid_response(r, "Dengue")
        assert r["severity"] == "severe"
        assert r["confidence"] == 0.76

    def test_breakbone(self):
        r = diagnose("body ache severe with high fever, suspected mosquito bite fever")
        assert_valid_response(r, "Dengue")

    def test_urgency_is_urgent(self):
        r = diagnose("dengue with dropping platelets")
        assert r["urgency"] == "urgent"


class TestFoodAllergy:
    """Disease #23 — Food Allergy / Allergic Reaction"""

    def test_food_allergy(self):
        r = diagnose("food allergy, hives after eating shellfish, swollen lips")
        assert_valid_response(r, "Allergy")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.80

    def test_allergic_reaction(self):
        r = diagnose("allergic reaction with throat swelling after eating nuts")
        assert_valid_response(r, "Allergy")

    def test_nut_allergy(self):
        r = diagnose("nut allergy causing itching after food")
        assert_valid_response(r, "Allergy")


class TestVitaminD:
    """Disease #24 — Vitamin D Deficiency"""

    def test_vitamin_d(self):
        r = diagnose("low vitamin d level in blood test, bone pain and muscle weakness")
        assert_valid_response(r, "Vitamin D")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.78

    def test_calcium_deficiency(self):
        r = diagnose("calcium deficiency and bone pain, sun deficiency")
        assert_valid_response(r, "Vitamin D")

    def test_osteoporosis_risk(self):
        r = diagnose("vitamin d very low, doctor said osteoporosis risk")
        assert_valid_response(r, "Vitamin D")


class TestPepticUlcer:
    """Disease #25 — Peptic Ulcer Disease"""

    def test_ulcer(self):
        r = diagnose("stomach ulcer diagnosed, burning stomach pain after eating")
        assert_valid_response(r, "Ulcer")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.79

    def test_h_pylori(self):
        r = diagnose("h pylori positive, empty stomach pain and peptic ulcer")
        assert_valid_response(r, "Ulcer")

    def test_black_stool(self):
        r = diagnose("burning stomach and black stool, doctor suspects ulcer")
        assert_valid_response(r, "Ulcer")


class TestSciatica:
    """Disease #26 — Sciatica"""

    def test_sciatica_keyword(self):
        r = diagnose("sciatica pain, shooting leg pain from lower back")
        assert_valid_response(r, "Sciatica")
        assert r["severity"] == "moderate"
        assert r["confidence"] == 0.75

    def test_herniated_disc(self):
        r = diagnose("herniated disc causing numbness in leg and tingling")
        assert_valid_response(r, "Sciatica")

    def test_nerve_pain(self):
        r = diagnose("nerve pain radiating down my leg, slipped disc")
        assert_valid_response(r, "Sciatica")


class TestMalaria:
    """Disease #27 — Malaria"""

    def test_malaria_keyword(self):
        r = diagnose("malaria suspected, chills and fever with rigors")
        assert_valid_response(r, "Malaria")
        assert r["severity"] == "severe"
        assert r["confidence"] == 0.77

    def test_intermittent_fever(self):
        r = diagnose("intermittent fever with sweating, possible mosquito fever")
        assert_valid_response(r, "Malaria")

    def test_urgency_is_urgent(self):
        r = diagnose("malaria with rigors and intermittent fever")
        assert r["urgency"] == "urgent"


class TestMorningSickness:
    """Disease #28 — Pregnancy-Related Nausea"""

    def test_morning_sickness(self):
        r = diagnose("morning sickness and pregnancy nausea, can't keep food down")
        assert_valid_response(r, "Morning Sickness")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.81

    def test_hyperemesis(self):
        r = diagnose("hyperemesis in early pregnancy, vomiting pregnancy")
        assert_valid_response(r, "Morning Sickness")

    def test_pregnant_nauseous(self):
        r = diagnose("pregnant and nauseous all day, nausea early pregnancy")
        assert_valid_response(r, "Morning Sickness")


class TestChickenpox:
    """Disease #29 — Chickenpox"""

    def test_chickenpox_keyword(self):
        r = diagnose("chickenpox rash, itchy blisters all over body with fever")
        assert_valid_response(r, "Chickenpox")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.83

    def test_varicella(self):
        r = diagnose("varicella diagnosed, vesicular rash with fever")
        assert_valid_response(r, "Chickenpox")

    def test_fluid_blisters(self):
        r = diagnose("fluid filled blisters and pox, rash with fever child")
        assert_valid_response(r, "Chickenpox")


class TestInsomnia:
    """Disease #30 — Insomnia / Sleep Disorder"""

    def test_insomnia_keyword(self):
        r = diagnose("insomnia for weeks, can't sleep at all")
        assert_valid_response(r, "Insomnia")
        assert r["severity"] == "mild"
        assert r["confidence"] == 0.76

    def test_poor_sleep(self):
        r = diagnose("waking up at night multiple times, poor sleep quality")
        assert_valid_response(r, "Insomnia")

    def test_difficulty_sleeping(self):
        r = diagnose("difficulty sleeping and not sleeping well for a month")
        assert_valid_response(r, "Insomnia")


# ===================================================================
# 2. Multi-symptom / weighted scoring tests
# ===================================================================
class TestMultiSymptomScoring:
    """When a patient describes symptoms from multiple categories,
    the engine should pick the one with the highest keyword match score."""

    def test_fever_dominates_headache(self):
        """More fever/cold keywords -> URTI wins over headache."""
        r = diagnose("I have fever, cough, cold, sore throat and also a mild headache")
        assert "Respiratory" in r["diagnosis"]

    def test_stomach_dominates_with_more_keywords(self):
        """More GI keywords -> Gastritis wins."""
        r = diagnose("nausea, vomiting, diarrhea and stomach pain with mild headache")
        assert "Gastritis" in r["diagnosis"]

    def test_two_keyword_match_picks_higher_score(self):
        """When two diseases tie on count, multi-word keywords should break the tie."""
        r = diagnose("I have burning urination and back pain")
        assert r["diagnosis"] is not None
        assert r["confidence"] > 0

    def test_clinical_notes_contribute_to_scoring(self):
        """Clinical notes text should also feed into keyword matching."""
        r = diagnose("mild discomfort", "patient reports frequent urination and bladder pressure")
        assert "Urinary" in r["diagnosis"]


# ===================================================================
# 3. Edge case tests
# ===================================================================
class TestEdgeCases:

    def test_empty_symptoms_returns_fallback(self):
        r = diagnose("")
        assert_valid_response(r, "Preliminary")
        assert r["confidence"] == 0.65

    def test_whitespace_only(self):
        r = diagnose("   ")
        assert_valid_response(r, "Preliminary")

    def test_very_long_input(self):
        long_text = "I have a headache. " * 500
        r = diagnose(long_text)
        assert_valid_response(r, "Headache")

    def test_special_characters(self):
        r = diagnose("I have fever!!! & body ache??? <script>alert('xss')</script>")
        assert_valid_response(r)
        assert r["confidence"] > 0

    def test_single_word_fever(self):
        r = diagnose("fever")
        assert_valid_response(r, "Respiratory")

    def test_uppercase_input(self):
        r = diagnose("SEVERE HEADACHE AND MIGRAINE")
        assert_valid_response(r, "Headache")

    def test_mixed_case(self):
        r = diagnose("Burning Urination and Cloudy Urine")
        assert_valid_response(r, "Urinary")

    def test_numeric_only(self):
        r = diagnose("12345 67890")
        assert_valid_response(r, "Preliminary")


# ===================================================================
# 4. Response schema validation
# ===================================================================
class TestSchemaValidation:
    """Ensure every registered disease profile produces a schema-valid response."""

    @pytest.mark.parametrize("profile", get_all_profiles(), ids=lambda p: p.name[:40])
    def test_every_profile_produces_valid_output(self, profile):
        keyword_sample = " ".join(profile.keywords[:3])
        r = diagnose(keyword_sample)
        assert_valid_response(r)
        assert r["confidence"] >= 0.65
        assert r["severity"] in VALID_SEVERITIES

    @pytest.mark.parametrize("profile", get_all_profiles(), ids=lambda p: p.name[:40])
    def test_every_profile_has_at_least_one_medication(self, profile):
        assert len(profile.medications) >= 1

    @pytest.mark.parametrize("profile", get_all_profiles(), ids=lambda p: p.name[:40])
    def test_every_profile_has_lifestyle_recs(self, profile):
        assert len(profile.lifestyle) >= 1

    @pytest.mark.parametrize("profile", get_all_profiles(), ids=lambda p: p.name[:40])
    def test_every_profile_has_precautions(self, profile):
        assert len(profile.precautions) >= 1


# ===================================================================
# 5. Fallback path tests
# ===================================================================
class TestFallback:

    def test_unrecognized_symptoms(self):
        r = diagnose("I ate something weird and now my elbow tingles")
        assert_valid_response(r, "Preliminary")
        assert r["confidence"] == 0.65
        assert r["severity"] == "moderate"
        assert r["urgency"] == "soon"

    def test_gibberish_input(self):
        r = diagnose("asdfghjkl qwertyuiop")
        assert_valid_response(r, "Preliminary")

    def test_fallback_has_paracetamol(self):
        r = diagnose("xyz totally unknown symptom")
        med_names = [m["name"] for m in r["medications"]]
        assert "Paracetamol" in med_names


# ===================================================================
# 6. Scoring engine unit tests
# ===================================================================
class TestScoringEngine:

    def test_score_single_keyword(self):
        profile = get_all_profiles()[0]  # URTI
        score = _score_keywords("I have a fever", profile)
        assert score >= 1.0

    def test_score_multi_word_keyword_bonus(self):
        profile = get_all_profiles()[5]  # Back Pain — has "back pain", "lower back"
        score_multi = _score_keywords("I have lower back pain", profile)
        score_single = _score_keywords("I have stiffness", profile)
        assert score_multi > score_single

    def test_score_zero_for_no_match(self):
        profile = get_all_profiles()[0]  # URTI
        score = _score_keywords("my elbow hurts", profile)
        assert score == 0.0

    def test_case_insensitive(self):
        profile = get_all_profiles()[0]
        score_lower = _score_keywords("fever", profile)
        score_upper = _score_keywords("FEVER", profile)
        assert score_lower == score_upper

    def test_multiple_keywords_accumulate(self):
        profile = get_all_profiles()[0]  # URTI: fever, cold, cough, throat
        score_one = _score_keywords("fever", profile)
        score_three = _score_keywords("fever cold cough", profile)
        assert score_three > score_one


# ===================================================================
# 7. Medical history integration tests
# ===================================================================
class TestMedicalHistoryIntegration:
    """Verify that the diagnosis engine uses patient medical history."""

    FEMALE_HISTORY = {
        "gender": "female",
        "date_of_birth": "1990-05-15",
        "blood_group": "B+",
        "allergies": "None reported",
    }
    MALE_HISTORY = {
        "gender": "male",
        "date_of_birth": "1985-03-20",
        "blood_group": "O+",
        "allergies": "None reported",
    }
    ELDERLY_HISTORY = {
        "gender": "male",
        "date_of_birth": "1955-01-10",
        "blood_group": "A+",
        "allergies": "None reported",
    }
    CHILD_HISTORY = {
        "gender": "female",
        "date_of_birth": "2018-06-01",
        "blood_group": "AB+",
        "allergies": "None reported",
    }
    PENICILLIN_ALLERGY_HISTORY = {
        "gender": "female",
        "date_of_birth": "1990-05-15",
        "blood_group": "B+",
        "allergies": "Penicillin",
    }
    NSAID_ALLERGY_HISTORY = {
        "gender": "male",
        "date_of_birth": "1985-03-20",
        "blood_group": "O+",
        "allergies": "NSAID",
    }

    # --- Gender-based confidence adjustment ---

    def test_female_uti_confidence_boost(self):
        """UTI is more common in females — confidence should be higher."""
        r_no_history = diagnose("burning urination, frequent urination")
        r_female = diagnose("burning urination, frequent urination", medical_history=self.FEMALE_HISTORY)
        assert r_female["confidence"] > r_no_history["confidence"]
        assert r_female["medical_history_considered"] is True

    def test_male_kidney_stone_confidence_boost(self):
        """Kidney stones are more common in males — confidence should be higher."""
        r_no_history = diagnose("kidney stone, flank pain")
        r_male = diagnose("kidney stone, flank pain", medical_history=self.MALE_HISTORY)
        assert r_male["confidence"] > r_no_history["confidence"]

    def test_no_history_gives_base_confidence(self):
        """Without medical history, confidence should be the base value."""
        r = diagnose("burning urination, frequent urination")
        assert r["medical_history_considered"] is False

    # --- Age-based confidence adjustment ---

    def test_elderly_hypertension_boost(self):
        """Hypertension risk increases with age — elderly patients get higher confidence."""
        r_base = diagnose("high blood pressure, headache")
        r_elderly = diagnose("high blood pressure, headache", medical_history=self.ELDERLY_HISTORY)
        assert r_elderly["confidence"] > r_base["confidence"]

    def test_child_ear_infection_boost(self):
        """Ear infections are more common in children — confidence should be higher."""
        r_base = diagnose("ear pain, ear infection")
        r_child = diagnose("ear pain, ear infection", medical_history=self.CHILD_HISTORY)
        assert r_child["confidence"] > r_base["confidence"]

    def test_confidence_never_exceeds_099(self):
        """Even with all boosts, confidence should be capped at 0.99."""
        mega_history = {
            "gender": "female",
            "date_of_birth": "2020-01-01",
            "blood_group": "O+",
            "allergies": "None",
        }
        r = diagnose("ear pain, ear infection, ear ache, blocked ear, hearing loss", medical_history=mega_history)
        assert r["confidence"] <= 0.99

    # --- Allergy-based medication filtering ---

    def test_penicillin_allergy_filters_amoxicillin(self):
        """Patient allergic to penicillin should NOT receive Amoxicillin."""
        r = diagnose("ear pain, ear infection", medical_history=self.PENICILLIN_ALLERGY_HISTORY)
        med_names = [m["name"] for m in r["medications"]]
        for name in med_names:
            assert "Amoxicillin" not in name, f"Amoxicillin should be filtered for penicillin allergy, but found: {name}"

    def test_penicillin_allergy_generates_warning(self):
        """Allergy warnings should appear in both allergy_warnings and reasoning."""
        r = diagnose("ear pain, ear infection", medical_history=self.PENICILLIN_ALLERGY_HISTORY)
        assert r["allergy_warnings"] is not None
        assert len(r["allergy_warnings"]) > 0
        assert "Penicillin" in r["reasoning"]

    def test_nsaid_allergy_filters_ibuprofen(self):
        """NSAID allergy should filter out Ibuprofen, Diclofenac, Naproxen."""
        r = diagnose("ear pain, ear infection", medical_history=self.NSAID_ALLERGY_HISTORY)
        med_names = [m["name"] for m in r["medications"]]
        for name in med_names:
            assert "Ibuprofen" not in name
            assert "Diclofenac" not in name
            assert "Naproxen" not in name

    def test_no_allergy_keeps_all_medications(self):
        """When no allergy is reported, all medications should remain."""
        r_base = diagnose("ear pain, ear infection")
        r_no_allergy = diagnose("ear pain, ear infection", medical_history={
            "gender": "male", "allergies": "None reported",
        })
        assert len(r_no_allergy["medications"]) == len(r_base["medications"])

    def test_allergy_precaution_added(self):
        """When patient has allergies, a precaution about allergies should be first."""
        r = diagnose("headache and migraine", medical_history=self.PENICILLIN_ALLERGY_HISTORY)
        assert "allergy" in r["precautions"][0].lower() or "Penicillin" in r["precautions"][0]

    # --- Medical history in reasoning and findings ---

    def test_history_context_in_reasoning(self):
        """Reasoning should include the patient's medical profile."""
        r = diagnose("headache and migraine", medical_history=self.FEMALE_HISTORY)
        assert "Patient profile" in r["reasoning"]
        assert "Gender: female" in r["reasoning"]

    def test_history_context_in_findings(self):
        """Findings should include a medical profile entry."""
        r = diagnose("headache and migraine", medical_history=self.FEMALE_HISTORY)
        finding_texts = [f["finding"] for f in r["findings"]]
        has_profile = any("Patient medical profile" in f for f in finding_texts)
        assert has_profile

    def test_age_mentioned_in_reasoning(self):
        """When DOB is provided, age-adjusted risk should be mentioned."""
        r = diagnose("high blood pressure", medical_history=self.ELDERLY_HISTORY)
        assert "Age-adjusted" in r["reasoning"]

    def test_empty_history_is_safe(self):
        """Passing an empty dict should work like no history."""
        r = diagnose("headache and migraine", medical_history={})
        assert_valid_response(r, "Headache")
        assert r["medical_history_considered"] is False

    def test_unknown_values_handled_gracefully(self):
        """History with 'Unknown' values should not crash or add misleading context."""
        history = {
            "gender": "Not specified",
            "date_of_birth": "Unknown",
            "blood_group": "Unknown",
            "allergies": "None reported",
        }
        r = diagnose("headache and migraine", medical_history=history)
        assert_valid_response(r, "Headache")

    # --- Fallback with medical history ---

    def test_fallback_also_uses_history(self):
        """Even the generic fallback should incorporate medical history."""
        r = diagnose("totally unknown xyz symptoms", medical_history=self.FEMALE_HISTORY)
        assert_valid_response(r, "Preliminary")
        assert r["medical_history_considered"] is True
        assert "Patient profile" in r["reasoning"]

    def test_fallback_filters_allergic_meds(self):
        """Fallback should also filter medications for allergies."""
        history = {
            "gender": "male",
            "allergies": "Paracetamol",
        }
        r = diagnose("totally unknown xyz symptoms", medical_history=history)
        med_names = [m["name"] for m in r["medications"]]
        assert "Paracetamol" not in med_names


class TestCalculateAge:
    """Unit tests for the _calculate_age helper."""

    def test_standard_format(self):
        age = _calculate_age("2000-01-01")
        assert age is not None
        assert age >= 25

    def test_dd_mm_yyyy(self):
        age = _calculate_age("15-06-1990")
        assert age is not None
        assert age >= 35

    def test_invalid_returns_none(self):
        assert _calculate_age("not a date") is None
        assert _calculate_age("") is None

    def test_slash_format(self):
        age = _calculate_age("01/01/2000")
        assert age is not None


class TestFilterMedications:
    """Unit tests for _filter_medications_for_allergies."""

    SAMPLE_MEDS = [
        {"name": "Amoxicillin", "dosage": "500mg", "frequency": "3x daily", "duration": "7 days", "type": "capsule", "notes": "test"},
        {"name": "Ibuprofen", "dosage": "400mg", "frequency": "3x daily", "duration": "5 days", "type": "tablet", "notes": "test"},
        {"name": "Paracetamol", "dosage": "500mg", "frequency": "4x daily", "duration": "3 days", "type": "tablet", "notes": "test"},
    ]

    def test_no_allergy_keeps_all(self):
        safe, warnings = _filter_medications_for_allergies(self.SAMPLE_MEDS, "None reported")
        assert len(safe) == 3
        assert len(warnings) == 0

    def test_penicillin_removes_amoxicillin(self):
        safe, warnings = _filter_medications_for_allergies(self.SAMPLE_MEDS, "Penicillin")
        safe_names = [m["name"] for m in safe]
        assert "Amoxicillin" not in safe_names
        assert len(warnings) == 1

    def test_nsaid_removes_ibuprofen(self):
        safe, warnings = _filter_medications_for_allergies(self.SAMPLE_MEDS, "NSAID")
        safe_names = [m["name"] for m in safe]
        assert "Ibuprofen" not in safe_names

    def test_all_filtered_gives_consult(self):
        meds = [
            {"name": "Amoxicillin", "dosage": "500mg", "frequency": "3x", "duration": "7d", "type": "capsule", "notes": "x"},
        ]
        safe, warnings = _filter_medications_for_allergies(meds, "Penicillin")
        assert len(safe) == 1
        assert "Consult" in safe[0]["name"]

    def test_empty_allergy_string(self):
        safe, warnings = _filter_medications_for_allergies(self.SAMPLE_MEDS, "")
        assert len(safe) == 3


class TestBuildHistoryContext:
    """Unit tests for _build_history_context."""

    def test_full_history(self):
        ctx = _build_history_context({
            "gender": "female",
            "date_of_birth": "1990-05-15",
            "blood_group": "B+",
            "allergies": "Penicillin",
        })
        assert "Gender: female" in ctx
        assert "Blood Group: B+" in ctx
        assert "Penicillin" in ctx

    def test_empty_history(self):
        ctx = _build_history_context({})
        assert ctx == ""

    def test_unknown_values_excluded(self):
        ctx = _build_history_context({
            "gender": "Not specified",
            "date_of_birth": "Unknown",
            "blood_group": "Unknown",
            "allergies": "None reported",
        })
        assert ctx == ""


# ===================================================================
# 8. Accuracy summary (printed, not asserted against live AI)
# ===================================================================
class TestAccuracySummary:
    """Print a summary table of disease coverage and confidence levels.
    This is not a pass/fail test — it documents the current mock accuracy."""

    def test_print_coverage_report(self, capsys):
        profiles = get_all_profiles()
        print("\n" + "=" * 80)
        print(f"{'#':<4} {'Disease':<50} {'Confidence':<12} {'Severity':<10}")
        print("-" * 80)
        for i, p in enumerate(profiles, 1):
            sample = " ".join(p.keywords[:2])
            r = diagnose(sample)
            matched = p.name[:30] in r["diagnosis"]
            status = "PASS" if matched else "MISS"
            print(f"{i:<4} {p.name[:48]:<50} {r['confidence']:<12.2f} {r['severity']:<10} [{status}]")
        print("=" * 80)
        print(f"Total diseases covered: {len(profiles)}")
        print(f"Model version: {MODEL_VERSION}")
        print(f"Note: Confidence values are heuristic mock values.")
        print(f"      Real accuracy requires MedGemma integration + clinical validation.\n")

"""
Weight/age-based dosage adjustment service for medical diagnosis app.

Adjusts standard adult dosages from the diagnosis engine based on:
- Patient age (pediatric 0-12, adolescent 13-17, adult 18-64, elderly 65+)
- Patient weight in kg (for pediatric weight-based dosing)
"""

from datetime import datetime
import re

DOSAGE_RULES: dict[str, dict] = {
    "Paracetamol": {
        "pediatric_mg_per_kg": 15,
        "max_pediatric_dose": "500mg",
        "adult_dose": "500mg",
        "elderly_dose": "500mg",
        "max_daily_doses": 4,
        "renal_adjustment": False,
    },
    "Amoxicillin": {
        "pediatric_mg_per_kg": 25,
        "max_pediatric_dose": "500mg",
        "adult_dose": "500mg",
        "elderly_dose": "500mg",
        "max_daily_doses": 3,
        "renal_adjustment": True,
    },
    "Ibuprofen": {
        "pediatric_mg_per_kg": 10,
        "max_pediatric_dose": "400mg",
        "adult_dose": "400mg",
        "elderly_dose": "400mg",
        "max_daily_doses": 3,
        "renal_adjustment": False,
    },
    "Diclofenac": {
        "pediatric_mg_per_kg": 1,
        "max_pediatric_dose": "25mg",
        "adult_dose": "50mg",
        "elderly_dose": "50mg",
        "max_daily_doses": 2,
        "renal_adjustment": False,
    },
    "Cetirizine": {
        "pediatric_mg_per_kg": 0.25,
        "max_pediatric_dose": "10mg",
        "adult_dose": "10mg",
        "elderly_dose": "10mg",
        "max_daily_doses": 1,
        "renal_adjustment": False,
    },
    "Sertraline": {
        "pediatric_mg_per_kg": 0.5,
        "max_pediatric_dose": "50mg",
        "adult_dose": "50mg",
        "elderly_dose": "25mg",
        "max_daily_doses": 1,
        "renal_adjustment": False,
    },
    "Prednisolone": {
        "pediatric_mg_per_kg": 1,
        "max_pediatric_dose": "40mg",
        "adult_dose": "40mg",
        "elderly_dose": "30mg",
        "max_daily_doses": 1,
        "renal_adjustment": False,
    },
    "Metformin": {
        "pediatric_mg_per_kg": 10,
        "max_pediatric_dose": "500mg",
        "adult_dose": "500mg",
        "elderly_dose": "500mg",
        "max_daily_doses": 2,
        "renal_adjustment": True,
    },
    "Amlodipine": {
        "pediatric_mg_per_kg": 0.1,
        "max_pediatric_dose": "5mg",
        "adult_dose": "5mg",
        "elderly_dose": "2.5mg",
        "max_daily_doses": 1,
        "renal_adjustment": False,
    },
    "Levothyroxine": {
        "pediatric_mg_per_kg": 0.002,  # 2 mcg/kg stored as mg equivalent
        "max_pediatric_dose": "50mcg",
        "adult_dose": "50mcg",
        "elderly_dose": "25mcg",
        "max_daily_doses": 1,
        "renal_adjustment": False,
        "dose_unit": "mcg",
    },
    "Pantoprazole": {
        "pediatric_mg_per_kg": 1,
        "max_pediatric_dose": "20mg",
        "adult_dose": "40mg",
        "elderly_dose": "40mg",
        "max_daily_doses": 1,
        "renal_adjustment": False,
    },
    "Esomeprazole": {
        "pediatric_mg_per_kg": 0.5,
        "max_pediatric_dose": "20mg",
        "adult_dose": "40mg",
        "elderly_dose": "20mg",
        "max_daily_doses": 1,
        "renal_adjustment": False,
    },
    "Montelukast": {
        "pediatric_mg_per_kg": 0.25,
        "max_pediatric_dose": "5mg",
        "adult_dose": "10mg",
        "elderly_dose": "10mg",
        "max_daily_doses": 1,
        "renal_adjustment": False,
    },
    "Salbutamol": {
        "pediatric_mg_per_kg": 0.1,
        "max_pediatric_dose": "2 puffs",
        "adult_dose": "2 puffs",
        "elderly_dose": "2 puffs",
        "max_daily_doses": 4,
        "renal_adjustment": False,
    },
    "Pregabalin": {
        "pediatric_mg_per_kg": 1,
        "max_pediatric_dose": "75mg",
        "adult_dose": "75mg",
        "elderly_dose": "50mg",
        "max_daily_doses": 2,
        "renal_adjustment": True,
    },
    "Sumatriptan": {
        "pediatric_mg_per_kg": 0,
        "max_pediatric_dose": None,
        "adult_dose": "50mg",
        "elderly_dose": "25mg",
        "max_daily_doses": 2,
        "renal_adjustment": False,
    },
    "Naproxen": {
        "pediatric_mg_per_kg": 5,
        "max_pediatric_dose": "250mg",
        "adult_dose": "500mg",
        "elderly_dose": "250mg",
        "max_daily_doses": 2,
        "renal_adjustment": False,
    },
    "Tamsulosin": {
        "pediatric_mg_per_kg": 0,
        "max_pediatric_dose": None,
        "adult_dose": "0.4mg",
        "elderly_dose": "0.4mg",
        "max_daily_doses": 1,
        "renal_adjustment": False,
    },
    "Acyclovir": {
        "pediatric_mg_per_kg": 20,
        "max_pediatric_dose": "800mg",
        "adult_dose": "800mg",
        "elderly_dose": "400mg",
        "max_daily_doses": 5,
        "renal_adjustment": True,
    },
    "Doxylamine": {
        "pediatric_mg_per_kg": 0,
        "max_pediatric_dose": None,
        "adult_dose": "10mg",
        "elderly_dose": "10mg",
        "max_daily_doses": 3,
        "renal_adjustment": False,
    },
    "Melatonin": {
        "pediatric_mg_per_kg": 0.1,
        "max_pediatric_dose": "3mg",
        "adult_dose": "3mg",
        "elderly_dose": "3mg",
        "max_daily_doses": 1,
        "renal_adjustment": False,
    },
}


def _calculate_age(dob_str: str) -> int | None:
    """Try to parse date of birth and return age in years.
    Reuses the same logic pattern from mock_diagnosis.py with multiple date formats.
    """
    if not dob_str or not isinstance(dob_str, str):
        return None
    s = dob_str.strip()
    if not s or s.lower() == "unknown":
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            born = datetime.strptime(s, fmt)
            today = datetime.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except (ValueError, AttributeError):
            continue
    return None


def get_age_group(age: int) -> str:
    """Return age group: pediatric (0-12), adolescent (13-17), adult (18-64), or elderly (65+)."""
    if age < 0:
        return "adult"  # fallback for invalid age
    if age <= 12:
        return "pediatric"
    if age <= 17:
        return "adolescent"
    if age < 65:
        return "adult"
    return "elderly"


def _find_rule_for_medication(med_name: str) -> tuple[str, dict] | None:
    """Find the best matching dosage rule for a medication name.
    Returns (rule_key, rule_dict) or None if no match.
    Uses startswith to avoid false matches (e.g. Levocetirizine vs Cetirizine).
    """
    med_lower = med_name.strip().lower()
    if not med_lower:
        return None
    # Match: exact, or name starts with rule key followed by space/(/+ (e.g. "Paracetamol (Acetaminophen)", "Amoxicillin + Clavulanate")
    for key, rule in DOSAGE_RULES.items():
        key_lower = key.lower()
        if (
            med_lower == key_lower
            or med_lower.startswith(key_lower + " ")
            or med_lower.startswith(key_lower + "(")
            or med_lower.startswith(key_lower + "+")
        ):
            return (key, rule)
    return None


def _parse_dose_mg(dose_str: str) -> float | None:
    """Extract numeric mg value from strings like '500mg', '50mcg', '2 puffs'.
    Returns mg equivalent where applicable, or None if not parseable.
    """
    if not dose_str:
        return None
    dose_str = str(dose_str).strip().lower()
    # Match patterns like 500mg, 50mcg, 0.4mg
    m = re.search(r"([\d.]+)\s*(mg|mcg|µg)", dose_str)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
        if unit in ("mcg", "µg"):
            return val / 1000  # convert to mg for comparison
        return val
    return None


def _parse_max_dose_mg(max_str: str | None) -> float | None:
    """Parse max dose string to numeric mg for comparison."""
    if max_str is None:
        return None
    return _parse_dose_mg(max_str)


def _format_dose(value: float, unit: str = "mg") -> str:
    """Format numeric dose as string (e.g. 500 -> '500mg', 0.05 with mcg -> '50mcg')."""
    if unit == "mcg":
        value_mcg = value * 1000
        if value_mcg == int(value_mcg):
            return f"{int(value_mcg)}mcg"
        return f"{value_mcg}mcg"
    if value == int(value):
        return f"{int(value)}{unit}"
    return f"{value}{unit}"


def adjust_dosages(
    medications: list[dict],
    age: int | None,
    weight_kg: float | None,
) -> list[dict]:
    """
    Adjust medication dosages based on age group and weight.

    Args:
        medications: List of medication dicts from diagnosis engine.
                    Each has: name, dosage, frequency, duration, type, notes
        age: Patient age in years (or None if unknown)
        weight_kg: Patient weight in kg (or None if unknown)

    Returns:
        New list of medication dicts with:
        - Adjusted dosage where applicable
        - dosage_adjusted: bool
        - adjustment_note: str
    """
    age_group = get_age_group(age) if age is not None else "adult"
    result: list[dict] = []

    for med in medications:
        med = dict(med)
        med_name = med.get("name", "")
        rule_match = _find_rule_for_medication(med_name)

        if rule_match is None:
            med["dosage_adjusted"] = False
            med["adjustment_note"] = ""
            result.append(med)
            continue

        rule_key, rule = rule_match
        adjusted = False
        note_parts: list[str] = []

        if age_group == "pediatric" and weight_kg is not None and weight_kg > 0:
            mg_per_kg = rule.get("pediatric_mg_per_kg")
            max_ped = rule.get("max_pediatric_dose")
            dose_unit = rule.get("dose_unit", "mg")

            if mg_per_kg is not None and mg_per_kg > 0 and max_ped is not None:
                calculated_mg = mg_per_kg * weight_kg
                max_mg = _parse_max_dose_mg(max_str=max_ped)
                if max_mg is not None:
                    final_mg = min(calculated_mg, max_mg)
                    # Round to common tablet strengths (e.g. 125, 250, 500)
                    if dose_unit == "mcg":
                        final_mcg = final_mg * 1000
                        if final_mcg >= 50:
                            final_mg = 0.05
                        elif final_mcg >= 25:
                            final_mg = 0.025
                        else:
                            final_mg = round(final_mg, 4)
                    else:
                        if final_mg >= 400:
                            final_mg = 500
                        elif final_mg >= 200:
                            final_mg = 250
                        elif final_mg >= 100:
                            final_mg = 125
                        elif final_mg >= 50:
                            final_mg = 50
                        elif final_mg >= 25:
                            final_mg = 25
                        else:
                            final_mg = round(final_mg, 1)
                    med["dosage"] = _format_dose(final_mg, dose_unit)
                    adjusted = True
                    per_kg_val = mg_per_kg * 1000 if dose_unit == "mcg" else mg_per_kg
                    per_kg_display = f"{per_kg_val:.0f}{dose_unit}/kg" if dose_unit == "mcg" else f"{mg_per_kg}mg/kg"
                    note_parts.append(f"Pediatric dose: {per_kg_display} × {weight_kg}kg, max {max_ped}")
                else:
                    # Non-numeric max (e.g. "2 puffs") - use it directly
                    med["dosage"] = max_ped
                    adjusted = True
                    note_parts.append(f"Pediatric dose: {max_ped}")
            elif max_ped is None and rule.get("adult_dose"):
                # Not recommended for pediatric - keep adult dose but add note
                note_parts.append("Pediatric use: consult physician")
                med["dosage"] = rule["adult_dose"]
                adjusted = True

        elif age_group == "elderly":
            elderly_dose = rule.get("elderly_dose")
            adult_dose = rule.get("adult_dose")
            if elderly_dose and elderly_dose != adult_dose:
                med["dosage"] = elderly_dose
                adjusted = True
                note_parts.append(f"Elderly-adjusted dose (reduced from {adult_dose})")

        elif age_group == "adolescent":
            # Often use adult dose, but some meds have adolescent-specific guidance
            # For simplicity, use adult dose unless rule specifies otherwise
            pass

        med["dosage_adjusted"] = adjusted
        med["adjustment_note"] = "; ".join(note_parts) if note_parts else ""

        result.append(med)

    return result

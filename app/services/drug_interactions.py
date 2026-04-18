"""
Drug interaction checking service for medical diagnosis app.

Provides functions to check for dangerous drug-drug interactions between
new prescriptions, existing medications, and within a single prescription.
Uses a comprehensive database of known interactions with real medical data.
"""

import re
from typing import Literal

Severity = Literal["critical", "major", "moderate", "minor"]

# Module-level constant: list of (drug_a, drug_b, severity, description)
# Drug names are normalized for matching; variations are handled by normalize_drug_name()
INTERACTIONS: list[tuple[str, str, Severity, str]] = [
    # Anticoagulants + NSAIDs/Aspirin
    ("Warfarin", "Aspirin", "critical", "Increased bleeding risk; both inhibit platelet function and Warfarin prolongs clotting. Risk of GI bleeding and hemorrhagic stroke."),
    ("Warfarin", "Ibuprofen", "critical", "Increased bleeding risk; NSAIDs inhibit platelet function and can cause GI ulceration. Warfarin metabolism may be affected."),
    ("Warfarin", "Diclofenac", "critical", "Increased bleeding risk; NSAIDs increase anticoagulant effect and GI bleeding risk."),
    ("Warfarin", "Naproxen", "critical", "Increased bleeding risk; NSAIDs potentiate anticoagulant effect and cause GI irritation."),
    ("Warfarin", "NSAIDs", "critical", "Increased bleeding risk; avoid combination. Use paracetamol for pain relief when on Warfarin."),
    # SSRIs + NSAIDs
    ("Sertraline", "Ibuprofen", "major", "Increased risk of GI bleeding; SSRIs impair platelet serotonin uptake. Avoid or use with gastroprotection."),
    ("Sertraline", "Aspirin", "major", "Increased bleeding risk; additive antiplatelet effects. Monitor for signs of bleeding."),
    ("Sertraline", "Diclofenac", "major", "Increased GI bleeding risk; combination impairs platelet function."),
    ("Escitalopram", "Ibuprofen", "major", "Increased GI bleeding risk; SSRIs and NSAIDs have additive bleeding effects."),
    ("Fluoxetine", "Naproxen", "major", "Increased bleeding risk; monitor for GI symptoms and bruising."),
    # ACE inhibitors + Potassium
    ("Lisinopril", "Potassium", "major", "Risk of hyperkalemia; ACE inhibitors reduce potassium excretion. Can cause dangerous cardiac arrhythmias."),
    ("Enalapril", "Potassium supplements", "major", "Hyperkalemia risk; avoid potassium supplements unless hypokalemia is documented."),
    ("Ramipril", "Potassium Chloride", "major", "Severe hyperkalemia possible; monitor serum potassium if combination is necessary."),
    ("ACE inhibitors", "Potassium", "major", "Hyperkalemia; ACE inhibitors impair renal potassium excretion."),
    # Metformin + Alcohol
    ("Metformin", "Alcohol", "major", "Increased risk of lactic acidosis; alcohol potentiates metformin's effect. Avoid heavy alcohol use."),
    # Beta-blockers + Calcium channel blockers
    ("Atenolol", "Verapamil", "major", "Additive bradycardia and heart block; risk of hypotension and heart failure exacerbation."),
    ("Metoprolol", "Diltiazem", "major", "Enhanced negative chronotropic and inotropic effects; monitor heart rate and BP closely."),
    ("Propranolol", "Verapamil", "critical", "Severe bradycardia, heart block, and hypotension possible. Generally avoid combination."),
    ("Beta-blockers", "Calcium channel blockers", "major", "Additive cardiac depression; use with caution, monitor closely."),
    # Antibiotics + Anticoagulants
    ("Amoxicillin", "Warfarin", "moderate", "Broad-spectrum antibiotics may alter gut flora and affect vitamin K production; may increase INR."),
    ("Amoxicillin + Clavulanate", "Warfarin", "moderate", "Antibiotics can disrupt vitamin K-producing bacteria; monitor INR more frequently."),
    ("Clarithromycin", "Warfarin", "major", "Clarithromycin inhibits CYP3A4; may significantly increase Warfarin levels and bleeding risk. Monitor INR closely."),
    # Levothyroxine + Calcium/Iron
    ("Levothyroxine", "Calcium", "major", "Calcium and calcium carbonate reduce levothyroxine absorption. Separate by at least 4 hours."),
    ("Levothyroxine", "Calcium Carbonate", "major", "Calcium carbonate significantly reduces thyroid hormone absorption. Take 4 hours apart."),
    ("Levothyroxine", "Iron", "major", "Iron supplements reduce levothyroxine absorption. Take at least 4 hours apart."),
    ("Levothyroxine", "Ferrous Sulfate", "major", "Iron supplements impair absorption; separate dosing by 4 hours minimum."),
    # PPIs + Clopidogrel
    ("Esomeprazole", "Clopidogrel", "major", "PPIs reduce activation of clopidogrel via CYP2C19 inhibition; may reduce antiplatelet efficacy."),
    ("Omeprazole", "Clopidogrel", "major", "Omeprazole inhibits CYP2C19; reduces clopidogrel conversion to active metabolite. Consider pantoprazole."),
    ("Pantoprazole", "Clopidogrel", "moderate", "Less CYP2C19 inhibition than omeprazole; preferred PPI if gastroprotection needed with clopidogrel."),
    # Pregabalin + CNS depressants
    ("Pregabalin", "Lorazepam", "major", "Additive CNS depression; increased risk of sedation, dizziness, and respiratory depression."),
    ("Pregabalin", "Diazepam", "major", "Enhanced sedation and risk of falls; avoid alcohol. Use lowest effective doses."),
    ("Pregabalin", "Zolpidem", "major", "Additive CNS depression; increased sedation and impaired coordination."),
    ("Pregabalin", "Alcohol", "major", "Enhanced CNS depression; risk of severe sedation and respiratory depression."),
    ("Pregabalin", "Gabapentin", "moderate", "Both are CNS depressants; additive sedation. Monitor for excessive drowsiness."),
    # Corticosteroids + NSAIDs
    ("Prednisolone", "Ibuprofen", "major", "Increased risk of GI ulceration and bleeding; both can cause gastric mucosal damage."),
    ("Prednisone", "Aspirin", "major", "Increased GI bleeding risk; corticosteroids and NSAIDs impair mucosal healing."),
    ("Dexamethasone", "Diclofenac", "major", "Additive GI toxicity; high risk of peptic ulcer and bleeding."),
    ("Corticosteroids", "NSAIDs", "major", "Significantly increased risk of peptic ulcer disease and GI bleeding."),
    # Additional common interactions
    ("Lithium", "Ibuprofen", "major", "NSAIDs can increase lithium levels; risk of lithium toxicity. Monitor lithium levels."),
    ("Lithium", "Naproxen", "major", "NSAIDs reduce lithium renal clearance; may cause lithium toxicity."),
    ("Methotrexate", "Ibuprofen", "major", "NSAIDs reduce methotrexate clearance; increased toxicity risk. Avoid or monitor closely."),
    ("Methotrexate", "Naproxen", "major", "NSAIDs can elevate methotrexate levels; risk of bone marrow suppression."),
    ("Digoxin", "Amoxicillin", "minor", "Some antibiotics may alter gut flora affecting digoxin absorption; usually minor."),
    ("Digoxin", "Clarithromycin", "major", "Clarithromycin inhibits P-glycoprotein; may increase digoxin levels."),
    ("Tramadol", "Sertraline", "major", "Serotonin syndrome risk; both increase serotonin. Avoid combination."),
    ("Tramadol", "Escitalopram", "major", "Risk of serotonin syndrome; monitor for agitation, hyperthermia, rigidity."),
    ("Warfarin", "Paracetamol", "moderate", "High-dose paracetamol may potentiate Warfarin; use with caution at doses >2g/day."),
    ("Aspirin", "Ibuprofen", "moderate", "Ibuprofen can reduce aspirin's antiplatelet effect if taken before aspirin. Take aspirin 2 hours before ibuprofen."),
    ("Aspirin", "Naproxen", "moderate", "Naproxen may interfere with aspirin's cardioprotective effect."),
    ("Metformin", "Contrast dye", "major", "Risk of lactic acidosis with iodinated contrast; hold metformin before and after imaging."),
    ("Sildenafil", "Nitrates", "critical", "Severe hypotension; never combine. Nitrates include nitroglycerin, isosorbide."),
    ("Rifampicin", "Warfarin", "major", "Rifampicin induces Warfarin metabolism; may decrease anticoagulant effect."),
    ("Fluconazole", "Warfarin", "major", "Fluconazole inhibits Warfarin metabolism; may increase bleeding risk."),
    ("Ciprofloxacin", "Warfarin", "moderate", "Fluoroquinolones may enhance Warfarin effect; monitor INR."),
    ("Trimethoprim", "Warfarin", "moderate", "Trimethoprim may potentiate Warfarin; increased bleeding risk."),
]


def normalize_drug_name(name: str) -> str:
    """
    Normalize drug name for matching against the interaction database.

    Handles variations like:
    - "Amoxicillin + Clavulanate" matches "Amoxicillin + Clavulanate" or "Amoxicillin"
    - "Ferrous Sulfate (Iron)" matches "Iron" or "Ferrous Sulfate"
    - Case insensitivity
    - Extra whitespace and common suffixes
    """
    if not name or not isinstance(name, str):
        return ""
    # Lowercase, strip, collapse whitespace
    s = re.sub(r"\s+", " ", name.strip().lower())
    # Remove common parenthetical suffixes for matching: (Iron), (Vitamin D), etc.
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s).strip()
    # Remove common dosage suffixes: 500mg, 40mg, etc.
    s = re.sub(r"\s*\d+\s*(mg|mcg|g|ml|iu|%)\s*", " ", s).strip()
    return re.sub(r"\s+", " ", s).strip()


def _get_base_drug_name(normalized: str) -> str:
    """
    Extract base drug name for matching. E.g. "amoxicillin + clavulanate" -> "amoxicillin"
    for matching "Amoxicillin" in the database.
    """
    # Split on + and take first part for combination drugs
    parts = re.split(r"\s*\+\s*", normalized)
    return parts[0].strip() if parts else normalized


def _matches_drug(med_normalized: str, db_drug: str) -> bool:
    """Check if normalized medication name matches the database drug name."""
    db_normalized = normalize_drug_name(db_drug)
    med_base = _get_base_drug_name(med_normalized)
    db_base = _get_base_drug_name(db_normalized)


    # Exact match
    if med_normalized == db_normalized:
        return True
    # Base name match (e.g. "amoxicillin" matches "amoxicillin + clavulanate")
    if med_base == db_base:
        return True
    # One contains the other (for "Amoxicillin" matching "Amoxicillin + Clavulanate")
    if med_normalized in db_normalized or db_normalized in med_normalized:
        return True
    # Handle class names (e.g. "NSAIDs" matches "Ibuprofen", "Diclofenac", etc.)
    nsaid_drugs = ["ibuprofen", "diclofenac", "naproxen", "aspirin", "ketoprofen", "meloxicam", "indomethacin"]
    if db_normalized == "nsaids" and med_base in nsaid_drugs:
        return True
    if med_normalized == "nsaids" and db_base in nsaid_drugs:
        return True

    ace_drugs = ["lisinopril", "enalapril", "ramipril", "captopril", "benazepril"]
    if db_normalized == "ace inhibitors" and med_base in ace_drugs:
        return True
    if med_normalized == "ace inhibitors" and db_base in ace_drugs:
        return True

    beta_drugs = ["atenolol", "metoprolol", "propranolol", "bisoprolol", "carvedilol"]
    if db_normalized == "beta-blockers" and med_base in beta_drugs:
        return True
    if med_normalized == "beta-blockers" and db_base in beta_drugs:
        return True

    ccb_drugs = ["verapamil", "diltiazem", "amlodipine", "nifedipine"]
    if db_normalized == "calcium channel blockers" and med_base in ccb_drugs:
        return True
    if med_normalized == "calcium channel blockers" and db_base in ccb_drugs:
        return True

    potassium_drugs = ["potassium", "potassium chloride", "potassium citrate", "potassium supplements"]
    if db_normalized in ["potassium", "potassium supplements", "potassium chloride"] and any(k in med_normalized for k in potassium_drugs):
        return True
    if any(k in db_normalized for k in potassium_drugs) and any(k in med_normalized for k in potassium_drugs):
        return True

    corticosteroid_drugs = ["prednisolone", "prednisone", "dexamethasone", "methylprednisolone", "hydrocortisone"]
    if db_normalized == "corticosteroids" and med_base in corticosteroid_drugs:
        return True
    if med_normalized == "corticosteroids" and db_base in corticosteroid_drugs:
        return True

    return False


def _get_recommendation(severity: Severity, drug_a: str, drug_b: str) -> str:
    """Generate a recommendation based on severity level."""
    recommendations = {
        "critical": f"Avoid combining {drug_a} and {drug_b}. This combination is contraindicated. Consult a physician before prescribing.",
        "major": f"Avoid or use with extreme caution. {drug_a} + {drug_b} carries significant risk. Consider alternatives or close monitoring.",
        "moderate": f"Use with caution. Monitor for adverse effects when combining {drug_a} and {drug_b}. Adjust dosing or timing if needed.",
        "minor": f"Monitor when using {drug_a} with {drug_b}. Minor interaction; may require periodic assessment.",
    }
    return recommendations.get(severity, "Consult a healthcare provider.")


def _check_pair(
    med_a: dict, med_b: dict, seen: set[tuple[str, str]]
) -> list[dict]:
    """Check a single medication pair for interactions. Returns list of warnings."""
    name_a = med_a.get("name", "")
    name_b = med_b.get("name", "")
    if not name_a or not name_b:
        return []

    norm_a = normalize_drug_name(name_a)
    norm_b = normalize_drug_name(name_b)
    if norm_a == norm_b:
        return []

    # Avoid duplicate checks (A-B and B-A)
    pair_key = tuple(sorted([norm_a, norm_b]))
    if pair_key in seen:
        return []
    seen.add(pair_key)

    warnings: list[dict] = []
    for db_a, db_b, severity, description in INTERACTIONS:
        a_matches = _matches_drug(norm_a, db_a) and _matches_drug(norm_b, db_b)
        b_matches = _matches_drug(norm_a, db_b) and _matches_drug(norm_b, db_a)
        if a_matches or b_matches:
            drug_a_display = name_a
            drug_b_display = name_b
            if b_matches:
                drug_a_display, drug_b_display = name_b, name_a
            warnings.append({
                "drug_a": drug_a_display,
                "drug_b": drug_b_display,
                "severity": severity,
                "description": description,
                "recommendation": _get_recommendation(severity, drug_a_display, drug_b_display),
            })
    return warnings


def check_interactions(
    new_medications: list[dict], existing_medications: list[dict]
) -> list[dict]:
    """
    Check for drug-drug interactions between new medications and existing medications.

    Args:
        new_medications: List of dicts with at least "name" key (e.g. from a new prescription)
        existing_medications: List of dicts with at least "name" key (patient's current meds)

    Returns:
        List of interaction warnings, each with: drug_a, drug_b, severity,
        description, recommendation
    """
    all_meds = list(existing_medications) + list(new_medications)
    return check_within_prescription(all_meds)


def check_within_prescription(medications: list[dict]) -> list[dict]:
    """
    Check for interactions within a single set of prescribed medications.

    Use when the AI or prescriber recommends multiple drugs in the same
    prescription (e.g. Aspirin and Ibuprofen together).

    Args:
        medications: List of dicts with at least "name" key

    Returns:
        List of interaction warnings, each with: drug_a, drug_b, severity,
        description, recommendation
    """
    if not medications or len(medications) < 2:
        return []

    warnings: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for i, med_a in enumerate(medications):
        for med_b in medications[i + 1 :]:
            pair_warnings = _check_pair(med_a, med_b, seen)
            warnings.extend(pair_warnings)

    # Sort by severity (critical first, then major, moderate, minor)
    severity_order = {"critical": 0, "major": 1, "moderate": 2, "minor": 3}
    warnings.sort(key=lambda w: severity_order.get(w["severity"], 4))

    return warnings

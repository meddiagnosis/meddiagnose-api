"""
Prescription safety checks for sensitive prescribing.

- Allergy filter: removes medications that match patient allergies (including cross-reactivity)
- Duplicate check: flags same drug or same therapeutic class prescribed twice
- High-risk drug warnings: flags drugs requiring special monitoring
- Pregnancy/clinical context: filters teratogenic drugs when pregnancy is indicated
"""

import re
from typing import Literal

# Allergy token -> drugs to exclude (including cross-reactive drugs)
# Format: lowercase allergy keyword -> list of drug names/patterns to match
ALLERGY_DRUG_MAP: dict[str, list[str]] = {
    "penicillin": [
        "Amoxicillin", "Ampicillin", "Benzylpenicillin", "Penicillin", "Amoxicillin + Clavulanate",
        "Co-amoxiclav", "Augmentin", "Piperacillin", "Flucloxacillin",
    ],
    "sulfa": [
        "Sulfamethoxazole", "Trimethoprim", "Co-trimoxazole", "Sulfadiazine", "Sulfasalazine",
        "Sulfonamide", "Sulfa", "Cotrimoxazole",
    ],
    "sulfonamide": [
        "Sulfamethoxazole", "Trimethoprim", "Co-trimoxazole", "Sulfadiazine", "Sulfasalazine",
    ],
    "aspirin": ["Aspirin", "Acetylsalicylic acid"],
    "nsaid": [
        "Ibuprofen", "Diclofenac", "Naproxen", "Aspirin", "Ketoprofen", "Meloxicam",
        "Indomethacin", "Piroxicam", "Celecoxib", "Etoricoxib",
    ],
    "ibuprofen": ["Ibuprofen", "Brufen", "Advil"],
    "diclofenac": ["Diclofenac", "Voltaren", "Voveran"],
    "naproxen": ["Naproxen", "Naprosyn"],
    "codeine": ["Codeine", "Tramadol", "Morphine", "Oxycodone", "Hydrocodone", "Pethidine"],
    "morphine": ["Morphine", "Codeine", "Tramadol", "Oxycodone", "Hydrocodone", "Pethidine"],
    "opioid": ["Morphine", "Codeine", "Tramadol", "Oxycodone", "Hydrocodone", "Pethidine", "Fentanyl"],
    "cephalosporin": [
        "Cephalexin", "Cefuroxime", "Cefixime", "Ceftriaxone", "Cefotaxime", "Cefaclor",
        "Cefadroxil", "Cefpodoxime",
    ],
    "azithromycin": ["Azithromycin", "Azithral"],
    "clarithromycin": ["Clarithromycin"],
    "macrolide": ["Azithromycin", "Clarithromycin", "Erythromycin"],
    "metformin": ["Metformin"],
    "contrast": ["Contrast", "Iodinated contrast"],
}

# Drugs that require special monitoring (add warning to notes)
HIGH_RISK_DRUGS: dict[str, str] = {
    "Warfarin": "Requires INR monitoring. Avoid sudden diet changes. Many drug interactions.",
    "Methotrexate": "Requires regular blood counts and LFT monitoring. Teratogenic — avoid in pregnancy.",
    "Lithium": "Requires serum level monitoring. Narrow therapeutic index.",
    "Digoxin": "Requires serum level monitoring. Risk of toxicity in elderly.",
    "Phenytoin": "Requires serum level monitoring. Teratogenic.",
    "Valproate": "Teratogenic. Requires LFT and platelet monitoring.",
    "Allopurinol": "Risk of severe hypersensitivity (SJS). Start low, increase gradually.",
    "Amiodarone": "Requires thyroid, LFT, and lung monitoring. Long half-life.",
    "Clozapine": "Requires regular CBC (agranulocytosis risk).",
}

# Teratogenic drugs — avoid when pregnancy is indicated
TERATOGENIC_DRUGS: list[str] = [
    "Methotrexate", "Warfarin", "Valproate", "Sodium Valproate", "Phenytoin", "Carbamazepine",
    "Isotretinoin", "Accutane", "Misoprostol", "Ribavirin", "Thalidomide", "Mycophenolate",
    "Leflunomide", "Spironolactone", "Finasteride", "Dutasteride", "Methimazole",
]

# Vital organ impairment: drugs to AVOID (contraindicated) when organ is impaired
# Inferred from clinical context (symptoms + notes)
RENAL_AVOID_DRUGS: list[str] = [
    "Metformin", "Ibuprofen", "Diclofenac", "Naproxen", "Ketorolac",
    "Gentamicin", "Amikacin", "Vancomycin", "Acyclovir", "Valacyclovir",
    "Co-trimoxazole", "Sulfamethoxazole", "Nitrofurantoin", "Colchicine",
    "Allopurinol", "Spironolactone", "Potassium", "Enoxaparin",
]
RENAL_CAUTION_DRUGS: dict[str, str] = {
    "Amoxicillin": "Dose reduction needed in severe renal impairment (eGFR <30).",
    "Ciprofloxacin": "Dose reduction in renal impairment. Avoid if eGFR <30.",
    "Gabapentin": "Dose reduction required. Accumulates in renal failure.",
    "Pregabalin": "Dose reduction in renal impairment. Reduce if eGFR <60.",
    "Ramipril": "Start low, monitor potassium. Contraindicated if eGFR <30.",
    "Lisinopril": "Dose reduction in renal impairment. Monitor K+ and creatinine.",
}

HEPATIC_AVOID_DRUGS: list[str] = [
    "Methotrexate", "Valproate", "Sodium Valproate", "Phenytoin",
    "Atorvastatin", "Simvastatin", "Rosuvastatin", "Lovastatin",
    "Amiodarone", "Rifampicin", "Isoniazid", "Pyrazinamide",
]
HEPATIC_CAUTION_DRUGS: dict[str, str] = {
    "Paracetamol": "Limit to 2g/day in liver disease. Avoid in severe hepatic impairment.",
    "Acetaminophen": "Limit to 2g/day in liver disease. Avoid in severe hepatic impairment.",
    "Metformin": "Avoid in severe liver disease (lactic acidosis risk).",
    "Warfarin": "Enhanced effect in liver disease. Monitor INR closely.",
}

# Heart failure: avoid or use with caution (fluid retention, negative inotrope)
HEART_FAILURE_AVOID_DRUGS: list[str] = [
    "Ibuprofen", "Diclofenac", "Naproxen", "Celecoxib", "Ketorolac",
    "Verapamil", "Diltiazem",  # Non-DHP CCBs — negative inotrope
    "Pioglitazone", "Rosiglitazone",
]

# Asthma/COPD: non-selective beta-blockers can cause bronchospasm
ASTHMA_AVOID_DRUGS: list[str] = [
    "Propranolol", "Timolol", "Nadolol", "Sotalol", "Carvedilol",  # Non-selective
]
ASTHMA_CAUTION_DRUGS: dict[str, str] = {
    "Metoprolol": "Prefer cardioselective (bisoprolol) in asthma. Use lowest dose.",
    "Atenolol": "Cardioselective but can worsen asthma at high doses.",
}

# Breastfeeding: avoid or use with caution (excreted in milk, harmful to infant)
LACTATION_AVOID_DRUGS: list[str] = [
    "Methotrexate", "Cyclophosphamide", "Doxorubicin", "Lithium", "Clozapine",
    "Valproate", "Sodium Valproate", "Phenytoin", "Carbamazepine",
    "Codeine", "Tramadol", "Morphine", "Oxycodone",  # CNS depression in infant
    "Aspirin", "Ciprofloxacin", "Doxycycline", "Metronidazole",
    "Isotretinoin", "Ribavirin", "Gold salts",
]
LACTATION_CAUTION_DRUGS: dict[str, str] = {
    "Paracetamol": "Compatible with breastfeeding at usual doses.",
    "Ibuprofen": "Low levels in milk. Short-term use generally acceptable.",
    "Amoxicillin": "Compatible. Monitor infant for diarrhoea or thrush.",
    "Sertraline": "Preferred SSRI in lactation. Monitor infant for drowsiness.",
}

# Pediatric: Aspirin and Reye's syndrome (children <18 with viral illness)
# Also drugs generally contraindicated in children
PEDIATRIC_AVOID_DRUGS: list[str] = [
    "Aspirin", "Acetylsalicylic acid",  # Reye's syndrome risk
    "Codeine", "Tramadol",  # Respiratory depression in children
    "Promethazine",  # Respiratory depression <2 years
    "Fluoroquinolones", "Ciprofloxacin", "Levofloxacin",  # Cartilage damage
    "Tetracycline", "Doxycycline",  # Tooth discolouration <8 years
]
PEDIATRIC_CAUTION_DRUGS: dict[str, str] = {
    "Ibuprofen": "Avoid in dehydrated children (renal risk).",
    "Dextromethorphan": "Avoid in children <4 years.",
}

# QT prolongation: risk of torsades when combined or in susceptible patients
# Detect from: long qt, qt prolongation, arrhythmia, bradycardia, cardiac
QT_PROLONGING_DRUGS: list[str] = [
    "Erythromycin", "Clarithromycin", "Azithromycin",  # Macrolides
    "Ciprofloxacin", "Levofloxacin", "Moxifloxacin",  # Fluoroquinolones
    "Domperidone", "Metoclopramide", "Ondansetron",
    "Haloperidol", "Quetiapine", "Risperidone", "Chlorpromazine",
    "Amiodarone", "Sotalol", "Flecainide", "Disopyramide",
    "Methadone", "Ondansetron",
]
QT_CAUTION_DRUGS: dict[str, str] = {
    "Azithromycin": "Prolongs QT. Avoid in known long QT or with other QT drugs.",
    "Domperidone": "QT prolongation risk. Avoid in cardiac disease.",
}

# Beers criteria: potentially inappropriate meds in elderly (65+)
BEERS_AVOID_DRUGS: list[str] = [
    "Diphenhydramine", "Chlorpheniramine", "Promethazine", "Doxylamine",
    "Diazepam", "Lorazepam", "Alprazolam", "Clonazepam", "Temazepam",
    "Amitriptyline", "Doxepin", "Oxybutynin", "Tolterodine", "Solifenacin",
    "Cyclobenzaprine", "Methocarbamol", "Carisoprodol", "Orphenadrine",
    "Ketorolac",  # Avoid in elderly (GI bleed, renal)
    "Nitrofurantoin",  # Avoid for long-term suppression in renal impairment
    "Prochlorperazine", "Metoclopramide",  # Extrapyramidal effects
]
BEERS_CAUTION_DRUGS: dict[str, str] = {
    "Warfarin": "High bleeding risk in elderly. Fall risk.",
    "Gabapentin": "Dizziness, fall risk. Start low.",
    "Pregabalin": "Dizziness, sedation. Fall risk in elderly.",
}

# Critical conditions and deadly diseases — require emergency care; some drugs contraindicated
# Keywords in clinical context or diagnosis that indicate life-threatening presentation
CRITICAL_CONDITION_KEYWORDS: list[str] = [
    "sepsis", "septic shock", "septicemia",
    "myocardial infarction", "heart attack", "acute mi", "stemi", "nstemi",
    "stroke", "cva", "hemorrhagic stroke", "ischemic stroke", "brain bleed",
    "meningitis", "encephalitis",
    "pulmonary embolism", "pe", "dvt", "deep vein thrombosis",
    "anaphylaxis", "anaphylactic shock",
    "diabetic ketoacidosis", "dka", "hyperosmolar",
    "gastrointestinal bleed", "gi bleed", "upper gi bleed", "hematemesis", "melena",
    "acute respiratory distress", "ards", "respiratory failure",
    "acute kidney injury", "aki", "acute renal failure",
    "suicide", "overdose", "poisoning",
    "status epilepticus", "seizure", "convulsion",
    "aortic dissection", "ruptured aneurysm",
    "tension pneumothorax", "cardiac tamponade",
    "eclampsia", "pre-eclampsia", "placental abruption",
    "ectopic pregnancy", "ruptured ectopic",
]
# AI severity/urgency that triggers critical warning
CRITICAL_SEVERITY = "critical"
CRITICAL_URGENCY = "emergency"

# Drug-condition contraindications: when critical condition detected, avoid these drugs
# Format: condition_keyword -> (avoid_drugs_list, caution_drugs_dict)
CRITICAL_DRUG_CONTRAINDICATIONS: dict[str, tuple[list[str], dict[str, str]]] = {
    "gi bleed": (
        ["Ibuprofen", "Diclofenac", "Naproxen", "Aspirin", "Ketorolac", "Celecoxib"],
        {"Warfarin": "Contraindicated in active GI bleed. Hold and seek emergency care."},
    ),
    "hemorrhagic stroke": (
        ["Warfarin", "Rivaroxaban", "Apixaban", "Dabigatran", "Heparin", "Enoxaparin", "Aspirin"],
        {"Clopidogrel": "Antiplatelet — avoid in acute hemorrhagic stroke."},
    ),
    "stroke": (
        [],
        {"Warfarin": "Anticoagulation timing depends on stroke type. Emergency evaluation first."},
    ),
    "dka": (
        ["Metformin"],  # Lactic acidosis risk
        {"Insulin": "Requires hospital management. Do not self-treat DKA at home."},
    ),
    "sepsis": (
        [],
        {"Ibuprofen": "May mask fever. Sepsis requires IV antibiotics and hospital care."},
    ),
    "anaphylaxis": (
        [],
        {"Beta-blocker": "Can blunt epinephrine response. Seek immediate epinephrine and ER."},
    ),
    "myocardial infarction": (
        [],
        {"Sildenafil": "Contraindicated with nitrates. MI requires emergency care."},
    ),
}

# Same therapeutic class — avoid prescribing two from same class
DRUG_CLASSES: dict[str, list[str]] = {
    "nsaid": ["Ibuprofen", "Diclofenac", "Naproxen", "Aspirin", "Ketoprofen", "Meloxicam", "Celecoxib"],
    "ppi": ["Omeprazole", "Pantoprazole", "Esomeprazole", "Rabeprazole", "Lansoprazole"],
    "ssri": ["Sertraline", "Escitalopram", "Fluoxetine", "Paroxetine", "Fluvoxamine"],
    "ace_inhibitor": ["Lisinopril", "Enalapril", "Ramipril", "Captopril", "Benazepril"],
    "arb": ["Losartan", "Valsartan", "Telmisartan", "Olmesartan", "Irbesartan"],
    "beta_blocker": ["Atenolol", "Metoprolol", "Propranolol", "Bisoprolol", "Carvedilol"],
    "ccb": ["Amlodipine", "Nifedipine", "Verapamil", "Diltiazem"],
    "statin": ["Atorvastatin", "Simvastatin", "Rosuvastatin", "Lovastatin", "Pravastatin"],
}


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _detect_organ_impairment(clinical_context: str) -> dict[str, bool]:
    """Detect vital organ impairment from clinical context (symptoms + notes)."""
    ctx = (clinical_context or "").lower()
    return {
        "renal": any(
            k in ctx for k in [
                "kidney", "renal", "ckd", "creatinine", "dialysis", "gfr", "egfr",
                "kidney disease", "renal failure", "renal impairment", "nephropathy",
            ]
        ),
        "hepatic": any(
            k in ctx for k in [
                "liver", "hepatic", "cirrhosis", "hepatitis", "jaundice", "alt", "ast",
                "liver disease", "liver failure", "hepatic impairment",
            ]
        ),
        "heart_failure": any(
            k in ctx for k in [
                "heart failure", "chf", "cardiomyopathy", "ef reduced", "ejection fraction",
                "systolic dysfunction", "congestive heart",
            ]
        ),
        "asthma": any(
            k in ctx for k in [
                "asthma", "asthmatic", "bronchospasm", "copd", "chronic obstructive",
            ]
        ),
        "breastfeeding": any(
            k in ctx for k in [
                "breastfeeding", "breast feeding", "lactating", "lactation", "nursing",
            ]
        ),
        "qt_risk": any(
            k in ctx for k in [
                "long qt", "qt prolongation", "arrhythmia", "bradycardia",
                "torsades", "cardiac arrhythmia", "heart rhythm",
            ]
        ),
    }


def _drug_in_list(med_name: str, drug_list: list[str]) -> bool:
    """Check if medication matches any drug in list."""
    med_lower = _normalize(med_name)
    if not med_lower:
        return False
    for drug in drug_list:
        if _normalize(drug) in med_lower or med_lower in _normalize(drug):
            return True
    return False


def _drug_in_dict(med_name: str, drug_dict: dict[str, str]) -> tuple[bool, str | None]:
    """Check if medication matches any drug in dict. Returns (matches, warning)."""
    med_lower = _normalize(med_name)
    if not med_lower:
        return False, None
    for drug, warning in drug_dict.items():
        if _normalize(drug) in med_lower or med_lower in _normalize(drug):
            return True, warning
    return False, None


def filter_organ_impairment(
    medications: list[dict],
    organ_status: dict[str, bool],
) -> tuple[list[dict], list[dict]]:
    """
    Filter or flag drugs based on renal, hepatic, cardiac, and respiratory status.
    Returns (filtered_medications, organ_warnings).
    organ_warnings: list of {organ, drug, action, message}
    """
    if not medications:
        return [], []

    warnings: list[dict] = []
    keep: list[dict] = []

    for med in medications:
        name = med.get("name", "")
        if not name:
            keep.append(med)
            continue

        exclude = False

        # Renal
        if organ_status.get("renal"):
            if _drug_in_list(name, RENAL_AVOID_DRUGS):
                exclude = True
                warnings.append({
                    "organ": "kidney",
                    "drug": name,
                    "action": "excluded",
                    "message": f"⚠ {name} was EXCLUDED — avoid in renal impairment (nephrotoxic or accumulates).",
                })
            else:
                matched, msg = _drug_in_dict(name, RENAL_CAUTION_DRUGS)
                if matched and msg:
                    warnings.append({
                        "organ": "kidney",
                        "drug": name,
                        "action": "caution",
                        "message": f"Kidney: {name} — {msg}",
                    })

        # Hepatic
        if organ_status.get("hepatic") and not exclude:
            if _drug_in_list(name, HEPATIC_AVOID_DRUGS):
                exclude = True
                warnings.append({
                    "organ": "liver",
                    "drug": name,
                    "action": "excluded",
                    "message": f"⚠ {name} was EXCLUDED — avoid in hepatic impairment (hepatotoxic or metabolized by liver).",
                })
            else:
                matched, msg = _drug_in_dict(name, HEPATIC_CAUTION_DRUGS)
                if matched and msg:
                    warnings.append({
                        "organ": "liver",
                        "drug": name,
                        "action": "caution",
                        "message": f"Liver: {name} — {msg}",
                    })

        # Heart failure
        if organ_status.get("heart_failure") and not exclude:
            if _drug_in_list(name, HEART_FAILURE_AVOID_DRUGS):
                exclude = True
                warnings.append({
                    "organ": "heart",
                    "drug": name,
                    "action": "excluded",
                    "message": f"⚠ {name} was EXCLUDED — avoid in heart failure (fluid retention or negative inotrope).",
                })

        # Asthma
        if organ_status.get("asthma") and not exclude:
            if _drug_in_list(name, ASTHMA_AVOID_DRUGS):
                exclude = True
                warnings.append({
                    "organ": "respiratory",
                    "drug": name,
                    "action": "excluded",
                    "message": f"⚠ {name} was EXCLUDED — non-selective beta-blocker can cause bronchospasm in asthma.",
                })
            else:
                matched, msg = _drug_in_dict(name, ASTHMA_CAUTION_DRUGS)
                if matched and msg:
                    warnings.append({
                        "organ": "respiratory",
                        "drug": name,
                        "action": "caution",
                        "message": f"Asthma: {name} — {msg}",
                    })

        # Breastfeeding
        if organ_status.get("breastfeeding") and not exclude:
            if _drug_in_list(name, LACTATION_AVOID_DRUGS):
                exclude = True
                warnings.append({
                    "organ": "breastfeeding",
                    "drug": name,
                    "action": "excluded",
                    "message": f"⚠ {name} was EXCLUDED — avoid in breastfeeding (excreted in milk, harmful to infant).",
                })
            else:
                matched, msg = _drug_in_dict(name, LACTATION_CAUTION_DRUGS)
                if matched and msg:
                    warnings.append({
                        "organ": "breastfeeding",
                        "drug": name,
                        "action": "caution",
                        "message": f"Breastfeeding: {name} — {msg}",
                    })

        # QT prolongation risk
        if organ_status.get("qt_risk") and not exclude:
            if _drug_in_list(name, QT_PROLONGING_DRUGS):
                warnings.append({
                    "organ": "cardiac",
                    "drug": name,
                    "action": "caution",
                    "message": f"QT prolongation: {name} — avoid or use with caution in patients with long QT or arrhythmia.",
                })
            else:
                matched, msg = _drug_in_dict(name, QT_CAUTION_DRUGS)
                if matched and msg:
                    warnings.append({
                        "organ": "cardiac",
                        "drug": name,
                        "action": "caution",
                        "message": f"QT: {name} — {msg}",
                    })

        if not exclude:
            keep.append(med)

    # If all excluded, add placeholder
    if not keep and medications:
        keep.append({
            "name": "Consult Doctor for Organ-Safe Alternatives",
            "dosage": "N/A",
            "frequency": "N/A",
            "when_to_take": "N/A",
            "duration": "N/A",
            "type": "other",
            "notes": "Standard medications are not suitable for your organ function. A physician can recommend dose-adjusted or alternative drugs.",
        })

    return keep, warnings


def _drug_matches_allergy(med_name: str, allergy_tokens: list[str]) -> tuple[bool, str | None]:
    """
    Check if medication matches any allergy. Returns (is_allergic, matched_allergy).
    """
    med_lower = _normalize(med_name)
    if not med_lower:
        return False, None

    for token in allergy_tokens:
        token = token.strip().lower()
        if not token:
            continue
        # Direct token in drug name (e.g. "penicillin" in "Amoxicillin" - no, amoxicillin is penicillin)
        # Check mapped drugs
        drugs = ALLERGY_DRUG_MAP.get(token, [token])  # If no map, use token as drug name
        for drug in drugs:
            if _normalize(drug) in med_lower or med_lower in _normalize(drug):
                return True, token
        # Also check if allergy token appears in drug name (e.g. "sulfa" in "Sulfamethoxazole")
        if token in med_lower:
            return True, token
    return False, None


def filter_allergies(
    medications: list[dict],
    allergies_str: str,
) -> tuple[list[dict], list[str]]:
    """
    Remove medications that match patient allergies (including cross-reactivity).
    Returns (safe_medications, allergy_warnings).
    """
    if not allergies_str or _normalize(allergies_str) in ("none", "none reported", "n/a", ""):
        return list(medications), []

    allergy_tokens = [a.strip() for a in re.split(r"[,;]", allergies_str) if a.strip()]
    safe: list[dict] = []
    warnings: list[str] = []

    for med in medications:
        med_name = med.get("name", "")
        is_allergic, matched = _drug_matches_allergy(med_name, allergy_tokens)
        if is_allergic:
            warnings.append(
                f"⚠ {med_name} was EXCLUDED — patient has reported allergy to '{matched}'. "
                "Inform your doctor about this allergy."
            )
        else:
            safe.append(med)

    if not safe and medications:
        safe.append({
            "name": "Consult Doctor for Safe Alternatives",
            "dosage": "N/A",
            "frequency": "N/A",
            "when_to_take": "N/A",
            "duration": "N/A",
            "type": "other",
            "notes": f"Standard medications conflict with reported allergies ({allergies_str}). "
                     "A physician can recommend safe alternatives.",
        })

    return safe, warnings


def check_duplicate_therapy(medications: list[dict]) -> list[dict]:
    """
    Flag duplicate drugs or two drugs from the same therapeutic class.
    Returns list of warning dicts: {drug_a, drug_b, message, severity}
    """
    if not medications or len(medications) < 2:
        return []

    warnings: list[dict] = []
    names = [m.get("name", "") for m in medications if m.get("name")]

    # Exact duplicate
    seen: set[str] = set()
    for n in names:
        norm = _normalize(n)
        if norm in seen:
            warnings.append({
                "drug_a": n,
                "drug_b": n,
                "message": f"Duplicate: {n} appears more than once.",
                "severity": "major",
            })
        seen.add(norm)

    # Same class
    for class_name, drugs in DRUG_CLASSES.items():
        matches = [n for n in names if any(_normalize(d) in _normalize(n) for d in drugs)]
        if len(matches) >= 2:
            warnings.append({
                "drug_a": matches[0],
                "drug_b": matches[1],
                "message": f"Same drug class: {matches[0]} and {matches[1]} — usually one is sufficient.",
                "severity": "moderate",
            })

    return warnings


def flag_high_risk_drugs(medications: list[dict]) -> list[dict]:
    """
    Add monitoring warnings for high-risk drugs.
    Returns list of {drug, warning} dicts.
    """
    warnings: list[dict] = []
    for med in medications:
        name = med.get("name", "")
        for drug, warning in HIGH_RISK_DRUGS.items():
            if _normalize(drug) in _normalize(name):
                warnings.append({"drug": name, "warning": warning})
                break
    return warnings


def filter_breastfeeding(
    medications: list[dict],
    is_breastfeeding: bool,
) -> tuple[list[dict], list[dict]]:
    """
    When breastfeeding is indicated, exclude or flag drugs.
    Returns (filtered_medications, breastfeeding_warnings).
    """
    if not is_breastfeeding:
        return list(medications), []

    warnings: list[dict] = []
    keep: list[dict] = []

    for med in medications:
        name = med.get("name", "")
        if not name:
            keep.append(med)
            continue
        if _drug_in_list(name, LACTATION_AVOID_DRUGS):
            warnings.append({
                "organ": "breastfeeding",
                "drug": name,
                "action": "excluded",
                "message": f"⚠ {name} was EXCLUDED — avoid in breastfeeding (excreted in milk, harmful to infant).",
            })
        else:
            matched, msg = _drug_in_dict(name, LACTATION_CAUTION_DRUGS)
            if matched and msg:
                warnings.append({
                    "organ": "breastfeeding",
                    "drug": name,
                    "action": "caution",
                    "message": f"Breastfeeding: {name} — {msg}",
                })
            keep.append(med)

    if not keep and medications:
        keep.append({
            "name": "Consult Doctor for Breastfeeding-Safe Alternatives",
            "dosage": "N/A",
            "frequency": "N/A",
            "when_to_take": "N/A",
            "duration": "N/A",
            "type": "other",
            "notes": "Standard medications are not suitable during breastfeeding. A physician can recommend safe alternatives.",
        })

    return keep, warnings


def filter_pediatric(
    medications: list[dict],
    age: int | None,
) -> tuple[list[dict], list[dict]]:
    """
    When age < 18, exclude or flag pediatric-contraindicated drugs.
    Returns (filtered_medications, pediatric_warnings).
    """
    if age is None or age >= 18:
        return list(medications), []

    warnings: list[dict] = []
    keep: list[dict] = []

    for med in medications:
        name = med.get("name", "")
        if not name:
            keep.append(med)
            continue
        if _drug_in_list(name, PEDIATRIC_AVOID_DRUGS):
            warnings.append({
                "organ": "pediatric",
                "drug": name,
                "action": "excluded",
                "message": f"⚠ {name} was EXCLUDED — contraindicated in children (e.g. Reye's, respiratory depression, cartilage/tooth damage).",
            })
        else:
            matched, msg = _drug_in_dict(name, PEDIATRIC_CAUTION_DRUGS)
            if matched and msg:
                warnings.append({
                    "organ": "pediatric",
                    "drug": name,
                    "action": "caution",
                    "message": f"Pediatric: {name} — {msg}",
                })
            keep.append(med)

    if not keep and medications:
        keep.append({
            "name": "Consult Doctor for Pediatric-Safe Alternatives",
            "dosage": "N/A",
            "frequency": "N/A",
            "when_to_take": "N/A",
            "duration": "N/A",
            "type": "other",
            "notes": "Standard medications are not suitable for pediatric use. A physician can recommend age-appropriate alternatives.",
        })

    return keep, warnings


def filter_qt_prolongation(
    medications: list[dict],
    has_qt_risk: bool,
) -> tuple[list[dict], list[dict]]:
    """
    When QT prolongation risk is indicated, exclude or flag QT-prolonging drugs.
    Returns (filtered_medications, qt_warnings).
    """
    if not has_qt_risk:
        return list(medications), []

    warnings: list[dict] = []
    keep: list[dict] = []

    for med in medications:
        name = med.get("name", "")
        if not name:
            keep.append(med)
            continue
        if _drug_in_list(name, QT_PROLONGING_DRUGS):
            warnings.append({
                "organ": "cardiac",
                "drug": name,
                "action": "caution",
                "message": f"QT prolongation: {name} — avoid or use with caution in patients with long QT or arrhythmia.",
            })
        else:
            matched, msg = _drug_in_dict(name, QT_CAUTION_DRUGS)
            if matched and msg:
                warnings.append({
                    "organ": "cardiac",
                    "drug": name,
                    "action": "caution",
                    "message": f"QT: {name} — {msg}",
                })
            keep.append(med)

    return keep, warnings


def filter_beers_elderly(
    medications: list[dict],
    age: int | None,
) -> tuple[list[dict], list[dict]]:
    """
    When age >= 65, flag Beers criteria drugs (potentially inappropriate in elderly).
    Returns (filtered_medications, beers_warnings).
    """
    if age is None or age < 65:
        return list(medications), []

    warnings: list[dict] = []
    keep: list[dict] = []

    for med in medications:
        name = med.get("name", "")
        if not name:
            keep.append(med)
            continue
        if _drug_in_list(name, BEERS_AVOID_DRUGS):
            warnings.append({
                "organ": "elderly",
                "drug": name,
                "action": "caution",
                "message": f"Beers criteria: {name} — potentially inappropriate in elderly (65+). Consider alternatives.",
            })
        else:
            matched, msg = _drug_in_dict(name, BEERS_CAUTION_DRUGS)
            if matched and msg:
                warnings.append({
                    "organ": "elderly",
                    "drug": name,
                    "action": "caution",
                    "message": f"Elderly: {name} — {msg}",
                })
            keep.append(med)

    return keep, warnings


def _detect_critical_condition(
    clinical_context: str | None,
    diagnosis: str | None,
    severity: str | None,
    urgency: str | None,
) -> tuple[bool, list[str]]:
    """
    Detect if presentation suggests critical/life-threatening condition.
    Returns (is_critical, list of matched condition keywords).
    """
    ctx = _normalize(clinical_context or "") + " " + _normalize(diagnosis or "")
    matched: list[str] = []

    for kw in CRITICAL_CONDITION_KEYWORDS:
        if kw in ctx:
            matched.append(kw)

    if (severity or "").lower() == CRITICAL_SEVERITY:
        matched.append("severity:critical")
    if (urgency or "").lower() == CRITICAL_URGENCY:
        matched.append("urgency:emergency")

    return len(matched) > 0, matched


def check_critical_condition_warnings(
    clinical_context: str | None,
    diagnosis: str | None,
    severity: str | None,
    urgency: str | None,
) -> list[dict]:
    """
    Return critical condition warnings when life-threatening presentation detected.
    These are prominent alerts — seek emergency care, do not rely on prescriptions alone.
    """
    is_critical, matched = _detect_critical_condition(
        clinical_context, diagnosis, severity, urgency
    )
    if not is_critical:
        return []

    warnings: list[dict] = []
    warnings.append({
        "organ": "critical",
        "drug": None,
        "action": "alert",
        "message": (
            "🚨 URGENT: This presentation may indicate a life-threatening condition. "
            "Seek immediate medical attention (ER or emergency services). "
            "Do not rely on prescriptions alone — professional evaluation is essential."
        ),
    })
    return warnings


def filter_critical_condition_drugs(
    medications: list[dict],
    matched_conditions: list[str],
) -> tuple[list[dict], list[dict]]:
    """
    When critical condition detected, exclude or flag drugs contraindicated in that condition.
    Returns (filtered_medications, critical_drug_warnings).
    """
    if not matched_conditions:
        return list(medications), []

    # Build avoid/caution sets from all matching conditions
    avoid_drugs: set[str] = set()
    caution_drugs: dict[str, str] = {}

    for cond in matched_conditions:
        # Skip severity/urgency markers
        if cond.startswith("severity:") or cond.startswith("urgency:"):
            continue
        for key, (avoid_list, caution_dict) in CRITICAL_DRUG_CONTRAINDICATIONS.items():
            if key in cond or cond in key:
                avoid_drugs.update(avoid_list)
                caution_drugs.update(caution_dict)

    if not avoid_drugs and not caution_drugs:
        return list(medications), []

    warnings: list[dict] = []
    keep: list[dict] = []

    for med in medications:
        name = med.get("name", "")
        if not name:
            keep.append(med)
            continue

        exclude = False
        if _drug_in_list(name, list(avoid_drugs)):
            exclude = True
            warnings.append({
                "organ": "critical",
                "drug": name,
                "action": "excluded",
                "message": f"⚠ {name} was EXCLUDED — contraindicated in suspected critical condition. Seek emergency care first.",
            })
        else:
            for drug, msg in caution_drugs.items():
                if _normalize(drug) in _normalize(name) or _normalize(name) in _normalize(drug):
                    warnings.append({
                        "organ": "critical",
                        "drug": name,
                        "action": "caution",
                        "message": f"Critical: {name} — {msg}",
                    })
                    break
            keep.append(med)

    if not keep and medications:
        keep.append({
            "name": "Seek Emergency Care — Do Not Self-Medicate",
            "dosage": "N/A",
            "frequency": "N/A",
            "when_to_take": "N/A",
            "duration": "N/A",
            "type": "other",
            "notes": "This presentation requires immediate medical evaluation. Go to the emergency room or call emergency services.",
        })

    return keep, warnings


def filter_teratogenic_for_pregnancy(
    medications: list[dict],
    is_pregnant: bool,
) -> tuple[list[dict], list[str]]:
    """
    When pregnancy is indicated, exclude teratogenic drugs.
    Returns (safe_medications, pregnancy_warnings).
    """
    if not is_pregnant:
        return list(medications), []

    safe: list[dict] = []
    warnings: list[str] = []

    for med in medications:
        med_name = med.get("name", "")
        is_teratogenic = any(
            _normalize(d) in _normalize(med_name) for d in TERATOGENIC_DRUGS
        )
        if is_teratogenic:
            warnings.append(
                f"⚠ {med_name} was EXCLUDED — contraindicated in pregnancy (teratogenic)."
            )
        else:
            safe.append(med)

    return safe, warnings


def apply_prescription_safety(
    medications: list[dict],
    allergies: str | None = None,
    clinical_context: str | None = None,
    age: int | None = None,
    diagnosis: str | None = None,
    severity: str | None = None,
    urgency: str | None = None,
) -> tuple[list[dict], dict]:
    """
    Apply all safety checks and return (safe_medications, safety_result).

    safety_result contains:
    - allergy_warnings: list[str]
    - allergy_filtered: bool
    - duplicate_warnings: list[dict]
    - high_risk_warnings: list[dict]
    - pregnancy_warnings: list[str]
    - organ_warnings: list[dict]  # {organ, drug, action, message} (includes breastfeeding, QT)
    - pediatric_warnings: list[dict]
    - beers_warnings: list[dict]
    - critical_warnings: list[dict]  # Life-threatening condition alerts + drug contraindications
    """
    result: dict = {
        "allergy_warnings": [],
        "allergy_filtered": False,
        "duplicate_warnings": [],
        "high_risk_warnings": [],
        "pregnancy_warnings": [],
        "organ_warnings": [],
        "pediatric_warnings": [],
        "beers_warnings": [],
        "critical_warnings": [],
    }

    if not medications:
        # Still check for critical condition alert (even with no meds)
        is_critical, matched = _detect_critical_condition(
            clinical_context, diagnosis, severity, urgency
        )
        if is_critical:
            result["critical_warnings"] = check_critical_condition_warnings(
                clinical_context, diagnosis, severity, urgency
            )
        return [], result

    meds = list(medications)
    context = (clinical_context or "").lower()

    # 0. Critical condition check (life-threatening) — run first
    is_critical, matched_conditions = _detect_critical_condition(
        clinical_context, diagnosis, severity, urgency
    )
    if is_critical:
        result["critical_warnings"] = check_critical_condition_warnings(
            clinical_context, diagnosis, severity, urgency
        )
        meds, critical_drug_warns = filter_critical_condition_drugs(meds, matched_conditions)
        result["critical_warnings"].extend(critical_drug_warns)

    # 1. Allergy filter
    if allergies:
        meds, allergy_warns = filter_allergies(meds, allergies)
        result["allergy_warnings"] = allergy_warns
        result["allergy_filtered"] = len(allergy_warns) > 0

    # 2. Pregnancy filter (heuristic: "pregnant" or "pregnancy" in context)
    is_pregnant = "pregnant" in context or "pregnancy" in context
    if is_pregnant:
        meds, preg_warns = filter_teratogenic_for_pregnancy(meds, True)
        result["pregnancy_warnings"] = preg_warns

    # 3. Vital organ impairment (renal, hepatic, heart failure, asthma, breastfeeding, QT)
    organ_status = _detect_organ_impairment(clinical_context)
    if any(organ_status.values()):
        meds, organ_warns = filter_organ_impairment(meds, organ_status)
        result["organ_warnings"] = organ_warns

    # 4. Pediatric filter (age < 18)
    if age is not None and age < 18:
        meds, ped_warns = filter_pediatric(meds, age)
        result["pediatric_warnings"] = ped_warns

    # 5. Beers criteria (age >= 65)
    if age is not None and age >= 65:
        _, beers_warns = filter_beers_elderly(meds, age)
        result["beers_warnings"] = beers_warns

    # 6. Duplicate check
    result["duplicate_warnings"] = check_duplicate_therapy(meds)

    # 7. High-risk drug flags
    result["high_risk_warnings"] = flag_high_risk_drugs(meds)

    return meds, result

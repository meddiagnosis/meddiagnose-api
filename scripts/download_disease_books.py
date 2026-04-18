"""
Download disease-specific medical content and save as PDFs.

Sources:
  - wikipedia: Wikipedia medical articles (default)
  - aiims: StatPearls from NCBI (AIIMS-style, used in Indian medical colleges)

Usage:
    cd backend
    python scripts/download_disease_books.py
    python scripts/download_disease_books.py --source aiims -n 40

Output:
    - disease_books/pdf/<disease_slug>.pdf  (or pdf/aiims/ for AIIMS)
    - disease_books/knowledge_index.json    (text chunks for RAG)
"""

from __future__ import annotations

import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Optional deps - wikipedia only needed for --source wikipedia
try:
    import httpx
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

try:
    from fpdf import FPDF
    _FPDF_AVAILABLE = True
except ImportError:
    _FPDF_AVAILABLE = False

NCBI_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
NCBI_BOOKS = "https://www.ncbi.nlm.nih.gov/books"

# Curated StatPearls NBK IDs (NCBI search often returns wrong articles)
# Add more at: https://www.ncbi.nlm.nih.gov/books/ (search "StatPearls <disease>")
DISEASE_NBK_MAP = {
    "Appendicitis": "NBK493193",
    "Acute Coronary Syndrome": "NBK459157",
    "Acute Sinusitis": "NBK547701",
    "Addison Disease": "NBK441994",
    "Addisons Disease": "NBK441994",
    "Alcoholic Hepatitis": "NBK470217",
    "Anaphylaxis": "NBK482124",
    "Achilles Tendinitis": "NBK538149",
    "Acute Liver Failure": "NBK482419",
    "Asthma": "NBK430901",
    "Type 2 Diabetes": "NBK513253",
    "Type 1 Diabetes": "NBK507713",
    "Diabetes": "NBK551501",
    "Gastroenteritis": "NBK518995",
    "Hypertension": "NBK470386",
    "Pneumonia": "NBK525774",
    "Gout": "NBK546606",
    "Osteoarthritis": "NBK482326",
    "Rheumatoid Arthritis": "NBK441999",
    "Arthritis": "NBK518992",
    "Depression": "NBK430847",
    "Anxiety": "NBK470361",
    "Migraine": "NBK560787",
    "Epilepsy": "NBK430749",
    "Tuberculosis": "NBK441916",
    "Malaria": "NBK551711",
    "GERD": "NBK441938",
    "Gastroesophageal Reflux Disease": "NBK441938",
    "Peptic Ulcer Disease": "NBK534792",
    "Chronic Kidney Disease": "NBK535404",
    "Hypothyroidism": "NBK519536",
    "Hyperthyroidism": "NBK537053",
    "Anemia": "NBK499994",
    "COPD": "NBK559281",
    "Heart Failure": "NBK355481",
    "Atrial Fibrillation": "NBK526072",
    "Stroke": "NBK539816",
    "Sepsis": "NBK430939",
    "Cellulitis": "NBK549792",
    "Urinary Tract Infection": "NBK470195",
    "Influenza": "NBK459363",
    "HIV": "NBK534860",
    "Aids": "NBK534860",
    "Lyme Disease": "NBK532914",
    "Schizophrenia": "NBK539864",
    "Bipolar Disorder": "NBK558998",
    "Pancreatitis": "NBK538337",
    "Cholecystitis": "NBK459171",
    "Diverticulitis": "NBK459316",
    "Crohn Disease": "NBK436021",
    "Ulcerative Colitis": "NBK459282",
    "Psoriasis": "NBK448142",
    "Eczema": "NBK538209",
    "Dermatitis": "NBK538209",
    "Lupus": "NBK555841",
    "Systemic Lupus Erythematosus": "NBK555841",
    "Multiple Sclerosis": "NBK499849",
    "Parkinson Disease": "NBK470193",
    "Alzheimers Disease": "NBK499922",
    "Obesity": "NBK459357",
    "Osteoporosis": "NBK441901",
    "Gallstones": "NBK424772",
    "Kidney Stones": "NBK442014",
    "Nephrolithiasis": "NBK442014",
    "Benign Prostatic Hyperplasia": "NBK558920",
    "Prostate Cancer": "NBK470550",
    "Breast Cancer": "NBK482286",
    "Colorectal Cancer": "NBK470268",
    "Lung Cancer": "NBK482357",
    "Leukemia": "NBK560660",
    "Lymphoma": "NBK448192",
    "Melanoma": "NBK470409",
    "Basal Cell Carcinoma": "NBK482439",
    "Squamous Cell Carcinoma": "NBK441939",
    "Cataracts": "NBK539699",
    "Glaucoma": "NBK538217",
    "Macular Degeneration": "NBK558054",
    "Otitis Media": "NBK538293",
    "Tonsillitis": "NBK544342",
    "Pharyngitis": "NBK519478",
    "Bronchitis": "NBK448067",
    "Pulmonary Embolism": "NBK532283",
    "Deep Vein Thrombosis": "NBK507708",
    "Varicose Veins": "NBK448068",
    "Abdominal Aortic Aneurysm": "NBK525944",
    "Peripheral Artery Disease": "NBK430745",
    "Pericarditis": "NBK431080",
    "Myocarditis": "NBK459432",
    "Endocarditis": "NBK499944",
    "Cardiomyopathy": "NBK513315",
    "Congestive Heart Failure": "NBK355481",
    "Vasovagal Syncope": "NBK448060",
    "Acute Respiratory Distress Syndrome": "NBK436002",
    "Acute Kidney Injury": "NBK441835",
    "Sickle Cell Disease": "NBK482384",
    "Thalassemia": "NBK545151",
    "Hemophilia": "NBK551607",
    "Thrombocytopenia": "NBK542208",
    "Cushing Syndrome": "NBK470218",
    "Cushings Disease": "NBK470218",
    "Acromegaly": "NBK431086",
    "Pituitary Adenoma": "NBK554588",
    "Thyroid Cancer": "NBK459376",
    "Thyroiditis": "NBK459499",
    "Vitamin D Deficiency": "NBK532266",
    "Vitamin B12 Deficiency": "NBK441923",
    "Iron Deficiency Anemia": "NBK448065",
    "Pernicious Anemia": "NBK540989",
    "Aplastic Anemia": "NBK534775",
    "Acute Myelogenous Leukemia": "NBK507836",
    "Acute Lymphocytic Leukemia": "NBK459148",
    "Chronic Lymphocytic Leukemia": "NBK535395",
    "Hodgkin Lymphoma": "NBK459387",
    "Non-Hodgkin Lymphoma": "NBK559327",
    "Multiple Myeloma": "NBK534764",
    "Amyloidosis": "NBK470604",
    "Sarcoidosis": "NBK554448",
    "Vasculitis": "NBK459479",
    "Fibromyalgia": "NBK540974",
    "Carpal Tunnel Syndrome": "NBK448179",
    "Plantar Fasciitis": "NBK549793",
    "Ankylosing Spondylitis": "NBK470546",
    "Vitiligo": "NBK559149",
    "Acne": "NBK459173",
    "Herpes Zoster": "NBK441824",
    "Shingles": "NBK441824",
    "Urticaria": "NBK538968",
    "Hives And Angioedema": "NBK538968",
    "Hives": "NBK538968",
    "Contact Dermatitis": "NBK459230",
    "Allergy": "NBK538315",
    "Allergies": "NBK538315",
    "Allergic Rhinitis": "NBK538186",
    "Asthma Attack": "NBK430901",
    "Pneumothorax": "NBK441944",
    "Pleural Effusion": "NBK448189",
    "Sleep Apnea": "NBK459476",
    "Obstructive Sleep Apnea": "NBK459476",
    "GERD": "NBK441938",
    "Gastritis": "NBK544250",
    "Irritable Bowel Syndrome": "NBK534810",
    "IBS": "NBK534810",
    "Celiac Disease": "NBK441900",
    "Clostridium Difficile": "NBK431054",
    "C Diff": "NBK431054",
    "Antibiotic Associated Diarrhea": "NBK431054",
    "Travelers Diarrhea": "NBK431054",
    "Whooping Cough": "NBK519008",
    "Pertussis": "NBK519008",
    "Infectious Mononucleosis": "NBK549783",
    "Mononucleosis": "NBK549783",
    "Pelvic Inflammatory Disease": "NBK499959",
    "PID": "NBK499959",
    "Polycystic Ovary Syndrome": "NBK459289",
    "PCOS": "NBK459289",
    "Amenorrhea": "NBK538020",
    "Yeast Infection": "NBK560624",
    "Candidiasis": "NBK560624",
    "Bacterial Vaginosis": "NBK459216",
    "ADHD": "NBK441838",
    "Adhd": "NBK441838",
    "Adult Adhd": "NBK441838",
    "Autism": "NBK525976",
    "Autism Spectrum Disorder": "NBK525976",
    "PTSD": "NBK559129",
    "Post Traumatic Stress Disorder": "NBK559129",
    "OCD": "NBK553084",
    "Obsessive Compulsive Disorder": "NBK553084",
    "Anorexia Nervosa": "NBK459148",
    "Bulimia Nervosa": "NBK441936",
    "Alcohol Use Disorder": "NBK532284",
    "Alzheimer Disease": "NBK499922",
    "Vascular Dementia": "NBK430817",
    "Traumatic Brain Injury": "NBK459147",
    "Concussion": "NBK459147",
    "Guillain Barre Syndrome": "NBK532254",
    "Guillain-Barré Syndrome": "NBK532254",
    "Myasthenia Gravis": "NBK559166",
    "Amyotrophic Lateral Sclerosis": "NBK556151",
    "ALS": "NBK556151",
    "Cluster Headache": "NBK544231",
    "Tension Headache": "NBK562274",
    "(Vertigo) Paroymsal  Positional Vertigo": "NBK559014",
    "Benign Paroxysmal Positional Vertigo": "NBK559014",
    "BPPV": "NBK559014",
    "Meniere Disease": "NBK544345",
    "Labyrinthitis": "NBK534857",
    "Conjunctivitis": "NBK541034",
    "Diabetic Retinopathy": "NBK554435",
    "Epistaxis": "NBK435997",
    "Nosebleed": "NBK435997",
    "Sinusitis": "NBK547701",
    "Laryngitis": "NBK534871",
    "Achalasia": "NBK441994",
    "Hiatal Hernia": "NBK448189",
    "Celiac Disease": "NBK441900",
    "Clostridium Difficile": "NBK431054",
    "Zika Virus": "NBK431060",
    "Cervical Cancer": "NBK431087",
    "Ectopic Pregnancy": "NBK539816",
    "Preeclampsia": "NBK570611",
    # Additional from id2label
    "Bells Palsy": "NBK482290",
    "Bell Palsy": "NBK482290",
    "Actinic Keratosis": "NBK557830",
    "Blood In Urine": "NBK534213",
    "Hematuria": "NBK534213",
    "Toxoplasmosis": "NBK563286",
    "Trichomoniasis": "NBK534826",
    "Typhoid Fever": "NBK557513",
    "Typhoid": "NBK557513",
    "Bronchial Asthma": "NBK430901",
    "Bronchiolitis": "NBK558968",
    "Bed Sores": "NBK554989",
    "Pressure Ulcer": "NBK554989",
    "Boils And Carbuncles": "NBK513141",
    "Carbuncle": "NBK513141",
    "Botulism": "NBK459273",
    "Bradycardia": "NBK493161",
    "Brain Aneurysm": "NBK441992",
    "Brain Avm": "NBK441994",
    "Arteriovenous Malformation": "NBK441994",
    "Broken Heart Syndrome": "NBK454201",
    "Takotsubo Cardiomyopathy": "NBK454201",
    "Bruxism": "NBK560711",
    "Bulimia": "NBK441936",
    "Burns": "NBK430741",
    "Candidiasis": "NBK560624",
    "Celiac Disease": "NBK441900",
    "Cellulitis": "NBK549792",
    "Chickenpox": "NBK448191",
    "Varicella": "NBK448191",
    "Chronic Fatigue Syndrome": "NBK557676",
    "Cirrhosis": "NBK482419",
    "Conjunctivitis": "NBK541034",
    "Pink Eye": "NBK541034",
    "Constipation": "NBK536949",
    "COPD": "NBK559281",
    "Coronary Artery Disease": "NBK564304",
    "Croup": "NBK431070",
    "Cushing Syndrome": "NBK470218",
    "Cushings Disease": "NBK470218",
    "Cystic Fibrosis": "NBK493206",
    "Dengue": "NBK430732",
    "Dermatitis": "NBK538209",
    "Eczema": "NBK538209",
    "Diarrhea": "NBK448082",
    "Diphtheria": "NBK559015",
    "Dysmenorrhea": "NBK558834",
    "Ear Infection": "NBK538293",
    "Emphysema": "NBK559281",
    "Encephalitis": "NBK470556",
    "Endometriosis": "NBK539044",
    "Epididymitis": "NBK559183",
    "Epilepsy": "NBK430749",
    "Erectile Dysfunction": "NBK562274",
    "Erysipelas": "NBK532247",
    "Fibromyalgia": "NBK540974",
    "Food Allergy": "NBK538526",
    "Folate Deficiency": "NBK535377",
    "Folic Acid Deficiency": "NBK535377",
    "Fracture": "NBK554993",
    "Gallstones": "NBK424772",
    "Cholelithiasis": "NBK424772",
    "Gastritis": "NBK544250",
    "Gastroenteritis": "NBK518995",
    "Viral Gastroenteritis": "NBK518995",
    "GERD": "NBK441938",
    "Gout": "NBK546606",
    "Graves Disease": "NBK537053",
    "Guillain Barre Syndrome": "NBK532254",
    "Guillain-Barré Syndrome": "NBK532254",
    "Hearing Loss": "NBK563267",  # Conductive Hearing Loss
    "Heart Failure": "NBK355481",
    "Heat Stroke": "NBK553239",
    "Heat Exhaustion": "NBK553239",
    "Hemorrhoids": "NBK500009",
    "Hepatitis B": "NBK430545",
    "Hepatitis C": "NBK430545",
    "Herniated Disc": "NBK470542",
    "Herpes Simplex": "NBK554754",
    "Herpes Zoster": "NBK441824",
    "Shingles": "NBK441824",
    "Hives": "NBK538968",
    "Urticaria": "NBK538968",
    "Hives And Angioedema": "NBK538968",
    "Hodgkin Lymphoma": "NBK459387",
    "Hypothyroidism": "NBK519536",
    "Hypoglycemia": "NBK534841",
    "Impetigo": "NBK430974",
    "Influenza": "NBK459363",
    "Flu": "NBK459363",
    "Insomnia": "NBK526136",
    "Iron Deficiency Anemia": "NBK448065",
    "Jaundice": "NBK544252",
    "Kidney Disease": "NBK535404",
    "Kidney Failure": "NBK441835",
    "Kidney Stones": "NBK442014",
    "Lactose Intolerance": "NBK532286",
    "Laryngitis": "NBK534871",
    "Lyme Disease": "NBK532914",
    "Lymphoma": "NBK448192",
    "Malaria": "NBK551711",
    "Measles": "NBK448068",
    "Meningitis": "NBK470360",
    "Menopause": "NBK507826",
    "Migraine": "NBK560787",
    "Mumps": "NBK534785",
    "Myocardial Infarction": "NBK459157",
    "Heart Attack": "NBK459157",
    "Nephrotic Syndrome": "NBK544364",
    "Neuropathy": "NBK542184",
    "Peripheral Neuropathy": "NBK542184",
    "Obesity": "NBK459357",
    "Osteoporosis": "NBK441901",
    "Otitis Media": "NBK538293",
    "Ovarian Cyst": "NBK560817",
    "Pancreatitis": "NBK538337",
    "Acute Pancreatitis": "NBK482468",
    "Chronic Pancreatitis": "NBK482468",
    "Peptic Ulcer": "NBK534792",
    "Peptic Ulcer Disease": "NBK534792",
    "Pericarditis": "NBK431080",
    "Peripheral Artery Disease": "NBK430745",
    "Peritonitis": "NBK459317",
    "Pharyngitis": "NBK519478",
    "Sore Throat": "NBK519478",
    "Pleurisy": "NBK558958",
    "Pneumonia": "NBK525774",
    "Pneumothorax": "NBK441944",
    "Polycystic Kidney Disease": "NBK1246",  # GeneReviews ADPKD
    "Prostatitis": "NBK553176",
    "Psoriasis": "NBK448142",
    "Pulmonary Embolism": "NBK532283",
    "Pyelonephritis": "NBK519537",
    "Rabies": "NBK448076",
    "Restless Leg Syndrome": "NBK558908",
    "Rheumatoid Arthritis": "NBK441999",
    "Rosacea": "NBK557574",
    "Rubella": "NBK507879",  # Congenital Rubella / German Measles
    "Scabies": "NBK544306",
    "Sciatica": "NBK507908",
    "Scoliosis": "NBK493908",
    "Seborrheic Dermatitis": "NBK551831",
    "Sepsis": "NBK430939",
    "Shock": "NBK531492",
    "Sickle Cell Disease": "NBK482384",
    "Sinusitis": "NBK547701",
    "Acute Sinusitis": "NBK547701",
    "Chronic Sinusitis": "NBK547701",
    "Sleep Apnea": "NBK459476",
    "Obstructive Sleep Apnea": "NBK459476",
    "Spinal Stenosis": "NBK441989",
    "Strep Throat": "NBK519478",
    "Stroke": "NBK539816",
    "CVA": "NBK539816",
    "Cerebrovascular Accident": "NBK539816",
    "Syphilis": "NBK534780",
    "Tendinitis": "NBK448194",
    "Tendonitis": "NBK448194",
    "Tetanus": "NBK459474",
    "Thalassemia": "NBK545151",
    "Thrombocytopenia": "NBK542208",
    "Tuberculosis": "NBK441916",
    "Uterine Fibroids": "NBK538273",
    "Leiomyoma": "NBK538273",
    "Uveitis": "NBK540989",
    "Vaginitis": "NBK470361",
    "Vertigo": "NBK532978",
    "Vesicoureteral Reflux": "NBK563262",
    "Vitamin B12 Deficiency": "NBK441923",
    "Vitamin D Deficiency": "NBK532266",
    "Von Willebrand Disease": "NBK459222",
    "Wet Macular Degeneration": "NBK558054",
    "Wilson Disease": "NBK562279",
    "Wilsons Disease": "NBK562279",
    # Additional from id2label (no content / PDF failed)
    "Trichinosis": "NBK536945",
    "Trichotillomania": "NBK493186",
    "Tricuspid Atresia": "NBK554495",
    "Trigeminal Neuralgia": "NBK554486",
    "Trigger Finger": "NBK459310",
    "Truncus Arteriosus": "NBK534774",
    "Tuberous Sclerosis": "NBK538492",
    "Turner Syndrome": "NBK554621",
    "Type 1 Diabetes In Children": "NBK507713",
    "Type 2 Diabetes In Children": "NBK513253",
    "Umbilical Hernia": "NBK459312",
    "Undescended Testicle": "NBK470270",
    "Cryptorchidism": "NBK470270",
    "Ventricular Septal Defect": "NBK470330",
    "Wilms Tumor": "NBK442004",
}


def _extract_statpearls_text(html: str, nbk: str) -> str | None:
    """Extract Introduction or first substantial paragraph from StatPearls HTML."""
    m = re.search(r"<h2[^>]*>Introduction</h2>\s*<p[^>]*>(.*?)</p>", html, re.DOTALL | re.I)
    if m:
        t = re.sub(r"<[^>]+>", " ", m.group(1))
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > 200:
            return f"[AIIMS/StatPearls {nbk}]\n\n{t[:2400]}"
    m = re.search(r"## Introduction\s+(.+?)(?=\n##|\Z)", html, re.DOTALL | re.I)
    if m:
        t = re.sub(r"<[^>]+>", " ", m.group(1))
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > 200:
            return f"[AIIMS/StatPearls {nbk}]\n\n{t[:2400]}"
    for block in re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL):
        t = re.sub(r"<[^>]+>", " ", block).strip()
        t = re.sub(r"\s+", " ", t)
        if len(t) > 250:
            return f"[AIIMS/StatPearls {nbk}]\n\n{t[:2400]}"
    return None


def _fetch_aiims_urllib(disease_name: str) -> str | None:
    """Fetch StatPearls via urllib (fallback when httpx has DNS issues)."""
    import urllib.request
    import urllib.parse
    term = disease_name.replace("(", "").replace(")", "").strip()
    # Try curated NBK map first (more reliable than NCBI search)
    nbk = DISEASE_NBK_MAP.get(disease_name) or DISEASE_NBK_MAP.get(term)
    if nbk:
        try:
            req = urllib.request.Request(
                f"{NCBI_BOOKS}/{nbk}/",
                headers={"User-Agent": "MedDiagnose/1.0 (medical education; +https://github.com/meddiagnose)"},
            )
            with urllib.request.urlopen(req, timeout=45) as r:
                html = r.read().decode()
            return _extract_statpearls_text(html, nbk)
        except Exception:
            pass
    term_enc = urllib.parse.quote(f"statpearls {term}")
    url1 = f"{NCBI_ESEARCH}?db=books&term={term_enc}&retmax=15&retmode=json"
    req_headers = {"User-Agent": "MedDiagnose/1.0 (medical education)"}
    try:
        req = urllib.request.Request(url1, headers=req_headers)
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read().decode())
    except Exception:
        return None
    ids = data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return None
    url2 = f"{NCBI_ESUMMARY}?db=books&id={','.join(ids[:10])}&retmode=json"
    try:
        req = urllib.request.Request(url2, headers=req_headers)
        with urllib.request.urlopen(req, timeout=45) as r:
            result = json.loads(r.read().decode()).get("result", {})
    except Exception:
        return None
    # Prefer chapter with matching title; fallback to first with NBK
    disease_lower = disease_name.lower()
    nbk = None
    for uid in ids:
        if uid not in result or uid == "uids":
            continue
        res = result[uid]
        if res.get("rtype") != "chapter":
            continue
        nbk = res.get("chapteraccessionid") or res.get("accessionid") or res.get("bookaccessionid")
        if nbk and str(nbk).startswith("NBK"):
            title = (res.get("title") or "").lower()
            # Prefer title containing disease keywords
            if any(w in title for w in disease_lower.split() if len(w) > 3):
                break
    if not nbk or not str(nbk).startswith("NBK"):
        nbk = None
        for uid in ids:
            if uid not in result or uid == "uids":
                continue
            res = result[uid]
            nbk = res.get("chapteraccessionid") or res.get("accessionid") or res.get("bookaccessionid")
            if nbk and str(nbk).startswith("NBK"):
                break
    if not nbk:
        return None
    url3 = f"{NCBI_BOOKS}/{nbk}/"
    try:
        req = urllib.request.Request(
            url3,
            headers={"User-Agent": "MedDiagnose/1.0 (medical education; +https://github.com/meddiagnose)"},
        )
        with urllib.request.urlopen(req, timeout=45) as r:
            html = r.read().decode()
    except Exception:
        return None
    return _extract_statpearls_text(html, nbk)


def fetch_aiims_statpearls(disease_name: str, client: httpx.Client | None = None) -> str | None:
    """Fetch StatPearls (AIIMS-style) content from NCBI Bookshelf."""
    term = disease_name.replace("(", "").replace(")", "").strip()
    # Try httpx first
    if client is not None:
        try:
            r = client.get(NCBI_ESEARCH, params={"db": "books", "term": f"statpearls {term}", "retmax": 3, "retmode": "json"}, timeout=15)
            r.raise_for_status()
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return None
            r2 = client.get(NCBI_ESUMMARY, params={"db": "books", "id": ids[0], "retmode": "json"}, timeout=15)
            r2.raise_for_status()
            res = r2.json().get("result", {}).get(ids[0], {})
            nbk = res.get("accessionid") or res.get("bookaccessionid")
            if not nbk or not str(nbk).startswith("NBK"):
                return None
            r3 = client.get(f"{NCBI_BOOKS}/{nbk}/", timeout=30)
            r3.raise_for_status()
            html = r3.text
        except Exception:
            return _fetch_aiims_urllib(disease_name)
    else:
        return _fetch_aiims_urllib(disease_name)
    return _extract_statpearls_text(html, nbk)


# Disease name -> Wikipedia search term (handle disambiguation)
DISEASE_WIKI_MAP = {
    "High Blood Cholesterol": "Hypercholesterolemia",
    "Blood In Urine": "Hematuria",
    "Broken Collarbone": "Clavicle fracture",
    "Dry Skin": "Xeroderma",
    "GERD": "Gastroesophageal reflux disease",
    "TMJ": "Temporomandibular joint dysfunction",
    "Bunions": "Bunion",
    "Bee Stings": "Bee sting",
    "Hives And Angioedema": "Urticaria",
    "Hair Loss": "Hair loss",
    "Allergies": "Allergy",
    "Neck Pain": "Neck pain",
    "Burns": "Burn",
    "Gastroenteritis": "Gastroenteritis",
    "Alcoholic Hepatitis": "Alcoholic hepatitis",
    "Broken Leg": "Leg fracture",
    "Broken Arm": "Arm fracture",
    "Brain AVM": "Arteriovenous malformation",
    "Low Sex Drive In Women": "Hypoactive sexual desire disorder",
    "Ruptured Spleen": "Splenic rupture",
    "Gilberts Syndrome": "Gilbert's syndrome",
    "Hand Foot And Mouth Disease": "Hand, foot and mouth disease",
    "Kidney Cysts": "Renal cyst",
    "Bone Spurs": "Osteophyte",
    "Hiatal Hernia": "Hiatal hernia",
    "Mortons Neuroma": "Morton's neuroma",
    "Arthritis": "Arthritis",
    "Osteoarthritis": "Osteoarthritis",
    "Conversion Disorder": "Conversion disorder",
    "Enterocele": "Enterocele",
    "Idiopathic Thrombocytopenic Purpura": "Immune thrombocytopenic purpura",
    "Pubic Lice Crabs": "Crab louse",
    "Dsrct": "Desmoplastic small round cell tumor",
    "Valley Fever": "Coccidioidomycosis",
    "Ehlers Danlos Syndrome": "Ehlers-Danlos syndrome",
    "Dissociative Disorders": "Dissociative identity disorder",
    "Painful Intercourse": "Dyspareunia",
    "Guillain Barre Syndrome": "Guillain-Barré syndrome",
    "Testicular Cancer Care": "Testicular cancer",
    "(Vertigo) Paroymsal  Positional Vertigo": "Benign paroxysmal positional vertigo",
}


def slugify(name: str) -> str:
    """Convert disease name to filesystem-safe slug."""
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "_", s)
    return s[:80] if s else "unknown"


def disease_to_wiki_term(name: str) -> str:
    """Map disease name to Wikipedia search term."""
    return DISEASE_WIKI_MAP.get(name, name)


def fetch_wikipedia_summary(disease_name: str, sentences: int = 25) -> str | None:
    """Fetch Wikipedia summary for a disease. Returns None on failure."""
    try:
        import wikipedia
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "wikipedia"])
        import wikipedia
    term = disease_to_wiki_term(disease_name)
    try:
        wikipedia.set_rate_limiting(True)
        summary = wikipedia.summary(term, sentences=sentences, auto_suggest=True)
        return summary.strip() if summary else None
    except wikipedia.exceptions.DisambiguationError as e:
        # Try first option
        if e.options:
            try:
                return wikipedia.summary(e.options[0], sentences=sentences)
            except Exception:
                pass
        return None
    except Exception:
        return None


def _sanitize_for_pdf(text: str) -> str:
    """Replace Unicode chars that break Helvetica with ASCII equivalents."""
    replacements = {
        "\u2013": "-",  # en-dash
        "\u2014": "-",  # em-dash
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u03b1": "alpha",  # Greek alpha
        "\u03b2": "beta",
        "\u30a2": "",  # Japanese, etc. - remove
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Remove other non-ASCII
    return "".join(c if ord(c) < 128 else " " for c in text)


def text_to_pdf(text: str, output_path: Path, title: str) -> bool:
    """Write text to a PDF file. Returns False if FPDF not available."""
    if not _FPDF_AVAILABLE:
        return False
    try:
        text = _sanitize_for_pdf(text)
        title = _sanitize_for_pdf(title)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title
        pdf.set_font("Helvetica", "B", size=14)
        pdf.multi_cell(0, 8, title, ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.ln(4)

        # Content (split long lines)
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                pdf.ln(4)
                continue
            # Wrap long lines
            pdf.multi_cell(0, 6, line[:500], ln=True)

        pdf.output(str(output_path))
        return True
    except Exception as e:
        print(f"  PDF error for {title}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--max", type=int, default=80, help="Max diseases to fetch (default 80)")
    parser.add_argument("--source", choices=["wikipedia", "aiims"], default="wikipedia",
                        help="Source: wikipedia or aiims (StatPearls/AIIMS-style)")
    parser.add_argument("-w", "--workers", type=int, default=5, help="Parallel workers (default 5)")
    args = parser.parse_args()

    id2label_path = Path(__file__).resolve().parent.parent / "tests" / "id2label.json"
    books_dir = Path(__file__).resolve().parent.parent.parent / "disease_books"
    pdf_dir = books_dir / "pdf" / ("aiims" if args.source == "aiims" else "")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    index_path = books_dir / ("knowledge_index_aiims.json" if args.source == "aiims" else "knowledge_index.json")

    with open(id2label_path) as f:
        id2label = json.load(f)

    diseases = sorted(set(id2label.values()))[: args.max]
    knowledge_index: dict[str, str] = {}
    index_lock = threading.Lock()
    print_lock = threading.Lock()

    def fetch_one(disease: str) -> tuple[str, str | None]:
        if args.source == "aiims":
            # Use urllib (httpx may have DNS issues in some environments)
            return disease, fetch_aiims_statpearls(disease, client=None)
        return disease, fetch_wikipedia_summary(disease)

    print(f"Downloading {len(diseases)} diseases (workers={args.workers}, source={args.source})...")
    print(f"PDFs: {pdf_dir}\n")

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_one, d): d for d in diseases}
        for future in as_completed(futures):
            disease = futures[future]
            try:
                _, summary = future.result()
                if not summary:
                    with print_lock:
                        done += 1
                        print(f"  [{done}/{len(diseases)}] {disease[:40]}... (no content)")
                    continue
                with index_lock:
                    knowledge_index[disease] = summary
                    with open(index_path, "w") as f:
                        json.dump(knowledge_index, f, indent=2)
                ok = text_to_pdf(summary, pdf_dir / f"{slugify(disease)}.pdf", disease)
                with print_lock:
                    done += 1
                    print(f"  [{done}/{len(diseases)}] {disease[:40]}... {'OK' if ok else '(PDF failed)'}")
            except Exception as e:
                with print_lock:
                    done += 1
                    print(f"  [{done}/{len(diseases)}] {disease[:40]}... ERROR: {e}")

    print(f"\nDone. {len(knowledge_index)} diseases indexed.")
    print(f"PDFs: {pdf_dir}")
    print(f"Index: {index_path}")


if __name__ == "__main__":
    main()

"""
Mock pharmacy locator service.

Provides a set of sample pharmacies across major Indian cities, each stocking
a realistic subset of the medications referenced by the disease profiles in
mock_diagnosis.py.  Distance is calculated using the Haversine formula so
results can be sorted by proximity to the patient's coordinates.

In production this would be replaced by a real pharmacy-inventory API or a
geospatial database query.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Canonical medication list (covers all meds referenced in disease profiles)
# ---------------------------------------------------------------------------

ALL_MEDICATIONS: list[str] = [
    "Paracetamol", "Cetirizine", "Strepsils", "Ibuprofen",
    "Pantoprazole", "Ondansetron", "ORS", "Levocetirizine",
    "Fluticasone Nasal Spray", "Nitrofurantoin", "Cranberry Extract",
    "Diclofenac", "Thiocolchicoside", "Diclofenac Gel", "Amlodipine",
    "Telmisartan", "Metformin", "Vitamin B12", "Hydrocortisone Cream",
    "Calamine Lotion", "Escitalopram", "Propranolol", "Melatonin",
    "Moxifloxacin Eye Drops", "Refresh Tears", "Olopatadine Eye Drops",
    "Ferrous Sulfate", "Folic Acid", "Domperidone", "Antacid Gel",
    "Glucosamine + Chondroitin", "Amoxicillin + Clavulanate",
    "Montelukast", "Salbutamol Inhaler", "Guaifenesin Syrup",
    "Levothyroxine", "Budesonide + Formoterol Inhaler",
    "Sumatriptan", "Naproxen", "Tamsulosin", "Potassium Citrate",
    "Sertraline", "Vitamin D3", "Amoxicillin", "Clarithromycin",
    "Esomeprazole", "Sucralfate", "Pregabalin", "Methylcobalamin",
    "Artemether + Lumefantrine", "Primaquine",
    "Doxylamine + Vitamin B6", "Ginger Capsules",
    "Acyclovir", "Prednisolone", "Epinephrine Auto-Injector",
    "Calcium + Vitamin D3", "Zolpidem",
    "Ciprofloxacin Ear Drops",
    "Colchicine", "Allopurinol", "Febuxostat", "Azithromycin", "Cefixime",
    "Isoniazid", "Rifampicin", "Pyrazinamide", "Ethambutol", "Pyridoxine",
    "Betahistine", "Cinnarizine", "Mebeverine", "Rifaximin", "Psyllium Husk",
    "Hyoscine Butylbromide", "Ursodeoxycholic Acid", "Clobetasol Cream",
    "Calcipotriol Cream", "Methotrexate", "Valacyclovir", "Tiotropium Inhaler",
    "Fluticasone + Salmeterol Inhaler", "Betadine Gargle", "Levetiracetam",
    "Sodium Valproate", "Clobazam", "Omega-3 Supplements", "Cyclosporine Eye Drops",
    "Permethrin Cream", "Ivermectin", "Spironolactone", "Oral Contraceptive Pill",
    "Coal Tar Shampoo", "Lactulose Syrup", "Sodium Bicarbonate",
]


@dataclass
class Pharmacy:
    id: int
    name: str
    address: str
    city: str
    state: str
    latitude: float
    longitude: float
    phone: str
    hours: str
    is_24hr: bool
    medications_in_stock: list[str] = field(default_factory=list)


PHARMACIES: list[Pharmacy] = [
    # ── Delhi / NCR ───────────────────────────────────────────────
    Pharmacy(1, "Apollo Pharmacy — Connaught Place", "Block A, Connaught Place, New Delhi", "New Delhi", "Delhi", 28.6315, 77.2167, "+91 11 4356 7890", "8:00 AM – 11:00 PM", False,
             ["Paracetamol", "Cetirizine", "Ibuprofen", "Pantoprazole", "ORS", "Diclofenac", "Metformin", "Amlodipine", "Telmisartan", "Vitamin B12", "Vitamin D3", "Amoxicillin", "Salbutamol Inhaler", "Montelukast", "Prednisolone", "Folic Acid", "Ferrous Sulfate", "Levothyroxine", "Domperidone", "Antacid Gel", "Esomeprazole", "Calamine Lotion", "Levocetirizine"]),
    Pharmacy(2, "MedPlus — Rajouri Garden", "A-3/12, Rajouri Garden, New Delhi", "New Delhi", "Delhi", 28.6494, 77.1247, "+91 11 2851 4321", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "ORS", "Cetirizine", "Ondansetron", "Amoxicillin", "Amoxicillin + Clavulanate", "Metformin", "Amlodipine", "Telmisartan", "Sertraline", "Escitalopram", "Melatonin", "Pregabalin", "Salbutamol Inhaler", "Montelukast", "Levothyroxine", "Vitamin D3", "Calcium + Vitamin D3", "Tamsulosin", "Sumatriptan", "Naproxen", "Zolpidem", "Colchicine", "Allopurinol", "Betahistine", "Levetiracetam", "Valacyclovir", "Ivermectin", "Permethrin Cream"]),
    Pharmacy(3, "Fortis Healthworld — Vasant Kunj", "Nelson Mandela Marg, Vasant Kunj, New Delhi", "New Delhi", "Delhi", 28.5200, 77.1537, "+91 11 4277 6600", "9:00 AM – 10:00 PM", False,
             ["Paracetamol", "Cetirizine", "Levocetirizine", "Fluticasone Nasal Spray", "Pantoprazole", "Domperidone", "Antacid Gel", "Metformin", "Vitamin B12", "Ferrous Sulfate", "Folic Acid", "Hydrocortisone Cream", "Calamine Lotion", "Moxifloxacin Eye Drops", "Refresh Tears", "Olopatadine Eye Drops", "Glucosamine + Chondroitin", "Levothyroxine", "Acyclovir"]),
    Pharmacy(4, "Guardian Pharmacy — Saket", "Select Citywalk Mall, Saket, New Delhi", "New Delhi", "Delhi", 28.5286, 77.2190, "+91 11 4060 5050", "10:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Strepsils", "Cetirizine", "ORS", "Diclofenac", "Vitamin D3", "Calcium + Vitamin D3", "Calamine Lotion", "Naproxen", "Cranberry Extract", "Ginger Capsules", "Melatonin", "Ferrous Sulfate", "Folic Acid"]),

    # ── Mumbai ────────────────────────────────────────────────────
    Pharmacy(5, "Apollo Pharmacy — Bandra West", "Hill Road, Bandra West, Mumbai", "Mumbai", "Maharashtra", 19.0596, 72.8295, "+91 22 2640 1234", "8:00 AM – 11:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "Domperidone", "Antacid Gel", "Metformin", "Amlodipine", "Telmisartan", "Amoxicillin", "Amoxicillin + Clavulanate", "Diclofenac", "Sertraline", "Vitamin D3", "Levothyroxine", "Montelukast", "Salbutamol Inhaler", "Folic Acid", "Ferrous Sulfate", "ORS", "Prednisolone"]),
    Pharmacy(6, "Netmeds — Andheri East", "Marol Naka, Andheri East, Mumbai", "Mumbai", "Maharashtra", 19.1197, 72.8789, "+91 22 6789 0000", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin", "Clarithromycin", "Sucralfate", "Pregabalin", "Methylcobalamin", "Tamsulosin", "Potassium Citrate", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Levothyroxine", "Escitalopram", "Propranolol", "Melatonin", "Zolpidem", "Acyclovir", "Azithromycin", "Colchicine", "Betahistine", "Mebeverine", "Levetiracetam", "Permethrin Cream", "Ivermectin"]),
    Pharmacy(7, "MedPlus — Powai", "Hiranandani Gardens, Powai, Mumbai", "Mumbai", "Maharashtra", 19.1176, 72.9060, "+91 22 2570 8888", "9:00 AM – 10:30 PM", False,
             ["Paracetamol", "Cetirizine", "Strepsils", "ORS", "Pantoprazole", "Domperidone", "Metformin", "Vitamin B12", "Ferrous Sulfate", "Folic Acid", "Calcium + Vitamin D3", "Vitamin D3", "Calamine Lotion", "Hydrocortisone Cream", "Moxifloxacin Eye Drops", "Refresh Tears", "Glucosamine + Chondroitin", "Thiocolchicoside"]),

    # ── Bangalore ─────────────────────────────────────────────────
    Pharmacy(8, "Apollo Pharmacy — Koramangala", "80 Feet Road, Koramangala, Bengaluru", "Bengaluru", "Karnataka", 12.9352, 77.6245, "+91 80 4112 3456", "8:00 AM – 11:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Sertraline", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "ORS", "Domperidone", "Antacid Gel", "Ferrous Sulfate", "Folic Acid", "Prednisolone", "Levocetirizine"]),
    Pharmacy(9, "MedPlus — Indiranagar", "100 Feet Road, Indiranagar, Bengaluru", "Bengaluru", "Karnataka", 12.9784, 77.6408, "+91 80 2520 7777", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Amoxicillin + Clavulanate", "Clarithromycin", "Pregabalin", "Methylcobalamin", "Tamsulosin", "Sumatriptan", "Naproxen", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Montelukast", "Levothyroxine", "Escitalopram", "Propranolol", "Melatonin", "Acyclovir", "Zolpidem", "Calamine Lotion", "Hydrocortisone Cream", "Colchicine", "Azithromycin", "Betahistine", "Valacyclovir", "Ivermectin", "Mebeverine", "Omega-3 Supplements"]),
    Pharmacy(10, "Fortis Healthworld — Whitefield", "ITPL Main Road, Whitefield, Bengaluru", "Bengaluru", "Karnataka", 12.9698, 77.7500, "+91 80 6726 3000", "9:00 AM – 10:00 PM", False,
             ["Paracetamol", "Cetirizine", "Strepsils", "Pantoprazole", "ORS", "Metformin", "Vitamin B12", "Calcium + Vitamin D3", "Vitamin D3", "Ferrous Sulfate", "Folic Acid", "Calamine Lotion", "Moxifloxacin Eye Drops", "Refresh Tears", "Olopatadine Eye Drops", "Glucosamine + Chondroitin", "Nitrofurantoin", "Cranberry Extract", "Ginger Capsules"]),

    # ── Hyderabad ─────────────────────────────────────────────────
    Pharmacy(11, "Apollo Pharmacy — Jubilee Hills", "Road No. 36, Jubilee Hills, Hyderabad", "Hyderabad", "Telangana", 17.4326, 78.4071, "+91 40 2355 0001", "8:00 AM – 11:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Sertraline", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Domperidone", "Antacid Gel", "Ferrous Sulfate", "Folic Acid", "Levocetirizine", "Prednisolone", "Acyclovir"]),
    Pharmacy(12, "MedPlus — Gachibowli", "Biodiversity Junction, Gachibowli, Hyderabad", "Hyderabad", "Telangana", 17.4400, 78.3489, "+91 40 6677 8899", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Clarithromycin", "Sucralfate", "Pregabalin", "Methylcobalamin", "Tamsulosin", "Potassium Citrate", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Montelukast", "Levothyroxine", "Escitalopram", "Melatonin", "Zolpidem", "Nitrofurantoin", "Artemether + Lumefantrine", "Primaquine", "Colchicine", "Azithromycin", "Betahistine", "Levetiracetam", "Valacyclovir", "Permethrin Cream"]),

    # ── Chennai ───────────────────────────────────────────────────
    Pharmacy(13, "Apollo Pharmacy — T. Nagar", "Usman Road, T. Nagar, Chennai", "Chennai", "Tamil Nadu", 13.0418, 80.2341, "+91 44 2434 5678", "8:00 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Sertraline", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "ORS", "Domperidone", "Ferrous Sulfate", "Folic Acid", "Vitamin B12", "Levocetirizine", "Calamine Lotion"]),
    Pharmacy(14, "Netmeds — OMR", "Sholinganallur, OMR, Chennai", "Chennai", "Tamil Nadu", 12.9010, 80.2279, "+91 44 4890 1234", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Levothyroxine", "Escitalopram", "Propranolol", "Melatonin", "Acyclovir", "Hydrocortisone Cream", "Moxifloxacin Eye Drops", "Refresh Tears"]),

    # ── Kolkata ───────────────────────────────────────────────────
    Pharmacy(15, "Apollo Pharmacy — Park Street", "Park Street, Kolkata", "Kolkata", "West Bengal", 22.5510, 88.3520, "+91 33 2229 1100", "8:30 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Domperidone", "Ferrous Sulfate", "Folic Acid", "Levocetirizine", "Sertraline", "Prednisolone"]),
    Pharmacy(16, "MedPlus — Salt Lake", "Sector V, Salt Lake, Kolkata", "Kolkata", "West Bengal", 22.5726, 88.4312, "+91 33 4001 2345", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Clarithromycin", "Pregabalin", "Methylcobalamin", "Tamsulosin", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Zolpidem", "Artemether + Lumefantrine", "Primaquine", "Acyclovir", "Calamine Lotion", "Nitrofurantoin"]),

    # ── Pune ──────────────────────────────────────────────────────
    Pharmacy(17, "Apollo Pharmacy — Koregaon Park", "Lane 6, Koregaon Park, Pune", "Pune", "Maharashtra", 18.5362, 73.8939, "+91 20 2613 4567", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Antacid Gel", "Vitamin B12", "Calamine Lotion", "Levocetirizine", "Montelukast"]),
    Pharmacy(18, "MedPlus — Hinjewadi", "Phase 1, Hinjewadi, Pune", "Pune", "Maharashtra", 18.5912, 73.7389, "+91 20 4890 6789", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Glucosamine + Chondroitin", "Thiocolchicoside", "Sumatriptan", "Naproxen", "Propranolol"]),

    # ── Ahmedabad ─────────────────────────────────────────────────
    Pharmacy(19, "Apollo Pharmacy — SG Highway", "Bodakdev, SG Highway, Ahmedabad", "Ahmedabad", "Gujarat", 23.0350, 72.5068, "+91 79 4030 1234", "8:00 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline"]),
    Pharmacy(20, "MedPlus — Prahlad Nagar", "Prahlad Nagar, Ahmedabad", "Ahmedabad", "Gujarat", 23.0132, 72.5109, "+91 79 2681 5678", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Tamsulosin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Calamine Lotion", "Hydrocortisone Cream", "Prednisolone"]),

    # ── Jaipur ────────────────────────────────────────────────────
    Pharmacy(21, "Apollo Pharmacy — MI Road", "MI Road, Jaipur", "Jaipur", "Rajasthan", 26.9124, 75.7873, "+91 141 401 2345", "8:30 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levothyroxine", "Levocetirizine"]),
    Pharmacy(22, "Fortis Healthworld — Malviya Nagar", "Malviya Nagar, Jaipur", "Jaipur", "Rajasthan", 26.8570, 75.8093, "+91 141 271 0000", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Artemether + Lumefantrine", "Primaquine", "Nitrofurantoin", "Calamine Lotion", "Acyclovir"]),

    # ── Lucknow ───────────────────────────────────────────────────
    Pharmacy(23, "Apollo Pharmacy — Hazratganj", "Hazratganj, Lucknow", "Lucknow", "Uttar Pradesh", 26.8504, 80.9460, "+91 522 402 3456", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12"]),
    Pharmacy(24, "MedPlus — Gomti Nagar", "Gomti Nagar, Lucknow", "Lucknow", "Uttar Pradesh", 26.8563, 80.9934, "+91 522 400 7890", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Artemether + Lumefantrine", "Primaquine", "Calamine Lotion", "Acyclovir", "Prednisolone", "Sertraline", "Zolpidem"]),

    # ═══════════════════════════════════════════════════════════════
    #  TIER 2 CITIES
    # ═══════════════════════════════════════════════════════════════

    # ── Chandigarh ───────────────────────────────────────────────
    Pharmacy(25, "Apollo Pharmacy — Sector 17", "SCO 45, Sector 17-C, Chandigarh", "Chandigarh", "Chandigarh", 30.7415, 76.7838, "+91 172 270 1234", "8:30 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12", "Sertraline", "Prednisolone"]),
    Pharmacy(26, "Fortis Pharmacy — Sector 62", "Phase 8, Mohali (Sector 62), Chandigarh", "Chandigarh", "Punjab", 30.7046, 76.7179, "+91 172 500 8888", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Calamine Lotion"]),

    # ── Indore ───────────────────────────────────────────────────
    Pharmacy(27, "Apollo Pharmacy — Vijay Nagar", "AB Road, Vijay Nagar, Indore", "Indore", "Madhya Pradesh", 22.7533, 75.8937, "+91 731 401 5678", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Antacid Gel"]),
    Pharmacy(28, "MedPlus — Palasia", "Palasia Square, Indore", "Indore", "Madhya Pradesh", 22.7196, 75.8577, "+91 731 256 7890", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Prednisolone"]),

    # ── Bhopal ───────────────────────────────────────────────────
    Pharmacy(29, "MedPlus — MP Nagar", "Zone-II, MP Nagar, Bhopal", "Bhopal", "Madhya Pradesh", 23.2332, 77.4347, "+91 755 405 1234", "8:30 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12", "Levothyroxine"]),

    # ── Nagpur ───────────────────────────────────────────────────
    Pharmacy(30, "Apollo Pharmacy — Dharampeth", "Dharampeth, Nagpur", "Nagpur", "Maharashtra", 21.1458, 79.0882, "+91 712 253 4567", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Sertraline", "Prednisolone"]),
    Pharmacy(31, "MedPlus — Sadar", "Sadar, Nagpur", "Nagpur", "Maharashtra", 21.1550, 79.0728, "+91 712 252 8901", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir"]),

    # ── Patna ────────────────────────────────────────────────────
    Pharmacy(32, "Apollo Pharmacy — Boring Road", "Boring Road, Patna", "Patna", "Bihar", 25.6093, 85.1376, "+91 612 235 6789", "8:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12", "Levothyroxine", "Artemether + Lumefantrine"]),
    Pharmacy(33, "MedPlus — Kankarbagh", "Kankarbagh, Patna", "Patna", "Bihar", 25.5941, 85.1741, "+91 612 230 4321", "8:30 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Salbutamol Inhaler", "Primaquine", "Artemether + Lumefantrine"]),

    # ── Coimbatore ───────────────────────────────────────────────
    Pharmacy(34, "Apollo Pharmacy — RS Puram", "RS Puram, Coimbatore", "Coimbatore", "Tamil Nadu", 11.0053, 76.9551, "+91 422 254 7890", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12", "Calamine Lotion"]),

    # ── Visakhapatnam ────────────────────────────────────────────
    Pharmacy(35, "MedPlus — Dwaraka Nagar", "Dwaraka Nagar, Visakhapatnam", "Visakhapatnam", "Andhra Pradesh", 17.7231, 83.3013, "+91 891 278 1234", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12", "Prednisolone", "Sertraline"]),

    # ── Kochi ────────────────────────────────────────────────────
    Pharmacy(36, "Apollo Pharmacy — MG Road", "MG Road, Ernakulam, Kochi", "Kochi", "Kerala", 9.9816, 76.2999, "+91 484 237 5678", "8:00 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12", "Calamine Lotion", "Sertraline"]),
    Pharmacy(37, "MedPlus — Edappally", "Lulu Mall Road, Edappally, Kochi", "Kochi", "Kerala", 10.0261, 76.3084, "+91 484 410 2345", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir"]),

    # ── Thiruvananthapuram ───────────────────────────────────────
    Pharmacy(38, "Medstore — Statue Junction", "Statue Junction, Thiruvananthapuram", "Thiruvananthapuram", "Kerala", 8.4991, 76.9515, "+91 471 233 6789", "8:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levothyroxine", "Levocetirizine"]),

    # ── Surat ────────────────────────────────────────────────────
    Pharmacy(39, "Apollo Pharmacy — Adajan", "Adajan, Surat", "Surat", "Gujarat", 21.1869, 72.7919, "+91 261 260 1234", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12", "Antacid Gel", "Calamine Lotion"]),

    # ── Vadodara ─────────────────────────────────────────────────
    Pharmacy(40, "MedPlus — Alkapuri", "Alkapuri, Vadodara", "Vadodara", "Gujarat", 22.3120, 73.1723, "+91 265 235 5678", "8:30 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12", "Levothyroxine"]),

    # ── Mysuru ───────────────────────────────────────────────────
    Pharmacy(41, "Apollo Pharmacy — Saraswathipuram", "Saraswathipuram, Mysuru", "Mysuru", "Karnataka", 12.3051, 76.6551, "+91 821 242 1234", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12", "Levothyroxine", "Calamine Lotion"]),

    # ── Mangalore ────────────────────────────────────────────────
    Pharmacy(42, "MedPlus — Hampankatta", "Hampankatta, Mangalore", "Mangalore", "Karnataka", 12.8714, 74.8430, "+91 824 242 5678", "8:30 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levothyroxine", "Levocetirizine"]),

    # ── Guwahati ─────────────────────────────────────────────────
    Pharmacy(43, "Apollo Pharmacy — GS Road", "GS Road, Guwahati", "Guwahati", "Assam", 26.1445, 91.7362, "+91 361 254 7890", "8:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3", "Levocetirizine", "Artemether + Lumefantrine", "Primaquine"]),

    # ── Bhubaneswar ──────────────────────────────────────────────
    Pharmacy(44, "Apollo Pharmacy — Saheed Nagar", "Saheed Nagar, Bhubaneswar", "Bhubaneswar", "Odisha", 20.2866, 85.8440, "+91 674 254 3456", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12", "Artemether + Lumefantrine", "Calamine Lotion"]),

    # ── Ranchi ───────────────────────────────────────────────────
    Pharmacy(45, "MedPlus — Main Road", "Main Road, Ranchi", "Ranchi", "Jharkhand", 23.3441, 85.3096, "+91 651 231 2345", "8:30 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3", "Levocetirizine", "Artemether + Lumefantrine"]),

    # ── Dehradun ─────────────────────────────────────────────────
    Pharmacy(46, "Apollo Pharmacy — Rajpur Road", "Rajpur Road, Dehradun", "Dehradun", "Uttarakhand", 30.3255, 78.0421, "+91 135 271 5678", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Vitamin B12", "Levothyroxine", "Montelukast"]),

    # ── Varanasi ─────────────────────────────────────────────────
    Pharmacy(47, "MedPlus — Sigra", "Sigra, Varanasi", "Varanasi", "Uttar Pradesh", 25.3176, 82.9739, "+91 542 239 1234", "8:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine"]),

    # ── Agra ─────────────────────────────────────────────────────
    Pharmacy(48, "Apollo Pharmacy — Sanjay Place", "Sanjay Place, Agra", "Agra", "Uttar Pradesh", 27.1767, 78.0081, "+91 562 401 5678", "8:30 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Amlodipine"]),

    # ── Kanpur ───────────────────────────────────────────────────
    Pharmacy(49, "MedPlus — Mall Road", "Mall Road, Kanpur", "Kanpur", "Uttar Pradesh", 26.4499, 80.3319, "+91 512 253 6789", "8:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3", "Levocetirizine", "Amlodipine"]),

    # ── Amritsar ─────────────────────────────────────────────────
    Pharmacy(50, "Apollo Pharmacy — Lawrence Road", "Lawrence Road, Amritsar", "Amritsar", "Punjab", 31.6340, 74.8723, "+91 183 250 2345", "8:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine"]),

    # ── Ludhiana ─────────────────────────────────────────────────
    Pharmacy(51, "MedPlus — Clock Tower", "Clock Tower, Ludhiana", "Ludhiana", "Punjab", 30.9010, 75.8573, "+91 161 277 8901", "8:30 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Calamine Lotion"]),

    # ── Nashik ───────────────────────────────────────────────────
    Pharmacy(52, "Apollo Pharmacy — College Road", "College Road, Nashik", "Nashik", "Maharashtra", 20.0063, 73.7901, "+91 253 257 3456", "8:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine"]),

    # ── Rajkot ───────────────────────────────────────────────────
    Pharmacy(53, "MedPlus — Kalawad Road", "Kalawad Road, Rajkot", "Rajkot", "Gujarat", 22.2916, 70.7837, "+91 281 244 7890", "8:30 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine"]),

    # ── Raipur ───────────────────────────────────────────────────
    Pharmacy(54, "Apollo Pharmacy — Pandri", "Pandri, Raipur", "Raipur", "Chhattisgarh", 21.2368, 81.6337, "+91 771 405 1234", "8:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3", "Levocetirizine", "Artemether + Lumefantrine"]),

    # ═══════════════════════════════════════════════════════════════
    #  TIER 3 CITIES
    # ═══════════════════════════════════════════════════════════════

    # ── Shimla ───────────────────────────────────────────────────
    Pharmacy(55, "Himachal Medical Store", "The Mall, Shimla", "Shimla", "Himachal Pradesh", 31.1048, 77.1734, "+91 177 265 4321", "9:00 AM – 8:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Rishikesh ────────────────────────────────────────────────
    Pharmacy(56, "Ganga Pharmacy", "Tapovan, Rishikesh", "Rishikesh", "Uttarakhand", 30.1290, 78.3282, "+91 135 243 5678", "8:30 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin D3", "Calamine Lotion"]),

    # ── Udaipur ──────────────────────────────────────────────────
    Pharmacy(57, "City Pharma — Hathi Pol", "Hathi Pol, Udaipur", "Udaipur", "Rajasthan", 24.5854, 73.7125, "+91 294 241 2345", "8:30 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Amlodipine"]),

    # ── Jodhpur ──────────────────────────────────────────────────
    Pharmacy(58, "Marwar Medical Store", "Station Road, Jodhpur", "Jodhpur", "Rajasthan", 26.2389, 73.0243, "+91 291 261 6789", "8:00 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3", "Levocetirizine"]),

    # ── Prayagraj (Allahabad) ────────────────────────────────────
    Pharmacy(59, "Sangam Medical Store", "Civil Lines, Prayagraj", "Prayagraj", "Uttar Pradesh", 25.4358, 81.8463, "+91 532 240 1234", "8:00 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3", "Levocetirizine"]),

    # ── Jabalpur ─────────────────────────────────────────────────
    Pharmacy(60, "Narmada Pharma", "Wright Town, Jabalpur", "Jabalpur", "Madhya Pradesh", 23.1815, 79.9864, "+91 761 240 5678", "8:30 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Gwalior ──────────────────────────────────────────────────
    Pharmacy(61, "Royal Medical Store", "MLB Road, Gwalior", "Gwalior", "Madhya Pradesh", 26.2183, 78.1828, "+91 751 234 2345", "8:30 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3"]),

    # ── Madurai ──────────────────────────────────────────────────
    Pharmacy(62, "Apollo Pharmacy — Anna Nagar", "Anna Nagar, Madurai", "Madurai", "Tamil Nadu", 9.9252, 78.1198, "+91 452 253 6789", "8:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine"]),

    # ── Tirupati ─────────────────────────────────────────────────
    Pharmacy(63, "Sri Balaji Medical Store", "TP Area, Tirupati", "Tirupati", "Andhra Pradesh", 13.6288, 79.4192, "+91 877 225 1234", "8:00 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3"]),

    # ── Pondicherry ──────────────────────────────────────────────
    Pharmacy(64, "Aurobindo Pharmacy", "Rue Suffren, White Town, Pondicherry", "Pondicherry", "Puducherry", 11.9339, 79.8306, "+91 413 233 5678", "8:30 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Calamine Lotion"]),

    # ── Panaji (Goa) ─────────────────────────────────────────────
    Pharmacy(65, "Goa Medical Store — Panjim", "18th June Road, Panaji", "Panaji", "Goa", 15.4989, 73.8278, "+91 832 222 2345", "8:00 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Calamine Lotion", "Hydrocortisone Cream"]),
    Pharmacy(66, "Mapusa Pharmacy", "Market Area, Mapusa, Goa", "Mapusa", "Goa", 15.5916, 73.8086, "+91 832 226 6789", "9:00 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Calamine Lotion"]),

    # ── Jammu ────────────────────────────────────────────────────
    Pharmacy(67, "Apollo Pharmacy — Residency Road", "Residency Road, Jammu", "Jammu", "Jammu & Kashmir", 32.7266, 74.8570, "+91 191 247 1234", "8:00 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Amlodipine"]),

    # ── Srinagar ─────────────────────────────────────────────────
    Pharmacy(68, "Dal Pharmacy", "Lal Chowk, Srinagar", "Srinagar", "Jammu & Kashmir", 34.0837, 74.7973, "+91 194 247 5678", "9:00 AM – 7:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Dharamshala ──────────────────────────────────────────────
    Pharmacy(69, "Himalayan Medical Store", "McLeod Ganj, Dharamshala", "Dharamshala", "Himachal Pradesh", 32.2190, 76.3234, "+91 1892 22 1234", "9:00 AM – 7:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Haridwar ─────────────────────────────────────────────────
    Pharmacy(70, "Ganga Medical Store", "Upper Road, Haridwar", "Haridwar", "Uttarakhand", 29.9457, 78.1642, "+91 1334 22 5678", "8:00 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3"]),

    # ── Meerut ───────────────────────────────────────────────────
    Pharmacy(71, "City Medical Store", "Abu Lane, Meerut", "Meerut", "Uttar Pradesh", 28.9845, 77.7064, "+91 121 264 2345", "8:30 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Amlodipine"]),

    # ── Bareilly ─────────────────────────────────────────────────
    Pharmacy(72, "Rohilkhand Pharmacy", "Civil Lines, Bareilly", "Bareilly", "Uttar Pradesh", 28.3670, 79.4304, "+91 581 257 6789", "8:30 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Siliguri ─────────────────────────────────────────────────
    Pharmacy(73, "North Bengal Pharmacy", "Hill Cart Road, Siliguri", "Siliguri", "West Bengal", 26.7271, 88.3953, "+91 353 253 1234", "8:00 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3", "Artemether + Lumefantrine"]),

    # ── Gangtok ──────────────────────────────────────────────────
    Pharmacy(74, "Sikkim Medical Store", "MG Marg, Gangtok", "Gangtok", "Sikkim", 27.3389, 88.6065, "+91 3592 20 5678", "9:00 AM – 7:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Imphal ───────────────────────────────────────────────────
    Pharmacy(75, "Manipur Pharmacy", "Paona Bazar, Imphal", "Imphal", "Manipur", 24.8170, 93.9368, "+91 385 244 2345", "8:30 AM – 7:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Artemether + Lumefantrine", "Primaquine"]),

    # ── Shillong ─────────────────────────────────────────────────
    Pharmacy(76, "Khasi Hills Pharmacy", "Police Bazar, Shillong", "Shillong", "Meghalaya", 25.5788, 91.8933, "+91 364 250 6789", "9:00 AM – 7:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Warangal ─────────────────────────────────────────────────
    Pharmacy(77, "MedPlus — Hanamkonda", "Hanamkonda, Warangal", "Warangal", "Telangana", 17.9689, 79.5941, "+91 870 257 1234", "8:30 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine"]),

    # ── Hubli-Dharwad ────────────────────────────────────────────
    Pharmacy(78, "Karnataka Medical Store", "Lamington Road, Hubli", "Hubli", "Karnataka", 15.3647, 75.1240, "+91 836 235 5678", "8:00 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3", "Levocetirizine"]),

    # ── Belgaum (Belagavi) ───────────────────────────────────────
    Pharmacy(79, "Kittur Pharma", "College Road, Belagavi", "Belagavi", "Karnataka", 15.8497, 74.5040, "+91 831 242 2345", "8:30 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Salem ────────────────────────────────────────────────────
    Pharmacy(80, "Steel City Pharmacy", "Cherry Road, Salem", "Salem", "Tamil Nadu", 11.6643, 78.1460, "+91 427 231 6789", "8:00 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine"]),

    # ── Trichy (Tiruchirappalli) ─────────────────────────────────
    Pharmacy(81, "Apollo Pharmacy — Cantonment", "Cantonment, Tiruchirappalli", "Tiruchirappalli", "Tamil Nadu", 10.8155, 78.6965, "+91 431 246 1234", "8:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine"]),

    # ── Ujjain ───────────────────────────────────────────────────
    Pharmacy(82, "Mahakal Medical Store", "Freeganj, Ujjain", "Ujjain", "Madhya Pradesh", 23.1765, 75.7885, "+91 734 255 5678", "8:30 AM – 8:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Mathura ──────────────────────────────────────────────────
    Pharmacy(83, "Vrindavan Pharmacy", "Station Road, Mathura", "Mathura", "Uttar Pradesh", 27.4924, 77.6737, "+91 565 250 2345", "8:30 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Ajmer ────────────────────────────────────────────────────
    Pharmacy(84, "Dargah Medical Store", "Dargah Bazar, Ajmer", "Ajmer", "Rajasthan", 26.4521, 74.6399, "+91 145 262 6789", "8:30 AM – 8:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3"]),

    # ═══════════════════════════════════════════════════════════════
    #  ADDITIONAL METRO CITY PHARMACIES
    # ═══════════════════════════════════════════════════════════════

    # ── Delhi / NCR (additional) ─────────────────────────────────
    Pharmacy(85, "Apollo Pharmacy — Dwarka", "Sector 12, Dwarka, New Delhi", "New Delhi", "Delhi", 28.5921, 77.0409, "+91 11 4501 1234", "8:00 AM – 11:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline", "Prednisolone", "Calamine Lotion"]),
    Pharmacy(86, "MedPlus — Rohini", "Sector 11, Rohini, New Delhi", "New Delhi", "Delhi", 28.7323, 77.1147, "+91 11 2755 5678", "8:30 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Antacid Gel", "Esomeprazole"]),
    Pharmacy(87, "Fortis Pharmacy — Noida", "Sector 18, Noida", "Noida", "Uttar Pradesh", 28.5700, 77.3219, "+91 120 450 2345", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Levothyroxine", "Escitalopram", "Sertraline", "Melatonin", "Vitamin D3", "Calcium + Vitamin D3", "Tamsulosin", "Acyclovir", "Prednisolone", "Azithromycin", "Colchicine", "Betahistine", "Levetiracetam", "Valacyclovir", "Ivermectin"]),
    Pharmacy(88, "Apollo Pharmacy — Gurgaon", "MG Road, Gurugram", "Gurugram", "Haryana", 28.4595, 77.0266, "+91 124 430 6789", "8:00 AM – 11:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Amoxicillin + Clavulanate", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Sertraline", "Escitalopram", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Pregabalin", "Melatonin"]),
    Pharmacy(89, "MedPlus — Gurgaon Sector 56", "Sector 56, Gurugram", "Gurugram", "Haryana", 28.4231, 77.0470, "+91 124 422 1234", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Clarithromycin", "Pregabalin", "Methylcobalamin", "Tamsulosin", "Sumatriptan", "Naproxen", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Levothyroxine", "Escitalopram", "Propranolol", "Melatonin", "Zolpidem", "Acyclovir", "Hydrocortisone Cream", "Azithromycin", "Colchicine", "Betahistine", "Mebeverine", "Valacyclovir", "Permethrin Cream"]),
    Pharmacy(90, "Netmeds — Greater Noida", "Pari Chowk, Greater Noida", "Greater Noida", "Uttar Pradesh", 28.4744, 77.5040, "+91 120 232 5678", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Montelukast", "Antacid Gel"]),
    Pharmacy(91, "Apollo Pharmacy — Lajpat Nagar", "Central Market, Lajpat Nagar, New Delhi", "New Delhi", "Delhi", 28.5700, 77.2400, "+91 11 2981 3456", "8:00 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Vitamin B12", "Levothyroxine", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Levocetirizine", "Sertraline", "Calamine Lotion", "Prednisolone", "Telmisartan"]),
    Pharmacy(92, "MedPlus — Faridabad", "Sector 15, Faridabad", "Faridabad", "Haryana", 28.3810, 77.3178, "+91 129 410 7890", "8:30 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Montelukast"]),
    Pharmacy(93, "Apollo Pharmacy — Ghaziabad", "Raj Nagar, Ghaziabad", "Ghaziabad", "Uttar Pradesh", 28.6692, 77.4538, "+91 120 279 1234", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Telmisartan", "Antacid Gel"]),

    # ── Mumbai (additional) ──────────────────────────────────────
    Pharmacy(94, "Apollo Pharmacy — Thane", "Ghodbunder Road, Thane", "Thane", "Maharashtra", 19.2183, 72.9781, "+91 22 2597 1234", "8:00 AM – 11:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Amoxicillin + Clavulanate", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline", "Prednisolone"]),
    Pharmacy(95, "MedPlus — Navi Mumbai", "Sector 17, Vashi, Navi Mumbai", "Navi Mumbai", "Maharashtra", 19.0760, 72.9988, "+91 22 2782 5678", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Tamsulosin", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Zolpidem", "Sumatriptan"]),
    Pharmacy(96, "Fortis Pharmacy — Borivali", "SV Road, Borivali West, Mumbai", "Mumbai", "Maharashtra", 19.2288, 72.8544, "+91 22 2890 2345", "8:00 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Calamine Lotion", "Antacid Gel"]),
    Pharmacy(97, "Apollo Pharmacy — Dadar", "Dadar TT, Dadar West, Mumbai", "Mumbai", "Maharashtra", 19.0178, 72.8478, "+91 22 2430 6789", "8:00 AM – 11:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline", "Prednisolone", "Escitalopram"]),
    Pharmacy(98, "MedPlus — Kalyan", "Station Road, Kalyan", "Kalyan", "Maharashtra", 19.2437, 73.1355, "+91 251 230 1234", "8:30 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine"]),

    # ── Bangalore (additional) ───────────────────────────────────
    Pharmacy(99, "Apollo Pharmacy — HSR Layout", "Sector 2, HSR Layout, Bengaluru", "Bengaluru", "Karnataka", 12.9116, 77.6389, "+91 80 4215 5678", "8:00 AM – 11:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline", "Prednisolone", "Calamine Lotion"]),
    Pharmacy(100, "MedPlus — Jayanagar", "4th Block, Jayanagar, Bengaluru", "Bengaluru", "Karnataka", 12.9250, 77.5938, "+91 80 2663 2345", "8:30 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Antacid Gel", "Esomeprazole"]),
    Pharmacy(101, "Netmeds — Electronic City", "Phase 1, Electronic City, Bengaluru", "Bengaluru", "Karnataka", 12.8456, 77.6603, "+91 80 4190 6789", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Sertraline", "Vitamin D3", "Calcium + Vitamin D3"]),
    Pharmacy(102, "Apollo Pharmacy — Marathahalli", "Outer Ring Road, Marathahalli, Bengaluru", "Bengaluru", "Karnataka", 12.9591, 77.6971, "+91 80 2523 1234", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Montelukast", "Telmisartan"]),

    # ── Hyderabad (additional) ───────────────────────────────────
    Pharmacy(103, "Apollo Pharmacy — Kukatpally", "KPHB Colony, Kukatpally, Hyderabad", "Hyderabad", "Telangana", 17.4948, 78.3996, "+91 40 2305 5678", "8:00 AM – 11:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline", "Prednisolone", "Antacid Gel"]),
    Pharmacy(104, "MedPlus — Secunderabad", "Paradise Circle, Secunderabad", "Secunderabad", "Telangana", 17.4399, 78.4983, "+91 40 2780 2345", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Sertraline", "Zolpidem", "Tamsulosin"]),
    Pharmacy(105, "Fortis Pharmacy — Ameerpet", "Ameerpet, Hyderabad", "Hyderabad", "Telangana", 17.4375, 78.4482, "+91 40 2341 6789", "8:30 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Calamine Lotion", "Hydrocortisone Cream"]),

    # ── Chennai (additional) ─────────────────────────────────────
    Pharmacy(106, "Apollo Pharmacy — Anna Nagar", "2nd Avenue, Anna Nagar, Chennai", "Chennai", "Tamil Nadu", 13.0850, 80.2101, "+91 44 2626 1234", "8:00 AM – 11:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline", "Prednisolone"]),
    Pharmacy(107, "MedPlus — Adyar", "LB Road, Adyar, Chennai", "Chennai", "Tamil Nadu", 13.0067, 80.2573, "+91 44 2441 5678", "8:30 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Calamine Lotion", "Antacid Gel", "Esomeprazole"]),
    Pharmacy(108, "Netmeds — Velachery", "Velachery Main Road, Chennai", "Chennai", "Tamil Nadu", 12.9815, 80.2180, "+91 44 4500 2345", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Vitamin D3", "Calcium + Vitamin D3"]),
    Pharmacy(109, "Apollo Pharmacy — Tambaram", "Mudichur Road, Tambaram, Chennai", "Chennai", "Tamil Nadu", 12.9249, 80.1000, "+91 44 2239 6789", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine"]),

    # ── Kolkata (additional) ─────────────────────────────────────
    Pharmacy(110, "Apollo Pharmacy — Howrah", "Shibpur, Howrah", "Howrah", "West Bengal", 22.5736, 88.3046, "+91 33 2640 1234", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline", "Prednisolone"]),
    Pharmacy(111, "MedPlus — New Town", "Action Area I, New Town, Kolkata", "Kolkata", "West Bengal", 22.5958, 88.4796, "+91 33 4605 5678", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Vitamin D3", "Sertraline"]),
    Pharmacy(112, "Fortis Pharmacy — Dum Dum", "VIP Road, Dum Dum, Kolkata", "Kolkata", "West Bengal", 22.6246, 88.4246, "+91 33 2557 2345", "8:30 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Calamine Lotion"]),

    # ── Pune (additional) ────────────────────────────────────────
    Pharmacy(113, "Apollo Pharmacy — Kothrud", "Karve Road, Kothrud, Pune", "Pune", "Maharashtra", 18.5074, 73.8077, "+91 20 2546 6789", "8:00 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline", "Prednisolone"]),
    Pharmacy(114, "MedPlus — Viman Nagar", "Viman Nagar, Pune", "Pune", "Maharashtra", 18.5679, 73.9143, "+91 20 4100 1234", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Budesonide + Formoterol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Vitamin D3"]),
    Pharmacy(115, "Fortis Pharmacy — Hadapsar", "Magarpatta City, Hadapsar, Pune", "Pune", "Maharashtra", 18.5089, 73.9260, "+91 20 2689 5678", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Calamine Lotion", "Antacid Gel"]),

    # ── Ahmedabad (additional) ───────────────────────────────────
    Pharmacy(116, "Apollo Pharmacy — Maninagar", "Maninagar, Ahmedabad", "Ahmedabad", "Gujarat", 23.0018, 72.6011, "+91 79 2546 2345", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline"]),
    Pharmacy(117, "MedPlus — Navrangpura", "CG Road, Navrangpura, Ahmedabad", "Ahmedabad", "Gujarat", 23.0362, 72.5600, "+91 79 2640 6789", "8:30 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Calamine Lotion", "Antacid Gel", "Esomeprazole"]),
    Pharmacy(118, "Netmeds — Satellite", "Satellite Road, Ahmedabad", "Ahmedabad", "Gujarat", 23.0270, 72.5294, "+91 79 2692 1234", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Tamsulosin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Vitamin D3", "Calcium + Vitamin D3", "Sertraline"]),

    # ═══════════════════════════════════════════════════════════════
    #  PUNJAB CITIES
    # ═══════════════════════════════════════════════════════════════

    # ── Amritsar (additional) ────────────────────────────────────
    Pharmacy(119, "MedPlus — Hall Bazar", "Hall Bazar, Amritsar", "Amritsar", "Punjab", 31.6204, 74.8765, "+91 183 256 5678", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Vitamin D3"]),
    Pharmacy(120, "Golden Temple Pharmacy", "Near Golden Temple, Amritsar", "Amritsar", "Punjab", 31.6200, 74.8765, "+91 183 255 2345", "7:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine", "Calamine Lotion"]),

    # ── Ludhiana (additional) ────────────────────────────────────
    Pharmacy(121, "Apollo Pharmacy — Model Town", "Model Town, Ludhiana", "Ludhiana", "Punjab", 30.8987, 75.8680, "+91 161 501 6789", "8:00 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline", "Prednisolone"]),
    Pharmacy(122, "Fortis Pharmacy — Ferozepur Road", "Ferozepur Road, Ludhiana", "Ludhiana", "Punjab", 30.8848, 75.8227, "+91 161 530 1234", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Vitamin D3", "Calcium + Vitamin D3"]),

    # ── Jalandhar ────────────────────────────────────────────────
    Pharmacy(123, "Apollo Pharmacy — BMC Chowk", "BMC Chowk, Jalandhar", "Jalandhar", "Punjab", 31.3260, 75.5762, "+91 181 505 5678", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Telmisartan"]),
    Pharmacy(124, "MedPlus — Model Town", "Model Town, Jalandhar", "Jalandhar", "Punjab", 31.3310, 75.5862, "+91 181 222 2345", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir"]),
    Pharmacy(125, "City Chemist — Jalandhar", "Nakodar Chowk, Jalandhar", "Jalandhar", "Punjab", 31.3150, 75.5690, "+91 181 224 6789", "8:30 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3", "Levocetirizine"]),

    # ── Patiala ──────────────────────────────────────────────────
    Pharmacy(126, "Apollo Pharmacy — The Mall", "The Mall, Patiala", "Patiala", "Punjab", 30.3398, 76.3869, "+91 175 230 1234", "8:00 AM – 10:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Telmisartan"]),
    Pharmacy(127, "MedPlus — Rajpura Road", "Rajpura Road, Patiala", "Patiala", "Punjab", 30.3275, 76.4060, "+91 175 222 5678", "8:30 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3", "Levocetirizine"]),

    # ── Bathinda ─────────────────────────────────────────────────
    Pharmacy(128, "Apollo Pharmacy — Mall Road", "Mall Road, Bathinda", "Bathinda", "Punjab", 30.2110, 74.9455, "+91 164 240 2345", "8:00 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Diclofenac", "Amoxicillin", "Vitamin D3", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Levothyroxine"]),
    Pharmacy(129, "Malwa Medical Store", "Goniana Road, Bathinda", "Bathinda", "Punjab", 30.2050, 74.9380, "+91 164 242 6789", "8:30 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Mohali ───────────────────────────────────────────────────
    Pharmacy(130, "Apollo Pharmacy — Phase 7", "Phase 7, SAS Nagar, Mohali", "Mohali", "Punjab", 30.7270, 76.6900, "+91 172 509 1234", "8:00 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Sertraline", "Escitalopram"]),
    Pharmacy(131, "MedPlus — Sector 71", "Sector 71, SAS Nagar, Mohali", "Mohali", "Punjab", 30.7040, 76.7170, "+91 172 502 5678", "24 Hours", True,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Levocetirizine", "Diclofenac", "Diclofenac Gel", "Pantoprazole", "Esomeprazole", "Ondansetron", "ORS", "Metformin", "Vitamin B12", "Amlodipine", "Telmisartan", "Amoxicillin + Clavulanate", "Pregabalin", "Methylcobalamin", "Salbutamol Inhaler", "Levothyroxine", "Escitalopram", "Melatonin", "Acyclovir", "Vitamin D3", "Calcium + Vitamin D3"]),

    # ── Pathankot ────────────────────────────────────────────────
    Pharmacy(132, "Pathankot Medical Store", "Dalhousie Road, Pathankot", "Pathankot", "Punjab", 32.2643, 75.6421, "+91 186 222 2345", "8:00 AM – 9:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3", "Levocetirizine"]),
    Pharmacy(133, "Apollo Pharmacy — Dhangu Road", "Dhangu Road, Pathankot", "Pathankot", "Punjab", 32.2720, 75.6380, "+91 186 225 6789", "8:30 AM – 9:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Amlodipine"]),

    # ── Hoshiarpur ───────────────────────────────────────────────
    Pharmacy(134, "Guru Nanak Medical Store", "Sutheri Road, Hoshiarpur", "Hoshiarpur", "Punjab", 31.5143, 75.9115, "+91 1882 22 1234", "8:30 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3"]),

    # ── Phagwara ─────────────────────────────────────────────────
    Pharmacy(135, "Lovely Medical Store", "GT Road, Phagwara", "Phagwara", "Punjab", 31.2240, 75.7708, "+91 1824 26 5678", "8:30 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Kapurthala ───────────────────────────────────────────────
    Pharmacy(136, "Kapurthala Pharmacy", "Jalandhar Road, Kapurthala", "Kapurthala", "Punjab", 31.3813, 75.3808, "+91 1822 23 2345", "9:00 AM – 8:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Gurdaspur ────────────────────────────────────────────────
    Pharmacy(137, "Border Pharmacy", "Railway Road, Gurdaspur", "Gurdaspur", "Punjab", 32.0414, 75.4031, "+91 1874 24 6789", "8:30 AM – 8:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Metformin"]),

    # ── Ferozepur ────────────────────────────────────────────────
    Pharmacy(138, "Ferozepur Medical Store", "Ferozepur Cantt, Ferozepur", "Ferozepur", "Punjab", 30.9331, 74.6225, "+91 1632 24 1234", "8:30 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine"]),

    # ── Sangrur ──────────────────────────────────────────────────
    Pharmacy(139, "Sangrur Chemist", "Bhawanigarh Road, Sangrur", "Sangrur", "Punjab", 30.2458, 75.8411, "+91 1672 23 5678", "8:30 AM – 8:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Moga ─────────────────────────────────────────────────────
    Pharmacy(140, "Moga Medical Store", "GT Road, Moga", "Moga", "Punjab", 30.8162, 75.1742, "+91 1636 23 2345", "8:30 AM – 8:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Mandi Gobindgarh ─────────────────────────────────────────
    Pharmacy(141, "Steel Town Pharmacy", "GT Road, Mandi Gobindgarh", "Mandi Gobindgarh", "Punjab", 30.6688, 76.2985, "+91 1765 25 6789", "8:30 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3"]),

    # ── Rupnagar (Ropar) ─────────────────────────────────────────
    Pharmacy(142, "Ropar Medical Store", "Chandigarh Road, Rupnagar", "Rupnagar", "Punjab", 30.9660, 76.5230, "+91 1881 22 1234", "8:30 AM – 8:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Nawanshahr (Shaheed Bhagat Singh Nagar) ──────────────────
    Pharmacy(143, "SBS Nagar Pharmacy", "Jalandhar Road, Nawanshahr", "Nawanshahr", "Punjab", 31.1256, 76.1164, "+91 1823 23 5678", "9:00 AM – 8:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Muktsar ──────────────────────────────────────────────────
    Pharmacy(144, "Muktsar Chemist", "Kotkapura Road, Muktsar", "Muktsar", "Punjab", 30.4768, 74.5140, "+91 1633 26 2345", "9:00 AM – 7:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Abohar ───────────────────────────────────────────────────
    Pharmacy(145, "Abohar Medical Store", "Hanumangarh Road, Abohar", "Abohar", "Punjab", 30.1453, 74.1950, "+91 1634 22 6789", "9:00 AM – 7:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Zirakpur ─────────────────────────────────────────────────
    Pharmacy(146, "Apollo Pharmacy — Zirakpur", "Ambala-Chandigarh Highway, Zirakpur", "Zirakpur", "Punjab", 30.6422, 76.8173, "+91 1762 50 1234", "8:00 AM – 10:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Amlodipine", "Telmisartan", "Diclofenac", "Amoxicillin", "Vitamin D3", "Levothyroxine", "Salbutamol Inhaler", "Montelukast", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Levocetirizine", "Escitalopram"]),

    # ── Khanna ───────────────────────────────────────────────────
    Pharmacy(147, "Khanna Pharmacy", "GT Road, Khanna", "Khanna", "Punjab", 30.6961, 76.2175, "+91 1628 22 5678", "8:30 AM – 8:00 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12"]),

    # ── Rajpura ──────────────────────────────────────────────────
    Pharmacy(148, "Rajpura Medical Store", "Patiala Road, Rajpura", "Rajpura", "Punjab", 30.4848, 76.5924, "+91 1762 24 2345", "8:30 AM – 8:30 PM", False,
             ["Paracetamol", "Ibuprofen", "Cetirizine", "Pantoprazole", "ORS", "Metformin", "Diclofenac", "Amoxicillin", "Salbutamol Inhaler", "Ferrous Sulfate", "Folic Acid", "Domperidone", "Vitamin B12", "Vitamin D3"]),
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points on Earth in kilometres."""
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


_CHAIN_PHOTOS: dict[str, str] = {
    "apollo":  "https://images.unsplash.com/photo-1586015555751-63bb77f4322a?w=400&h=250&fit=crop",
    "medplus": "https://images.unsplash.com/photo-1576602976047-174e57a47881?w=400&h=250&fit=crop",
    "fortis":  "https://images.unsplash.com/photo-1631549916768-4119b2e5f926?w=400&h=250&fit=crop",
    "netmeds": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88?w=400&h=250&fit=crop",
    "guardian": "https://images.unsplash.com/photo-1471864190281-a93a3070b6de?w=400&h=250&fit=crop",
}

_GENERIC_PHOTOS: list[str] = [
    "https://images.unsplash.com/photo-1585435557343-3b092031a831?w=400&h=250&fit=crop",
    "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2?w=400&h=250&fit=crop",
    "https://images.unsplash.com/photo-1576072446584-2ınınce3f5c0?w=400&h=250&fit=crop",
    "https://images.unsplash.com/photo-1583947215259-38e31be8751f?w=400&h=250&fit=crop",
    "https://images.unsplash.com/photo-1631549916768-4119b2e5f926?w=400&h=250&fit=crop",
    "https://images.unsplash.com/photo-1576602976047-174e57a47881?w=400&h=250&fit=crop",
]


def _pharmacy_photo(pharmacy: Pharmacy) -> str:
    """Return a storefront photo URL for the pharmacy."""
    name_lower = pharmacy.name.lower()
    for chain, url in _CHAIN_PHOTOS.items():
        if chain in name_lower:
            return url
    return _GENERIC_PHOTOS[pharmacy.id % len(_GENERIC_PHOTOS)]


def _build_pharmacy_result(
    pharmacy: Pharmacy,
    medications: list[str],
    latitude: float | None,
    longitude: float | None,
) -> dict | None:
    """Build a result dict for a single pharmacy if it stocks any requested medication."""
    stock_lower = [s.lower() for s in pharmacy.medications_in_stock]
    available = [m for m in medications if m.strip().lower() in stock_lower]

    if not available:
        return None

    unavailable = [m for m in medications if m.strip().lower() not in stock_lower]

    distance: float | None = None
    if latitude is not None and longitude is not None:
        distance = round(
            _haversine_km(latitude, longitude, pharmacy.latitude, pharmacy.longitude), 1
        )

    return {
        "id": pharmacy.id,
        "name": pharmacy.name,
        "address": pharmacy.address,
        "city": pharmacy.city,
        "state": pharmacy.state,
        "latitude": pharmacy.latitude,
        "longitude": pharmacy.longitude,
        "phone": pharmacy.phone,
        "hours": pharmacy.hours,
        "is_24hr": pharmacy.is_24hr,
        "distance_km": distance,
        "available_medications": available,
        "unavailable_medications": unavailable,
        "availability_ratio": round(len(available) / max(len(medications), 1), 2),
        "photo_url": _pharmacy_photo(pharmacy),
    }


def find_nearby_pharmacies(
    medications: list[str],
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float = 50.0,
    limit: int = 30,
) -> list[dict]:
    """Return pharmacies that stock *any* of the requested medications,
    sorted by distance when coordinates are provided.

    If no pharmacies are found within the radius, falls back to returning
    all matching pharmacies nationwide so the user always gets results.
    """
    all_matching: list[dict] = []
    for pharmacy in PHARMACIES:
        result = _build_pharmacy_result(pharmacy, medications, latitude, longitude)
        if result:
            all_matching.append(result)

    has_coords = latitude is not None and longitude is not None

    if has_coords:
        within_radius = [r for r in all_matching if (r["distance_km"] or 0) <= radius_km]
        if within_radius:
            within_radius.sort(key=lambda r: (-(r["availability_ratio"]), r["distance_km"] or 0))
            return within_radius[:limit]

    all_matching.sort(
        key=lambda r: (-(r["availability_ratio"]), r["distance_km"] or 0)
        if has_coords
        else (-(r["availability_ratio"]),)
    )
    return all_matching[:limit]

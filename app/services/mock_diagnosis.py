"""
Mock diagnosis engine with 50 disease categories and weighted keyword scoring.

In production, replace `diagnose()` with a call to MedGemma on Vertex AI.
The scoring system here matches symptom text against keyword lists and picks
the disease with the highest weighted match count.
"""

from dataclasses import dataclass, field

MODEL_VERSION = "medgemma-mock-v3"


@dataclass
class DiseaseProfile:
    name: str
    keywords: list[str]
    base_confidence: float
    severity: str
    reasoning_template: str
    findings: list[dict]
    medications: list[dict]
    lifestyle: list[str]
    precautions: list[str]
    recommended_tests: list[str]
    when_to_see_doctor: str
    urgency: str
    keyword_weights: dict[str, float] = field(default_factory=dict)


DISEASE_PROFILES: list[DiseaseProfile] = [
    # 1 — Upper Respiratory Tract Infection
    DiseaseProfile(
        name="Upper Respiratory Tract Infection (Common Cold / Viral Fever)",
        keywords=["fever", "cold", "cough", "throat", "runny nose", "sneezing", "body ache", "chills"],
        base_confidence=0.85,
        severity="mild",
        reasoning_template="Based on the reported symptoms ({symptoms}), this appears to be a viral upper respiratory infection. The combination of symptoms is consistent with a common viral illness that typically resolves within 5-7 days.",
        findings=[
            {"finding": "Symptoms consistent with viral URTI", "severity": "low"},
            {"finding": "No red flags for bacterial infection noted", "severity": "low"},
        ],
        medications=[
            {"name": "Paracetamol (Acetaminophen)", "dosage": "500mg", "frequency": "Every 6 hours as needed", "duration": "3-5 days", "type": "tablet", "notes": "Take for fever and body ache. Do not exceed 4 tablets in 24 hours."},
            {"name": "Cetirizine", "dosage": "10mg", "frequency": "Once daily at night", "duration": "5 days", "type": "tablet", "notes": "For runny nose and sneezing. May cause drowsiness."},
            {"name": "Throat lozenges (Strepsils)", "dosage": "1 lozenge", "frequency": "Every 3-4 hours", "duration": "As needed", "type": "tablet", "notes": "Dissolve slowly in mouth for sore throat relief."},
        ],
        lifestyle=["Rest well and get adequate sleep (7-8 hours)", "Drink warm fluids — soup, herbal tea, warm water with honey", "Gargle with warm salt water 3 times daily", "Avoid cold drinks and fried/oily food", "Stay home to prevent spreading the infection"],
        precautions=["Wash hands frequently", "Cover mouth when coughing/sneezing", "Avoid contact with infants and elderly"],
        recommended_tests=["Complete Blood Count (CBC) if fever persists beyond 5 days"],
        when_to_see_doctor="Visit a doctor immediately if: fever exceeds 103°F, difficulty breathing, symptoms worsen after 5 days, blood in sputum, or severe headache with stiff neck.",
        urgency="routine",
    ),

    # 2 — Tension-Type Headache
    DiseaseProfile(
        name="Tension-Type Headache",
        keywords=["headache", "migraine", "head pain", "temple pressure", "forehead pain"],
        base_confidence=0.78,
        severity="mild",
        reasoning_template="The reported symptoms ({symptoms}) are consistent with a tension-type headache, the most common form of primary headache. Often related to stress, poor posture, or eye strain.",
        findings=[
            {"finding": "Symptoms suggest tension-type headache", "severity": "low"},
            {"finding": "No neurological red flags identified", "severity": "low"},
        ],
        medications=[
            {"name": "Ibuprofen", "dosage": "400mg", "frequency": "Every 8 hours with food", "duration": "2-3 days", "type": "tablet", "notes": "Take with food to avoid stomach upset. Do not take on empty stomach."},
            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours if needed", "duration": "2 days", "type": "tablet", "notes": "Alternative to Ibuprofen. Do not combine both."},
        ],
        lifestyle=["Take regular breaks from screens (20-20-20 rule)", "Practice stress management and deep breathing", "Ensure good posture while working", "Stay hydrated — drink 2-3 liters of water daily", "Get regular exercise (30 min walk daily)"],
        precautions=["Avoid prolonged screen time", "Maintain regular sleep schedule"],
        recommended_tests=["Eye examination if headaches are frequent"],
        when_to_see_doctor="Seek immediate care if: sudden severe headache ('thunderclap'), headache with vision changes, fever with stiff neck, headache after head injury, or progressively worsening headaches.",
        urgency="routine",
    ),

    # 3 — Acute Gastritis / Gastroenteritis
    DiseaseProfile(
        name="Acute Gastritis / Gastroenteritis",
        keywords=["stomach", "digestion", "nausea", "vomit", "diarrhea", "abdominal", "stomach pain", "loose motion"],
        base_confidence=0.80,
        severity="moderate",
        reasoning_template="Based on symptoms ({symptoms}), this appears to be acute gastritis or gastroenteritis, likely caused by dietary factors or a mild infection. The condition usually resolves with proper hydration and dietary modifications.",
        findings=[
            {"finding": "GI symptoms consistent with gastritis", "severity": "medium"},
            {"finding": "Dehydration risk present", "severity": "medium"},
        ],
        medications=[
            {"name": "Pantoprazole", "dosage": "40mg", "frequency": "Once daily before breakfast", "duration": "7 days", "type": "tablet", "notes": "Take 30 minutes before first meal of the day."},
            {"name": "Ondansetron (Emeset)", "dosage": "4mg", "frequency": "Every 8 hours as needed", "duration": "2-3 days", "type": "tablet", "notes": "For nausea and vomiting. Place on tongue to dissolve."},
            {"name": "ORS (Oral Rehydration Solution)", "dosage": "1 sachet in 1L water", "frequency": "Sip throughout the day", "duration": "3-5 days", "type": "syrup", "notes": "Critical to prevent dehydration. Drink at least 2-3 liters daily."},
        ],
        lifestyle=["Follow BRAT diet (Bananas, Rice, Applesauce, Toast)", "Avoid spicy, oily, and acidic foods for 5 days", "Eat small frequent meals instead of large ones", "Avoid caffeine, alcohol, and carbonated drinks", "Stay hydrated with clear fluids"],
        precautions=["Wash hands before eating", "Ensure food hygiene", "Avoid street food temporarily"],
        recommended_tests=["Stool examination if symptoms persist", "H. pylori test if recurrent"],
        when_to_see_doctor="Seek immediate care if: blood in vomit or stool, severe abdominal pain, signs of dehydration (dark urine, dizziness), high fever above 102°F, or symptoms last more than 3 days.",
        urgency="soon",
    ),

    # 4 — Allergic Rhinitis / Sinusitis
    DiseaseProfile(
        name="Allergic Rhinitis / Sinusitis",
        keywords=["sneezing", "nasal congestion", "sinus", "itchy eyes", "blocked nose", "nasal drip", "watery nose"],
        base_confidence=0.82,
        severity="mild",
        reasoning_template="The reported symptoms ({symptoms}) point towards allergic rhinitis or sinusitis. This is commonly triggered by allergens like dust, pollen, or weather changes. Symptoms can be effectively managed with antihistamines and nasal care.",
        findings=[
            {"finding": "Symptoms consistent with allergic rhinitis / sinusitis", "severity": "low"},
            {"finding": "No signs of secondary bacterial infection", "severity": "low"},
        ],
        medications=[
            {"name": "Levocetirizine", "dosage": "5mg", "frequency": "Once daily at night", "duration": "7-10 days", "type": "tablet", "notes": "Non-drowsy antihistamine. Take at bedtime."},
            {"name": "Fluticasone Nasal Spray", "dosage": "2 sprays per nostril", "frequency": "Once daily in the morning", "duration": "14 days", "type": "inhaler", "notes": "Shake well before use. Do not tilt head back."},
            {"name": "Steam inhalation", "dosage": "10-15 minutes", "frequency": "Twice daily", "duration": "7 days", "type": "topical", "notes": "Add a few drops of eucalyptus oil for better relief."},
        ],
        lifestyle=["Keep windows closed during high-pollen days", "Use air purifiers indoors", "Wash bedding in hot water weekly", "Avoid known allergens (dust, pet dander, smoke)", "Stay hydrated"],
        precautions=["Do not blow nose too forcefully", "Avoid sudden temperature changes", "Use a humidifier in dry environments"],
        recommended_tests=["Allergy skin prick test if recurrent", "Sinus X-ray if symptoms persist beyond 2 weeks"],
        when_to_see_doctor="See a doctor if: green/yellow thick nasal discharge persists beyond 10 days, facial pain with fever, recurrent episodes more than 4 times per year, or symptoms severely affect daily activities.",
        urgency="routine",
    ),

    # 5 — Urinary Tract Infection (UTI)
    DiseaseProfile(
        name="Urinary Tract Infection (UTI)",
        keywords=["burning urination", "frequent urination", "urine", "bladder", "painful urination", "urinary", "cloudy urine"],
        base_confidence=0.83,
        severity="moderate",
        reasoning_template="The symptoms described ({symptoms}) are suggestive of a urinary tract infection. UTIs are common bacterial infections of the urinary system that require antibiotic treatment to prevent complications.",
        findings=[
            {"finding": "Symptoms strongly suggestive of lower UTI (cystitis)", "severity": "medium"},
            {"finding": "Risk of ascending infection if untreated", "severity": "medium"},
        ],
        medications=[
            {"name": "Nitrofurantoin", "dosage": "100mg", "frequency": "Twice daily with food", "duration": "5 days", "type": "capsule", "notes": "Complete the full course even if symptoms improve. Take with meals."},
            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours as needed", "duration": "2-3 days", "type": "tablet", "notes": "For pain and discomfort."},
            {"name": "Cranberry Extract", "dosage": "500mg", "frequency": "Twice daily", "duration": "14 days", "type": "capsule", "notes": "Supportive supplement to help prevent recurrence."},
        ],
        lifestyle=["Drink at least 3 liters of water daily to flush bacteria", "Urinate frequently — do not hold urine", "Wipe front to back after using the toilet", "Avoid caffeine, alcohol, and spicy food during treatment", "Wear loose cotton undergarments"],
        precautions=["Complete the full antibiotic course", "Avoid sexual activity during acute infection", "Do not use bubble baths or scented products in genital area"],
        recommended_tests=["Urine Routine & Microscopy", "Urine Culture & Sensitivity", "Ultrasound KUB if recurrent"],
        when_to_see_doctor="Seek immediate medical attention if: blood in urine, fever with chills, severe back/flank pain, nausea/vomiting, or symptoms do not improve within 48 hours of starting antibiotics.",
        urgency="soon",
    ),

    # 6 — Lower Back Pain / Musculoskeletal
    DiseaseProfile(
        name="Lower Back Pain / Musculoskeletal Strain",
        keywords=["back pain", "lower back", "spine", "muscle pain", "stiffness", "spasm", "sciatica"],
        base_confidence=0.76,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) are consistent with musculoskeletal lower back pain, commonly caused by poor posture, muscle strain, or prolonged sitting. Most cases resolve with conservative treatment within 2-4 weeks.",
        findings=[
            {"finding": "Symptoms consistent with mechanical / muscular back pain", "severity": "low"},
            {"finding": "No red flags for neurological compromise noted", "severity": "low"},
        ],
        medications=[
            {"name": "Diclofenac", "dosage": "50mg", "frequency": "Twice daily after meals", "duration": "5 days", "type": "tablet", "notes": "Anti-inflammatory painkiller. Take with food. Avoid if you have stomach ulcers."},
            {"name": "Thiocolchicoside", "dosage": "4mg", "frequency": "Twice daily", "duration": "5 days", "type": "capsule", "notes": "Muscle relaxant. May cause mild drowsiness."},
            {"name": "Diclofenac Gel", "dosage": "Apply thin layer", "frequency": "3 times daily on affected area", "duration": "7 days", "type": "topical", "notes": "Gently massage into skin. Wash hands after application."},
        ],
        lifestyle=["Apply hot/cold compresses alternately", "Avoid prolonged sitting — take breaks every 30 minutes", "Practice gentle stretching and core strengthening exercises", "Maintain good posture; use ergonomic chair", "Sleep on a firm mattress; place a pillow between knees"],
        precautions=["Avoid heavy lifting for 2 weeks", "Do not twist the spine forcefully", "Avoid bed rest beyond 1-2 days — stay gently active"],
        recommended_tests=["Lumbar spine X-ray if pain persists beyond 4 weeks", "MRI if radiating leg pain (sciatica) is present"],
        when_to_see_doctor="See a doctor urgently if: pain radiates down the leg below the knee, numbness or weakness in legs, loss of bladder/bowel control, pain after trauma/fall, or progressive worsening despite treatment.",
        urgency="routine",
    ),

    # 7 — Hypertension (High BP)
    DiseaseProfile(
        name="Hypertension (High Blood Pressure)",
        keywords=["blood pressure", "high bp", "hypertension", "dizziness", "chest pressure", "high blood pressure"],
        base_confidence=0.81,
        severity="moderate",
        reasoning_template="The symptoms and health data ({symptoms}) suggest possible hypertension. High blood pressure is a silent condition that increases the risk of heart disease, stroke, and kidney damage. Regular monitoring and lifestyle changes are essential.",
        findings=[
            {"finding": "Symptoms and/or report values suggestive of elevated blood pressure", "severity": "medium"},
            {"finding": "Cardiovascular risk assessment recommended", "severity": "medium"},
        ],
        medications=[
            {"name": "Amlodipine", "dosage": "5mg", "frequency": "Once daily in the morning", "duration": "Ongoing (as prescribed)", "type": "tablet", "notes": "Calcium channel blocker. Take at the same time each day. Do not stop abruptly."},
            {"name": "Telmisartan", "dosage": "40mg", "frequency": "Once daily", "duration": "Ongoing (as prescribed)", "type": "tablet", "notes": "ARB for blood pressure control. Monitor potassium levels periodically."},
        ],
        lifestyle=["Reduce salt (sodium) intake to less than 5g per day", "Exercise regularly — at least 30 minutes of brisk walking daily", "Maintain a healthy weight (BMI 18.5-24.9)", "Follow the DASH diet (fruits, vegetables, whole grains, low fat)", "Limit alcohol and quit smoking", "Practice stress reduction (meditation, yoga)"],
        precautions=["Monitor blood pressure at home twice daily", "Do not skip medications", "Avoid excessive caffeine", "Report any persistent headache or vision changes"],
        recommended_tests=["Blood Pressure monitoring (home and clinic)", "Lipid Profile", "Renal Function Test", "ECG", "Echocardiogram if indicated"],
        when_to_see_doctor="Seek emergency care if: BP exceeds 180/120 mmHg, severe headache with confusion, chest pain, difficulty breathing, sudden vision changes, or one-sided weakness/numbness.",
        urgency="soon",
    ),

    # 8 — Type 2 Diabetes Indicators
    DiseaseProfile(
        name="Type 2 Diabetes Mellitus — Indicators",
        keywords=["blood sugar", "diabetes", "thirst", "frequent urination", "fatigue", "glucose", "sugar level", "hba1c"],
        base_confidence=0.79,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) along with any lab values provided raise concern for Type 2 diabetes or pre-diabetes. Early detection and management through diet, exercise, and medication can prevent serious complications.",
        findings=[
            {"finding": "Symptoms consistent with hyperglycemia / insulin resistance", "severity": "medium"},
            {"finding": "Risk factors for Type 2 diabetes identified", "severity": "medium"},
        ],
        medications=[
            {"name": "Metformin", "dosage": "500mg", "frequency": "Twice daily with meals", "duration": "Ongoing (as prescribed)", "type": "tablet", "notes": "Start with low dose and increase gradually. May cause GI upset initially."},
            {"name": "Vitamin B12 Supplement", "dosage": "1500mcg", "frequency": "Once daily", "duration": "Ongoing", "type": "tablet", "notes": "Long-term Metformin can lower B12 levels."},
        ],
        lifestyle=["Follow a low-glycemic-index diet (avoid white rice, white bread, sugary drinks)", "Exercise at least 150 minutes per week (walking, cycling, swimming)", "Lose 5-7% body weight if overweight", "Eat plenty of fiber (vegetables, whole grains, lentils)", "Monitor blood sugar regularly", "Get adequate sleep (7-8 hours)"],
        precautions=["Carry glucose tablets or candy for hypoglycemia emergencies", "Check feet daily for cuts or sores", "Do not skip meals if on medication", "Limit fruit juice and processed snacks"],
        recommended_tests=["Fasting Blood Sugar (FBS)", "HbA1c (Glycated Hemoglobin)", "Post-Prandial Blood Sugar", "Lipid Profile", "Kidney Function Test", "Eye examination (fundoscopy)"],
        when_to_see_doctor="See a doctor urgently if: blood sugar exceeds 300 mg/dL, fruity breath odor, excessive thirst with frequent urination, unexplained weight loss, blurry vision, or non-healing wounds.",
        urgency="soon",
    ),

    # 9 — Skin Infection / Dermatitis
    DiseaseProfile(
        name="Skin Infection / Dermatitis",
        keywords=["rash", "skin", "itching", "redness", "eczema", "acne", "hives", "fungal", "ring worm"],
        base_confidence=0.77,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) suggest a dermatological condition, possibly dermatitis, eczema, or a localized skin infection. Skin conditions are often managed effectively with topical treatments and trigger avoidance.",
        findings=[
            {"finding": "Skin symptoms suggestive of dermatitis or localized infection", "severity": "low"},
            {"finding": "Pattern assessment needed — photo recommended for better analysis", "severity": "low"},
        ],
        medications=[
            {"name": "Hydrocortisone Cream 1%", "dosage": "Apply thin layer", "frequency": "Twice daily on affected area", "duration": "7 days", "type": "topical", "notes": "Mild steroid. Do not use on face for more than 5 days. Avoid near eyes."},
            {"name": "Cetirizine", "dosage": "10mg", "frequency": "Once daily at night", "duration": "7 days", "type": "tablet", "notes": "For itching relief. May cause mild drowsiness."},
            {"name": "Calamine Lotion", "dosage": "Apply generously", "frequency": "3-4 times daily", "duration": "As needed", "type": "topical", "notes": "Soothing for itchy and inflamed skin. Shake well before use."},
        ],
        lifestyle=["Moisturize skin twice daily with fragrance-free lotion", "Wear loose, breathable cotton clothing", "Avoid hot showers — use lukewarm water", "Use mild, soap-free cleansers", "Keep nails short to prevent scratching damage"],
        precautions=["Do not scratch affected areas", "Avoid known irritants (harsh detergents, perfumes)", "Do not share towels or clothing", "Discontinue any new cosmetic product that may be a trigger"],
        recommended_tests=["Skin scraping for KOH mount (if fungal infection suspected)", "Allergy patch testing if recurrent", "Skin biopsy if lesion is atypical or persistent"],
        when_to_see_doctor="See a doctor if: rash spreads rapidly, blisters or pus formation, fever accompanying the rash, no improvement after 7 days of treatment, or rash affects large body areas.",
        urgency="routine",
    ),

    # 10 — Anxiety / Stress Disorder
    DiseaseProfile(
        name="Generalized Anxiety / Stress Disorder",
        keywords=["anxiety", "stress", "panic", "palpitations", "insomnia", "nervous", "restless", "worry", "racing heart"],
        base_confidence=0.74,
        severity="moderate",
        reasoning_template="The symptoms described ({symptoms}) are consistent with an anxiety or stress-related disorder. These conditions are very treatable with a combination of lifestyle changes, therapy, and sometimes medication. You are not alone.",
        findings=[
            {"finding": "Symptoms consistent with generalized anxiety disorder", "severity": "medium"},
            {"finding": "Physical symptoms may be stress-related (somatic anxiety)", "severity": "low"},
        ],
        medications=[
            {"name": "Escitalopram", "dosage": "5mg", "frequency": "Once daily in the morning", "duration": "As prescribed by psychiatrist", "type": "tablet", "notes": "SSRI antidepressant. Takes 2-4 weeks for full effect. Do not stop abruptly — consult doctor before discontinuing."},
            {"name": "Propranolol", "dosage": "10mg", "frequency": "As needed before stressful events", "duration": "Short-term", "type": "tablet", "notes": "Beta-blocker for physical symptoms (palpitations, tremor). Not for daily use without doctor guidance."},
            {"name": "Melatonin", "dosage": "3mg", "frequency": "Once at bedtime", "duration": "2-4 weeks", "type": "tablet", "notes": "For sleep support. Take 30 minutes before bedtime."},
        ],
        lifestyle=["Practice deep breathing exercises (4-7-8 technique) daily", "Exercise regularly — 30 minutes of moderate activity daily", "Limit caffeine and alcohol intake", "Maintain a consistent sleep schedule", "Practice mindfulness or meditation for 10 minutes daily", "Talk to someone you trust about your feelings"],
        precautions=["Do not self-prescribe psychiatric medications", "Avoid alcohol as a coping mechanism", "Limit social media and news consumption if triggering", "Seek professional help if symptoms interfere with daily life"],
        recommended_tests=["Thyroid Function Test (to rule out hyperthyroidism)", "Complete Blood Count", "Vitamin D and B12 levels"],
        when_to_see_doctor="Seek help immediately if: thoughts of self-harm or suicide, panic attacks lasting more than 20 minutes, inability to carry out daily activities, persistent insomnia for over 2 weeks, or chest pain that worsens with anxiety.",
        urgency="soon",
    ),

    # 11 — Conjunctivitis (Eye Infection)
    DiseaseProfile(
        name="Conjunctivitis (Eye Infection)",
        keywords=["eye pain", "red eye", "watery eyes", "eye discharge", "conjunctivitis", "itchy eyes", "pink eye", "swollen eyelid"],
        base_confidence=0.84,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) are indicative of conjunctivitis (pink eye), which can be viral, bacterial, or allergic in origin. Most cases resolve within 1-2 weeks with proper eye care and medication.",
        findings=[
            {"finding": "Symptoms consistent with conjunctivitis", "severity": "low"},
            {"finding": "Differentiation between viral, bacterial, and allergic types recommended", "severity": "low"},
        ],
        medications=[
            {"name": "Moxifloxacin Eye Drops", "dosage": "1 drop in affected eye", "frequency": "4 times daily", "duration": "7 days", "type": "topical", "notes": "Antibiotic eye drops. Wash hands before and after application. Do not touch dropper tip to eye."},
            {"name": "Carboxymethylcellulose Eye Drops (Refresh Tears)", "dosage": "1-2 drops", "frequency": "4-6 times daily", "duration": "7-14 days", "type": "topical", "notes": "Lubricating artificial tears. Safe for frequent use."},
            {"name": "Olopatadine Eye Drops", "dosage": "1 drop in each eye", "frequency": "Twice daily", "duration": "7 days", "type": "topical", "notes": "Anti-allergic eye drops if itching is prominent."},
        ],
        lifestyle=["Wash hands thoroughly before touching eyes", "Use cold compresses on closed eyes for relief", "Avoid wearing contact lenses until fully healed", "Do not share towels, pillows, or eye makeup", "Clean eye discharge gently with a clean damp cloth"],
        precautions=["Highly contagious — avoid close contact with others", "Do not rub or touch affected eyes", "Replace eye makeup and contact lens case", "Wash pillowcases and towels daily during infection"],
        recommended_tests=["Eye swab culture if severe or non-responsive to treatment", "Slit lamp examination if vision is affected"],
        when_to_see_doctor="See an eye doctor if: severe eye pain, significant vision changes, sensitivity to light, symptoms worsen after 48 hours of treatment, or thick yellow/green discharge persists.",
        urgency="routine",
    ),

    # 12 — Anemia / Iron Deficiency
    DiseaseProfile(
        name="Anemia / Iron Deficiency",
        keywords=["weakness", "fatigue", "pale", "dizzy", "iron", "anemia", "tired", "exhaustion", "breathless", "low hemoglobin"],
        base_confidence=0.75,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) suggest possible anemia or iron deficiency. Anemia reduces the blood's ability to carry oxygen, leading to fatigue and weakness. Dietary changes and supplements are usually effective, but underlying causes must be identified.",
        findings=[
            {"finding": "Symptoms consistent with iron deficiency anemia", "severity": "medium"},
            {"finding": "Underlying cause should be investigated (dietary, blood loss, chronic disease)", "severity": "medium"},
        ],
        medications=[
            {"name": "Ferrous Sulfate (Iron)", "dosage": "200mg", "frequency": "Twice daily on empty stomach", "duration": "3 months", "type": "tablet", "notes": "Take with vitamin C (orange juice) for better absorption. May cause dark stools — this is normal."},
            {"name": "Folic Acid", "dosage": "5mg", "frequency": "Once daily", "duration": "3 months", "type": "tablet", "notes": "Supports red blood cell production."},
            {"name": "Vitamin B12", "dosage": "1500mcg", "frequency": "Once daily", "duration": "3 months", "type": "tablet", "notes": "Essential if B12 deficiency is concurrent."},
        ],
        lifestyle=["Eat iron-rich foods: spinach, lentils, red meat, beans, fortified cereals", "Pair iron-rich meals with vitamin C sources (citrus fruits, tomatoes)", "Avoid tea/coffee with meals (inhibits iron absorption)", "Cook in cast iron cookware to boost iron content", "Eat beetroot, pomegranate, and dates regularly"],
        precautions=["Iron supplements may cause constipation — increase fiber intake", "Do not take iron with calcium or antacids", "Watch for signs of heavy menstrual bleeding (a common cause)", "Complete the full course even after feeling better"],
        recommended_tests=["Complete Blood Count (CBC) with peripheral smear", "Serum Iron, TIBC, and Ferritin levels", "Vitamin B12 and Folate levels", "Reticulocyte count", "Stool occult blood test if GI bleeding suspected"],
        when_to_see_doctor="See a doctor if: extreme fatigue interfering with daily life, rapid heartbeat or shortness of breath at rest, fainting episodes, blood in stool, or hemoglobin below 8 g/dL.",
        urgency="soon",
    ),

    # 13 — Acid Reflux / GERD
    DiseaseProfile(
        name="Acid Reflux / GERD (Gastroesophageal Reflux Disease)",
        keywords=["heartburn", "acid reflux", "chest burn", "burping", "acidity", "sour taste", "regurgitation"],
        base_confidence=0.82,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) are characteristic of acid reflux or GERD. Stomach acid flows back into the esophagus causing a burning sensation. Lifestyle changes combined with acid-reducing medication provide effective relief.",
        findings=[
            {"finding": "Symptoms consistent with gastroesophageal reflux (GERD)", "severity": "low"},
            {"finding": "No alarm features (dysphagia, weight loss) noted", "severity": "low"},
        ],
        medications=[
            {"name": "Pantoprazole", "dosage": "40mg", "frequency": "Once daily, 30 min before breakfast", "duration": "4-8 weeks", "type": "tablet", "notes": "Proton pump inhibitor. Take on empty stomach for best effect."},
            {"name": "Domperidone", "dosage": "10mg", "frequency": "Three times daily before meals", "duration": "2 weeks", "type": "tablet", "notes": "Improves stomach motility. Take 15-30 minutes before eating."},
            {"name": "Antacid Gel (Gelusil / Mucaine)", "dosage": "10ml", "frequency": "After meals and at bedtime", "duration": "As needed", "type": "syrup", "notes": "Provides quick relief from acidity. Shake well before use."},
        ],
        lifestyle=["Eat smaller, more frequent meals", "Avoid eating 2-3 hours before bedtime", "Elevate head of bed by 6 inches while sleeping", "Avoid trigger foods: spicy, citrus, tomato, chocolate, coffee", "Lose weight if overweight", "Avoid tight clothing around the waist"],
        precautions=["Do not lie down immediately after eating", "Quit smoking — it weakens the lower esophageal sphincter", "Limit alcohol and carbonated beverages", "Avoid NSAIDs (ibuprofen) as they worsen reflux"],
        recommended_tests=["Upper GI Endoscopy if symptoms persist beyond 8 weeks", "H. pylori test", "24-hour pH monitoring if diagnosis is uncertain"],
        when_to_see_doctor="See a doctor if: difficulty swallowing, unintentional weight loss, persistent vomiting, blood in vomit or stool, chest pain that could be cardiac, or symptoms not improving after 4 weeks of treatment.",
        urgency="routine",
    ),

    # 14 — Joint Pain / Arthritis
    DiseaseProfile(
        name="Joint Pain / Arthritis",
        keywords=["joint pain", "knee pain", "swelling joints", "arthritis", "stiff joints", "joint stiffness", "joint swelling"],
        base_confidence=0.76,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) suggest joint inflammation, possibly due to osteoarthritis, rheumatoid arthritis, or overuse injury. Proper diagnosis of the type of arthritis is important for targeted treatment.",
        findings=[
            {"finding": "Symptoms suggestive of joint inflammation / arthritis", "severity": "medium"},
            {"finding": "Type differentiation needed (osteo vs rheumatoid vs gouty)", "severity": "medium"},
        ],
        medications=[
            {"name": "Diclofenac", "dosage": "50mg", "frequency": "Twice daily after meals", "duration": "7 days", "type": "tablet", "notes": "Anti-inflammatory. Take with food. Avoid if history of stomach ulcers."},
            {"name": "Glucosamine + Chondroitin", "dosage": "1500mg + 1200mg", "frequency": "Once daily", "duration": "3-6 months", "type": "tablet", "notes": "Joint supplement. Benefits may take 6-8 weeks to appear."},
            {"name": "Diclofenac Gel", "dosage": "Apply thin layer", "frequency": "3 times daily on affected joint", "duration": "10 days", "type": "topical", "notes": "Topical pain relief. Massage gently. Wash hands after."},
        ],
        lifestyle=["Maintain a healthy weight to reduce joint stress", "Low-impact exercises: swimming, cycling, walking", "Apply warm compress for stiffness, cold pack for swelling", "Strengthen muscles around joints with targeted exercises", "Use supportive footwear and knee braces if needed"],
        precautions=["Avoid high-impact activities (running, jumping) during flare-ups", "Do not ignore morning stiffness lasting >30 minutes (may indicate RA)", "Avoid prolonged immobility — keep joints gently moving", "Protect joints during physical activities"],
        recommended_tests=["X-ray of affected joint", "ESR and CRP (inflammation markers)", "Rheumatoid Factor (RF) and Anti-CCP", "Serum Uric Acid (to rule out gout)", "MRI if soft tissue damage suspected"],
        when_to_see_doctor="See a doctor if: joint is red, hot, and severely swollen; morning stiffness lasts more than 1 hour; joint deformity developing; fever with joint pain; or significant limitation in daily activities.",
        urgency="soon",
    ),

    # 15 — Respiratory Infection (Bronchitis/Pneumonia)
    DiseaseProfile(
        name="Lower Respiratory Infection (Bronchitis / Suspected Pneumonia)",
        keywords=["breathing difficulty", "shortness of breath", "wheezing", "chest tightness", "chest congestion", "productive cough", "breathless"],
        base_confidence=0.72,
        severity="severe",
        reasoning_template="The symptoms ({symptoms}) raise concern for a lower respiratory tract infection such as bronchitis or pneumonia. Difficulty breathing and chest symptoms require prompt medical evaluation to rule out serious lung conditions.",
        findings=[
            {"finding": "Lower respiratory symptoms — bronchitis or pneumonia suspected", "severity": "high"},
            {"finding": "Oxygen saturation monitoring recommended", "severity": "high"},
        ],
        medications=[
            {"name": "Amoxicillin + Clavulanate", "dosage": "625mg", "frequency": "Twice daily", "duration": "7 days", "type": "tablet", "notes": "Antibiotic. Complete the full course. Take with food."},
            {"name": "Montelukast", "dosage": "10mg", "frequency": "Once daily at bedtime", "duration": "14 days", "type": "tablet", "notes": "Leukotriene receptor antagonist. Helps with breathing and wheezing."},
            {"name": "Salbutamol Inhaler", "dosage": "2 puffs", "frequency": "Every 4-6 hours as needed", "duration": "As needed", "type": "inhaler", "notes": "Bronchodilator for acute breathlessness. Shake before use. Use spacer if available."},
            {"name": "Guaifenesin Syrup", "dosage": "10ml", "frequency": "Three times daily", "duration": "5 days", "type": "syrup", "notes": "Expectorant to loosen mucus. Drink plenty of water alongside."},
        ],
        lifestyle=["Rest and avoid strenuous activity", "Use a humidifier to ease breathing", "Practice pursed-lip breathing when breathless", "Stay well hydrated — warm fluids help loosen congestion", "Sleep in a semi-upright position with pillows"],
        precautions=["Do not ignore worsening breathlessness", "Avoid smoking and secondhand smoke exposure", "Wear a mask in dusty or polluted environments", "Monitor temperature and oxygen saturation if possible"],
        recommended_tests=["Chest X-ray (PA view)", "Complete Blood Count", "Sputum Culture & Sensitivity", "Pulse Oximetry", "Arterial Blood Gas if SpO2 < 92%"],
        when_to_see_doctor="SEEK IMMEDIATE MEDICAL CARE if: severe breathlessness at rest, lips or fingertips turning blue, high fever above 103°F with rigors, coughing up blood, confusion or drowsiness, or oxygen saturation below 94%.",
        urgency="urgent",
    ),

    # 16 — Thyroid Disorder (Hypothyroidism)
    DiseaseProfile(
        name="Thyroid Disorder (Hypothyroidism)",
        keywords=["thyroid", "weight gain", "hair loss", "cold intolerance", "dry skin", "constipation", "sluggish", "tsh", "hypothyroid"],
        base_confidence=0.80,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) are suggestive of hypothyroidism — an underactive thyroid gland. This slows metabolism and affects nearly every organ. It is highly treatable with daily thyroid hormone replacement.",
        findings=[
            {"finding": "Symptoms consistent with hypothyroidism", "severity": "medium"},
            {"finding": "Thyroid function test recommended to confirm", "severity": "medium"},
        ],
        medications=[
            {"name": "Levothyroxine", "dosage": "50mcg", "frequency": "Once daily on empty stomach", "duration": "Ongoing (lifelong in most cases)", "type": "tablet", "notes": "Take 30-60 minutes before breakfast. Do not take with calcium or iron supplements."},
        ],
        lifestyle=["Eat a balanced diet rich in iodine (dairy, eggs, seafood)", "Exercise regularly to boost metabolism", "Manage stress through yoga and meditation", "Get adequate sleep (7-9 hours)", "Avoid excessive soy and cruciferous vegetables (raw)"],
        precautions=["Never adjust thyroid dose without medical advice", "Take medication at the same time daily", "Inform doctor before any surgery or pregnancy", "Separate thyroid medication from other supplements by 4 hours"],
        recommended_tests=["TSH (Thyroid Stimulating Hormone)", "Free T3 and Free T4", "Anti-TPO antibodies", "Thyroid ultrasound if goiter present"],
        when_to_see_doctor="See a doctor if: severe fatigue interfering with daily life, unexplained weight gain despite diet changes, depression, very slow heart rate, or swelling in the neck (goiter).",
        urgency="soon",
    ),

    # 17 — Asthma
    DiseaseProfile(
        name="Bronchial Asthma",
        keywords=["asthma", "wheezing attack", "night cough", "breathless exercise", "allergic asthma", "inhaler needed", "tight chest morning"],
        base_confidence=0.81,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) are consistent with bronchial asthma — a chronic inflammatory airway disease. Proper controller medication and trigger avoidance can achieve excellent symptom control.",
        findings=[
            {"finding": "Symptoms suggestive of bronchial asthma", "severity": "medium"},
            {"finding": "Airway reversibility testing recommended", "severity": "medium"},
        ],
        medications=[
            {"name": "Budesonide + Formoterol Inhaler", "dosage": "200/6mcg, 2 puffs", "frequency": "Twice daily", "duration": "Ongoing (controller)", "type": "inhaler", "notes": "Rinse mouth after use to prevent oral thrush. Use spacer for better delivery."},
            {"name": "Salbutamol Inhaler (Rescue)", "dosage": "2 puffs", "frequency": "As needed for acute symptoms", "duration": "As needed", "type": "inhaler", "notes": "Bronchodilator for quick relief. If using more than 3 times/week, asthma is not well controlled."},
            {"name": "Montelukast", "dosage": "10mg", "frequency": "Once daily at bedtime", "duration": "Ongoing", "type": "tablet", "notes": "Leukotriene modifier. Helps prevent exercise and allergy-triggered attacks."},
        ],
        lifestyle=["Identify and avoid personal triggers (dust, pollen, smoke, cold air)", "Use allergen-proof bedding covers", "Warm up before exercise", "Keep home well-ventilated and dust-free", "Practice breathing exercises (Buteyko, diaphragmatic breathing)"],
        precautions=["Always carry rescue inhaler", "Follow an asthma action plan", "Do not stop controller medication even when feeling well", "Get annual flu vaccination"],
        recommended_tests=["Pulmonary Function Test (PFT/Spirometry)", "Peak Expiratory Flow Rate (PEFR) monitoring", "Allergy testing (IgE, skin prick)", "Chest X-ray to rule out other causes"],
        when_to_see_doctor="SEEK EMERGENCY CARE if: severe breathlessness (cannot speak full sentences), lips turning blue, rescue inhaler provides no relief within 15 minutes, or peak flow drops below 50% of personal best.",
        urgency="soon",
    ),

    # 18 — Migraine with Aura
    DiseaseProfile(
        name="Migraine with Aura",
        keywords=["migraine aura", "visual disturbance", "throbbing headache", "light sensitivity", "photophobia", "nausea with headache", "one-sided headache"],
        base_confidence=0.77,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) indicate migraine with aura — a neurological condition characterized by throbbing headache, visual disturbances, and sensitivity to light/sound. Preventive therapy can significantly reduce attack frequency.",
        findings=[
            {"finding": "Symptoms consistent with migraine with aura", "severity": "medium"},
            {"finding": "Neurological evaluation recommended to exclude secondary causes", "severity": "medium"},
        ],
        medications=[
            {"name": "Sumatriptan", "dosage": "50mg", "frequency": "At onset of migraine, may repeat once after 2 hours", "duration": "As needed (max 200mg/day)", "type": "tablet", "notes": "Triptan — most effective when taken at first sign of headache. Do not use for aura phase."},
            {"name": "Naproxen", "dosage": "500mg", "frequency": "Twice daily during attack", "duration": "1-2 days", "type": "tablet", "notes": "Anti-inflammatory. Take with food. Alternative if triptans are contraindicated."},
            {"name": "Propranolol (Preventive)", "dosage": "40mg", "frequency": "Twice daily", "duration": "3-6 months minimum", "type": "tablet", "notes": "Beta-blocker for migraine prevention. Reduces attack frequency by 50%. Do not stop abruptly."},
        ],
        lifestyle=["Maintain regular sleep schedule — same bedtime and wake time", "Keep a migraine diary to identify triggers", "Stay hydrated and don't skip meals", "Reduce screen brightness and use blue light filters", "Practice relaxation techniques (progressive muscle relaxation)"],
        precautions=["Avoid known triggers (chocolate, aged cheese, red wine, MSG, bright lights)", "Do not overuse painkillers (risk of medication-overuse headache)", "Triptans are contraindicated in uncontrolled hypertension or heart disease", "Aura phase should not be treated with triptans"],
        recommended_tests=["Neurological examination", "MRI Brain (to exclude structural causes)", "Visual field testing if aura is prolonged"],
        when_to_see_doctor="Seek immediate care if: worst headache of your life, headache with fever and neck stiffness, aura lasting more than 60 minutes, new neurological symptoms (weakness, speech difficulty), or migraines suddenly changing in pattern.",
        urgency="soon",
    ),

    # 19 — Kidney Stones
    DiseaseProfile(
        name="Kidney Stones (Renal Calculi)",
        keywords=["kidney stone", "flank pain", "renal colic", "blood in urine", "sharp side pain", "kidney pain", "groin pain radiating"],
        base_confidence=0.79,
        severity="severe",
        reasoning_template="The symptoms ({symptoms}) are highly suggestive of kidney stones (renal calculi). The colicky pain pattern and possible hematuria are characteristic. Most stones under 5mm pass spontaneously; larger stones may need intervention.",
        findings=[
            {"finding": "Symptoms consistent with ureteral colic / kidney stones", "severity": "high"},
            {"finding": "Imaging recommended to confirm stone size and location", "severity": "high"},
        ],
        medications=[
            {"name": "Diclofenac", "dosage": "75mg", "frequency": "Twice daily (or IM injection for acute pain)", "duration": "3-5 days", "type": "tablet", "notes": "First-line for renal colic pain. Take with food."},
            {"name": "Tamsulosin", "dosage": "0.4mg", "frequency": "Once daily after meals", "duration": "2-4 weeks", "type": "capsule", "notes": "Alpha-blocker that relaxes the ureter to help stone passage. May cause dizziness — stand up slowly."},
            {"name": "Potassium Citrate", "dosage": "1080mg", "frequency": "Three times daily", "duration": "3 months", "type": "tablet", "notes": "Alkalinizes urine to prevent new stone formation. Dissolve in water."},
        ],
        lifestyle=["Drink at least 3 liters of water daily (aim for pale/clear urine)", "Reduce salt intake to less than 5g/day", "Limit animal protein (meat, fish) to moderate portions", "Eat calcium-rich foods (dairy) — do NOT restrict dietary calcium", "Reduce oxalate-rich foods (spinach, nuts, chocolate, tea) if calcium oxalate stones"],
        precautions=["Strain urine to catch passed stones for analysis", "Do not ignore recurrent episodes", "Avoid excessive vitamin C supplements (>500mg/day)", "Limit cola and sugary drinks"],
        recommended_tests=["Non-contrast CT Abdomen (gold standard)", "Kidney Ultrasound", "Urine Routine & Microscopy", "24-hour Urine Collection for stone metabolic workup", "Serum calcium, uric acid, creatinine"],
        when_to_see_doctor="SEEK EMERGENCY CARE if: unbearable pain not relieved by medication, fever with chills (indicates infected stone), complete inability to urinate, persistent vomiting, or both kidneys affected.",
        urgency="urgent",
    ),

    # 20 — Depression
    DiseaseProfile(
        name="Major Depressive Disorder",
        keywords=["depression", "depressed", "hopeless", "lost interest", "suicidal", "worthless", "crying", "no motivation", "sad all the time"],
        base_confidence=0.73,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) are consistent with major depressive disorder. Depression is a medical condition — not a character flaw — and it is highly treatable. Combination of therapy and medication shows the best outcomes.",
        findings=[
            {"finding": "Symptoms meeting criteria for major depressive episode", "severity": "medium"},
            {"finding": "Risk assessment and professional mental health evaluation recommended", "severity": "high"},
        ],
        medications=[
            {"name": "Sertraline", "dosage": "50mg", "frequency": "Once daily in the morning", "duration": "Minimum 6-12 months", "type": "tablet", "notes": "SSRI antidepressant. Takes 4-6 weeks for full effect. Do not stop abruptly — taper under medical guidance."},
            {"name": "Vitamin D3", "dosage": "60,000 IU", "frequency": "Once weekly for 8 weeks, then monthly", "duration": "As per levels", "type": "capsule", "notes": "Low vitamin D is associated with depression. Take with a fatty meal for better absorption."},
        ],
        lifestyle=["Engage in physical activity — even 20 minutes of walking helps", "Maintain a daily routine and set small achievable goals", "Stay connected with friends and family", "Limit alcohol — it worsens depression", "Practice gratitude journaling", "Get sunlight exposure in the morning (15-20 minutes)"],
        precautions=["NEVER ignore thoughts of self-harm — seek immediate help", "Do not self-medicate with alcohol or recreational drugs", "Inform a trusted person about how you're feeling", "Keep follow-up appointments with your mental health professional"],
        recommended_tests=["PHQ-9 Depression Screening Questionnaire", "Thyroid Function Test (to rule out hypothyroidism)", "Vitamin D and B12 levels", "Complete Blood Count"],
        when_to_see_doctor="SEEK IMMEDIATE HELP if: thoughts of suicide or self-harm, plan to hurt yourself, giving away possessions, feeling trapped with no way out, or sudden calmness after a period of deep depression. Crisis helpline: iCall 9152987821 / Vandrevala Foundation 1860-2662-345.",
        urgency="urgent",
    ),

    # 21 — Ear Infection (Otitis Media)
    DiseaseProfile(
        name="Ear Infection (Otitis Media)",
        keywords=["ear pain", "ear ache", "ear infection", "blocked ear", "hearing loss", "ear discharge", "ringing ear", "tinnitus"],
        base_confidence=0.81,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) suggest an ear infection (otitis media), which is an infection or inflammation of the middle ear. Most cases resolve with appropriate antibiotic treatment within 7-10 days.",
        findings=[
            {"finding": "Symptoms suggestive of acute otitis media", "severity": "low"},
            {"finding": "Otoscopic examination recommended for confirmation", "severity": "low"},
        ],
        medications=[
            {"name": "Amoxicillin", "dosage": "500mg", "frequency": "Three times daily", "duration": "7 days", "type": "capsule", "notes": "First-line antibiotic for ear infections. Complete the full course even if symptoms improve."},
            {"name": "Ibuprofen", "dosage": "400mg", "frequency": "Every 8 hours with food", "duration": "3-5 days", "type": "tablet", "notes": "For pain and inflammation. Take with food."},
            {"name": "Antibiotic Ear Drops (Ciprofloxacin)", "dosage": "4 drops in affected ear", "frequency": "Twice daily", "duration": "7 days", "type": "topical", "notes": "If outer ear is also involved. Warm drops to body temperature before instilling."},
        ],
        lifestyle=["Apply warm compress to the affected ear for pain relief", "Keep the ear dry — avoid swimming", "Do not insert anything into the ear canal", "Sleep with the affected ear facing up", "Stay hydrated and rest well"],
        precautions=["Do not use cotton buds or earbuds in the infected ear", "Avoid flying during acute infection (pressure changes worsen pain)", "Complete full antibiotic course to prevent resistance", "Watch for spread of infection (facial weakness, severe headache)"],
        recommended_tests=["Otoscopic examination", "Tympanometry if hearing loss persists", "Audiometry if recurrent infections", "CT Temporal Bone if complications suspected"],
        when_to_see_doctor="See a doctor if: fever above 102°F with ear pain, pus or blood draining from ear, facial drooping on the affected side, sudden hearing loss, or symptoms persist beyond 72 hours of antibiotics.",
        urgency="routine",
    ),

    # 22 — Dengue / Viral Fever
    DiseaseProfile(
        name="Dengue Fever / Viral Hemorrhagic Fever",
        keywords=["dengue", "platelet", "high fever", "body ache severe", "rash with fever", "joint pain with fever", "breakbone", "mosquito bite fever"],
        base_confidence=0.76,
        severity="severe",
        reasoning_template="The symptoms ({symptoms}) raise concern for dengue fever or a viral hemorrhagic fever, especially in endemic areas. Dengue requires close monitoring of platelet counts and hydration. Early detection prevents complications.",
        findings=[
            {"finding": "Symptoms consistent with dengue / viral hemorrhagic fever", "severity": "high"},
            {"finding": "Platelet monitoring and hydration are critical", "severity": "high"},
        ],
        medications=[
            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours (max 4g/day)", "duration": "5-7 days", "type": "tablet", "notes": "ONLY paracetamol for dengue fever. DO NOT take Ibuprofen, Aspirin, or Diclofenac — they increase bleeding risk."},
            {"name": "ORS (Oral Rehydration Solution)", "dosage": "1 sachet in 1L water", "frequency": "Sip throughout the day", "duration": "Until recovery", "type": "syrup", "notes": "Aggressive hydration is the cornerstone of dengue treatment. Aim for 3-4 liters daily."},
        ],
        lifestyle=["Rest completely — avoid any physical exertion", "Drink papaya leaf extract (shown to help platelet recovery)", "Eat light, easily digestible foods", "Monitor temperature every 4 hours", "Use mosquito nets and repellents to prevent spread"],
        precautions=["AVOID all NSAIDs (Ibuprofen, Aspirin, Diclofenac) — they cause bleeding", "Watch for warning signs during days 3-7 (critical phase)", "Do not self-medicate with antibiotics (dengue is viral)", "Prevent mosquito breeding around your home"],
        recommended_tests=["Complete Blood Count with Platelet Count (daily)", "Dengue NS1 Antigen (first 5 days)", "Dengue IgM/IgG Antibodies (after day 5)", "Liver Function Tests", "Hematocrit monitoring"],
        when_to_see_doctor="SEEK EMERGENCY CARE if: severe abdominal pain, persistent vomiting, bleeding (gums, nose, blood in vomit/stool), platelet count below 50,000, restlessness or drowsiness, rapid breathing, or cold clammy skin.",
        urgency="urgent",
    ),

    # 23 — Food Allergy / Anaphylaxis Risk
    DiseaseProfile(
        name="Food Allergy / Allergic Reaction",
        keywords=["food allergy", "allergic reaction", "swollen lips", "hives after eating", "throat swelling", "itching after food", "shellfish allergy", "nut allergy"],
        base_confidence=0.80,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) suggest an allergic reaction, possibly triggered by food. Allergic reactions can range from mild (hives) to life-threatening (anaphylaxis). Identifying the allergen and having an action plan is critical.",
        findings=[
            {"finding": "Symptoms consistent with IgE-mediated food allergy", "severity": "medium"},
            {"finding": "Risk of anaphylaxis — action plan needed", "severity": "high"},
        ],
        medications=[
            {"name": "Cetirizine", "dosage": "10mg", "frequency": "Once daily", "duration": "5-7 days", "type": "tablet", "notes": "Antihistamine for mild allergic reactions. Fast-acting."},
            {"name": "Prednisolone", "dosage": "40mg", "frequency": "Once daily in the morning", "duration": "3-5 days", "type": "tablet", "notes": "Short-course steroid for moderate reactions. Take with food. Do not extend without medical advice."},
            {"name": "Epinephrine Auto-Injector (EpiPen)", "dosage": "0.3mg", "frequency": "Single dose in outer thigh for anaphylaxis", "duration": "Emergency use only", "type": "injection", "notes": "CARRY AT ALL TIMES if history of anaphylaxis. Use immediately if throat swelling, difficulty breathing, or fainting."},
        ],
        lifestyle=["Read food labels meticulously", "Inform restaurants about your allergies before ordering", "Wear a medical alert bracelet", "Teach family/friends how to use your EpiPen", "Keep a food diary to identify trigger foods"],
        precautions=["Always carry emergency medication (antihistamine + EpiPen)", "Avoid cross-contaminated foods", "Be cautious with new cuisines and packaged foods", "Allergic reactions can worsen with each exposure"],
        recommended_tests=["Specific IgE blood test (RAST)", "Skin Prick Test for common allergens", "Oral Food Challenge (under medical supervision)", "Total IgE levels"],
        when_to_see_doctor="CALL EMERGENCY (112) IMMEDIATELY if: throat tightness or swelling, difficulty breathing, dizziness or fainting, rapid pulse, widespread hives with breathing difficulty, or any two organ systems affected (skin + GI, skin + respiratory).",
        urgency="urgent",
    ),

    # 24 — Vitamin D Deficiency
    DiseaseProfile(
        name="Vitamin D Deficiency",
        keywords=["vitamin d", "bone pain", "muscle weakness", "sun deficiency", "low vitamin d", "calcium deficiency", "rickets", "osteoporosis risk"],
        base_confidence=0.78,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) suggest vitamin D deficiency, which is extremely common, especially in people with limited sun exposure. Adequate supplementation and lifestyle changes can resolve symptoms within 8-12 weeks.",
        findings=[
            {"finding": "Symptoms consistent with vitamin D deficiency", "severity": "low"},
            {"finding": "Serum 25-OH vitamin D testing recommended", "severity": "low"},
        ],
        medications=[
            {"name": "Cholecalciferol (Vitamin D3)", "dosage": "60,000 IU", "frequency": "Once weekly for 8 weeks", "duration": "8 weeks (loading), then monthly maintenance", "type": "capsule", "notes": "Take with a fatty meal for optimal absorption. Follow up with blood test after 8 weeks."},
            {"name": "Calcium + Vitamin D3", "dosage": "500mg Calcium + 250 IU D3", "frequency": "Twice daily", "duration": "3-6 months", "type": "tablet", "notes": "Take with meals. Do not take with iron supplements simultaneously."},
        ],
        lifestyle=["Get 15-20 minutes of morning sunlight daily (before 10 AM)", "Eat vitamin D rich foods: fatty fish, egg yolks, fortified milk", "Include calcium-rich foods: dairy, green leafy vegetables, almonds", "Regular weight-bearing exercise to strengthen bones", "Avoid excessive caffeine (reduces calcium absorption)"],
        precautions=["Do not take mega-doses without medical supervision (toxicity risk)", "Separate calcium supplements from thyroid/iron medication by 4 hours", "Recheck levels after completing the loading dose", "Pregnant women should consult their OB-GYN for appropriate dosing"],
        recommended_tests=["Serum 25-Hydroxyvitamin D", "Serum Calcium and Phosphorus", "Parathyroid Hormone (PTH)", "DEXA scan if osteoporosis suspected"],
        when_to_see_doctor="See a doctor if: bone pain that worsens, frequent fractures from minor injuries, severe muscle cramps, numbness or tingling in hands/feet, or symptoms persist despite 8 weeks of supplementation.",
        urgency="routine",
    ),

    # 25 — Gastric Ulcer / Peptic Ulcer Disease
    DiseaseProfile(
        name="Peptic Ulcer Disease (Gastric / Duodenal Ulcer)",
        keywords=["ulcer", "stomach ulcer", "burning stomach", "pain after eating", "empty stomach pain", "peptic", "h pylori", "black stool"],
        base_confidence=0.79,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) suggest peptic ulcer disease — erosion of the stomach or duodenal lining, commonly caused by H. pylori infection or NSAID use. Treatment with acid-suppressing medication and antibiotics (if H. pylori positive) achieves healing in 4-8 weeks.",
        findings=[
            {"finding": "Symptoms consistent with peptic ulcer disease", "severity": "medium"},
            {"finding": "H. pylori testing recommended", "severity": "medium"},
        ],
        medications=[
            {"name": "Esomeprazole", "dosage": "40mg", "frequency": "Once daily before breakfast", "duration": "8 weeks", "type": "capsule", "notes": "Proton pump inhibitor. Take 30 min before first meal."},
            {"name": "Amoxicillin", "dosage": "1000mg", "frequency": "Twice daily", "duration": "14 days (if H. pylori positive)", "type": "capsule", "notes": "Part of H. pylori triple therapy. Complete the full course."},
            {"name": "Clarithromycin", "dosage": "500mg", "frequency": "Twice daily", "duration": "14 days (if H. pylori positive)", "type": "tablet", "notes": "Second antibiotic in triple therapy. May cause metallic taste."},
            {"name": "Sucralfate", "dosage": "1g", "frequency": "Four times daily (before meals and at bedtime)", "duration": "4-8 weeks", "type": "tablet", "notes": "Mucosal protectant. Take on empty stomach. Space 2 hours from other medications."},
        ],
        lifestyle=["Eat small, frequent meals at regular intervals", "Avoid spicy, acidic, and fried foods", "Quit smoking — it delays ulcer healing", "Limit alcohol and carbonated beverages", "Manage stress through relaxation techniques"],
        precautions=["Stop all NSAIDs (Ibuprofen, Diclofenac, Aspirin) unless medically essential", "Do not skip PPI doses — consistent acid suppression is key", "Report black/tarry stools immediately (indicates GI bleeding)", "Complete H. pylori eradication therapy fully"],
        recommended_tests=["Upper GI Endoscopy (OGD)", "H. pylori test (urea breath test or stool antigen)", "Complete Blood Count (to check for anemia from bleeding)", "Fecal Occult Blood Test"],
        when_to_see_doctor="SEEK EMERGENCY CARE if: vomiting blood or coffee-ground material, black tarry stools, sudden severe abdominal pain (possible perforation), fainting or dizziness, or rapid heart rate with pale skin.",
        urgency="soon",
    ),

    # 26 — Sciatica / Lumbar Radiculopathy
    DiseaseProfile(
        name="Sciatica (Lumbar Radiculopathy)",
        keywords=["sciatica", "leg pain from back", "shooting leg pain", "numbness in leg", "tingling leg", "herniated disc", "slipped disc", "nerve pain"],
        base_confidence=0.75,
        keyword_weights={"sciatica": 2.0, "herniated disc": 2.0, "slipped disc": 2.0, "shooting leg pain": 1.5},
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) point to sciatica — pain radiating along the sciatic nerve from the lower back down through the leg. This is commonly caused by a herniated disc or spinal stenosis compressing a nerve root.",
        findings=[
            {"finding": "Symptoms consistent with lumbar radiculopathy (sciatica)", "severity": "medium"},
            {"finding": "MRI recommended to evaluate disc/nerve involvement", "severity": "medium"},
        ],
        medications=[
            {"name": "Pregabalin", "dosage": "75mg", "frequency": "Twice daily", "duration": "4-8 weeks", "type": "capsule", "notes": "Neuropathic pain medication. Start low and increase gradually. May cause dizziness initially."},
            {"name": "Diclofenac", "dosage": "50mg", "frequency": "Twice daily after meals", "duration": "7 days", "type": "tablet", "notes": "Anti-inflammatory for acute pain. Take with food."},
            {"name": "Methylcobalamin (Vitamin B12)", "dosage": "1500mcg", "frequency": "Once daily", "duration": "3 months", "type": "tablet", "notes": "Supports nerve repair and regeneration."},
        ],
        lifestyle=["Apply ice pack for first 48 hours, then switch to heat", "Gentle stretching — piriformis stretch, knee-to-chest stretch", "Walk short distances to keep active (avoid bed rest)", "Use proper lifting technique (bend knees, not back)", "Consider physiotherapy for core strengthening"],
        precautions=["Avoid heavy lifting, bending, and twisting", "Do not sit for more than 30 minutes at a stretch", "Use a lumbar support cushion when sitting", "Avoid high-impact activities until pain subsides"],
        recommended_tests=["MRI Lumbosacral Spine", "Nerve Conduction Study (NCS) / EMG", "X-ray Lumbosacral Spine (for bony causes)", "Straight Leg Raise (SLR) test"],
        when_to_see_doctor="SEEK URGENT CARE if: loss of bladder or bowel control (cauda equina syndrome), progressive weakness in leg or foot, numbness in saddle area (groin/inner thigh), or pain worsening despite 6 weeks of treatment.",
        urgency="soon",
    ),

    # 27 — Malaria
    DiseaseProfile(
        name="Malaria",
        keywords=["malaria", "chills and fever", "rigors", "intermittent fever", "sweating with fever", "mosquito fever", "spleen pain"],
        base_confidence=0.77,
        severity="severe",
        reasoning_template="The symptoms ({symptoms}) in the context of possible mosquito exposure suggest malaria. This is a parasitic infection transmitted by Anopheles mosquitoes that requires prompt diagnosis and treatment to prevent severe complications.",
        findings=[
            {"finding": "Symptoms consistent with malaria (Plasmodium infection)", "severity": "high"},
            {"finding": "Blood smear and rapid diagnostic test needed urgently", "severity": "high"},
        ],
        medications=[
            {"name": "Artemether + Lumefantrine (ACT)", "dosage": "80/480mg", "frequency": "Twice daily for 3 days (6 doses total)", "duration": "3 days", "type": "tablet", "notes": "Take with fatty food for better absorption. Complete all 6 doses at 0, 8, 24, 36, 48, 60 hours."},
            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours as needed", "duration": "Until fever resolves", "type": "tablet", "notes": "For fever management. Do NOT use Aspirin."},
            {"name": "Primaquine", "dosage": "15mg", "frequency": "Once daily for 14 days", "duration": "14 days (for P. vivax/ovale)", "type": "tablet", "notes": "To eliminate liver-stage parasites and prevent relapse. G6PD test required before starting — contraindicated in G6PD deficiency."},
        ],
        lifestyle=["Complete bed rest until fever subsides", "Increase fluid intake significantly", "Eat easily digestible, high-calorie food", "Use mosquito nets and repellents during recovery", "Monitor temperature every 4 hours"],
        precautions=["Complete the full antimalarial course even if feeling better", "G6PD testing is mandatory before primaquine", "Watch for signs of severe malaria (confusion, convulsions, dark urine)", "Prevent mosquito bites to avoid re-infection and transmission"],
        recommended_tests=["Peripheral Blood Smear (thick and thin film)", "Malaria Rapid Diagnostic Test (RDT)", "Complete Blood Count with Platelet Count", "Liver and Kidney Function Tests", "G6PD test before primaquine"],
        when_to_see_doctor="SEEK EMERGENCY CARE if: altered consciousness or confusion, repeated convulsions, severe anemia (extreme pallor), dark/cola-colored urine, jaundice, severe vomiting preventing oral medication, or respiratory distress.",
        urgency="urgent",
    ),

    # 28 — Gastroesophageal Reflux in Pregnancy / Morning Sickness
    DiseaseProfile(
        name="Pregnancy-Related Nausea / Morning Sickness",
        keywords=["morning sickness", "pregnancy nausea", "vomiting pregnancy", "pregnant and nauseous", "hyperemesis", "nausea early pregnancy"],
        base_confidence=0.81,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) are consistent with pregnancy-related nausea (morning sickness), which affects up to 80% of pregnancies. It typically peaks at 8-12 weeks and resolves by 16-20 weeks. Severe cases (hyperemesis gravidarum) may need medical intervention.",
        findings=[
            {"finding": "Symptoms consistent with pregnancy-related nausea/morning sickness", "severity": "low"},
            {"finding": "Hyperemesis gravidarum should be excluded if symptoms are severe", "severity": "medium"},
        ],
        medications=[
            {"name": "Doxylamine + Vitamin B6 (Pyridoxine)", "dosage": "10mg/10mg", "frequency": "At bedtime (may add morning and afternoon doses)", "duration": "As needed during first trimester", "type": "tablet", "notes": "First-line for pregnancy nausea. FDA Category A — safe in pregnancy."},
            {"name": "Ginger Capsules", "dosage": "250mg", "frequency": "Four times daily", "duration": "As needed", "type": "capsule", "notes": "Natural remedy with evidence for pregnancy nausea. Can also sip ginger tea."},
            {"name": "Ondansetron (if severe)", "dosage": "4mg", "frequency": "Every 8 hours as needed", "duration": "Short-term only", "type": "tablet", "notes": "Reserve for severe cases not responding to first-line therapy. Use only after doctor consultation."},
        ],
        lifestyle=["Eat small, frequent meals (every 2 hours)", "Keep plain crackers or dry toast by the bed — eat before rising", "Avoid strong smells, spicy, and fatty foods", "Stay hydrated with small sips — try cold water, lemonade, or coconut water", "Get fresh air and avoid stuffy environments"],
        precautions=["Do NOT take any medication without OB-GYN approval", "Watch for signs of hyperemesis: inability to keep any food/liquid down, weight loss >5%", "Ensure adequate folic acid and prenatal vitamin intake", "Report any vaginal bleeding or abdominal pain immediately"],
        recommended_tests=["Urine pregnancy test / serum beta-hCG", "Urine ketones (if not keeping food down)", "Thyroid function test", "Complete blood count", "Electrolytes if severe vomiting"],
        when_to_see_doctor="See your OB-GYN if: unable to keep any food or liquid down for 24 hours, weight loss of more than 2kg, dark concentrated urine, dizziness or fainting, blood in vomit, or fever above 100.4°F.",
        urgency="soon",
    ),

    # 29 — Chickenpox / Varicella
    DiseaseProfile(
        name="Chickenpox (Varicella)",
        keywords=["chickenpox", "varicella", "itchy blisters", "vesicular rash", "pox", "fluid filled blisters", "rash with fever child"],
        base_confidence=0.83,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) are characteristic of chickenpox (varicella), a highly contagious viral infection caused by the varicella-zoster virus. It typically presents with an itchy vesicular rash, fever, and malaise. Most cases are self-limiting in children.",
        findings=[
            {"finding": "Symptoms and rash pattern consistent with varicella (chickenpox)", "severity": "low"},
            {"finding": "Highly contagious — isolation until all lesions have crusted", "severity": "medium"},
        ],
        medications=[
            {"name": "Calamine Lotion", "dosage": "Apply to itchy areas", "frequency": "3-4 times daily", "duration": "Until lesions crust over (7-10 days)", "type": "topical", "notes": "Soothing for itchy blisters. Pat on gently, do not rub."},
            {"name": "Paracetamol", "dosage": "500mg (adult) / weight-based for children", "frequency": "Every 6 hours as needed", "duration": "3-5 days", "type": "tablet", "notes": "For fever. DO NOT give Aspirin to children (risk of Reye's syndrome)."},
            {"name": "Acyclovir", "dosage": "800mg", "frequency": "Five times daily for adults", "duration": "7 days", "type": "tablet", "notes": "Antiviral — most effective if started within 24 hours of rash onset. Recommended for adults, adolescents, and immunocompromised patients."},
        ],
        lifestyle=["Keep cool — heat worsens itching", "Trim fingernails short to prevent scratching and scarring", "Wear loose cotton clothing", "Take lukewarm oatmeal baths for itch relief", "Stay isolated at home until ALL blisters have crusted (usually 5-7 days)"],
        precautions=["Highly contagious from 2 days before rash until all lesions crust", "Avoid contact with pregnant women, newborns, and immunocompromised people", "Do NOT give Aspirin or Ibuprofen to children with chickenpox", "Avoid scratching — can lead to secondary bacterial infection and scarring"],
        recommended_tests=["Usually clinical diagnosis (no tests needed)", "Tzanck smear or PCR if diagnosis uncertain", "Varicella IgM antibodies if needed"],
        when_to_see_doctor="See a doctor if: high fever persisting beyond 4 days, rash becomes very red/warm/tender (secondary infection), difficulty breathing, confusion or drowsiness, rash near eyes, or patient is pregnant/immunocompromised/newborn.",
        urgency="routine",
    ),

    # 30 — Insomnia / Sleep Disorder
    DiseaseProfile(
        name="Insomnia / Sleep Disorder",
        keywords=["insomnia", "can't sleep", "sleep problem", "waking up at night", "poor sleep", "sleepless", "difficulty sleeping", "not sleeping"],
        base_confidence=0.76,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) indicate insomnia or a sleep disorder. Chronic sleep deprivation affects physical health, mental well-being, and daily functioning. Cognitive behavioral therapy for insomnia (CBT-I) is the gold standard treatment.",
        findings=[
            {"finding": "Symptoms consistent with insomnia / sleep disorder", "severity": "low"},
            {"finding": "Underlying causes (anxiety, depression, medical conditions) should be evaluated", "severity": "medium"},
        ],
        medications=[
            {"name": "Melatonin", "dosage": "3-5mg", "frequency": "Once, 30 minutes before bedtime", "duration": "2-4 weeks", "type": "tablet", "notes": "Natural sleep hormone supplement. Helps regulate sleep-wake cycle. Not habit-forming."},
            {"name": "Zolpidem", "dosage": "5mg", "frequency": "Once at bedtime", "duration": "2-4 weeks maximum", "type": "tablet", "notes": "Prescription sleep aid. Use only short-term and under doctor supervision. Do not drive after taking."},
        ],
        lifestyle=["Follow strict sleep hygiene: same bedtime and wake time every day", "Avoid screens (phone, TV, laptop) 1 hour before bed", "Keep bedroom cool, dark, and quiet", "Avoid caffeine after 2 PM and alcohol before bed", "Exercise regularly but not within 3 hours of bedtime", "Try relaxation techniques: 4-7-8 breathing, progressive muscle relaxation", "Use bed ONLY for sleep — no work, eating, or scrolling"],
        precautions=["Do not become dependent on sleeping pills", "Avoid napping for more than 20 minutes during the day", "Limit fluid intake before bed to avoid nighttime bathroom trips", "Seek help for underlying anxiety or depression"],
        recommended_tests=["Sleep diary (2-week tracking)", "Epworth Sleepiness Scale questionnaire", "Polysomnography (sleep study) if sleep apnea suspected", "Thyroid function test", "Iron studies (restless legs syndrome)"],
        when_to_see_doctor="See a doctor if: insomnia persists beyond 4 weeks despite good sleep hygiene, you snore loudly with pauses in breathing (sleep apnea), excessive daytime sleepiness causing safety concerns (driving), or insomnia is accompanied by depression or anxiety.",
        urgency="routine",
    ),

    # 31 — Polycystic Ovary Syndrome (PCOS)
    DiseaseProfile(
        name="Polycystic Ovary Syndrome (PCOS)",
        keywords=["pcos", "irregular periods", "missed period", "acne hormonal", "hirsutism", "facial hair women", "weight gain women", "ovarian cyst", "infertility female"],
        base_confidence=0.78,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) are suggestive of Polycystic Ovary Syndrome (PCOS), a hormonal disorder common in women of reproductive age. PCOS is manageable with lifestyle changes, hormonal therapy, and metabolic control.",
        findings=[
            {"finding": "Symptoms consistent with PCOS / hormonal imbalance", "severity": "medium"},
            {"finding": "Hormonal panel and pelvic ultrasound recommended", "severity": "medium"},
        ],
        medications=[
            {"name": "Metformin", "dosage": "500mg", "frequency": "Twice daily with meals", "duration": "Ongoing (as prescribed)", "type": "tablet", "notes": "Improves insulin resistance. Start low, increase gradually. GI upset common initially."},
            {"name": "Oral Contraceptive Pill (Ethinyl Estradiol + Drospirenone)", "dosage": "1 tablet", "frequency": "Once daily for 21 days, 7 days break", "duration": "As prescribed by gynecologist", "type": "tablet", "notes": "Regulates periods, reduces acne and hirsutism. Use only under medical supervision."},
            {"name": "Spironolactone", "dosage": "50mg", "frequency": "Once daily", "duration": "3-6 months", "type": "tablet", "notes": "Anti-androgen for hirsutism and acne. Avoid in pregnancy. Monitor potassium levels."},
        ],
        lifestyle=["Maintain a healthy weight — even 5% weight loss improves symptoms", "Follow a low-glycemic-index diet (whole grains, vegetables, lean protein)", "Exercise 150 minutes per week (walking, yoga, swimming)", "Manage stress through meditation and relaxation", "Track menstrual cycles with an app"],
        precautions=["Do not ignore irregular periods — seek evaluation", "Spironolactone must be used with contraception (teratogenic)", "Monitor blood sugar regularly if on Metformin", "Watch for signs of diabetes and metabolic syndrome"],
        recommended_tests=["Pelvic Ultrasound (transvaginal)", "Hormonal panel: LH, FSH, Testosterone, DHEAS", "Fasting Blood Sugar and HbA1c", "Lipid Profile", "Thyroid Function Test", "Prolactin levels"],
        when_to_see_doctor="See a gynecologist if: periods absent for more than 3 months, heavy or prolonged bleeding, difficulty conceiving, rapid weight gain, or signs of depression.",
        urgency="soon",
    ),

    # 32 — Gout
    DiseaseProfile(
        name="Gout (Uric Acid Arthritis)",
        keywords=["gout", "uric acid", "big toe pain", "swollen toe", "gouty arthritis", "tophi", "joint redness hot"],
        base_confidence=0.80,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) are characteristic of gout — a form of inflammatory arthritis caused by elevated uric acid levels. Acute attacks are extremely painful but highly treatable. Long-term uric acid control prevents future flares.",
        findings=[
            {"finding": "Symptoms consistent with acute gouty arthritis", "severity": "medium"},
            {"finding": "Serum uric acid and joint fluid analysis recommended", "severity": "medium"},
        ],
        medications=[
            {"name": "Colchicine", "dosage": "0.5mg", "frequency": "Twice daily during acute attack", "duration": "3-5 days", "type": "tablet", "notes": "Most effective within 12 hours of attack onset. May cause diarrhea."},
            {"name": "Naproxen", "dosage": "500mg", "frequency": "Twice daily with food", "duration": "5-7 days", "type": "tablet", "notes": "Anti-inflammatory for acute flare. Take with food. Avoid if kidney issues."},
            {"name": "Allopurinol", "dosage": "100mg", "frequency": "Once daily (increase gradually to 300mg)", "duration": "Ongoing (long-term prevention)", "type": "tablet", "notes": "Uric acid lowering therapy. Start ONLY after acute attack resolves. Never start during a flare."},
            {"name": "Febuxostat", "dosage": "40mg", "frequency": "Once daily", "duration": "Ongoing (if allopurinol intolerant)", "type": "tablet", "notes": "Alternative to Allopurinol. Monitor liver function periodically."},
        ],
        lifestyle=["Drink at least 3 liters of water daily", "Avoid high-purine foods: red meat, organ meats, shellfish", "Limit alcohol, especially beer and spirits", "Reduce fructose-sweetened drinks", "Maintain a healthy weight — avoid crash diets"],
        precautions=["Do NOT start Allopurinol during an acute attack", "Avoid Aspirin (increases uric acid)", "Diuretics can worsen gout — inform your doctor", "Keep the affected joint elevated and apply ice"],
        recommended_tests=["Serum Uric Acid", "Joint fluid analysis (polarized microscopy for crystals)", "Kidney Function Test", "Complete Blood Count", "X-ray of affected joint"],
        when_to_see_doctor="See a doctor if: joint is extremely red/hot/swollen, fever with joint pain, attacks becoming more frequent, tophi (hard lumps) forming near joints, or kidney stone symptoms.",
        urgency="soon",
    ),

    # 33 — Typhoid Fever
    DiseaseProfile(
        name="Typhoid Fever (Enteric Fever)",
        keywords=["typhoid", "prolonged fever", "step ladder fever", "abdominal pain with fever", "widal test", "rose spots", "fever 10 days"],
        base_confidence=0.78,
        severity="severe",
        reasoning_template="The symptoms ({symptoms}) raise concern for typhoid fever (enteric fever), a bacterial infection caused by Salmonella typhi. Common in areas with poor sanitation, typhoid requires antibiotic treatment and can lead to serious complications if untreated.",
        findings=[
            {"finding": "Symptoms consistent with enteric fever / typhoid", "severity": "high"},
            {"finding": "Blood culture and Widal test recommended", "severity": "high"},
        ],
        medications=[
            {"name": "Azithromycin", "dosage": "500mg", "frequency": "Once daily", "duration": "7 days", "type": "tablet", "notes": "First-line antibiotic for uncomplicated typhoid. Complete the full course."},
            {"name": "Cefixime", "dosage": "200mg", "frequency": "Twice daily", "duration": "14 days", "type": "tablet", "notes": "Alternative oral antibiotic. Take with or without food."},
            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours as needed", "duration": "Until fever resolves", "type": "tablet", "notes": "For fever management. Avoid NSAIDs."},
            {"name": "ORS (Oral Rehydration Solution)", "dosage": "1 sachet in 1L water", "frequency": "Sip throughout the day", "duration": "Until recovery", "type": "syrup", "notes": "Maintain hydration. Aim for 2-3 liters daily."},
        ],
        lifestyle=["Complete bed rest during fever", "Eat soft, easily digestible food (khichdi, dal, rice)", "Drink boiled or filtered water only", "Maintain strict hand hygiene", "Avoid raw vegetables and street food during recovery"],
        precautions=["Complete the full antibiotic course to prevent relapse and carrier state", "Typhoid carriers can spread infection — follow hygiene strictly", "Avoid cooking for others until cleared by doctor", "Get typhoid vaccination for prevention"],
        recommended_tests=["Blood Culture (gold standard)", "Widal Test", "Complete Blood Count", "Liver Function Test", "Stool Culture"],
        when_to_see_doctor="SEEK IMMEDIATE CARE if: fever above 104°F, severe abdominal pain or distension, blood in stool, confusion or altered consciousness, persistent vomiting, or signs of intestinal perforation.",
        urgency="urgent",
    ),

    # 34 — Tuberculosis
    DiseaseProfile(
        name="Tuberculosis (TB)",
        keywords=["tuberculosis", "tb", "persistent cough", "cough 3 weeks", "night sweats", "weight loss cough", "blood in sputum", "hemoptysis"],
        base_confidence=0.74,
        severity="severe",
        reasoning_template="The symptoms ({symptoms}) raise concern for tuberculosis (TB), particularly given the duration and associated features. TB is a curable infectious disease that requires a prolonged multi-drug antibiotic regimen. Early detection and treatment are crucial.",
        findings=[
            {"finding": "Symptoms suggestive of pulmonary tuberculosis", "severity": "high"},
            {"finding": "Sputum examination and chest imaging urgently needed", "severity": "high"},
        ],
        medications=[
            {"name": "Isoniazid (INH)", "dosage": "300mg", "frequency": "Once daily", "duration": "6 months (intensive + continuation)", "type": "tablet", "notes": "Core TB drug. Take on empty stomach. Take with Pyridoxine (B6) to prevent neuropathy."},
            {"name": "Rifampicin", "dosage": "450-600mg (weight-based)", "frequency": "Once daily before breakfast", "duration": "6 months", "type": "capsule", "notes": "Turns urine/tears orange-red — this is normal. Avoid alcohol."},
            {"name": "Pyrazinamide", "dosage": "1500mg", "frequency": "Once daily", "duration": "2 months (intensive phase)", "type": "tablet", "notes": "Used in initial intensive phase. May increase uric acid levels."},
            {"name": "Ethambutol", "dosage": "800-1200mg (weight-based)", "frequency": "Once daily", "duration": "2 months (intensive phase)", "type": "tablet", "notes": "Report any vision changes immediately. Eye test recommended before and during treatment."},
            {"name": "Pyridoxine (Vitamin B6)", "dosage": "10mg", "frequency": "Once daily", "duration": "Throughout TB treatment", "type": "tablet", "notes": "Prevents INH-induced peripheral neuropathy."},
        ],
        lifestyle=["Complete the full treatment course (DOTS) — no exceptions", "Eat a nutritious, high-protein diet", "Rest well during the intensive phase", "Ensure good ventilation in living spaces", "Cover mouth when coughing — wear a mask"],
        precautions=["NEVER stop TB treatment early — leads to drug-resistant TB", "Avoid alcohol completely during treatment", "Report vision changes immediately (Ethambutol side effect)", "Infectious until 2 weeks of effective treatment — isolate if possible"],
        recommended_tests=["Sputum for AFB (Acid-Fast Bacilli) — 2 samples", "Chest X-ray PA view", "GeneXpert MTB/RIF (rapid molecular test)", "Mantoux / Tuberculin Skin Test (TST)", "Liver Function Test (baseline and periodic)", "Complete Blood Count"],
        when_to_see_doctor="SEEK IMMEDIATE CARE if: coughing up blood, severe chest pain, high fever with rigors, significant weight loss, enlarged lymph nodes, or symptoms in close contacts.",
        urgency="urgent",
    ),

    # 35 — Vertigo / BPPV
    DiseaseProfile(
        name="Vertigo / Benign Paroxysmal Positional Vertigo (BPPV)",
        keywords=["vertigo", "spinning", "room spinning", "dizziness turning", "balance problem", "giddiness", "nausea with dizziness", "positional dizziness"],
        base_confidence=0.79,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) are consistent with vertigo, most likely BPPV — a common inner ear disorder where displaced calcium crystals cause brief spinning episodes triggered by head position changes. It is benign and treatable with repositioning maneuvers.",
        findings=[
            {"finding": "Symptoms suggestive of BPPV / peripheral vertigo", "severity": "low"},
            {"finding": "Dix-Hallpike test recommended for confirmation", "severity": "low"},
        ],
        medications=[
            {"name": "Betahistine", "dosage": "16mg", "frequency": "Three times daily", "duration": "2-4 weeks", "type": "tablet", "notes": "Improves inner ear blood flow. Take with food."},
            {"name": "Cinnarizine", "dosage": "25mg", "frequency": "Three times daily", "duration": "1-2 weeks", "type": "tablet", "notes": "Anti-vertigo. May cause drowsiness. Avoid driving."},
            {"name": "Domperidone", "dosage": "10mg", "frequency": "Three times daily before meals", "duration": "5-7 days", "type": "tablet", "notes": "For associated nausea and vomiting."},
        ],
        lifestyle=["Perform Epley maneuver (guided by a physiotherapist initially)", "Avoid sudden head movements and position changes", "Get up slowly from bed — sit for a minute before standing", "Stay hydrated", "Vestibular rehabilitation exercises as prescribed"],
        precautions=["Avoid driving during acute vertigo episodes", "Do not climb heights or operate heavy machinery", "Keep the home well-lit to prevent falls", "Sleep with head slightly elevated"],
        recommended_tests=["Dix-Hallpike Test", "Audiometry", "MRI Brain (if central cause suspected)", "Electronystagmography (ENG)"],
        when_to_see_doctor="See a doctor if: vertigo lasts more than 24 hours continuously, hearing loss, severe headache with vertigo, double vision, slurred speech, difficulty walking, or numbness/weakness (stroke warning signs).",
        urgency="routine",
    ),

    # 36 — Irritable Bowel Syndrome (IBS)
    DiseaseProfile(
        name="Irritable Bowel Syndrome (IBS)",
        keywords=["ibs", "irritable bowel", "bloating", "abdominal cramps", "alternating diarrhea constipation", "mucus in stool", "gas", "flatulence", "bowel habit change"],
        base_confidence=0.76,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) are consistent with Irritable Bowel Syndrome (IBS), a functional gastrointestinal disorder. IBS does not cause structural damage but significantly affects quality of life. Management focuses on diet, stress reduction, and symptom-targeted medication.",
        findings=[
            {"finding": "Symptoms meet criteria for IBS (Rome IV criteria)", "severity": "low"},
            {"finding": "Organic causes should be excluded in patients over 40 or with alarm features", "severity": "medium"},
        ],
        medications=[
            {"name": "Mebeverine", "dosage": "135mg", "frequency": "Three times daily before meals", "duration": "4-8 weeks", "type": "tablet", "notes": "Antispasmodic for abdominal cramps. Take 20 minutes before meals."},
            {"name": "Rifaximin", "dosage": "550mg", "frequency": "Three times daily", "duration": "14 days", "type": "tablet", "notes": "Non-absorbable antibiotic for IBS with bloating. May be repeated."},
            {"name": "Psyllium Husk (Isabgol)", "dosage": "1 tablespoon in water", "frequency": "Once daily at bedtime", "duration": "Ongoing", "type": "syrup", "notes": "Soluble fiber supplement. Helps both diarrhea and constipation. Drink plenty of water with it."},
            {"name": "Probiotics (Lactobacillus)", "dosage": "1 capsule", "frequency": "Once daily", "duration": "3 months", "type": "capsule", "notes": "Supports gut microbiome balance. Take on empty stomach."},
        ],
        lifestyle=["Follow a low-FODMAP diet (guided by a dietitian)", "Eat regular meals at fixed times — do not skip meals", "Identify and avoid trigger foods (keep a food diary)", "Exercise regularly — 30 minutes of walking daily", "Manage stress — IBS is strongly stress-linked"],
        precautions=["Do not ignore alarm symptoms (blood in stool, weight loss, fever)", "Avoid excessive caffeine and carbonated drinks", "Limit artificial sweeteners (sorbitol, xylitol)", "Gradual fiber increase — too fast causes more bloating"],
        recommended_tests=["Complete Blood Count", "Celiac Panel (tTG-IgA)", "Stool examination for occult blood", "Thyroid Function Test", "Colonoscopy if age >40 or alarm features present"],
        when_to_see_doctor="See a doctor if: blood in stool, unintentional weight loss, symptoms waking you from sleep, family history of colon cancer or IBD, onset after age 50, or progressive worsening despite treatment.",
        urgency="routine",
    ),

    # 37 — Gallstones (Cholelithiasis)
    DiseaseProfile(
        name="Gallstones (Cholelithiasis)",
        keywords=["gallstone", "right upper pain", "pain after fatty food", "biliary colic", "gallbladder", "upper abdomen pain", "pain radiating to shoulder"],
        base_confidence=0.78,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) suggest gallstones (cholelithiasis) — solid deposits in the gallbladder that can cause biliary colic. Pain typically occurs after fatty meals and radiates to the right shoulder or back. Surgery may be needed for symptomatic stones.",
        findings=[
            {"finding": "Symptoms consistent with biliary colic / gallstones", "severity": "medium"},
            {"finding": "Abdominal ultrasound recommended for confirmation", "severity": "medium"},
        ],
        medications=[
            {"name": "Hyoscine Butylbromide (Buscopan)", "dosage": "20mg", "frequency": "Three times daily", "duration": "As needed for colic", "type": "tablet", "notes": "Antispasmodic for biliary colic. May cause dry mouth."},
            {"name": "Diclofenac", "dosage": "75mg", "frequency": "IM injection for acute colic, or 50mg oral twice daily", "duration": "3-5 days", "type": "tablet", "notes": "First-line for acute biliary pain. Take with food."},
            {"name": "Ursodeoxycholic Acid", "dosage": "300mg", "frequency": "Twice daily", "duration": "6-12 months", "type": "capsule", "notes": "May dissolve small cholesterol stones. Only for non-surgical candidates."},
        ],
        lifestyle=["Avoid high-fat and fried foods — opt for low-fat diet", "Eat smaller, more frequent meals", "Maintain a healthy weight — avoid rapid weight loss", "Increase fiber intake (fruits, vegetables, whole grains)", "Stay hydrated"],
        precautions=["Do not ignore recurrent pain episodes — gallstones can cause complications", "Rapid weight loss increases gallstone risk", "Watch for signs of cholecystitis (persistent pain, fever, jaundice)", "Surgical removal (cholecystectomy) is the definitive treatment"],
        recommended_tests=["Abdominal Ultrasound (first-line)", "Liver Function Tests", "Complete Blood Count", "Serum Amylase/Lipase (to exclude pancreatitis)", "MRCP if common bile duct stones suspected"],
        when_to_see_doctor="SEEK EMERGENCY CARE if: pain lasting more than 6 hours, fever with chills, jaundice (yellow eyes/skin), clay-colored stools, dark urine, or severe persistent vomiting.",
        urgency="soon",
    ),

    # 38 — Psoriasis
    DiseaseProfile(
        name="Psoriasis",
        keywords=["psoriasis", "silvery scales", "scaly patches", "plaque skin", "elbow rash", "knee rash", "scalp flaking", "nail pitting"],
        base_confidence=0.79,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) are consistent with psoriasis — a chronic autoimmune condition causing rapid skin cell buildup. It manifests as red, scaly patches typically on elbows, knees, scalp, and lower back. While not curable, it is very manageable.",
        findings=[
            {"finding": "Symptoms suggestive of plaque psoriasis", "severity": "medium"},
            {"finding": "Dermatological assessment recommended for severity grading", "severity": "medium"},
        ],
        medications=[
            {"name": "Clobetasol Propionate Cream 0.05%", "dosage": "Apply thin layer to plaques", "frequency": "Twice daily", "duration": "2-4 weeks (then taper)", "type": "topical", "notes": "Potent topical steroid. Do not use on face or groin. Use sparingly."},
            {"name": "Calcipotriol Cream", "dosage": "Apply thin layer", "frequency": "Twice daily", "duration": "8-12 weeks", "type": "topical", "notes": "Vitamin D analog. Safe for long-term use. Avoid near eyes."},
            {"name": "Methotrexate", "dosage": "7.5-15mg", "frequency": "Once weekly", "duration": "As prescribed by dermatologist", "type": "tablet", "notes": "For moderate-severe psoriasis. Requires regular blood monitoring. AVOID in pregnancy. Take folic acid 5mg the day after."},
            {"name": "Coal Tar Shampoo", "dosage": "Apply to scalp", "frequency": "2-3 times per week", "duration": "Ongoing", "type": "topical", "notes": "For scalp psoriasis. Leave on for 5-10 minutes before rinsing."},
        ],
        lifestyle=["Moisturize skin daily with thick emollients (petroleum jelly, coconut oil)", "Avoid skin trauma — psoriasis can develop at injury sites (Koebner phenomenon)", "Manage stress — flares are often stress-triggered", "Get brief, controlled sunlight exposure (UV therapy)", "Avoid alcohol and smoking — both worsen psoriasis"],
        precautions=["Never stop Methotrexate abruptly — consult doctor", "Regular blood tests required while on systemic therapy", "Avoid live vaccines while on immunosuppressants", "Psoriasis is NOT contagious — educate family and friends"],
        recommended_tests=["Clinical examination (PASI score)", "Skin biopsy if diagnosis uncertain", "CBC, LFT, RFT (baseline for systemic therapy)", "Lipid profile", "Joint assessment if psoriatic arthritis suspected"],
        when_to_see_doctor="See a dermatologist if: psoriasis covers more than 10% body surface, joint pain or stiffness developing, significant impact on quality of life, no improvement with topical treatment, or pustular/erythrodermic psoriasis (emergency).",
        urgency="soon",
    ),

    # 39 — Herpes Zoster (Shingles)
    DiseaseProfile(
        name="Herpes Zoster (Shingles)",
        keywords=["shingles", "herpes zoster", "band rash", "burning pain one side", "blisters one side", "dermatome rash", "post herpetic"],
        base_confidence=0.82,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) are characteristic of herpes zoster (shingles) — reactivation of the varicella-zoster virus in a single dermatome. Early antiviral treatment within 72 hours of rash onset reduces severity and risk of postherpetic neuralgia.",
        findings=[
            {"finding": "Symptoms consistent with herpes zoster (shingles)", "severity": "medium"},
            {"finding": "Antiviral treatment should be started within 72 hours of rash onset", "severity": "high"},
        ],
        medications=[
            {"name": "Valacyclovir", "dosage": "1000mg", "frequency": "Three times daily", "duration": "7 days", "type": "tablet", "notes": "Start ASAP — most effective within 72 hours of rash onset. Stay well hydrated."},
            {"name": "Pregabalin", "dosage": "75mg", "frequency": "Twice daily", "duration": "4-8 weeks", "type": "capsule", "notes": "For neuropathic pain. May cause dizziness. Increase dose gradually."},
            {"name": "Calamine Lotion", "dosage": "Apply to rash", "frequency": "3-4 times daily", "duration": "Until lesions crust", "type": "topical", "notes": "Soothing for itchy blisters. Pat on gently."},
            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours as needed", "duration": "As needed", "type": "tablet", "notes": "For pain relief."},
        ],
        lifestyle=["Keep the rash clean and dry", "Wear loose cotton clothing over affected area", "Cool compresses may provide relief", "Rest adequately — stress can worsen symptoms", "Avoid scratching — risk of secondary bacterial infection"],
        precautions=["Contagious to people who haven't had chickenpox (until all blisters crust)", "Avoid contact with pregnant women, newborns, and immunocompromised", "Do not use NSAIDs if risk of bleeding", "Vaccination (Shingrix) prevents shingles in adults over 50"],
        recommended_tests=["Usually clinical diagnosis", "Tzanck smear or PCR if uncertain", "VZV IgM antibodies if needed"],
        when_to_see_doctor="SEEK URGENT CARE if: rash near the eye or forehead (ophthalmic zoster — risk of vision loss), severe uncontrolled pain, rash spreading beyond one dermatome, fever and malaise, or immunocompromised patient.",
        urgency="soon",
    ),

    # 40 — COPD
    DiseaseProfile(
        name="Chronic Obstructive Pulmonary Disease (COPD)",
        keywords=["copd", "chronic cough", "smoker cough", "emphysema", "chronic bronchitis", "barrel chest", "breathless exertion", "sputum daily"],
        base_confidence=0.77,
        severity="severe",
        reasoning_template="The symptoms ({symptoms}) are consistent with COPD — a chronic progressive lung disease usually caused by long-term smoking. While not reversible, treatment can slow progression, reduce symptoms, and improve quality of life significantly.",
        findings=[
            {"finding": "Symptoms suggestive of COPD", "severity": "high"},
            {"finding": "Pulmonary function testing recommended for staging", "severity": "high"},
        ],
        medications=[
            {"name": "Tiotropium Inhaler", "dosage": "18mcg", "frequency": "Once daily", "duration": "Ongoing", "type": "inhaler", "notes": "Long-acting bronchodilator (maintenance). Use daily even when feeling well. Rinse mouth after."},
            {"name": "Salbutamol Inhaler (Rescue)", "dosage": "2 puffs", "frequency": "As needed for acute symptoms", "duration": "As needed", "type": "inhaler", "notes": "Short-acting bronchodilator for quick relief."},
            {"name": "Fluticasone + Salmeterol Inhaler", "dosage": "250/50mcg", "frequency": "Twice daily", "duration": "Ongoing", "type": "inhaler", "notes": "ICS/LABA combination for moderate-severe COPD. Rinse mouth after use."},
            {"name": "Azithromycin (prophylactic)", "dosage": "250mg", "frequency": "Three times per week", "duration": "As prescribed", "type": "tablet", "notes": "Reduces exacerbation frequency in severe COPD. Monitor hearing and ECG."},
        ],
        lifestyle=["QUIT SMOKING — the single most important intervention", "Pulmonary rehabilitation program", "Annual flu and pneumococcal vaccination", "Practice pursed-lip breathing during exertion", "Stay active with gentle exercise (walking, yoga)"],
        precautions=["Avoid air pollution, dust, and chemical fumes", "Use home oxygen as prescribed — do not adjust flow rate", "Report any increase in sputum or change in color immediately", "Avoid sedatives and sleeping pills that suppress breathing"],
        recommended_tests=["Spirometry (FEV1/FVC ratio)", "Chest X-ray", "Arterial Blood Gas (ABG)", "Alpha-1 Antitrypsin level", "CT Chest (if emphysema suspected)", "6-Minute Walk Test"],
        when_to_see_doctor="SEEK EMERGENCY CARE if: severe breathlessness at rest, lips or fingertips turning blue (cyanosis), confusion or drowsiness, unable to speak in sentences, chest pain, or swelling in ankles/legs.",
        urgency="urgent",
    ),

    # 41 — Tonsillitis / Pharyngitis
    DiseaseProfile(
        name="Tonsillitis / Pharyngitis",
        keywords=["tonsillitis", "sore throat severe", "swollen tonsils", "difficulty swallowing", "white patches throat", "strep throat", "throat infection"],
        base_confidence=0.83,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) suggest tonsillitis or pharyngitis — inflammation of the tonsils/throat usually caused by viral or bacterial infection. Streptococcal pharyngitis requires antibiotic treatment to prevent rheumatic fever.",
        findings=[
            {"finding": "Symptoms consistent with acute tonsillitis / pharyngitis", "severity": "low"},
            {"finding": "Rapid strep test or throat culture recommended", "severity": "low"},
        ],
        medications=[
            {"name": "Amoxicillin", "dosage": "500mg", "frequency": "Three times daily", "duration": "10 days", "type": "capsule", "notes": "First-line for strep throat. Complete the FULL 10-day course to prevent rheumatic fever."},
            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours as needed", "duration": "3-5 days", "type": "tablet", "notes": "For pain and fever."},
            {"name": "Throat lozenges (Strepsils)", "dosage": "1 lozenge", "frequency": "Every 3-4 hours", "duration": "As needed", "type": "tablet", "notes": "Dissolve slowly for sore throat relief."},
            {"name": "Betadine Gargle", "dosage": "15ml diluted", "frequency": "Three times daily", "duration": "5-7 days", "type": "topical", "notes": "Antiseptic gargle. Dilute as directed. Do not swallow."},
        ],
        lifestyle=["Gargle with warm salt water 3-4 times daily", "Drink warm fluids — herbal tea, soup, warm water with honey", "Rest your voice — avoid shouting or whispering", "Eat soft foods that are easy to swallow", "Stay home to prevent spreading the infection"],
        precautions=["Complete the full antibiotic course even if feeling better", "Watch for peritonsillar abscess signs (worsening one-sided pain, trismus)", "Frequent tonsillitis (>5/year) may warrant tonsillectomy discussion", "Do not share utensils or drinking glasses"],
        recommended_tests=["Rapid Antigen Detection Test (RADT) for Strep", "Throat Culture and Sensitivity", "Complete Blood Count", "ASO Titre if rheumatic fever suspected"],
        when_to_see_doctor="See a doctor if: unable to swallow saliva, difficulty breathing, muffled voice ('hot potato' voice), fever above 103°F, rash with sore throat, or symptoms not improving after 48 hours of antibiotics.",
        urgency="routine",
    ),

    # 42 — Frozen Shoulder (Adhesive Capsulitis)
    DiseaseProfile(
        name="Frozen Shoulder (Adhesive Capsulitis)",
        keywords=["frozen shoulder", "shoulder stiffness", "shoulder pain night", "can't raise arm", "shoulder restricted", "shoulder pain movement", "adhesive capsulitis"],
        base_confidence=0.77,
        severity="moderate",
        reasoning_template="The symptoms ({symptoms}) are consistent with frozen shoulder (adhesive capsulitis) — progressive shoulder stiffness and pain that limits range of motion. It typically goes through three phases (freezing, frozen, thawing) over 1-3 years but can be accelerated with treatment.",
        findings=[
            {"finding": "Symptoms suggestive of adhesive capsulitis (frozen shoulder)", "severity": "medium"},
            {"finding": "Active and passive range of motion both restricted", "severity": "medium"},
        ],
        medications=[
            {"name": "Diclofenac", "dosage": "50mg", "frequency": "Twice daily after meals", "duration": "2 weeks", "type": "tablet", "notes": "Anti-inflammatory. Take with food."},
            {"name": "Pregabalin", "dosage": "75mg", "frequency": "Once at bedtime", "duration": "4-6 weeks", "type": "capsule", "notes": "For night pain. May cause dizziness."},
            {"name": "Intra-articular Corticosteroid Injection", "dosage": "Methylprednisolone 40mg", "frequency": "Single injection (may repeat after 6 weeks)", "duration": "1-2 injections", "type": "injection", "notes": "Administered by orthopedic doctor. Provides rapid pain relief. Combined with physiotherapy."},
        ],
        lifestyle=["Start physiotherapy early — gentle pendulum exercises and stretching", "Apply hot pack before exercises, ice pack after", "Do wall-climbing finger exercises daily", "Maintain as much shoulder movement as possible", "Be patient — recovery takes months but does happen"],
        precautions=["Do not immobilize the shoulder — controlled movement is essential", "Avoid forceful manipulation without medical supervision", "Diabetics are at higher risk — maintain blood sugar control", "Sleep with a pillow supporting the affected arm"],
        recommended_tests=["X-ray Shoulder (AP and axillary views)", "MRI Shoulder (to exclude rotator cuff tear)", "Blood Sugar / HbA1c (diabetes association)", "Thyroid Function Test"],
        when_to_see_doctor="See an orthopedic doctor if: severe pain interfering with sleep, no improvement after 6 weeks of physiotherapy, sudden inability to move shoulder (possible tear), or numbness/tingling in arm.",
        urgency="soon",
    ),

    # 43 — Chronic Kidney Disease Indicators
    DiseaseProfile(
        name="Chronic Kidney Disease — Indicators",
        keywords=["kidney disease", "creatinine high", "swollen feet", "puffy eyes morning", "foamy urine", "reduced urine", "kidney failure", "dialysis", "egfr low"],
        base_confidence=0.75,
        severity="severe",
        reasoning_template="The symptoms ({symptoms}) suggest early indicators of chronic kidney disease (CKD). CKD progresses silently and can be slowed significantly with early intervention. Blood pressure control, diabetes management, and nephrology follow-up are essential.",
        findings=[
            {"finding": "Symptoms and/or lab values suggestive of renal impairment", "severity": "high"},
            {"finding": "Nephrology referral recommended for staging and management", "severity": "high"},
        ],
        medications=[
            {"name": "Telmisartan", "dosage": "40mg", "frequency": "Once daily", "duration": "Ongoing", "type": "tablet", "notes": "ARB — protects kidneys and controls blood pressure. Monitor potassium and creatinine."},
            {"name": "Sodium Bicarbonate", "dosage": "500mg", "frequency": "Three times daily", "duration": "As prescribed", "type": "tablet", "notes": "Corrects metabolic acidosis in CKD. Take as directed."},
            {"name": "Erythropoietin (EPO) Injection", "dosage": "4000 IU", "frequency": "Once weekly (subcutaneous)", "duration": "Ongoing", "type": "injection", "notes": "For anemia of CKD. Administered by healthcare provider. Monitor hemoglobin."},
            {"name": "Calcium + Vitamin D3", "dosage": "500mg/250 IU", "frequency": "Twice daily", "duration": "Ongoing", "type": "tablet", "notes": "Prevents renal osteodystrophy. Take with meals."},
        ],
        lifestyle=["Restrict salt intake to less than 5g/day", "Follow a renal diet (controlled protein, potassium, phosphorus)", "Stay well hydrated but follow fluid restriction if advised", "Control blood pressure and blood sugar meticulously", "Avoid smoking"],
        precautions=["AVOID NSAIDs (Ibuprofen, Diclofenac) — they damage kidneys further", "Avoid contrast dyes unless absolutely necessary", "Adjust all medication doses for kidney function", "Monitor weight daily for fluid retention"],
        recommended_tests=["Serum Creatinine and eGFR", "Urine Albumin-Creatinine Ratio (ACR)", "Blood Urea Nitrogen (BUN)", "Electrolytes (Sodium, Potassium, Phosphorus)", "Kidney Ultrasound", "Complete Blood Count", "Parathyroid Hormone"],
        when_to_see_doctor="SEEK URGENT CARE if: significant swelling (legs, face), shortness of breath, very reduced urine output, nausea with confusion, severe itching all over, chest pain, or blood in urine.",
        urgency="urgent",
    ),

    # 44 — Hepatitis (Viral)
    DiseaseProfile(
        name="Viral Hepatitis (A / B / E)",
        keywords=["hepatitis", "jaundice", "yellow eyes", "yellow skin", "liver infection", "dark urine", "pale stool", "nausea with jaundice", "liver pain"],
        base_confidence=0.80,
        severity="severe",
        reasoning_template="The symptoms ({symptoms}) are suggestive of viral hepatitis — an infection causing liver inflammation. Identifying the specific virus (A, B, C, or E) is crucial as treatment and prognosis differ. Most acute hepatitis A and E resolve spontaneously; hepatitis B/C may need antiviral therapy.",
        findings=[
            {"finding": "Symptoms consistent with acute viral hepatitis", "severity": "high"},
            {"finding": "Viral markers and liver function tests urgently needed", "severity": "high"},
        ],
        medications=[
            {"name": "Ursodeoxycholic Acid", "dosage": "300mg", "frequency": "Twice daily", "duration": "4-8 weeks", "type": "capsule", "notes": "Supports bile flow and liver recovery. Take with food."},
            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 8 hours if needed (max 2g/day)", "duration": "As needed", "type": "tablet", "notes": "Low dose ONLY for fever/pain. Reduced dose due to liver involvement. AVOID if liver function severely impaired."},
            {"name": "Domperidone", "dosage": "10mg", "frequency": "Three times daily before meals", "duration": "1-2 weeks", "type": "tablet", "notes": "For nausea. Take 15-30 minutes before meals."},
            {"name": "Lactulose Syrup", "dosage": "15-30ml", "frequency": "Twice daily", "duration": "As needed", "type": "syrup", "notes": "Prevents hepatic encephalopathy. Dose adjusted for 2-3 soft stools daily."},
        ],
        lifestyle=["Complete bed rest during acute phase", "Follow a high-carbohydrate, low-fat diet", "Avoid alcohol completely — even after recovery for 6 months", "Drink boiled water and maintain strict hygiene", "Sugarcane juice and coconut water are traditional supportive remedies"],
        precautions=["AVOID alcohol, paracetamol overdose, and hepatotoxic drugs", "Do not share razors, toothbrushes, or needles (Hep B/C)", "Hepatitis B vaccination for close contacts", "Practice safe sex if hepatitis B positive"],
        recommended_tests=["Liver Function Test (Bilirubin, ALT, AST, ALP)", "Hepatitis Panel (HAV IgM, HBsAg, Anti-HCV, HEV IgM)", "Complete Blood Count", "Prothrombin Time / INR", "Abdominal Ultrasound"],
        when_to_see_doctor="SEEK EMERGENCY CARE if: deep jaundice (bilirubin >15), confusion or drowsiness (hepatic encephalopathy), severe abdominal pain, bleeding tendency, persistent vomiting, or inability to eat/drink.",
        urgency="urgent",
    ),

    # 45 — Plantar Fasciitis
    DiseaseProfile(
        name="Plantar Fasciitis (Heel Pain)",
        keywords=["heel pain", "plantar fasciitis", "foot pain morning", "heel spur", "pain first step", "arch pain", "heel pain standing"],
        base_confidence=0.81,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) are characteristic of plantar fasciitis — inflammation of the thick tissue band on the bottom of the foot connecting the heel to the toes. The hallmark is intense heel pain with the first steps in the morning. Most cases resolve with conservative treatment.",
        findings=[
            {"finding": "Symptoms consistent with plantar fasciitis", "severity": "low"},
            {"finding": "Heel spur may or may not be present on X-ray", "severity": "low"},
        ],
        medications=[
            {"name": "Ibuprofen", "dosage": "400mg", "frequency": "Three times daily with food", "duration": "7-10 days", "type": "tablet", "notes": "Anti-inflammatory. Take with food."},
            {"name": "Diclofenac Gel", "dosage": "Apply to heel", "frequency": "Three times daily", "duration": "2 weeks", "type": "topical", "notes": "Topical anti-inflammatory. Massage gently into heel area."},
        ],
        lifestyle=["Do calf and plantar fascia stretches before getting out of bed", "Roll a frozen water bottle under the foot for 10 minutes", "Wear supportive shoes with good arch support — avoid flat shoes", "Use silicone heel cups or custom orthotics", "Maintain a healthy weight to reduce heel pressure"],
        precautions=["Avoid walking barefoot on hard surfaces", "Do not ignore persistent pain — it can become chronic", "Avoid high heels and unsupportive flip-flops", "Night splints may help in resistant cases"],
        recommended_tests=["X-ray of foot (heel spur evaluation)", "Ultrasound of plantar fascia (thickness measurement)", "MRI foot if resistant to treatment"],
        when_to_see_doctor="See a doctor if: heel pain not improving after 2 weeks of home treatment, pain is severe and limits walking, numbness or tingling in the foot, heel pain after injury, or bilateral heel pain (systemic cause possible).",
        urgency="routine",
    ),

    # 46 — Carpal Tunnel Syndrome
    DiseaseProfile(
        name="Carpal Tunnel Syndrome",
        keywords=["carpal tunnel", "wrist pain", "hand numbness", "tingling fingers", "hand weakness", "dropping things", "wrist pain typing", "numbness night hand"],
        base_confidence=0.78,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) suggest carpal tunnel syndrome — compression of the median nerve as it passes through the carpal tunnel in the wrist. It commonly causes numbness, tingling, and weakness in the thumb, index, and middle fingers.",
        findings=[
            {"finding": "Symptoms suggestive of median nerve compression (carpal tunnel)", "severity": "low"},
            {"finding": "Nerve conduction study recommended for confirmation", "severity": "medium"},
        ],
        medications=[
            {"name": "Ibuprofen", "dosage": "400mg", "frequency": "Three times daily with food", "duration": "7-10 days", "type": "tablet", "notes": "For pain and inflammation. Take with food."},
            {"name": "Methylcobalamin (Vitamin B12)", "dosage": "1500mcg", "frequency": "Once daily", "duration": "3 months", "type": "tablet", "notes": "Supports nerve health and repair."},
            {"name": "Wrist Splint", "dosage": "Wear at night", "frequency": "Every night", "duration": "4-6 weeks", "type": "topical", "notes": "Keeps wrist in neutral position. Reduces nighttime symptoms."},
        ],
        lifestyle=["Take regular breaks from typing/mouse use (every 30 minutes)", "Do wrist stretches and nerve gliding exercises", "Keep wrist in neutral position while working", "Use ergonomic keyboard and mouse", "Avoid sleeping on the affected hand"],
        precautions=["Do not ignore progressive weakness — can lead to permanent damage", "Avoid repetitive wrist flexion/extension", "Treat underlying conditions (diabetes, thyroid) that worsen CTS", "Surgery may be needed if conservative treatment fails"],
        recommended_tests=["Nerve Conduction Study (NCS) / Electromyography (EMG)", "Phalen's test and Tinel's sign (clinical)", "Thyroid Function Test", "Fasting Blood Sugar / HbA1c", "Wrist X-ray if bony cause suspected"],
        when_to_see_doctor="See a doctor if: persistent numbness not relieved by splinting, progressive hand weakness, difficulty with fine motor tasks (buttoning), muscle wasting at base of thumb, or symptoms in both hands.",
        urgency="routine",
    ),

    # 47 — Epilepsy / Seizure Disorder
    DiseaseProfile(
        name="Epilepsy / Seizure Disorder",
        keywords=["seizure", "epilepsy", "fits", "convulsion", "loss of consciousness", "jerking movements", "absence spell", "tongue biting"],
        base_confidence=0.76,
        severity="severe",
        reasoning_template="The symptoms ({symptoms}) suggest a seizure disorder / epilepsy — a neurological condition characterized by recurrent, unprovoked seizures. Proper diagnosis of seizure type is essential for choosing the right antiepileptic medication.",
        findings=[
            {"finding": "Symptoms consistent with epileptic seizures", "severity": "high"},
            {"finding": "EEG and neuroimaging recommended for diagnosis and classification", "severity": "high"},
        ],
        medications=[
            {"name": "Levetiracetam", "dosage": "500mg", "frequency": "Twice daily", "duration": "Ongoing (minimum 2 years seizure-free)", "type": "tablet", "notes": "First-line anticonvulsant. Well tolerated. May cause irritability — report mood changes."},
            {"name": "Sodium Valproate", "dosage": "500mg", "frequency": "Twice daily", "duration": "Ongoing", "type": "tablet", "notes": "Broad-spectrum anticonvulsant. AVOID in women of childbearing age (teratogenic). Monitor liver function."},
            {"name": "Clobazam", "dosage": "10mg", "frequency": "At bedtime", "duration": "As adjunctive therapy", "type": "tablet", "notes": "Add-on therapy for refractory seizures. Benzodiazepine — may cause drowsiness."},
        ],
        lifestyle=["Take medication at the same time every day — never miss a dose", "Get adequate sleep (sleep deprivation triggers seizures)", "Avoid alcohol and recreational drugs", "Avoid known seizure triggers (flashing lights, extreme stress)", "Inform family/friends about seizure first aid"],
        precautions=["NEVER stop antiepileptic medication suddenly (risk of status epilepticus)", "Avoid swimming alone or working at heights", "Do not drive until seizure-free period as per local regulations", "Women should plan pregnancy — teratogenic drug management needed"],
        recommended_tests=["EEG (Electroencephalogram)", "MRI Brain with epilepsy protocol", "Complete Blood Count", "Liver Function Test", "Serum drug levels (therapeutic monitoring)", "Video EEG if diagnosis uncertain"],
        when_to_see_doctor="CALL EMERGENCY (112) if: seizure lasting more than 5 minutes (status epilepticus), repeated seizures without recovery between them, seizure with head injury, first-ever seizure, breathing difficulty after seizure, or seizure in pregnancy.",
        urgency="urgent",
    ),

    # 48 — Conjunctival Dryness / Dry Eye Syndrome
    DiseaseProfile(
        name="Dry Eye Syndrome",
        keywords=["dry eyes", "eye strain", "burning eyes", "gritty eyes", "tired eyes", "screen eyes", "blurred vision fatigue", "watering eyes paradox"],
        base_confidence=0.80,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) are consistent with dry eye syndrome, a very common condition caused by insufficient tear production or excessive tear evaporation. Prolonged screen use, air conditioning, and aging are major contributing factors.",
        findings=[
            {"finding": "Symptoms consistent with dry eye syndrome / computer vision syndrome", "severity": "low"},
            {"finding": "Tear film evaluation recommended", "severity": "low"},
        ],
        medications=[
            {"name": "Carboxymethylcellulose Eye Drops (Refresh Tears)", "dosage": "1-2 drops per eye", "frequency": "4-6 times daily", "duration": "Ongoing", "type": "topical", "notes": "Preservative-free artificial tears preferred. Safe for frequent use."},
            {"name": "Omega-3 Fatty Acid Supplements", "dosage": "1000mg", "frequency": "Once daily", "duration": "3 months", "type": "capsule", "notes": "Fish oil or flaxseed oil. Improves tear quality over time."},
            {"name": "Cyclosporine Eye Drops 0.05%", "dosage": "1 drop per eye", "frequency": "Twice daily", "duration": "3-6 months", "type": "topical", "notes": "For moderate-severe dry eye. Increases natural tear production. May sting initially."},
        ],
        lifestyle=["Follow 20-20-20 rule: every 20 min, look at something 20 feet away for 20 seconds", "Blink consciously and frequently when using screens", "Use a humidifier in air-conditioned rooms", "Stay well hydrated — drink 2-3 liters of water daily", "Position screen below eye level to reduce eye opening"],
        precautions=["Avoid direct air from fans/ACs hitting the eyes", "Reduce contact lens wear time if eyes feel dry", "Avoid eye rubbing", "Limit screen time and take regular breaks"],
        recommended_tests=["Schirmer's Test (tear production)", "Tear Break-Up Time (TBUT)", "Slit lamp examination", "Meibomian gland evaluation"],
        when_to_see_doctor="See an eye doctor if: persistent redness or pain, significant vision changes, excessive discharge, symptoms not improving with artificial tears, or suspected autoimmune dry eye (Sjögren's syndrome).",
        urgency="routine",
    ),

    # 49 — Scabies
    DiseaseProfile(
        name="Scabies",
        keywords=["scabies", "intense itching night", "burrow marks", "itching finger webs", "rash spreading family", "mites", "sarcoptes"],
        base_confidence=0.82,
        severity="mild",
        reasoning_template="The symptoms ({symptoms}) are suggestive of scabies — a highly contagious skin infestation caused by the mite Sarcoptes scabiei. Intense itching (especially at night) and characteristic burrow marks are hallmarks. All family members and close contacts must be treated simultaneously.",
        findings=[
            {"finding": "Symptoms consistent with scabies infestation", "severity": "low"},
            {"finding": "All household contacts should be treated simultaneously", "severity": "medium"},
        ],
        medications=[
            {"name": "Permethrin Cream 5%", "dosage": "Apply neck down to entire body", "frequency": "Once at night, wash off after 8-12 hours", "duration": "Repeat after 1 week", "type": "topical", "notes": "Apply to ALL skin from neck to toes, including between fingers, under nails. Treat ALL household members."},
            {"name": "Ivermectin", "dosage": "200mcg/kg body weight", "frequency": "Single dose, repeat after 2 weeks", "duration": "2 doses total", "type": "tablet", "notes": "Oral alternative. Take on empty stomach. Not for pregnant women or children <15 kg."},
            {"name": "Cetirizine", "dosage": "10mg", "frequency": "Once daily at night", "duration": "2-3 weeks", "type": "tablet", "notes": "For itching relief. Itching may persist for 2-4 weeks after successful treatment (post-scabetic itch)."},
            {"name": "Calamine Lotion", "dosage": "Apply to itchy areas", "frequency": "3-4 times daily", "duration": "As needed", "type": "topical", "notes": "Soothing for itchy skin."},
        ],
        lifestyle=["Wash all clothing, bedding, and towels in hot water (60°C) on treatment day", "Vacuum carpets and upholstered furniture", "Bag items that can't be washed for 72 hours (mites die without host)", "Trim fingernails short to prevent scratching damage", "Avoid close physical contact until treatment is complete"],
        precautions=["TREAT ALL HOUSEHOLD MEMBERS AND CLOSE CONTACTS at the same time", "Itching can persist 2-4 weeks post-treatment — this is normal", "Reapply cream to hands if washed within 8 hours", "Do not share clothing, bedding, or towels"],
        recommended_tests=["Skin scraping with microscopy (mites, eggs, or fecal pellets)", "Dermoscopy (delta-wing jet pattern)", "Usually clinical diagnosis based on history and distribution"],
        when_to_see_doctor="See a doctor if: rash not improving 2 weeks after treatment, secondary bacterial infection (pus, crusting), widespread crusted/Norwegian scabies, symptoms in infants or immunocompromised patients, or persistent itching beyond 4 weeks.",
        urgency="routine",
    ),

    # 50 — Appendicitis Warning Signs
    DiseaseProfile(
        name="Appendicitis — Warning Signs",
        keywords=["appendicitis", "right lower pain", "pain around navel moving right", "rebound tenderness", "nausea with right abdominal pain", "loss of appetite abdominal pain"],
        base_confidence=0.78,
        severity="severe",
        keyword_weights={"appendicitis": 2.0, "right lower pain": 1.5, "pain around navel moving right": 2.0},
        reasoning_template="The symptoms ({symptoms}) raise concern for acute appendicitis — an inflammation of the appendix that typically requires emergency surgery. The classic presentation is pain starting around the navel and migrating to the right lower abdomen.",
        findings=[
            {"finding": "Symptoms suggestive of acute appendicitis", "severity": "high"},
            {"finding": "Surgical evaluation and imaging needed urgently", "severity": "high"},
        ],
        medications=[
            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours", "duration": "Until surgical evaluation", "type": "tablet", "notes": "Mild pain relief while awaiting medical evaluation. Do not mask symptoms."},
        ],
        lifestyle=["Do not eat or drink anything (NPO) once appendicitis is suspected — surgery may be needed", "Rest in a comfortable position", "Apply ice pack (not heat) to the painful area", "Reach the nearest emergency department immediately"],
        precautions=["DO NOT take strong painkillers that may mask symptoms", "DO NOT apply heat or hot water bottle to abdomen", "DO NOT take laxatives or enemas", "DO NOT delay seeking medical care — ruptured appendix is life-threatening"],
        recommended_tests=["CT Abdomen (gold standard)", "Ultrasound Abdomen (especially in children and pregnant women)", "Complete Blood Count (elevated WBC)", "C-Reactive Protein (CRP)", "Urinalysis (to exclude UTI/kidney stones)"],
        when_to_see_doctor="GO TO EMERGENCY ROOM IMMEDIATELY if: severe right lower abdominal pain, pain that starts around the navel and moves to the right, fever with abdominal pain, inability to pass gas, nausea/vomiting with progressive pain, or abdominal rigidity.",
        urgency="emergency",
    ),
]


def _score_keywords(text: str, profile: DiseaseProfile) -> float:
    """Count how many of the profile's keywords appear in the symptom text.
    Multi-word keywords (e.g. 'back pain') get a +0.5 bonus because they are
    more specific than single-word matches."""
    text_lower = text.lower()
    score = 0.0
    for kw in profile.keywords:
        if kw in text_lower:
            bonus = 0.5 if " " in kw else 0.0
            weight = profile.keyword_weights.get(kw, 1.0)
            score += (1.0 + bonus) * weight
    return score


GENDER_RISK_FACTORS: dict[str, dict[str, float]] = {
    "female": {
        "Urinary Tract Infection (UTI)": 0.06,
        "Thyroid Disorder (Hypothyroidism)": 0.04,
        "Migraine with Aura": 0.03,
        "Anemia / Iron Deficiency": 0.04,
        "Major Depressive Disorder": 0.02,
        "Polycystic Ovary Syndrome (PCOS)": 0.06,
        "Dry Eye Syndrome": 0.02,
        "Carpal Tunnel Syndrome": 0.03,
        "Frozen Shoulder (Adhesive Capsulitis)": 0.02,
    },
    "male": {
        "Kidney Stones (Renal Calculi)": 0.05,
        "Hypertension (High Blood Pressure)": 0.03,
        "Peptic Ulcer Disease (Gastric / Duodenal Ulcer)": 0.03,
        "Gout (Uric Acid Arthritis)": 0.05,
        "Chronic Obstructive Pulmonary Disease (COPD)": 0.03,
    },
}

AGE_RISK_RANGES: list[tuple[int, int, dict[str, float]]] = [
    (0, 12, {
        "Ear Infection (Otitis Media)": 0.05,
        "Chickenpox (Varicella)": 0.05,
        "Upper Respiratory Tract Infection (Common Cold / Flu)": 0.03,
        "Tonsillitis / Pharyngitis": 0.04,
        "Scabies": 0.02,
    }),
    (13, 25, {
        "Skin Infection / Dermatitis": 0.03,
        "Generalized Anxiety / Stress Disorder": 0.03,
        "Insomnia / Sleep Disorder": 0.02,
        "Polycystic Ovary Syndrome (PCOS)": 0.03,
        "Tonsillitis / Pharyngitis": 0.02,
    }),
    (26, 45, {
        "Lower Back Pain / Musculoskeletal Strain": 0.03,
        "Sciatica (Lumbar Radiculopathy)": 0.03,
        "Major Depressive Disorder": 0.02,
        "Irritable Bowel Syndrome (IBS)": 0.03,
        "Carpal Tunnel Syndrome": 0.02,
        "Dry Eye Syndrome": 0.02,
    }),
    (46, 65, {
        "Hypertension (High Blood Pressure)": 0.04,
        "Type 2 Diabetes Mellitus — Indicators": 0.04,
        "Joint Pain / Arthritis": 0.03,
        "Gout (Uric Acid Arthritis)": 0.03,
        "Chronic Obstructive Pulmonary Disease (COPD)": 0.03,
        "Frozen Shoulder (Adhesive Capsulitis)": 0.03,
        "Herpes Zoster (Shingles)": 0.03,
        "Gallstones (Cholelithiasis)": 0.02,
    }),
    (66, 120, {
        "Hypertension (High Blood Pressure)": 0.05,
        "Type 2 Diabetes Mellitus — Indicators": 0.05,
        "Joint Pain / Arthritis": 0.05,
        "Vitamin D Deficiency": 0.03,
        "Chronic Kidney Disease — Indicators": 0.04,
        "Chronic Obstructive Pulmonary Disease (COPD)": 0.04,
        "Herpes Zoster (Shingles)": 0.04,
        "Vertigo / Benign Paroxysmal Positional Vertigo (BPPV)": 0.03,
    }),
]

DRUG_CLASS_KEYWORDS: dict[str, list[str]] = {
    "penicillin": ["Amoxicillin", "Amoxicillin + Clavulanate"],
    "nsaid": ["Ibuprofen", "Diclofenac", "Naproxen", "Aspirin"],
    "sulfa": ["Sulfamethoxazole"],
    "aspirin": ["Aspirin"],
    "ibuprofen": ["Ibuprofen"],
    "diclofenac": ["Diclofenac"],
    "amoxicillin": ["Amoxicillin", "Amoxicillin + Clavulanate"],
    "clarithromycin": ["Clarithromycin"],
    "cetirizine": ["Cetirizine"],
    "paracetamol": ["Paracetamol"],
    "acetaminophen": ["Paracetamol"],
    "macrolide": ["Azithromycin", "Clarithromycin"],
    "azithromycin": ["Azithromycin"],
    "methotrexate": ["Methotrexate"],
    "valproate": ["Sodium Valproate"],
    "colchicine": ["Colchicine"],
    "allopurinol": ["Allopurinol"],
    "rifampicin": ["Rifampicin"],
    "isoniazid": ["Isoniazid"],
}


def _calculate_age(dob_str: str) -> int | None:
    """Try to parse date of birth and return age in years."""
    from datetime import datetime
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            born = datetime.strptime(dob_str.strip(), fmt)
            today = datetime.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except (ValueError, AttributeError):
            continue
    return None


def _get_age_risk_boosts(age: int) -> dict[str, float]:
    """Return confidence boosts for diseases that are more likely at this age."""
    for lo, hi, boosts in AGE_RISK_RANGES:
        if lo <= age <= hi:
            return boosts
    return {}


def _filter_medications_for_allergies(
    medications: list[dict],
    allergies_str: str,
) -> tuple[list[dict], list[str]]:
    """Remove medications the patient is allergic to.
    Returns (safe_medications, allergy_warnings)."""
    if not allergies_str or allergies_str.lower() in ("none", "none reported", "n/a", ""):
        return list(medications), []

    allergy_tokens = [a.strip().lower() for a in allergies_str.replace(",", " ").split()]
    flagged_drug_names: set[str] = set()
    for token in allergy_tokens:
        if token in DRUG_CLASS_KEYWORDS:
            flagged_drug_names.update(DRUG_CLASS_KEYWORDS[token])

    safe: list[dict] = []
    warnings: list[str] = []
    for med in medications:
        med_name = med.get("name", "")
        is_flagged = any(flagged.lower() in med_name.lower() for flagged in flagged_drug_names)
        if is_flagged:
            warnings.append(
                f"⚠ {med_name} was EXCLUDED from recommendations because of your reported allergy to "
                f"'{allergies_str}'. Inform your doctor about this allergy."
            )
        else:
            safe.append(med)

    if not safe:
        safe.append({
            "name": "Consult Doctor for Alternatives",
            "dosage": "N/A",
            "frequency": "N/A",
            "duration": "N/A",
            "type": "consultation",
            "notes": f"All standard medications for this condition conflict with your reported allergies ({allergies_str}). Please consult a physician for safe alternatives.",
        })

    return safe, warnings


def _build_history_context(medical_history: dict) -> str:
    """Build a human-readable medical history paragraph for reasoning."""
    parts: list[str] = []
    gender = medical_history.get("gender", "").strip()
    if gender and gender.lower() not in ("not specified", "unknown", ""):
        parts.append(f"Gender: {gender}")

    dob = medical_history.get("date_of_birth", "").strip()
    age = _calculate_age(dob) if dob and dob.lower() != "unknown" else None
    if age is not None:
        parts.append(f"Age: {age} years")

    bg = medical_history.get("blood_group", "").strip()
    if bg and bg.lower() not in ("unknown", ""):
        parts.append(f"Blood Group: {bg}")

    allergies = medical_history.get("allergies", "").strip()
    if allergies and allergies.lower() not in ("none reported", "none", "n/a", ""):
        parts.append(f"Known Allergies: {allergies}")

    vitals = medical_history.get("vitals") or {}
    if vitals:
        vp = []
        if vitals.get("systolic_bp") is not None and vitals.get("diastolic_bp") is not None:
            vp.append(f"BP {vitals['systolic_bp']}/{vitals['diastolic_bp']} mmHg")
        if vitals.get("spo2") is not None:
            vp.append(f"SpO2 {vitals['spo2']}%")
        if vitals.get("heart_rate") is not None:
            vp.append(f"HR {vitals['heart_rate']} bpm")
        if vitals.get("temperature_f") is not None:
            vp.append(f"Temp {vitals['temperature_f']}°F")
        if vitals.get("respiratory_rate") is not None:
            vp.append(f"RR {vitals['respiratory_rate']}/min")
        if vitals.get("blood_sugar_mg_dl") is not None:
            vp.append(f"Glucose {vitals['blood_sugar_mg_dl']} mg/dL")
        if vitals.get("weight_kg") is not None:
            vp.append(f"Weight {vitals['weight_kg']} kg")
        if vitals.get("pain_level") is not None:
            vp.append(f"Pain {vitals['pain_level']}/10")
        if vitals.get("ecg_notes"):
            vp.append(f"ECG: {vitals['ecg_notes']}")
        if vp:
            parts.append("Vitals: " + "; ".join(vp))

    if not parts:
        base = ""
    else:
        base = " | ".join(parts)
    prior = medical_history.get("prior_context")
    if prior and isinstance(prior, str):
        return f"{base}\n\n{prior}" if base else prior
    return base


def diagnose(symptoms: str, clinical_notes: str = "", medical_history: dict | None = None) -> dict:
    """Run symptom text through the weighted scoring engine and return
    the best-matching disease profile as a structured dict.

    When medical_history is provided (keys: allergies, blood_group, gender,
    date_of_birth), the engine will:
      1. Adjust confidence based on age/gender risk factors
      2. Filter out medications the patient is allergic to
      3. Add allergy warnings and medical context to reasoning
    """
    if medical_history is None:
        medical_history = {}

    combined_text = f"{symptoms} {clinical_notes}".strip()
    if not combined_text:
        return _fallback_response(symptoms, medical_history)

    gender = (medical_history.get("gender") or "").strip().lower()
    dob = (medical_history.get("date_of_birth") or "").strip()
    allergies = (medical_history.get("allergies") or "").strip()
    age = _calculate_age(dob) if dob and dob.lower() != "unknown" else None

    gender_boosts = GENDER_RISK_FACTORS.get(gender, {})
    age_boosts = _get_age_risk_boosts(age) if age is not None else {}

    best_profile: DiseaseProfile | None = None
    best_score = 0.0

    for profile in DISEASE_PROFILES:
        score = _score_keywords(combined_text, profile)
        if score > best_score:
            best_score = score
            best_profile = profile

    if best_profile is None or best_score == 0:
        return _fallback_response(symptoms, medical_history)

    confidence = best_profile.base_confidence
    confidence += gender_boosts.get(best_profile.name, 0.0)
    confidence += age_boosts.get(best_profile.name, 0.0)
    confidence = round(min(confidence, 0.99), 2)

    safe_meds, allergy_warnings = _filter_medications_for_allergies(
        best_profile.medications, allergies
    )

    history_ctx = _build_history_context(medical_history)
    reasoning = best_profile.reasoning_template.format(symptoms=symptoms)
    if history_ctx:
        reasoning += f"\n\nPatient profile: {history_ctx}."
    if age is not None:
        reasoning += f" Age-adjusted risk factors have been considered."
    if allergy_warnings:
        reasoning += "\n\n" + "\n".join(allergy_warnings)

    precautions = list(best_profile.precautions)
    if allergies and allergies.lower() not in ("none reported", "none", "n/a", ""):
        precautions.insert(0, f"IMPORTANT: You have reported allergies to '{allergies}'. Inform every healthcare provider about this before any treatment.")

    findings = list(best_profile.findings)
    if history_ctx:
        findings.append({"finding": f"Patient medical profile: {history_ctx}", "severity": "info"})

    from app.services.dietary_routine_plans import get_dietary_plan, get_routine_plan
    from app.services.ayurvedic_medicines import get_ayurvedic_medicines

    return {
        "diagnosis": best_profile.name,
        "reasoning": reasoning,
        "severity": best_profile.severity,
        "confidence": confidence,
        "findings": findings,
        "medications": safe_meds,
        "lifestyle_recommendations": best_profile.lifestyle,
        "precautions": precautions,
        "recommended_tests": best_profile.recommended_tests,
        "when_to_see_doctor": best_profile.when_to_see_doctor,
        "urgency": best_profile.urgency,
        "dietary_plan": get_dietary_plan(best_profile.name),
        "routine_plan": get_routine_plan(best_profile.name),
        "ayurvedic_medicines": get_ayurvedic_medicines(best_profile.name),
        "model_version": MODEL_VERSION,
        "medical_history_considered": bool(medical_history),
        "allergy_warnings": allergy_warnings if allergy_warnings else None,
    }


def _fallback_response(symptoms: str, medical_history: dict | None = None) -> dict:
    """Generic fallback for unrecognized symptom patterns."""
    if medical_history is None:
        medical_history = {}

    allergies = (medical_history.get("allergies") or "").strip()
    base_meds = [
        {"name": "Paracetamol", "dosage": "500mg", "frequency": "Every 6 hours if needed", "duration": "As needed", "type": "tablet", "notes": "For general discomfort and mild pain relief."},
    ]
    safe_meds, allergy_warnings = _filter_medications_for_allergies(base_meds, allergies)

    history_ctx = _build_history_context(medical_history)
    reasoning = f"Based on the reported symptoms ({symptoms}), a more detailed clinical examination is recommended. The symptoms need further evaluation with appropriate diagnostic tests for an accurate diagnosis."
    if history_ctx:
        reasoning += f"\n\nPatient profile: {history_ctx}."
    if allergy_warnings:
        reasoning += "\n\n" + "\n".join(allergy_warnings)

    from app.services.dietary_routine_plans import get_dietary_plan, get_routine_plan
    from app.services.ayurvedic_medicines import get_ayurvedic_medicines

    return {
        "diagnosis": f"Preliminary Assessment Required — Symptoms: {symptoms[:100]}",
        "reasoning": reasoning,
        "severity": "moderate",
        "confidence": 0.65,
        "findings": [{"finding": f"Patient reports: {symptoms}", "severity": "medium"}],
        "medications": safe_meds,
        "lifestyle_recommendations": ["Monitor symptoms and note any changes", "Rest adequately", "Stay well hydrated", "Maintain a healthy diet"],
        "recommended_tests": ["Complete Blood Count (CBC)", "Basic Metabolic Panel", "Urinalysis"],
        "when_to_see_doctor": "Please consult a physician for a thorough examination, especially if symptoms worsen, persist beyond 3 days, or are accompanied by high fever, severe pain, or breathing difficulty.",
        "urgency": "soon",
        "precautions": ["Do not self-medicate beyond basic OTC pain relief", "Keep track of symptoms for the doctor visit"],
        "dietary_plan": get_dietary_plan(""),
        "routine_plan": get_routine_plan(""),
        "ayurvedic_medicines": get_ayurvedic_medicines(""),
        "model_version": MODEL_VERSION,
        "medical_history_considered": bool(medical_history),
        "allergy_warnings": allergy_warnings if allergy_warnings else None,
    }


def get_all_profiles() -> list[DiseaseProfile]:
    """Return all registered disease profiles (useful for tests and docs)."""
    return list(DISEASE_PROFILES)


def _build_medication_index() -> dict[str, list[DiseaseProfile]]:
    """Build a reverse index: normalised medication name -> list of disease profiles."""
    index: dict[str, list[DiseaseProfile]] = {}
    for profile in DISEASE_PROFILES:
        for med in profile.medications:
            raw_name = med.get("name", "")
            key = raw_name.split("(")[0].strip().lower()
            if key:
                index.setdefault(key, []).append(profile)
    return index


_MED_INDEX: dict[str, list[DiseaseProfile]] = _build_medication_index()


def identify_diseases_by_medications(
    medications: list[str],
    symptoms: str = "",
    vitals: dict | None = None,
) -> list[dict]:
    """Given a list of medication names a patient is taking, plus optional
    symptoms text and vital signs, return possible diseases ranked by how many
    of the provided medications match each disease profile.

    When symptoms or vitals are provided the confidence is adjusted upward for
    profiles whose keywords match the symptom text, and vitals observations are
    appended to the reasoning."""

    if vitals is None:
        vitals = {}

    disease_matches: dict[str, dict] = {}

    for med_input in medications:
        med_lower = med_input.strip().lower()
        if not med_lower:
            continue

        for index_key, profiles in _MED_INDEX.items():
            if med_lower in index_key or index_key in med_lower:
                for profile in profiles:
                    name = profile.name
                    if name not in disease_matches:
                        disease_matches[name] = {
                            "disease": name,
                            "matched_medications": [],
                            "total_disease_medications": len(profile.medications),
                            "severity": profile.severity,
                            "urgency": profile.urgency,
                            "confidence": 0.0,
                            "reasoning": "",
                            "recommended_tests": profile.recommended_tests,
                            "when_to_see_doctor": profile.when_to_see_doctor,
                            "all_medications": profile.medications,
                            "lifestyle_recommendations": profile.lifestyle,
                            "precautions": profile.precautions,
                            "_profile": profile,
                        }
                    matched = disease_matches[name]["matched_medications"]
                    if med_input not in matched:
                        matched.append(med_input)

    symptoms_lower = symptoms.strip().lower() if symptoms else ""

    vitals_notes: list[str] = []
    temp = vitals.get("temperature_f")
    if temp is not None:
        if temp >= 100.4:
            vitals_notes.append(f"Elevated temperature ({temp}°F) — indicates fever")
        elif temp <= 95.0:
            vitals_notes.append(f"Low temperature ({temp}°F) — indicates hypothermia")
        else:
            vitals_notes.append(f"Temperature {temp}°F (normal range)")

    sys_bp = vitals.get("systolic_bp")
    dia_bp = vitals.get("diastolic_bp")
    if sys_bp is not None and dia_bp is not None:
        if sys_bp >= 140 or dia_bp >= 90:
            vitals_notes.append(f"Blood Pressure {sys_bp}/{dia_bp} mmHg — elevated (hypertensive range)")
        elif sys_bp < 90 or dia_bp < 60:
            vitals_notes.append(f"Blood Pressure {sys_bp}/{dia_bp} mmHg — low (hypotensive)")
        else:
            vitals_notes.append(f"Blood Pressure {sys_bp}/{dia_bp} mmHg (normal range)")
    elif sys_bp is not None:
        vitals_notes.append(f"Systolic BP {sys_bp} mmHg")

    hr = vitals.get("heart_rate")
    if hr is not None:
        if hr > 100:
            vitals_notes.append(f"Heart Rate {hr} bpm — tachycardia")
        elif hr < 60:
            vitals_notes.append(f"Heart Rate {hr} bpm — bradycardia")
        else:
            vitals_notes.append(f"Heart Rate {hr} bpm (normal range)")

    spo2 = vitals.get("spo2")
    if spo2 is not None:
        if spo2 < 95:
            vitals_notes.append(f"SpO2 {spo2}% — below normal, may indicate respiratory compromise")
        else:
            vitals_notes.append(f"SpO2 {spo2}% (normal)")

    sugar = vitals.get("blood_sugar")
    if sugar is not None:
        if sugar > 200:
            vitals_notes.append(f"Blood Sugar {sugar} mg/dL — significantly elevated")
        elif sugar > 140:
            vitals_notes.append(f"Blood Sugar {sugar} mg/dL — elevated (pre-diabetic / diabetic range)")
        elif sugar < 70:
            vitals_notes.append(f"Blood Sugar {sugar} mg/dL — low (hypoglycemia)")
        else:
            vitals_notes.append(f"Blood Sugar {sugar} mg/dL (normal range)")

    rr = vitals.get("respiratory_rate")
    if rr is not None:
        if rr > 20:
            vitals_notes.append(f"Respiratory Rate {rr}/min — elevated (tachypnea)")
        elif rr < 12:
            vitals_notes.append(f"Respiratory Rate {rr}/min — low (bradypnea)")
        else:
            vitals_notes.append(f"Respiratory Rate {rr}/min (normal)")

    results: list[dict] = []
    for info in disease_matches.values():
        profile: DiseaseProfile = info.pop("_profile")

        match_ratio = len(info["matched_medications"]) / max(info["total_disease_medications"], 1)
        input_ratio = len(info["matched_medications"]) / max(len(medications), 1)
        base_conf = 0.50 + 0.35 * match_ratio + 0.15 * input_ratio

        symptom_boost = 0.0
        if symptoms_lower:
            symptom_score = _score_keywords(symptoms_lower, profile)
            if symptom_score > 0:
                symptom_boost = min(symptom_score * 0.02, 0.15)

        info["confidence"] = round(min(base_conf + symptom_boost, 0.97), 2)

        reasoning_parts = [
            f"The patient is taking {', '.join(info['matched_medications'])}, which "
            f"{'is' if len(info['matched_medications']) == 1 else 'are'} commonly prescribed for "
            f"{info['disease']}. {len(info['matched_medications'])} out of "
            f"{info['total_disease_medications']} typical medications for this condition matched.",
        ]
        if symptoms_lower and symptom_boost > 0:
            reasoning_parts.append(
                f"The reported symptoms further support this assessment (symptom correlation detected)."
            )
        if vitals_notes:
            reasoning_parts.append(
                "Vitals assessment: " + "; ".join(vitals_notes) + "."
            )
        info["reasoning"] = " ".join(reasoning_parts)
        results.append(info)

    results.sort(key=lambda r: (r["confidence"], len(r["matched_medications"])), reverse=True)
    return results

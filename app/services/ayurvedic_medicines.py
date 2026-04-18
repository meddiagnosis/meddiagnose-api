"""
Ayurvedic medicine recommendation engine.

Maps diagnosed conditions to traditional Ayurvedic formulations, single herbs,
and home remedies with proper dosage, timing, and safety notes.

Each recommendation includes:
  - name: Ayurvedic medicine / herb name (Sanskrit + common name)
  - form: Churna, Vati, Kashayam, Kwath, Ghrita, Lehyam, Ras, Tail, etc.
  - dosage: Recommended dosage
  - frequency: When and how often to take
  - duration: Recommended course
  - notes: Important safety information, contraindications
  - category: "classical" | "patent" | "single_herb" | "home_remedy"

DISCLAIMER: These are traditional Ayurvedic references and NOT a substitute
for professional medical advice. Always consult a qualified Ayurvedic
practitioner (BAMS) before starting any Ayurvedic treatment.
"""

from __future__ import annotations


def _default_ayurvedic() -> list[dict]:
    """General immunity and wellness Ayurvedic recommendations."""
    return [
        {
            "name": "Chyawanprash",
            "form": "Avaleha (herbal jam)",
            "dosage": "1 tablespoon (15g)",
            "frequency": "Twice daily — morning empty stomach & before bed",
            "duration": "Daily — can be taken long-term",
            "notes": "Classical Rasayana (rejuvenative). Contains Amla, Ashwagandha, and 40+ herbs. Boosts immunity and vitality. Diabetics should use sugar-free variant.",
            "category": "classical",
        },
        {
            "name": "Tulsi (Holy Basil) — Ocimum sanctum",
            "form": "Fresh leaves / Ark (extract)",
            "dosage": "4-5 fresh leaves OR 2-3ml Tulsi Ark",
            "frequency": "Twice daily with warm water",
            "duration": "Daily — safe for long-term use",
            "notes": "Immunomodulatory, anti-microbial, adaptogenic. Considered sacred in Ayurveda. Avoid in pregnancy in therapeutic doses.",
            "category": "single_herb",
        },
        {
            "name": "Triphala Churna",
            "form": "Churna (powder)",
            "dosage": "3-5g (1 teaspoon)",
            "frequency": "Once at bedtime with warm water",
            "duration": "2-3 months as a course",
            "notes": "Combination of Amalaki, Bibhitaki, Haritaki. Gentle detoxifier (Tridosha-shamaka). Improves digestion, metabolism, and elimination. Safe for most people.",
            "category": "classical",
        },
        {
            "name": "Ashwagandha (Withania somnifera)",
            "form": "Churna or Capsule",
            "dosage": "3-5g churna OR 500mg capsule",
            "frequency": "Twice daily with warm milk or water",
            "duration": "2-3 months",
            "notes": "Premier Rasayana herb. Adaptogenic, reduces stress (cortisol), improves energy and sleep. Avoid in hyperthyroidism and pregnancy.",
            "category": "single_herb",
        },
        {
            "name": "Haldi Doodh (Golden Milk)",
            "form": "Home remedy",
            "dosage": "1 glass warm milk + 1/2 tsp turmeric + pinch of black pepper",
            "frequency": "Once daily before bed",
            "duration": "Daily — safe long-term",
            "notes": "Turmeric (Haridra) is anti-inflammatory and immunomodulatory. Black pepper (Pippali) enhances curcumin absorption by 2000%. Classical Ayurvedic combination.",
            "category": "home_remedy",
        },
    ]


AYURVEDIC_DB: dict[str, list[dict]] = {

    # 1 — Upper Respiratory Tract Infection
    "Upper Respiratory Tract Infection": [
        {"name": "Sitopaladi Churna", "form": "Churna (powder)", "dosage": "3-5g", "frequency": "3 times daily with honey (Madhu) after meals", "duration": "5-7 days", "notes": "Classical formulation from Sharangdhara Samhita. Excellent for cough, cold, fever, and bronchitis. Contains Mishri, Vansalochan, Pippali, Ela, Dalchini.", "category": "classical"},
        {"name": "Talisadi Churna", "form": "Churna (powder)", "dosage": "2-3g", "frequency": "3 times daily with honey", "duration": "5-7 days", "notes": "Extended version of Sitopaladi with Talispatra. More potent for productive cough and chest congestion. Kapha-Vata shamaka.", "category": "classical"},
        {"name": "Tribhuvankirti Ras", "form": "Vati (tablet)", "dosage": "1 tablet (125mg)", "frequency": "2-3 times daily with ginger juice or honey", "duration": "3-5 days", "notes": "Classical Rasa Aushadhi for acute fever (Jwara). Contains Shuddha Hingula, Pippali, Shunthi. Very effective in first 48 hours of fever. Discontinue once fever breaks.", "category": "classical"},
        {"name": "Tulsi Kwath (Tulsi Kadha)", "form": "Kwath (decoction)", "dosage": "50-100ml", "frequency": "2-3 times daily, warm", "duration": "Until symptoms resolve", "notes": "Boil Tulsi leaves, Adrak (ginger), Dalchini (cinnamon), Kali Mirch (black pepper), Laung (clove) in 2 cups water, reduce to 1 cup. Classical Agni-deepana and Jwara-nashaka.", "category": "home_remedy"},
        {"name": "Sudarshan Ghana Vati", "form": "Vati (tablet)", "dosage": "2 tablets (500mg each)", "frequency": "Twice daily after meals with warm water", "duration": "5-7 days", "notes": "Contains Chirayata and 48 other herbs. Specific for all types of Jwara (fever). Anti-pyretic and liver-protective.", "category": "classical"},
        {"name": "Lavangadi Vati", "form": "Vati (tablet)", "dosage": "1-2 tablets", "frequency": "3-4 times daily — dissolve slowly in mouth", "duration": "5-7 days", "notes": "Classical throat remedy. Contains Lavanga (clove), Karpura (camphor), Jatiphala. Soothes sore throat and reduces cough.", "category": "classical"},
    ],

    # 2 — Tension-Type Headache
    "Tension-Type Headache": [
        {"name": "Pathyadi Kwath", "form": "Kwath (decoction)", "dosage": "30-50ml", "frequency": "Twice daily on empty stomach", "duration": "7-14 days", "notes": "Classical formulation from Sharangdhara Samhita for Shirahshool (headache). Contains Haritaki, Neem, Guduchi, Amla. Also beneficial for sinusitis-related headache.", "category": "classical"},
        {"name": "Shirashuladi Vajra Ras", "form": "Vati (tablet)", "dosage": "125-250mg", "frequency": "Twice daily with honey or warm water", "duration": "7-14 days", "notes": "Specific Rasa Aushadhi for chronic headaches. Should be taken under Ayurvedic practitioner supervision.", "category": "classical"},
        {"name": "Brahmi (Bacopa monnieri)", "form": "Churna / Capsule / Fresh juice", "dosage": "3-5g churna OR 500mg capsule OR 10ml fresh juice", "frequency": "Twice daily", "duration": "1-3 months", "notes": "Medhya Rasayana (brain tonic). Reduces mental stress, improves cognition, and calms Vata-Pitta. Excellent for stress-induced headaches. Safe for long-term use.", "category": "single_herb"},
        {"name": "Jatamansi (Nardostachys jatamansi)", "form": "Churna or Capsule", "dosage": "1-3g churna OR 250mg capsule", "frequency": "Twice daily", "duration": "1-2 months", "notes": "Premier Ayurvedic nervine. Calms the mind, reduces anxiety-related headaches. Also helps insomnia. Avoid in pregnancy.", "category": "single_herb"},
        {"name": "Chandanadi Tail (Nasya)", "form": "Nasal oil (Nasya)", "dosage": "2-3 drops in each nostril", "frequency": "Once daily in the morning", "duration": "7-14 days", "notes": "Nasya Karma — one of Panchakarma therapies. Medicated oil applied to nostrils to relieve head and sinus pain. Lie down with head tilted back for 5 min after application.", "category": "classical"},
    ],

    # 3 — Acute Gastritis / Gastroenteritis
    "Acute Gastritis": [
        {"name": "Avipattikar Churna", "form": "Churna (powder)", "dosage": "3-5g", "frequency": "Twice daily after meals with lukewarm water", "duration": "14-21 days", "notes": "Classical formulation from Bhaishajya Ratnavali. Best Ayurvedic medicine for hyperacidity (Amlapitta). Contains Trikatu, Triphala, Musta, Vidanga. Pitta-shamaka.", "category": "classical"},
        {"name": "Sutshekhar Ras", "form": "Vati (tablet)", "dosage": "125-250mg", "frequency": "Twice daily with milk or warm water after meals", "duration": "14-21 days", "notes": "Classical Rasa Aushadhi for all Pitta disorders — acidity, burning, nausea. Contains Shuddha Parada, Swarna Makshika Bhasma, Shunthi. Practitioner-guided use recommended.", "category": "classical"},
        {"name": "Kamadudha Ras (Mauktik Yukta)", "form": "Vati (tablet)", "dosage": "125-250mg", "frequency": "Twice daily with milk", "duration": "14-21 days", "notes": "Contains Mukta Bhasma (Pearl). Premier Pitta-shamaka. Excellent for acid reflux, gastritis, and burning sensation. Use pearl-containing variant for best results.", "category": "classical"},
        {"name": "Shatavari (Asparagus racemosus)", "form": "Churna or Capsule", "dosage": "3-5g churna OR 500mg capsule", "frequency": "Twice daily with milk", "duration": "1-2 months", "notes": "Supreme Pitta-shamaka herb. Soothes gastric mucosa, reduces inflammation. Also a Rasayana. Safe in pregnancy. Avoid if there is Ama (toxins) / severe indigestion.", "category": "single_herb"},
        {"name": "Jeera + Dhania + Saunf Water", "form": "Home remedy (infusion)", "dosage": "1 cup (100-150ml)", "frequency": "After every meal", "duration": "Until symptoms resolve", "notes": "Boil 1/2 tsp each of Jeera (cumin), Dhania (coriander seeds), and Saunf (fennel) in 2 cups water, reduce to 1 cup. Classical Deepana-Pachana remedy that improves Agni without aggravating Pitta.", "category": "home_remedy"},
    ],

    # 4 — Allergic Rhinitis / Sinusitis
    "Allergic Rhinitis": [
        {"name": "Haridra Khanda", "form": "Granules", "dosage": "3-5g", "frequency": "Twice daily with warm milk", "duration": "1-2 months", "notes": "Classical anti-allergic formulation. Haridra (turmeric) is the main ingredient. Best for Pratishyaya (allergic rhinitis), skin allergies, urticaria.", "category": "classical"},
        {"name": "Anu Taila (Nasya)", "form": "Nasal oil (Nasya)", "dosage": "2-4 drops in each nostril", "frequency": "Once daily in the morning", "duration": "7-21 days", "notes": "Classical Nasya oil from Ashtanga Hridayam. Best for nasal congestion, sinusitis, allergic rhinitis. Lie supine with head tilted back, instill oil, sniff gently. Do not use during active cold/infection.", "category": "classical"},
        {"name": "Lakshmi Vilas Ras", "form": "Vati (tablet)", "dosage": "125-250mg", "frequency": "Twice daily with honey", "duration": "14-30 days", "notes": "Classical Rasa Aushadhi for Kapha-Vata disorders. Excellent for chronic sinusitis, rhinitis, and recurrent cold. Contains Abhrak Bhasma, Maricha, Pippali.", "category": "classical"},
        {"name": "Trikatu Churna", "form": "Churna (powder)", "dosage": "1-2g", "frequency": "Twice daily with honey before meals", "duration": "14-21 days", "notes": "Combination of Shunthi (ginger), Maricha (black pepper), Pippali (long pepper). Agni-deepana and Kapha-nashaka. Opens nasal passages. Avoid in hyperacidity (Pitta prakriti).", "category": "classical"},
    ],

    # 5 — UTI
    "Urinary Tract Infection": [
        {"name": "Chandraprabha Vati", "form": "Vati (tablet)", "dosage": "2 tablets (500mg each)", "frequency": "Twice daily with warm water", "duration": "14-30 days", "notes": "Classical formulation from Sharangdhara Samhita. Best Ayurvedic medicine for all urinary disorders (Mutrakricchra). Contains 37 ingredients including Shilajit, Guggulu, Loha Bhasma.", "category": "classical"},
        {"name": "Gokshuradi Guggulu", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "Twice daily with water or milk", "duration": "21-30 days", "notes": "Contains Gokshura (Tribulus terrestris) and Guggulu. Specific for Mutravaha Srotas disorders — UTI, kidney stones, prostate issues. Diuretic and anti-inflammatory.", "category": "classical"},
        {"name": "Punarnava (Boerhavia diffusa)", "form": "Churna or Kwath", "dosage": "3-5g churna OR 50ml kwath", "frequency": "Twice daily", "duration": "14-30 days", "notes": "Name means 'one that renews the body'. Best Ayurvedic diuretic (Mutrala). Reduces swelling, cleanses urinary tract. Also hepato-protective.", "category": "single_herb"},
        {"name": "Dhaniya (Coriander) Infusion", "form": "Home remedy", "dosage": "1 cup (100-150ml)", "frequency": "3-4 times daily", "duration": "Until symptoms resolve", "notes": "Soak 2 tbsp coriander seeds in 2 cups water overnight, boil and reduce to 1 cup. Cooling, Pitta-shamaka, natural diuretic. Classical remedy for burning urination (Mutra-daha).", "category": "home_remedy"},
    ],

    # 6 — Lower Back Pain
    "Lower Back Pain": [
        {"name": "Mahayograj Guggulu", "form": "Vati (tablet)", "dosage": "2 tablets (250mg each)", "frequency": "Twice daily with warm water or milk", "duration": "1-2 months", "notes": "Premier classical formulation for all Vata disorders — joint pain, back pain, sciatica, arthritis. Contains Guggulu, Trikatu, Triphala, and multiple Bhasmas. Best taken with Dashamoola Kwath.", "category": "classical"},
        {"name": "Mahanarayan Tail (external)", "form": "Tail (medicated oil)", "dosage": "Apply liberally on affected area", "frequency": "Twice daily — gentle massage for 15-20 min", "duration": "14-30 days", "notes": "Classical Vata-shamaka oil from Bhaishajya Ratnavali. Contains 50+ herbs in sesame oil base. Follow with warm fomentation (Swedana) using hot water bag for maximum benefit.", "category": "classical"},
        {"name": "Dashamoola Kwath", "form": "Kwath (decoction)", "dosage": "30-50ml", "frequency": "Twice daily with warm water", "duration": "14-30 days", "notes": "Decoction of 10 roots (Dashmoola). Supreme Vata-shamaka. Used in back pain, body pain, post-delivery recovery. Can also be added to bath water (Parisheka Swedana).", "category": "classical"},
        {"name": "Nirgundi (Vitex negundo)", "form": "Tail (oil) for external use / Kwath", "dosage": "External massage OR 30ml kwath internally", "frequency": "Twice daily", "duration": "14-21 days", "notes": "Called 'Nirgundi' because it protects the body from disease. Best Vedanasthapana (analgesic) herb. Anti-inflammatory and muscle relaxant. Oil massage on lower back is very effective.", "category": "single_herb"},
    ],

    # 7 — Hypertension
    "Hypertension": [
        {"name": "Sarpagandha Ghana Vati", "form": "Vati (tablet)", "dosage": "250-500mg", "frequency": "Twice daily", "duration": "As advised by practitioner", "notes": "Contains Rauwolfia serpentina — the herb from which modern BP drug Reserpine was originally derived. Classical Ayurvedic antihypertensive. MUST be taken under Ayurvedic practitioner supervision. Not for depression patients.", "category": "classical"},
        {"name": "Arjuna (Terminalia arjuna)", "form": "Churna / Capsule / Ksheer Pak", "dosage": "3-5g churna OR 500mg capsule", "frequency": "Twice daily — best as Arjuna Ksheer Pak (boiled in milk)", "duration": "Long-term (3-6 months)", "notes": "Premier Hridya (cardio-protective) herb in Ayurveda. Strengthens heart muscle, lowers BP, reduces cholesterol. Named after the Mahabharata hero. Classical reference in Charaka Samhita.", "category": "single_herb"},
        {"name": "Brahmi (Bacopa monnieri)", "form": "Churna / Fresh juice / Capsule", "dosage": "3-5g churna OR 500mg capsule", "frequency": "Twice daily with water", "duration": "2-3 months", "notes": "Medhya Rasayana. Calms the nervous system, reduces stress-induced hypertension. Also improves memory and cognition. Safe for long-term use.", "category": "single_herb"},
        {"name": "Jatamansi (Nardostachys jatamansi)", "form": "Churna or Capsule", "dosage": "1-3g", "frequency": "Once daily at bedtime", "duration": "1-2 months", "notes": "Calms Vata and Pitta. Reduces anxiety, improves sleep, and has mild antihypertensive action. Often combined with Sarpagandha.", "category": "single_herb"},
        {"name": "Shankhpushpi (Convolvulus pluricaulis)", "form": "Syrup or Churna", "dosage": "10ml syrup OR 3-5g churna", "frequency": "Twice daily", "duration": "1-3 months", "notes": "Medhya Rasayana that calms the mind and reduces blood pressure through its anxiolytic effect. Tridosha-shamaka.", "category": "single_herb"},
    ],

    # 8 — Type 2 Diabetes
    "Type 2 Diabetes": [
        {"name": "Chandraprabha Vati", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "Twice daily with water", "duration": "2-3 months", "notes": "Multi-target classical formulation. Useful in Prameha (diabetes), UTI, and metabolic disorders. Contains Shilajit, Guggulu, Iron.", "category": "classical"},
        {"name": "Gudmar (Gymnema sylvestre) — Meshashringi", "form": "Churna / Capsule / Fresh leaf", "dosage": "3-5g churna OR 500mg capsule", "frequency": "Twice daily before meals", "duration": "3-6 months", "notes": "Name means 'sugar destroyer' — chewing the leaf temporarily blocks sweet taste. Clinically proven to reduce blood sugar and regenerate beta cells. Premier Prameha herb. Also reduces sugar cravings.", "category": "single_herb"},
        {"name": "Shilajit (Asphaltum)", "form": "Resin / Capsule", "dosage": "300-500mg", "frequency": "Twice daily with warm milk or water", "duration": "2-3 months", "notes": "Rasayana and Prameha-hara. Improves insulin sensitivity, energy, and vitality. Must use purified (Shuddha) Shilajit only. Buy from reputed Ayurvedic companies only.", "category": "single_herb"},
        {"name": "Jamun Beej Churna (Syzygium cumini)", "form": "Churna (seed powder)", "dosage": "3-5g", "frequency": "Twice daily with water before meals", "duration": "2-3 months", "notes": "Jamun (Java Plum) seed powder is a classical Prameha remedy. Reduces blood sugar and improves insulin secretion. Fruit is also beneficial. Widely available.", "category": "single_herb"},
        {"name": "Nisha-Amalaki Churna", "form": "Churna (powder)", "dosage": "3-5g", "frequency": "Twice daily with warm water", "duration": "2-3 months", "notes": "Classical combination of Haridra (turmeric) + Amalaki (amla). Prameha-nashaka from Charaka Samhita. Simple, effective, and safe for long-term use. Also improves immunity.", "category": "classical"},
        {"name": "Karela (Momordica charantia) Juice", "form": "Fresh juice / Home remedy", "dosage": "30-50ml fresh juice", "frequency": "Once daily on empty stomach", "duration": "Regular use", "notes": "Bitter Gourd (Karela) is Tikta Rasa — pacifies Pitta and Kapha, the dosha combination behind most Prameha. Contains plant-insulin. Mix with amla juice to improve taste.", "category": "home_remedy"},
    ],

    # 9 — Skin Infection / Dermatitis
    "Skin Infection": [
        {"name": "Kaishore Guggulu", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "Twice daily with warm water", "duration": "1-2 months", "notes": "Classical blood purifier (Rakta-shodhaka). Best for inflammatory skin conditions, eczema, acne, gout. Contains Guggulu, Triphala, Guduchi. Also anti-arthritic.", "category": "classical"},
        {"name": "Mahamanjisthadi Kwath", "form": "Kwath (decoction) / Tablet", "dosage": "30-50ml kwath OR 2 tablets", "frequency": "Twice daily", "duration": "1-3 months", "notes": "Premier Rakta-Prasadana (blood purifying) formulation. Contains Manjistha, Neem, Haridra, and 40+ herbs. Excellent for chronic skin diseases, acne, eczema, psoriasis.", "category": "classical"},
        {"name": "Neem (Azadirachta indica)", "form": "Capsule / Kwath / Paste (external)", "dosage": "Internally: 500mg capsule OR 30ml kwath. Externally: paste on affected area", "frequency": "Twice daily internal; as needed external", "duration": "1-2 months", "notes": "Sarva-roga-nivarini (curer of all diseases). Best anti-microbial and anti-fungal herb. Neem oil for external fungal infections. Neem water bath for widespread rash.", "category": "single_herb"},
        {"name": "Haridra (Turmeric) + Chandan (Sandalwood) Paste", "form": "External paste / Lepa", "dosage": "Apply thin layer on affected area", "frequency": "Once daily — leave for 20-30 min, wash off", "duration": "Until lesions heal", "notes": "Classical Lepa (topical paste). Mix turmeric powder + sandalwood powder + rose water. Anti-inflammatory, cooling, and antiseptic. Pitta-shamaka externally.", "category": "home_remedy"},
    ],

    # 10 — Anxiety / Stress
    "Anxiety": [
        {"name": "Ashwagandha (Withania somnifera)", "form": "Churna / KSM-66 Capsule", "dosage": "3-5g churna OR 600mg KSM-66 capsule", "frequency": "Twice daily with warm milk", "duration": "2-3 months", "notes": "Premier adaptogenic Rasayana. Clinically proven to reduce cortisol by 28-30%. Balances Vata dosha — the primary dosha in anxiety. Best taken as Ashwagandha Ksheer Pak (boiled in milk with ghee).", "category": "single_herb"},
        {"name": "Brahmi Vati (with gold/silver)", "form": "Vati (tablet)", "dosage": "1-2 tablets (125-250mg)", "frequency": "Twice daily with milk or honey", "duration": "1-3 months", "notes": "Classical Medhya formulation with Swarna (gold) or Rajata (silver) Bhasma. For anxiety, depression, insomnia, poor memory. Practitioner supervision recommended for Bhasma-containing formulations.", "category": "classical"},
        {"name": "Saraswatarishta", "form": "Arishta (fermented liquid)", "dosage": "15-20ml", "frequency": "Twice daily after meals with equal water", "duration": "2-3 months", "notes": "Classical Medhya Arishta containing Brahmi, Shatavari, Ashwagandha, Haritaki. Nourishes the nervous system, improves speech and memory, reduces anxiety. Contains self-generated alcohol (5-10%) as a preservative and bio-enhancer.", "category": "classical"},
        {"name": "Jatamansi (Nardostachys jatamansi)", "form": "Churna / Capsule", "dosage": "1-3g", "frequency": "Once at bedtime with warm milk", "duration": "1-2 months", "notes": "Best Ayurvedic nervine sedative. Calms Prana Vayu. Induces natural sleep without morning grogginess. Often called 'Ayurvedic Valerian'. Can be combined with Ashwagandha.", "category": "single_herb"},
        {"name": "Shankhpushpi Syrup", "form": "Syrup", "dosage": "10-15ml", "frequency": "Twice daily with water", "duration": "2-3 months", "notes": "Medhya Rasayana from Charaka Samhita. Calms the mind, reduces racing thoughts, improves concentration. Safe for children and elderly. The four Medhya herbs in Ayurveda: Brahmi, Shankhpushpi, Guduchi, Yashtimadhu.", "category": "single_herb"},
    ],

    # 11 — Eye Infection
    "Conjunctivitis": [
        {"name": "Triphala Ghrita", "form": "Ghrita (medicated ghee)", "dosage": "5-10g internally OR Triphala wash externally", "frequency": "Internally: once at bedtime. Eye wash: 2-3 times daily", "duration": "7-14 days", "notes": "Classical Netra-Rasayana (eye tonic). For eye wash: boil 1 tsp Triphala in 1 cup water, cool, filter through clean cloth, use as eye wash. Do not apply ghee directly in eyes.", "category": "classical"},
        {"name": "Saptamrit Lauh", "form": "Vati (tablet)", "dosage": "250mg", "frequency": "Twice daily with honey and ghee", "duration": "1-2 months", "notes": "Classical Netra-Rasayana with Loha Bhasma (iron), Triphala, Yashtimadhu. Strengthens eyes, improves vision, useful in conjunctivitis and other eye disorders.", "category": "classical"},
        {"name": "Rose Water Eye Drops", "form": "Eye drops (home remedy)", "dosage": "1-2 drops per eye", "frequency": "2-3 times daily", "duration": "Until symptoms resolve", "notes": "Use pure, food-grade rose water only. Cooling and soothing for inflamed eyes. Classical Pitta-shamaka for Netra-roga. Not a substitute for antibiotic drops if bacterial infection.", "category": "home_remedy"},
    ],

    # 12 — Anemia / Iron Deficiency
    "Anemia": [
        {"name": "Lohasava", "form": "Asava (fermented liquid)", "dosage": "15-20ml", "frequency": "Twice daily after meals with equal water", "duration": "2-3 months", "notes": "Classical iron-rich formulation. Contains Loha Bhasma (iron), Triphala, Trikatu, Chitraka. Best Ayurvedic medicine for Pandu Roga (anemia). Self-generated alcohol aids iron absorption.", "category": "classical"},
        {"name": "Dhatri Lauh", "form": "Vati (tablet)", "dosage": "250-500mg", "frequency": "Twice daily with honey or warm water", "duration": "2-3 months", "notes": "Contains Amalaki (richest vitamin C source) + Loha Bhasma. Vitamin C from Amla enhances iron absorption. Classical synergy — better than just iron tablets.", "category": "classical"},
        {"name": "Punarnava Mandoor", "form": "Vati (tablet)", "dosage": "2 tablets (500mg each)", "frequency": "Twice daily with buttermilk", "duration": "1-3 months", "notes": "Classical formulation for Pandu (anemia) + Shotha (swelling). Contains Mandoor Bhasma (iron oxide), Punarnava, Triphala, Trikatu. Also addresses edema that often accompanies severe anemia.", "category": "classical"},
        {"name": "Amla + Jaggery (Gur) Laddoo", "form": "Home remedy", "dosage": "1-2 laddoos", "frequency": "Daily as snack", "duration": "Regular use", "notes": "Amla provides 600-900mg vitamin C per 100g. Jaggery (Gur) is iron-rich. Together they form a natural iron supplement. Add sesame seeds (Til) for extra iron.", "category": "home_remedy"},
    ],

    # 13 — Acid Reflux / GERD
    "Acid Reflux": [
        {"name": "Avipattikar Churna", "form": "Churna (powder)", "dosage": "3-5g", "frequency": "Twice daily after meals with lukewarm water or milk", "duration": "14-30 days", "notes": "The premier Ayurvedic antacid formulation. Corrects Agni (digestive fire) without suppressing it — unlike modern antacids. Contains Trikatu, Triphala, Musta, Nishoth.", "category": "classical"},
        {"name": "Kamadudha Ras", "form": "Vati (tablet)", "dosage": "125-250mg", "frequency": "Twice daily with milk", "duration": "14-21 days", "notes": "Pitta-shamaka Rasa Aushadhi. Contains Mukta Bhasma (Pearl), Praval Bhasma (Coral). Neutralizes acid, soothes burning. Classical reference in Rasa Tarangini.", "category": "classical"},
        {"name": "Yashtimadhu (Glycyrrhiza glabra) — Mulethi", "form": "Churna / Capsule / Chew stick", "dosage": "3-5g churna OR 500mg capsule OR chew a small piece", "frequency": "Twice daily", "duration": "14-30 days", "notes": "Demulcent — coats and protects gastric mucosa. The original natural antacid. Also called Madhuyashti (sweet stick). Avoid long-term use in hypertension. Modern drug 'Carbenoxolone' was derived from this herb.", "category": "single_herb"},
        {"name": "Gulkand (Rose Petal Preserve)", "form": "Lehyam / Home remedy", "dosage": "1-2 teaspoons", "frequency": "Twice daily — with milk or directly", "duration": "Regular use in summer/Pitta season", "notes": "Classical Pitta-shamaka. Cooling, reduces acidity and heat. Made from rose petals and sugar/mishri. Can be mixed with cold milk. Also relieves mouth ulcers.", "category": "home_remedy"},
    ],

    # 14 — Joint Pain / Arthritis
    "Joint Pain": [
        {"name": "Yograj Guggulu", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "Twice daily with warm water or Dashamoola Kwath", "duration": "1-3 months", "notes": "Classical formulation for Vata-Vyadhi (all Vata disorders). Contains Guggulu, Chitraka, Pippali, Triphala. First-line Ayurvedic medicine for joint pain, arthritis, and rheumatism.", "category": "classical"},
        {"name": "Mahanarayan Tail", "form": "Tail (external oil)", "dosage": "Apply on affected joints", "frequency": "Twice daily — massage 15-20 min followed by warm compress", "duration": "Regular use", "notes": "50+ herb medicated oil in sesame oil base. Best external oil for joint pain, stiffness, and inflammation. Warm the oil slightly before application. Follow with Swedana (steam/fomentation).", "category": "classical"},
        {"name": "Rasnadi Guggulu", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "Twice daily with warm water", "duration": "1-2 months", "notes": "Contains Rasna (Pluchea lanceolata) — premier Vata-shamaka herb. Specific for Amavata (Rheumatoid-like condition) and Sandhivata (Osteoarthritis). Often combined with Dashamoola Kwath.", "category": "classical"},
        {"name": "Shallaki (Boswellia serrata)", "form": "Capsule / Churna", "dosage": "400-600mg capsule OR 3-5g churna", "frequency": "Twice daily", "duration": "2-3 months", "notes": "Boswellic acids have been clinically proven anti-inflammatory (comparable to NSAIDs without GI side effects). Best for Sandhivata (osteoarthritis) and Amavata (inflammatory arthritis).", "category": "single_herb"},
    ],

    # 15 — Bronchitis / Pneumonia
    "Respiratory Infection": [
        {"name": "Vasavaleha", "form": "Avaleha (herbal jam)", "dosage": "5-10g", "frequency": "Twice daily with warm milk or water", "duration": "14-30 days", "notes": "Classical formulation based on Vasa (Adhatoda vasica). Best for productive cough with blood-tinged sputum (Raktapitta). Bronchodilator and mucolytic. Modern drug Bromhexine was derived from this plant.", "category": "classical"},
        {"name": "Kantakari Avaleha", "form": "Avaleha (herbal jam)", "dosage": "5-10g", "frequency": "Twice daily with warm water", "duration": "14-21 days", "notes": "Contains Kantakari (Solanum xanthocarpum). Kasa-Shwasa-hara (anti-cough, anti-asthmatic). Excellent for bronchitis with wheezing.", "category": "classical"},
        {"name": "Sitopaladi + Talisadi Churna", "form": "Churna (powder)", "dosage": "3-5g mixed", "frequency": "3 times daily with honey", "duration": "7-14 days", "notes": "Classical combination for Kasa-Shwasa (cough and breathlessness). The honey acts as Yogavahi (bio-enhancer) and itself is Kapha-nashaka.", "category": "classical"},
    ],

    # 16 — Thyroid (Hypothyroidism)
    "Thyroid Disorder": [
        {"name": "Kanchanar Guggulu", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "Twice daily with warm water", "duration": "2-3 months", "notes": "Premier classical formulation for Galaganda (goiter/thyroid disorders). Contains Kanchanar bark, Triphala, Trikatu, Guggulu. Reduces thyroid nodules and regulates function. Must not replace thyroid hormone if prescribed.", "category": "classical"},
        {"name": "Ashwagandha (Withania somnifera)", "form": "Churna / Capsule", "dosage": "3-5g churna OR 500mg capsule", "frequency": "Twice daily with warm milk", "duration": "2-3 months", "notes": "Clinically shown to improve T3, T4, and TSH levels in subclinical hypothyroidism. Adaptogenic — normalizes thyroid function. Avoid in hyperthyroidism.", "category": "single_herb"},
        {"name": "Punarnava (Boerhavia diffusa)", "form": "Churna / Capsule", "dosage": "3-5g", "frequency": "Twice daily", "duration": "1-2 months", "notes": "Reduces hypothyroid-related water retention and swelling. Diuretic and anti-inflammatory. Also hepato-protective.", "category": "single_herb"},
    ],

    # 17 — Asthma
    "Bronchial Asthma": [
        {"name": "Swas Kuthar Ras", "form": "Vati (tablet)", "dosage": "125-250mg", "frequency": "2-3 times daily with honey and ginger juice", "duration": "14-30 days", "notes": "Classical Rasa Aushadhi specific for Tamaka Shwasa (bronchial asthma). Contains Shuddha Parada, Tankan Bhasma, Maricha. Practitioner supervision required.", "category": "classical"},
        {"name": "Kantakari + Vasa combination", "form": "Kwath / Syrup", "dosage": "30-50ml kwath OR 10ml syrup", "frequency": "Twice daily", "duration": "1-2 months", "notes": "Kantakari is Shwasa-hara and Vasa is bronchodilator. Classical synergistic combination for chronic asthma management. Reduces frequency and severity of attacks.", "category": "classical"},
        {"name": "Haridra (Turmeric) + Honey", "form": "Home remedy", "dosage": "1/2 tsp turmeric + 1 tsp honey", "frequency": "Twice daily (morning and before bed)", "duration": "Regular use", "notes": "Curcumin is anti-inflammatory and immunomodulatory. Honey is Kapha-nashaka and Yogavahi. Together they reduce airway inflammation. Avoid during acute asthma attack.", "category": "home_remedy"},
    ],

    # 18 — Migraine
    "Migraine": [
        {"name": "Pathyadi Kwath", "form": "Kwath (decoction)", "dosage": "30-50ml", "frequency": "Twice daily on empty stomach", "duration": "1-2 months", "notes": "Classical Shirahshool-nashaka (headache destroyer). Contains Haritaki, Neem, Guduchi, Devdaru. Especially effective for Pitta-type headaches (throbbing, light-sensitive).", "category": "classical"},
        {"name": "Godanti Bhasma", "form": "Bhasma (calcined powder)", "dosage": "250-500mg", "frequency": "Twice daily with honey", "duration": "14-30 days", "notes": "Calcined gypsum. Pitta-shamaka. Specific for migraine with heat/burning/light sensitivity. Classical reference in Ayurveda Prakasha. Safe bhasma — no heavy metals.", "category": "classical"},
        {"name": "Brahmi + Jatamansi + Shankhpushpi", "form": "Combined churna", "dosage": "3-5g mixed", "frequency": "Twice daily with warm milk", "duration": "2-3 months", "notes": "Triple Medhya Rasayana combination. Addresses the neurological root cause of migraines. Preventive — reduces frequency over time. Safe for long-term use.", "category": "single_herb"},
    ],

    # 19 — Kidney Stones
    "Kidney Stones": [
        {"name": "Gokshuradi Guggulu", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "Twice daily with water", "duration": "1-3 months", "notes": "Best for Ashmari (urinary stones). Gokshura is lithotriptic (Bhedaniya — stone-breaking). Guggulu is anti-inflammatory. Combine with plenty of water intake (3+ liters/day).", "category": "classical"},
        {"name": "Chandraprabha Vati", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "Twice daily", "duration": "1-2 months", "notes": "Supports Gokshuradi Guggulu. Strengthens Mutravaha Srotas (urinary system). Contains Shilajit and mineral bhasmas. Classical multi-target formulation.", "category": "classical"},
        {"name": "Pashanbhed (Bergenia ligulata)", "form": "Churna / Kwath", "dosage": "3-5g churna OR 50ml kwath", "frequency": "Twice daily", "duration": "1-2 months", "notes": "Name literally means 'stone breaker'. Classical lithotriptic herb used since Charaka's time. Diuretic and anti-calculi. Combine with Kulatha (Horse gram) kwath for enhanced action.", "category": "single_herb"},
        {"name": "Kulatha (Horse Gram) Water", "form": "Home remedy", "dosage": "1-2 cups", "frequency": "Daily", "duration": "Regular use", "notes": "Soak 2 tbsp Kulatha dal overnight, boil in 3 cups water, reduce to 1 cup, strain. Classical Ashmari-nashaka. Creates alkaline urine conditions unfavorable for stone formation.", "category": "home_remedy"},
    ],

    # 20 — Depression
    "Depressive Disorder": [
        {"name": "Brahmi Vati (Swarna Yukta)", "form": "Vati (tablet)", "dosage": "125-250mg", "frequency": "Twice daily with milk and honey", "duration": "2-3 months", "notes": "Gold-containing Medhya Rasayana. Swarna Bhasma has been used in Ayurveda as a mood elevator and anti-depressant for millennia. Practitioner supervision required for gold-containing formulations.", "category": "classical"},
        {"name": "Ashwagandha", "form": "Churna / KSM-66 Capsule", "dosage": "3-5g churna OR 600mg capsule", "frequency": "Twice daily with warm milk", "duration": "3-6 months", "notes": "Adaptogenic and Rasayana. Reduces cortisol, improves serotonin signaling. Clinically proven for depression and anxiety. Best taken as Ashwagandha Ksheer Pak.", "category": "single_herb"},
        {"name": "Saraswatarishta", "form": "Arishta (fermented liquid)", "dosage": "15-20ml", "frequency": "Twice daily after meals with equal water", "duration": "2-3 months", "notes": "Nourishes Manas (mind) and Prana Vayu. Combination of Medhya herbs — Brahmi, Ashwagandha, Shatavari, Vidari. Classical nervine tonic.", "category": "classical"},
        {"name": "Jatamansi + Ashwagandha Milk", "form": "Home remedy", "dosage": "1/2 tsp Jatamansi + 1 tsp Ashwagandha in 1 cup warm milk", "frequency": "Once at bedtime", "duration": "1-2 months", "notes": "Calming bedtime tonic. Improves sleep quality, reduces negative thought patterns, nourishes the nervous system. Add 1/4 tsp nutmeg (Jaiphal) for enhanced sedative effect.", "category": "home_remedy"},
    ],

    # 21 — Ear Infection
    "Ear Infection": [
        {"name": "Bilva Tail (Ear drops)", "form": "Tail (medicated oil)", "dosage": "2-3 warm drops in affected ear", "frequency": "Twice daily", "duration": "7-14 days", "notes": "Classical Karna-Purana (ear instillation) oil. Warm the oil to body temperature (lukewarm). Lie on opposite side for 5 min after instillation. Do NOT use if eardrum is perforated.", "category": "classical"},
        {"name": "Dashmoola Kwath", "form": "Kwath (decoction)", "dosage": "30-50ml", "frequency": "Twice daily with warm water", "duration": "7-14 days", "notes": "Vata-shamaka decoction of 10 roots. Addresses the Vata component of ear pain (Karna Shool). Anti-inflammatory systemic action.", "category": "classical"},
    ],

    # 22 — Dengue
    "Dengue": [
        {"name": "Papaya Leaf Juice", "form": "Fresh juice / Home remedy", "dosage": "25-30ml fresh leaf juice", "frequency": "Twice daily", "duration": "5-7 days during illness", "notes": "Clinically proven to increase platelet count. Use fresh Carica papaya leaves — wash, crush, extract juice. Bitter taste — can add a little honey. Multiple clinical trials support efficacy. Classical Ayurvedic use as Eranda-Karkatakadi.", "category": "home_remedy"},
        {"name": "Sudarshan Ghana Vati", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "3 times daily with warm water", "duration": "7-10 days", "notes": "Best Ayurvedic anti-pyretic for Vishama Jwara (intermittent/viral fevers including dengue). Contains 48 herbs with Chirayata as the main ingredient.", "category": "classical"},
        {"name": "Giloy (Guduchi — Tinospora cordifolia)", "form": "Kwath / Tablet / Fresh juice", "dosage": "30-50ml kwath OR 500mg tablet OR 10ml fresh juice", "frequency": "Twice daily", "duration": "7-14 days", "notes": "Called 'Amrita' (nectar of immortality). Immunomodulatory, anti-viral, raises platelet count. The single most important herb during dengue. Boil fresh Giloy stem in water for kwath.", "category": "single_herb"},
    ],

    # 24 — Vitamin D Deficiency
    "Vitamin D Deficiency": [
        {"name": "Lakshadi Guggulu", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "Twice daily with warm milk", "duration": "2-3 months", "notes": "Classical Asthi-Sandhana (bone-healing) formulation. Contains Laksha, Asthi Shrinkhala, Guggulu. Strengthens bones and aids calcium metabolism. Often used post-fracture.", "category": "classical"},
        {"name": "Praval Pishti / Praval Bhasma", "form": "Pishti (fine powder)", "dosage": "250-500mg", "frequency": "Twice daily with milk", "duration": "1-2 months", "notes": "Coral-derived natural calcium. Pitta-shamaka and calcium-rich. Better absorbed than synthetic calcium as it contains trace minerals. Classical reference in Rasa Tarangini.", "category": "classical"},
        {"name": "Ashwagandha + Shatavari", "form": "Combined churna in milk", "dosage": "3g each in warm milk", "frequency": "Once daily", "duration": "2-3 months", "notes": "Rasayana combination that supports bone health, hormone balance, and calcium absorption. Ashwagandha supports vitamin D metabolism. Shatavari provides plant-based calcium.", "category": "single_herb"},
    ],

    # 30 — Insomnia
    "Insomnia": [
        {"name": "Jatamansi (Nardostachys jatamansi)", "form": "Churna / Capsule", "dosage": "1-3g", "frequency": "Once at bedtime with warm milk", "duration": "1-2 months", "notes": "Best Ayurvedic herb for Anidra (insomnia). Natural sedative without morning grogginess. Calms Prana Vayu and Sadhaka Pitta. Can be used as Jatamansi Ghrita for enhanced effect.", "category": "single_herb"},
        {"name": "Brahmi Vati", "form": "Vati (tablet)", "dosage": "1-2 tablets", "frequency": "Once at bedtime with milk", "duration": "1-2 months", "notes": "Medhya Rasayana. Calms mental chatter and promotes deep, restorative sleep (Swapna). Also improves dream quality. Works better than Brahmi alone due to synergistic herbs.", "category": "classical"},
        {"name": "Ashwagandha Ksheer Pak", "form": "Home remedy (milk preparation)", "dosage": "1 cup", "frequency": "Once at bedtime", "duration": "Regular use", "notes": "Boil 1 tsp Ashwagandha + 1/4 tsp nutmeg (Jaiphal) in 1 cup milk with 1 tsp ghee. Classical Nidra-janaka (sleep-inducing) Rasayana preparation from Charaka Samhita.", "category": "home_remedy"},
    ],

    # 31 — PCOS
    "Polycystic Ovary Syndrome": [
        {"name": "Pushyanug Churna", "form": "Churna (powder)", "dosage": "3-5g", "frequency": "Twice daily with honey or warm water", "duration": "2-3 months", "notes": "Premier classical formulation for all Stri Roga (gynecological disorders). Contains Pushyanug, Lodhra, Nagkesar. Regulates menstrual cycle, reduces excessive bleeding.", "category": "classical"},
        {"name": "Kanchanar Guggulu", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "Twice daily with warm water", "duration": "2-3 months", "notes": "Acts on Granthi (cysts and growths). Reduces ovarian cysts through its Lekhana (scraping) action. Also addresses thyroid component of PCOS.", "category": "classical"},
        {"name": "Shatavari (Asparagus racemosus)", "form": "Churna / Capsule", "dosage": "3-5g churna OR 500mg capsule", "frequency": "Twice daily with milk", "duration": "3-6 months", "notes": "The best Stri-Rasayana (female rejuvenative). Balances estrogen, supports ovarian function, improves fertility. Name means 'she who has 100 husbands' — indicating vitality.", "category": "single_herb"},
        {"name": "Gudmar (Gymnema sylvestre)", "form": "Capsule", "dosage": "500mg", "frequency": "Twice daily before meals", "duration": "2-3 months", "notes": "Addresses insulin resistance component of PCOS. Reduces sugar cravings, aids weight management. PCOS often has a metabolic-hormonal dual pathology.", "category": "single_herb"},
    ],

    # 32 — Gout
    "Gout": [
        {"name": "Kaishore Guggulu", "form": "Vati (tablet)", "dosage": "2 tablets", "frequency": "Twice daily with warm water", "duration": "1-2 months", "notes": "Best for Vatarakta (gout). Rakta-shodhaka (blood purifier) + anti-inflammatory. Contains Guduchi, Triphala, Guggulu. Reduces uric acid and joint inflammation.", "category": "classical"},
        {"name": "Giloy (Guduchi)", "form": "Churna / Kwath / Satva", "dosage": "Giloy Satva 500mg OR 30ml kwath", "frequency": "Twice daily", "duration": "1-2 months", "notes": "Guduchi Satva (starch extract) is the most concentrated form. Anti-inflammatory and uric acid-lowering. Classical treatment for Vatarakta in Charaka Samhita.", "category": "single_herb"},
        {"name": "Punarnavadi Kwath", "form": "Kwath (decoction)", "dosage": "30-50ml", "frequency": "Twice daily", "duration": "14-30 days", "notes": "Diuretic decoction that helps flush uric acid through kidneys. Anti-inflammatory. Also reduces swelling in gouty joints.", "category": "classical"},
    ],

    # 36 — IBS
    "Irritable Bowel Syndrome": [
        {"name": "Kutajarishta", "form": "Arishta (fermented liquid)", "dosage": "15-20ml", "frequency": "Twice daily after meals with equal water", "duration": "1-2 months", "notes": "Classical formulation from Charaka Samhita. Best for Atisara (diarrhea-predominant IBS). Contains Kutaja (Holarrhena antidysenterica) — the premier anti-diarrheal herb.", "category": "classical"},
        {"name": "Hingwashtak Churna", "form": "Churna (powder)", "dosage": "2-3g", "frequency": "Before meals with warm water or first morsel of food", "duration": "14-30 days", "notes": "Best Agni-deepana (appetite kindler) and Vayu-nashaka (anti-flatulent). Contains Hing (Asafoetida), Trikatu, Jeera, Ajwain. Addresses bloating and gas — cardinal symptoms of IBS.", "category": "classical"},
        {"name": "Bilva (Aegle marmelos)", "form": "Churna / Capsule", "dosage": "3-5g", "frequency": "Twice daily", "duration": "1-2 months", "notes": "Sacred tree in Ayurveda. Bilva fruit is astringent — binds loose stools. Also anti-microbial. Unripe Bilva fruit is more astringent (for diarrhea); ripe fruit is mild laxative (for constipation-type IBS).", "category": "single_herb"},
        {"name": "Takra (Medicated Buttermilk)", "form": "Home remedy", "dosage": "1 glass (200ml)", "frequency": "With lunch daily", "duration": "Regular use", "notes": "Buttermilk with roasted cumin + rock salt + curry leaves. Classical Agni-vardhaka. Probiotic, easy to digest, reduces Vata. Charaka says 'Takra is the best drink for IBS patients.'", "category": "home_remedy"},
    ],

    # 38 — Psoriasis
    "Psoriasis": [
        {"name": "Panchatikta Ghrita Guggulu", "form": "Vati + Ghrita", "dosage": "2 tablets; Ghrita: 5-10g", "frequency": "Twice daily", "duration": "2-3 months", "notes": "The best classical formulation for Kustha (chronic skin diseases including psoriasis). Pancha-tikta = 5 bitter herbs (Neem, Patol, Guduchi, Vasa, Kantakari). Bitter taste pacifies Pitta and purifies Rakta. Often paired with Panchatikta Ghrita (medicated ghee) internally.", "category": "classical"},
        {"name": "Mahamanjisthadi Kwath", "form": "Kwath / Tablet", "dosage": "30-50ml kwath OR 2 tablets", "frequency": "Twice daily", "duration": "2-3 months", "notes": "Supreme Rakta-Prasadana. 40+ herb decoction for chronic, stubborn skin diseases. Manjistha is the main herb — cleanses blood, reduces inflammation and discoloration.", "category": "classical"},
        {"name": "Karanj Tail (external)", "form": "Tail (medicated oil)", "dosage": "Apply thin layer on patches", "frequency": "Twice daily", "duration": "Until improvement", "notes": "Karanj (Pongamia pinnata) oil has anti-psoriatic properties. Can be mixed with coconut oil if too strong. Classical Kushta-hara external application.", "category": "classical"},
    ],

    # 40 — COPD
    "Obstructive Pulmonary Disease": [
        {"name": "Agastya Haritaki Rasayana", "form": "Avaleha (herbal jam)", "dosage": "5-10g", "frequency": "Twice daily with warm water or milk", "duration": "2-3 months", "notes": "Classical Rasayana specific for Shwasa-Kasa (respiratory disorders). Contains Haritaki, Dashamoola, Bala, and 15+ herbs. Strengthens lungs, reduces mucus, improves breathing capacity.", "category": "classical"},
        {"name": "Vasavaleha", "form": "Avaleha (herbal jam)", "dosage": "5-10g", "frequency": "Twice daily", "duration": "1-2 months", "notes": "Vasa (Adhatoda vasica) based bronchodilator and mucolytic. Opens airways and reduces sputum. The modern drug Bromhexine originated from this plant.", "category": "classical"},
        {"name": "Pippali (Piper longum) Rasayana", "form": "Churna — Vardhamana Pippali", "dosage": "Start with 1 Pippali, increase by 1 daily to 10, then decrease", "frequency": "Once daily with warm milk and honey", "duration": "20-day course, can repeat after 1 month gap", "notes": "Vardhamana (gradual escalation) Pippali Rasayana from Charaka Samhita. Rejuvenates lungs (Pranavaha Srotas). Classical protocol for chronic respiratory diseases.", "category": "classical"},
    ],
}


def get_ayurvedic_medicines(diagnosis_name: str) -> list[dict]:
    """Return condition-specific Ayurvedic medicine recommendations."""
    for key, medicines in AYURVEDIC_DB.items():
        if key.lower() in diagnosis_name.lower():
            return medicines
    return _default_ayurvedic()

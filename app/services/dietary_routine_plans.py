"""
Dietary and daily routine plan generator based on diagnosis.

Generates condition-specific dietary recommendations and structured daily
routine plans that complement the medical treatment.
"""

from __future__ import annotations


def _default_dietary_plan() -> list[dict]:
    return [
        {
            "category": "Recommended Foods",
            "icon": "green",
            "items": [
                "Fresh fruits and vegetables (5+ servings/day)",
                "Whole grains — brown rice, oats, whole wheat roti",
                "Lean protein — dal, paneer, chicken, fish, eggs",
                "Nuts and seeds in moderation (almonds, walnuts, flaxseed)",
                "Low-fat dairy — curd, buttermilk, skimmed milk",
                "Healthy fats — olive oil, mustard oil",
            ],
        },
        {
            "category": "Foods to Avoid",
            "icon": "red",
            "items": [
                "Excessive sugar and sugary drinks",
                "Deep-fried and heavily processed food",
                "Excessive salt (limit to 5g/day)",
                "Alcohol and caffeinated beverages in excess",
                "Packaged/junk food with preservatives",
            ],
        },
        {
            "category": "Hydration",
            "icon": "blue",
            "items": [
                "Drink 8-10 glasses (2.5-3L) of water daily",
                "Start morning with a glass of warm water",
                "Herbal teas — green tea, chamomile, ginger tea",
                "Fresh coconut water for electrolytes",
            ],
        },
        {
            "category": "Sample Meal Plan",
            "icon": "meal",
            "items": [
                "Breakfast (7-8 AM): Oats porridge with fruits OR vegetable poha with curd",
                "Mid-Morning (10-11 AM): A fruit (banana/apple) + handful of almonds",
                "Lunch (12:30-1:30 PM): 2 roti + dal + sabzi + salad + curd",
                "Evening Snack (4-5 PM): Green tea + roasted chana OR sprouts",
                "Dinner (7-8 PM): Light khichdi OR 1 roti + vegetable soup + salad",
                "Before Bed: Warm turmeric milk (haldi doodh)",
            ],
        },
    ]


def _default_routine_plan() -> list[dict]:
    return [
        {
            "time": "Early Morning (6:00 - 7:00 AM)",
            "icon": "sunrise",
            "activities": [
                "Wake up and drink a glass of warm water with lemon",
                "5 minutes of deep breathing / pranayama",
                "Light stretching for 10 minutes",
                "Morning walk for 20-30 minutes (if able)",
            ],
        },
        {
            "time": "Morning (7:00 - 9:00 AM)",
            "icon": "morning",
            "activities": [
                "Shower and freshen up",
                "Healthy breakfast as per dietary plan",
                "Take prescribed morning medications with food",
                "Brief meditation or mindfulness (5-10 min)",
            ],
        },
        {
            "time": "Mid-Day (10:00 AM - 1:00 PM)",
            "icon": "sun",
            "activities": [
                "Mid-morning snack (fruit/nuts)",
                "Stay hydrated — drink water every hour",
                "Take short breaks if working (every 45 min)",
                "Balanced lunch as per dietary plan",
            ],
        },
        {
            "time": "Afternoon (1:00 - 5:00 PM)",
            "icon": "afternoon",
            "activities": [
                "Short rest or power nap (15-20 min) if needed",
                "Afternoon medications if prescribed",
                "Light activity — short walk, gentle stretching",
                "Evening snack as per dietary plan",
            ],
        },
        {
            "time": "Evening (5:00 - 8:00 PM)",
            "icon": "evening",
            "activities": [
                "Light exercise — yoga, walking, or gentle activity",
                "Dinner as per dietary plan (keep it light)",
                "Take evening medications if prescribed",
                "Quality time with family / relaxation",
            ],
        },
        {
            "time": "Night (8:00 - 10:00 PM)",
            "icon": "moon",
            "activities": [
                "Avoid screens 30 min before bed",
                "Warm turmeric milk or chamomile tea",
                "Gentle stretching or deep breathing",
                "Sleep by 10:00 PM — aim for 7-8 hours",
            ],
        },
    ]


DISEASE_PLANS: dict[str, dict] = {

    "Upper Respiratory Tract Infection": {
        "dietary": [
            {"category": "Immune-Boosting Foods", "icon": "green", "items": [
                "Warm chicken or vegetable soup (kadha)",
                "Citrus fruits — oranges, mosambi, amla (rich in Vitamin C)",
                "Ginger-honey-lemon tea (3-4 times/day)",
                "Garlic and turmeric in cooking (natural anti-inflammatories)",
                "Warm dal-chawal with ghee",
                "Tulsi (holy basil) tea",
                "Steamed vegetables — carrots, broccoli, spinach",
            ]},
            {"category": "Foods to Avoid", "icon": "red", "items": [
                "Cold drinks, ice cream, and chilled water",
                "Deep-fried food — pakoras, samosas, chips",
                "Dairy if it increases mucus (some people)",
                "Sugary sweets and processed snacks",
                "Spicy and oily food that irritates throat",
            ]},
            {"category": "Hydration & Soothing Drinks", "icon": "blue", "items": [
                "Warm water throughout the day (every 30 min)",
                "Kadha — boil ginger, tulsi, pepper, cloves in water",
                "Honey + warm water (soothing for sore throat)",
                "Haldi doodh (turmeric milk) before bed",
                "Avoid caffeine — switch to green tea",
            ]},
            {"category": "Sample Recovery Meal Plan", "icon": "meal", "items": [
                "Breakfast: Warm moong dal cheela + ginger tea",
                "Mid-Morning: Orange or mosambi juice (fresh, not cold)",
                "Lunch: Soft khichdi with ghee + steamed vegetables",
                "Evening: Tulsi-ginger kadha + dry fruit laddoo",
                "Dinner: Tomato or mixed veg soup + 1 soft roti",
                "Bedtime: Turmeric milk with honey",
            ]},
        ],
        "routine": [
            {"time": "Early Morning (6:30 - 7:30 AM)", "icon": "sunrise", "activities": [
                "Warm water with honey and lemon",
                "Steam inhalation for 5-7 minutes (add eucalyptus oil)",
                "Gentle stretching only — no intense exercise",
                "Gargle with warm salt water",
            ]},
            {"time": "Morning (7:30 - 9:00 AM)", "icon": "morning", "activities": [
                "Warm shower (avoid cold water)",
                "Immune-boosting breakfast as per diet plan",
                "Take prescribed medications (paracetamol, cetirizine)",
                "Rest if feeling feverish",
            ]},
            {"time": "Mid-Day (10:00 AM - 1:00 PM)", "icon": "sun", "activities": [
                "Kadha or warm herbal drink",
                "Stay in warm environment — avoid AC drafts",
                "Light lunch — easily digestible food",
                "Steam inhalation again if congested",
            ]},
            {"time": "Afternoon (1:00 - 5:00 PM)", "icon": "afternoon", "activities": [
                "Rest or sleep — body heals during rest",
                "Keep drinking warm fluids every hour",
                "Gargle with salt water after lunch",
                "Light reading or relaxation — avoid strain",
            ]},
            {"time": "Evening (5:00 - 8:00 PM)", "icon": "evening", "activities": [
                "Short slow walk indoors if feeling better",
                "Light dinner — soup-based meal",
                "Evening medication dose",
                "Steam inhalation before bed",
            ]},
            {"time": "Night (8:00 - 10:00 PM)", "icon": "moon", "activities": [
                "Turmeric milk with a pinch of pepper",
                "Elevate head with extra pillow (reduces congestion)",
                "Apply Vicks / balm on chest if needed",
                "Sleep early — aim for 8-9 hours during recovery",
            ]},
        ],
    },

    "Tension-Type Headache": {
        "dietary": [
            {"category": "Brain-Healthy Foods", "icon": "green", "items": [
                "Magnesium-rich foods — spinach, almonds, pumpkin seeds, bananas",
                "Omega-3 fatty acids — walnuts, flaxseeds, fatty fish",
                "Complex carbs — whole wheat, oats, brown rice",
                "Fresh fruits — especially berries and watermelon",
                "Hydrating foods — cucumber, watermelon, coconut water",
            ]},
            {"category": "Headache Triggers to Avoid", "icon": "red", "items": [
                "Excessive caffeine (more than 2 cups/day)",
                "Alcohol — especially red wine",
                "MSG-containing food (Chinese takeout, instant noodles)",
                "Aged cheese, processed meats (contain tyramine)",
                "Artificial sweeteners (aspartame)",
                "Skipping meals — maintain regular eating schedule",
            ]},
            {"category": "Hydration", "icon": "blue", "items": [
                "Drink 3+ liters of water daily (dehydration is a key trigger)",
                "Peppermint tea — natural headache reliever",
                "Ginger tea with honey",
                "Avoid excessive sugary drinks",
            ]},
            {"category": "Sample Meal Plan", "icon": "meal", "items": [
                "Breakfast (7-8 AM): Oats with banana + pumpkin seeds + green tea",
                "Mid-Morning: Handful of almonds + coconut water",
                "Lunch: Brown rice + palak dal + salad + curd",
                "Evening: Peppermint tea + trail mix (nuts + seeds)",
                "Dinner (7 PM): Multigrain roti + light sabzi + soup",
            ]},
        ],
        "routine": [
            {"time": "Early Morning (6:00 - 7:00 AM)", "icon": "sunrise", "activities": [
                "Wake up at consistent time every day",
                "Drink 2 glasses of water immediately",
                "5-10 minutes neck and shoulder stretches",
                "Deep breathing exercise — 4-7-8 technique",
            ]},
            {"time": "Morning (7:00 - 9:00 AM)", "icon": "morning", "activities": [
                "Do not skip breakfast — have it within 1 hour of waking",
                "Gentle yoga — child's pose, cat-cow, forward fold",
                "Brief walk in fresh air (15-20 min)",
                "Take pain relief medication only if needed",
            ]},
            {"time": "Mid-Day (10:00 AM - 1:00 PM)", "icon": "sun", "activities": [
                "Follow 20-20-20 rule for screen time",
                "Stand and stretch every 45 minutes",
                "Check posture — keep screen at eye level",
                "Balanced lunch — don't skip or delay",
            ]},
            {"time": "Afternoon (1:00 - 5:00 PM)", "icon": "afternoon", "activities": [
                "Apply peppermint oil to temples if tension builds",
                "5-minute desk stretches — neck rolls, shoulder shrugs",
                "Stay hydrated — set hourly water reminders",
                "Short mindfulness break (5 min guided meditation)",
            ]},
            {"time": "Evening (5:00 - 8:00 PM)", "icon": "evening", "activities": [
                "30-minute walk or light exercise",
                "Progressive muscle relaxation (PMR) technique",
                "Light, early dinner",
                "Reduce screen brightness and use blue light filter",
            ]},
            {"time": "Night (8:00 - 10:00 PM)", "icon": "moon", "activities": [
                "Warm bath with Epsom salts (relieves tension)",
                "Gentle neck stretches before bed",
                "No screens 30 min before sleep",
                "Consistent bedtime — sleep and wake at same time daily",
            ]},
        ],
    },

    "Acute Gastritis": {
        "dietary": [
            {"category": "Stomach-Soothing Foods", "icon": "green", "items": [
                "Bananas (coating and protective for stomach lining)",
                "Plain rice / khichdi with minimal spice",
                "Boiled/steamed vegetables — potato, lauki, tori",
                "Curd / yogurt (probiotics help gut healing)",
                "Toast or plain crackers when nauseous",
                "Papaya (contains digestive enzymes)",
                "Coconut water (gentle on stomach + electrolytes)",
            ]},
            {"category": "Foods to Strictly Avoid", "icon": "red", "items": [
                "Spicy food — chili, mirchi, garam masala",
                "Oily / fried food — pakoras, poori, fried rice",
                "Acidic foods — tomatoes, citrus (temporarily)",
                "Tea and coffee on empty stomach",
                "Alcohol and carbonated drinks",
                "Raw onion and garlic in excess",
                "Mint (can relax lower esophageal sphincter)",
            ]},
            {"category": "Hydration & Healing Drinks", "icon": "blue", "items": [
                "ORS solution if dehydrated from vomiting/diarrhea",
                "Jeera water (cumin water) — boil and sip warm",
                "Buttermilk (chaas) with a pinch of rock salt",
                "Room temperature water (avoid cold or hot extremes)",
                "Avoid tea/coffee for 2-3 days",
            ]},
            {"category": "Recovery Meal Plan", "icon": "meal", "items": [
                "Breakfast: Plain toast or idli + curd",
                "Mid-Morning: Banana + coconut water",
                "Lunch: Plain rice + moong dal (no spice) + boiled potato",
                "Evening: Buttermilk + 2 plain biscuits",
                "Dinner: Khichdi with ghee OR lauki soup + soft roti",
                "Note: Eat small, frequent meals — every 2-3 hours",
            ]},
        ],
        "routine": [
            {"time": "Early Morning (6:30 - 7:00 AM)", "icon": "sunrise", "activities": [
                "Drink jeera (cumin) water on empty stomach",
                "Gentle walk only — no vigorous activity",
                "DO NOT drink tea/coffee first thing",
            ]},
            {"time": "Morning (7:00 - 9:00 AM)", "icon": "morning", "activities": [
                "Light breakfast within 30 min of waking",
                "Take antacid/medication as prescribed",
                "Sit upright for 30 min after eating",
                "Gentle abdominal breathing exercise",
            ]},
            {"time": "Mid-Day (10:00 AM - 1:00 PM)", "icon": "sun", "activities": [
                "Small snack at 10:30 AM (banana or toast)",
                "Early, mild lunch by 12:30 PM",
                "Sip buttermilk with meals",
                "Avoid lying down immediately after eating",
            ]},
            {"time": "Afternoon (2:00 - 5:00 PM)", "icon": "afternoon", "activities": [
                "Rest — sleep on left side if napping (reduces acid reflux)",
                "Stay hydrated — sip water frequently",
                "Evening snack at 4:30 PM",
                "Avoid stress — practice slow breathing",
            ]},
            {"time": "Evening (5:00 - 8:00 PM)", "icon": "evening", "activities": [
                "Very light dinner by 7:00 PM",
                "Short slow walk after dinner (10 min)",
                "Take evening medication if prescribed",
                "Avoid eating anything after 8 PM",
            ]},
            {"time": "Night (8:00 - 10:00 PM)", "icon": "moon", "activities": [
                "Elevate head of bed slightly (acid reflux prevention)",
                "Do not lie flat for at least 2 hours after dinner",
                "Warm water — no cold drinks before bed",
                "Relaxation — avoid stressful activities before sleep",
            ]},
        ],
    },

    "Type 2 Diabetes": {
        "dietary": [
            {"category": "Low Glycemic Index Foods", "icon": "green", "items": [
                "Whole grains — brown rice, jowar roti, bajra roti, oats",
                "Vegetables — karela (bitter gourd), methi, spinach, broccoli",
                "Proteins — dal, chana, rajma, tofu, chicken breast, fish",
                "Healthy fats — almonds, walnuts, olive oil, flaxseeds",
                "Low-GI fruits — apple, pear, guava, berries, jamun",
                "Cinnamon (dalchini) — add to food/tea for blood sugar control",
            ]},
            {"category": "Foods to Avoid / Limit", "icon": "red", "items": [
                "White rice (switch to brown rice, limit portions)",
                "Maida-based items — naan, bread, biscuits, pasta",
                "Sugar, jaggery, honey in excess",
                "Sweet fruits — mango, banana, grapes, chikoo (limit)",
                "Fruit juices (spike blood sugar — eat whole fruit instead)",
                "Potatoes, white bread, instant noodles (high GI)",
                "Soft drinks, packaged juices, sweetened tea",
            ]},
            {"category": "Portion Control Tips", "icon": "blue", "items": [
                "Use smaller plates — fill half with vegetables",
                "Eat protein and fiber BEFORE carbs at each meal",
                "Limit roti to 2 per meal (use multigrain/jowar/bajra)",
                "Maintain consistent meal timing — never skip meals",
                "Post-meal walk for 10-15 minutes helps control sugar spikes",
            ]},
            {"category": "Diabetic-Friendly Meal Plan", "icon": "meal", "items": [
                "Breakfast (7-8 AM): Moong dal cheela + methi tea OR oats upma",
                "Mid-Morning (10 AM): 1 apple + 5 soaked almonds",
                "Lunch (12:30 PM): 1.5 bajra roti + palak paneer + salad + buttermilk",
                "Evening (4 PM): Roasted chana + green tea",
                "Dinner (7 PM): 1 jowar roti + lauki sabzi + dal + salad",
                "Bedtime: 1 glass warm milk (no sugar) if needed",
            ]},
        ],
        "routine": [
            {"time": "Early Morning (5:30 - 6:30 AM)", "icon": "sunrise", "activities": [
                "Check fasting blood sugar (if monitoring)",
                "Drink warm methi (fenugreek) water (soak seeds overnight)",
                "30-minute brisk walk — critical for sugar control",
                "Light yoga — surya namaskar, pranayama",
            ]},
            {"time": "Morning (7:00 - 9:00 AM)", "icon": "morning", "activities": [
                "Breakfast within 1 hour of waking — never skip",
                "Take diabetes medication as prescribed",
                "Post-breakfast: 10-minute walk",
                "Monitor blood sugar if advised by doctor",
            ]},
            {"time": "Mid-Day (10:00 AM - 1:00 PM)", "icon": "sun", "activities": [
                "Small mid-morning snack (nuts/fruit)",
                "Stay hydrated — water, not juice",
                "Balanced lunch — high fiber, moderate carbs",
                "10-minute walk after lunch",
            ]},
            {"time": "Afternoon (2:00 - 5:00 PM)", "icon": "afternoon", "activities": [
                "Avoid afternoon sugar cravings — eat protein-rich snack",
                "Stay active — avoid prolonged sitting",
                "Check blood sugar if feeling dizzy/lightheaded",
                "Evening snack at 4 PM",
            ]},
            {"time": "Evening (5:00 - 8:00 PM)", "icon": "evening", "activities": [
                "30-minute exercise — walk, cycling, or swimming",
                "Early dinner by 7:30 PM maximum",
                "Take evening medication",
                "Post-dinner walk — 15 minutes mandatory",
            ]},
            {"time": "Night (8:30 - 10:00 PM)", "icon": "moon", "activities": [
                "Check blood sugar before bed (if monitoring)",
                "Foot inspection — check for cuts, sores daily",
                "No eating after 8:30 PM",
                "Sleep by 10 PM — poor sleep worsens insulin resistance",
            ]},
        ],
    },

    "Hypertension": {
        "dietary": [
            {"category": "Heart-Healthy / DASH Diet Foods", "icon": "green", "items": [
                "Potassium-rich foods — bananas, sweet potatoes, spinach, coconut water",
                "Low-sodium vegetables — lauki, tori, carrots, broccoli",
                "Whole grains — oats, brown rice, whole wheat roti",
                "Lean protein — fish (especially omega-3 rich), chicken, dal, sprouts",
                "Low-fat dairy — curd, buttermilk, skimmed milk",
                "Garlic (raw or cooked) — natural BP reducer",
                "Beetroot juice — shown to reduce BP by 4-10 mmHg",
            ]},
            {"category": "Foods to Strictly Limit", "icon": "red", "items": [
                "Salt — limit to under 5g/day (1 teaspoon). Use rock salt.",
                "Pickles, papad, chutneys (very high sodium)",
                "Processed food — chips, instant noodles, canned food",
                "Red meat and saturated fats",
                "Excessive caffeine (max 2 cups/day)",
                "Alcohol — strictly limit or avoid",
                "MSG and soy sauce (hidden sodium)",
            ]},
            {"category": "Hydration for BP Control", "icon": "blue", "items": [
                "2.5-3L water daily — well-hydrated vessels have lower pressure",
                "Hibiscus tea (1-2 cups/day) — clinically proven to lower BP",
                "Coconut water — natural potassium source",
                "Reduce or eliminate sugary drinks",
            ]},
            {"category": "Sample DASH Meal Plan", "icon": "meal", "items": [
                "Breakfast: Oats porridge with banana + flaxseeds + green tea",
                "Mid-Morning: Beetroot juice + 5 walnuts",
                "Lunch: 2 roti (no extra salt) + lauki dal + cucumber raita",
                "Evening: Hibiscus tea + roasted makhana (fox nuts)",
                "Dinner: Grilled fish/paneer + steamed veggies + brown rice",
            ]},
        ],
        "routine": [
            {"time": "Early Morning (6:00 AM)", "icon": "sunrise", "activities": [
                "Check blood pressure (maintain a log)",
                "Drink warm water with lemon",
                "30-40 min brisk walk or light jogging",
                "Deep breathing — 5 min (activates parasympathetic system)",
            ]},
            {"time": "Morning (7:00 - 9:00 AM)", "icon": "morning", "activities": [
                "Low-sodium breakfast as per plan",
                "Take BP medication at same time every day",
                "Morning meditation — 10 minutes",
                "Avoid rushing — stress spikes BP",
            ]},
            {"time": "Mid-Day (10:00 AM - 1:00 PM)", "icon": "sun", "activities": [
                "Mid-morning snack (fruit/nuts)",
                "Stay hydrated — drink water regularly",
                "Low-salt lunch — cook with minimal sodium",
                "Avoid heavy/spicy meals",
            ]},
            {"time": "Afternoon (2:00 - 5:00 PM)", "icon": "afternoon", "activities": [
                "Short relaxation break — avoid chronic stress",
                "No extra salt in snacks (avoid chips, namkeen)",
                "Gentle walk or stretching",
                "Monitor BP if feeling dizzy or headache",
            ]},
            {"time": "Evening (5:00 - 8:00 PM)", "icon": "evening", "activities": [
                "30-minute exercise — swimming, cycling, or brisk walking",
                "Light dinner — low sodium, high potassium",
                "Take evening medication if prescribed",
                "Relaxation — music, reading, family time",
            ]},
            {"time": "Night (9:00 - 10:00 PM)", "icon": "moon", "activities": [
                "Check and log evening BP",
                "Warm milk with a pinch of turmeric (no salt)",
                "Avoid late-night eating",
                "Sleep by 10 PM — sleep deprivation raises BP",
            ]},
        ],
    },

    "Iron Deficiency Anemia": {
        "dietary": [
            {"category": "Iron-Rich Foods", "icon": "green", "items": [
                "Dark leafy greens — spinach (palak), bathua, sarson ka saag",
                "Legumes — chana, rajma, moong, masoor dal, black beans",
                "Jaggery (gur) — natural iron source, use instead of sugar",
                "Dates and raisins (khajur and kishmish) — 4-5 daily",
                "Beetroot — eat raw, cooked, or as juice",
                "Pomegranate — whole fruit and juice",
                "Sesame seeds (til) — add to food or eat til laddoo",
                "Organ meats / liver (if non-vegetarian) — richest iron source",
            ]},
            {"category": "Vitamin C (Iron Absorption Boosters)", "icon": "blue", "items": [
                "Always pair iron-rich food with Vitamin C for absorption",
                "Amla (Indian gooseberry) — richest Vitamin C source",
                "Lemon juice on dal, salads, and iron-rich food",
                "Orange or mosambi after meals",
                "Guava, kiwi, bell peppers",
            ]},
            {"category": "Foods that Block Iron Absorption", "icon": "red", "items": [
                "Tea and coffee with meals (tannins block iron — drink 1 hour after meals)",
                "Excessive calcium with iron-rich meals (separate by 2 hours)",
                "Processed food with phosphates",
                "Excessive whole grains at every meal (phytates reduce absorption)",
            ]},
            {"category": "Iron-Building Meal Plan", "icon": "meal", "items": [
                "Breakfast: Beetroot paratha + amla chutney + jaggery tea",
                "Mid-Morning: Pomegranate juice + 4 dates",
                "Lunch: Palak dal + bajra roti + salad with lemon dressing",
                "Evening: Til (sesame) laddoo + orange",
                "Dinner: Rajma curry + rice + beetroot raita",
                "Bedtime: Warm milk with jaggery (2 hours after dinner)",
            ]},
        ],
        "routine": _default_routine_plan(),
    },

    "Anxiety Disorder": {
        "dietary": [
            {"category": "Anxiety-Reducing Foods", "icon": "green", "items": [
                "Magnesium-rich — dark chocolate (70%+), almonds, spinach, pumpkin seeds",
                "Omega-3 fatty acids — walnuts, flaxseeds, chia seeds, fatty fish",
                "Complex carbs for serotonin — oats, whole wheat, sweet potato",
                "Probiotic-rich food — curd, kefir, fermented vegetables (gut-brain axis)",
                "Chamomile and ashwagandha tea — natural anxiolytics",
                "Bananas — contain tryptophan (serotonin precursor)",
                "Turmeric — curcumin has anti-anxiety properties",
            ]},
            {"category": "Anxiety Trigger Foods to Avoid", "icon": "red", "items": [
                "Caffeine — strictly limit to 1 cup/day or eliminate",
                "Alcohol — worsens anxiety despite initial calming effect",
                "Sugar and refined carbs — cause blood sugar crashes that mimic anxiety",
                "Processed food with artificial additives",
                "Energy drinks and sodas",
            ]},
            {"category": "Calming Drinks", "icon": "blue", "items": [
                "Chamomile tea (2-3 cups daily — clinically proven for anxiety)",
                "Ashwagandha milk — 1 cup before bed",
                "Warm milk with nutmeg (jaiphal) before sleep",
                "Lavender or peppermint herbal tea",
                "Reduce caffeine intake gradually to avoid withdrawal",
            ]},
            {"category": "Sample Calming Meal Plan", "icon": "meal", "items": [
                "Breakfast: Oats with banana, walnuts + chamomile tea",
                "Mid-Morning: Dark chocolate (2 squares) + pumpkin seeds",
                "Lunch: Brown rice + dal + palak sabzi + curd",
                "Evening: Ashwagandha tea + trail mix (almonds, flaxseeds)",
                "Dinner: Light khichdi + warm soup (early, by 7:30 PM)",
                "Bedtime: Warm milk with a pinch of nutmeg",
            ]},
        ],
        "routine": [
            {"time": "Early Morning (6:00 - 7:00 AM)", "icon": "sunrise", "activities": [
                "Wake at consistent time — irregular sleep worsens anxiety",
                "NO checking phone/news for first 30 minutes",
                "10-minute guided meditation (use Headspace, Calm, or YouTube)",
                "Gentle yoga — child's pose, legs up the wall, savasana",
            ]},
            {"time": "Morning (7:00 - 9:00 AM)", "icon": "morning", "activities": [
                "Grounding exercise — 5-4-3-2-1 senses technique",
                "Nourishing breakfast — don't skip (low blood sugar = anxiety)",
                "Take medication if prescribed",
                "Write in a journal — 3 things you're grateful for",
            ]},
            {"time": "Mid-Day (10:00 AM - 1:00 PM)", "icon": "sun", "activities": [
                "Break work into 25-min focused blocks (Pomodoro technique)",
                "Step outside for 10 minutes — sunlight boosts serotonin",
                "Practice box breathing if anxious (4-4-4-4 counts)",
                "Mindful lunch — eat slowly, no screen while eating",
            ]},
            {"time": "Afternoon (2:00 - 5:00 PM)", "icon": "afternoon", "activities": [
                "Limit caffeine after noon",
                "Short walk in nature or park if possible",
                "Progressive muscle relaxation if tension builds",
                "Call a friend or family member — social connection reduces anxiety",
            ]},
            {"time": "Evening (5:00 - 8:00 PM)", "icon": "evening", "activities": [
                "30-minute exercise — proven equal to anti-anxiety medication",
                "Light, early dinner",
                "Limit news and social media consumption",
                "Creative hobby — painting, music, gardening, cooking",
            ]},
            {"time": "Night (8:00 - 10:00 PM)", "icon": "moon", "activities": [
                "Digital sunset — screens off by 9 PM",
                "Calming routine — warm bath, herbal tea, light reading",
                "Body scan meditation (10 min — lie down, relax each body part)",
                "Write any worries in a journal and close it — symbolic release",
                "Sleep by 10 PM — consistent bedtime is critical",
            ]},
        ],
    },

    "Vitamin D Deficiency": {
        "dietary": [
            {"category": "Vitamin D Rich Foods", "icon": "green", "items": [
                "Fatty fish — salmon, mackerel, sardines (best food source)",
                "Egg yolks — include 1-2 whole eggs daily",
                "Fortified milk and cereals",
                "Mushrooms (sun-exposed varieties)",
                "Cod liver oil supplement (if recommended by doctor)",
                "Paneer and cheese (contain some Vitamin D)",
            ]},
            {"category": "Calcium-Rich Foods (Vitamin D needs calcium)", "icon": "blue", "items": [
                "Ragi (finger millet) — highest calcium grain in India",
                "Sesame seeds (til) — sprinkle on food",
                "Curd and buttermilk daily",
                "Dark leafy greens — broccoli, kale",
                "Almonds and dried figs",
            ]},
            {"category": "Foods to Moderate", "icon": "red", "items": [
                "Excessive caffeine (reduces calcium absorption)",
                "Very high-fiber meals with calcium (separate by 1-2 hours)",
                "Excess sodium (causes calcium excretion)",
                "Soft drinks (phosphoric acid leaches calcium)",
            ]},
            {"category": "Sample Bone-Health Meal Plan", "icon": "meal", "items": [
                "Breakfast: 2 egg omelette + ragi dosa + glass of fortified milk",
                "Mid-Morning: 15-20 minutes of direct sunlight + almonds",
                "Lunch: Fish curry / paneer + roti + til chutney + curd",
                "Evening: Sesame laddoo + warm milk",
                "Dinner: Mushroom sabzi + dal + rice + salad",
            ]},
        ],
        "routine": [
            {"time": "Early Morning (6:00 - 7:00 AM)", "icon": "sunrise", "activities": [
                "Wake up and prepare for sun exposure",
                "Light warm-up stretches",
                "Drink warm water with lemon (Vitamin C aids absorption)",
            ]},
            {"time": "Morning (7:00 - 10:00 AM)", "icon": "morning", "activities": [
                "CRITICAL: 15-20 minutes direct sunlight (arms and face exposed)",
                "Best sun exposure time: 7-10 AM (UVB rays active)",
                "Breakfast with Vitamin D foods",
                "Take Vitamin D supplement if prescribed (with fatty food for absorption)",
            ]},
            {"time": "Mid-Day (10:00 AM - 2:00 PM)", "icon": "sun", "activities": [
                "Sit near a window for natural light while working",
                "Calcium-rich snack mid-morning",
                "Balanced lunch with protein and calcium",
                "Weight-bearing exercise if able (strengthens bones)",
            ]},
            {"time": "Afternoon (2:00 - 5:00 PM)", "icon": "afternoon", "activities": [
                "Brief outdoor walk (even 10 min helps)",
                "Stay active — bone density improves with movement",
                "Calcium-rich evening snack",
            ]},
            {"time": "Evening (5:00 - 8:00 PM)", "icon": "evening", "activities": [
                "30-minute exercise — walking, light weights, or yoga",
                "Dinner with Vitamin D and calcium foods",
                "Avoid excessive indoor-only lifestyle",
            ]},
            {"time": "Night (8:00 - 10:00 PM)", "icon": "moon", "activities": [
                "Warm milk (calcium + helps sleep)",
                "Gentle stretching — especially for bone/joint stiffness",
                "Adequate sleep — bone repair happens during deep sleep",
            ]},
        ],
    },
}


def get_dietary_plan(diagnosis_name: str) -> list[dict]:
    """Return a condition-specific dietary plan, or a healthy default."""
    for key, plans in DISEASE_PLANS.items():
        if key.lower() in diagnosis_name.lower():
            return plans.get("dietary", _default_dietary_plan())
    return _default_dietary_plan()


def get_routine_plan(diagnosis_name: str) -> list[dict]:
    """Return a condition-specific daily routine plan, or a healthy default."""
    for key, plans in DISEASE_PLANS.items():
        if key.lower() in diagnosis_name.lower():
            return plans.get("routine", _default_routine_plan())
    return _default_routine_plan()

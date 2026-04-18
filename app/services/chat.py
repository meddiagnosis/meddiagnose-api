"""
Medical AI chatbot service with keyword-based FAQ matching.

In production, replace respond() with a call to MedGemma/GPT with medical context.
"""

FAQ_RULES: list[tuple[list[str], str]] = [
    (["milk", "dairy", "food", "take with"],
     "Most antibiotics like Amoxicillin can be taken with or without food. However, some medications like Levothyroxine should be taken on an empty stomach, 30-60 minutes before breakfast. Calcium-rich foods (milk, yogurt) can reduce absorption of certain antibiotics and thyroid medications. Check each medication's specific notes for guidance."),

    (["alcohol", "drink", "beer", "wine"],
     "Avoid alcohol while taking most medications, especially: antibiotics (can reduce effectiveness), paracetamol (liver damage risk), NSAIDs like ibuprofen (increases stomach bleeding risk), antidepressants (amplifies sedation), and metformin (lactic acidosis risk). Wait at least 48 hours after finishing antibiotics before drinking."),

    (["side effect", "side effects", "adverse", "reaction"],
     "Common side effects vary by medication. Antibiotics may cause diarrhea and stomach upset. NSAIDs can cause stomach irritation. Antihistamines may cause drowsiness. If you experience severe side effects like difficulty breathing, swelling, rash, or severe stomach pain, stop the medication and seek emergency care immediately."),

    (["how long", "duration", "when will", "better", "improve"],
     "Recovery time varies by condition. Common cold/flu: 5-7 days. Bacterial infections with antibiotics: improvement in 48-72 hours. Chronic conditions (hypertension, diabetes, thyroid): these require ongoing management. If symptoms don't improve within the expected timeframe or worsen, consult your doctor."),

    (["pregnant", "pregnancy", "breastfeed", "nursing", "lactation"],
     "Many medications are unsafe during pregnancy and breastfeeding. NEVER take any medication during pregnancy without consulting your OB-GYN. Common medications to AVOID: NSAIDs (especially in third trimester), ACE inhibitors, certain antibiotics, and most psychiatric medications. Paracetamol is generally considered safe for pain relief during pregnancy."),

    (["miss", "missed", "forgot", "skip"],
     "If you miss a dose: take it as soon as you remember, unless it's almost time for the next dose. Never take a double dose to make up for a missed one. For antibiotics, try to complete the full course even if you feel better. For blood pressure or thyroid medication, consistency is especially important."),

    (["stop", "discontinue", "quit taking"],
     "Do NOT stop medications abruptly without consulting your doctor, especially: antidepressants (withdrawal symptoms), beta-blockers (rebound hypertension), corticosteroids (adrenal crisis), and anticonvulsants. Antibiotics should always be completed fully even if symptoms improve, to prevent resistance."),

    (["exercise", "gym", "workout", "physical activity"],
     "Light to moderate exercise is beneficial for most conditions. However, avoid strenuous exercise if you have: acute fever, severe respiratory infection, or recent injury. For heart conditions and hypertension, start slowly and monitor heart rate. Walking 20-30 minutes daily is a good baseline for most patients."),

    (["sleep", "insomnia", "can't sleep", "tired"],
     "Good sleep hygiene helps recovery: maintain a fixed sleep schedule, avoid screens 1 hour before bed, keep the room cool and dark, avoid caffeine after 2 PM. Some medications (corticosteroids, certain antibiotics) can affect sleep. If a medication is causing insomnia, ask your doctor about adjusting the timing."),

    (["diet", "eat", "food to avoid", "nutrition"],
     "General dietary advice during illness: stay hydrated (2-3L water daily), eat light and easily digestible foods, avoid spicy and oily food if you have stomach issues. For specific conditions: diabetics should monitor carb intake, hypertension patients should limit salt to <5g/day, kidney stone patients should increase fluid intake significantly."),

    (["fever", "temperature", "when to worry"],
     "A fever above 103°F (39.4°C) in adults or 100.4°F (38°C) in infants under 3 months needs immediate medical attention. For moderate fever (100-102°F), paracetamol can help. Stay hydrated, rest, and monitor temperature every 4 hours. Seek care if fever persists beyond 3 days or is accompanied by stiff neck, confusion, or difficulty breathing."),

    (["contagious", "spread", "infect", "isolation"],
     "Contagious conditions require isolation: chickenpox (until all blisters crust, ~5-7 days), flu (stay home for at least 24 hours after fever resolves), conjunctivitis (while discharge is present), and strep throat (24 hours after starting antibiotics). Wash hands frequently and avoid sharing personal items."),

    (["cost", "price", "expensive", "generic", "alternative"],
     "Ask your pharmacist about generic alternatives — they contain the same active ingredient at lower cost. Many medications have affordable generic versions. Some pharmaceutical companies offer patient assistance programs. Discuss cost concerns with your doctor; they can often suggest equally effective but more affordable alternatives."),

    (["emergency", "hospital", "ambulance", "911"],
     "Call emergency services (911/112/108) immediately if you experience: chest pain or pressure, difficulty breathing, sudden severe headache, signs of stroke (FAST: Face drooping, Arm weakness, Speech difficulty, Time to call), severe allergic reaction (anaphylaxis), uncontrolled bleeding, or loss of consciousness."),

    (["vitamin", "supplement", "zinc", "immunity"],
     "Common helpful supplements: Vitamin D (if deficient), Vitamin C (supports immunity), Zinc (may shorten cold duration), Iron (for anemia). However, avoid mega-doses without medical advice. Some supplements interact with medications (e.g., calcium reduces thyroid med absorption, vitamin K affects blood thinners). Always inform your doctor about supplements you take."),
]

GREETING_KEYWORDS = ["hi", "hello", "hey", "help", "what can you"]
THANKS_KEYWORDS = ["thank", "thanks", "thx", "appreciate"]


def respond(message: str, diagnosis_context: dict | None = None) -> str:
    """Generate a response to a patient's medical question."""
    msg_lower = message.lower().strip()

    if any(kw in msg_lower for kw in GREETING_KEYWORDS):
        return ("Hello! I'm MedDiagnose AI Assistant. I can help answer questions about your medications, "
                "symptoms, diet, side effects, and general health advice. What would you like to know?")

    if any(kw in msg_lower for kw in THANKS_KEYWORDS):
        return ("You're welcome! Remember, I provide general health information only. "
                "For personalized medical advice, always consult your healthcare provider. "
                "Is there anything else you'd like to know?")

    best_match = None
    best_score = 0
    for keywords, answer in FAQ_RULES:
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score > best_score:
            best_score = score
            best_match = answer

    if best_match and best_score >= 1:
        context_note = ""
        if diagnosis_context and diagnosis_context.get("ai_diagnosis"):
            context_note = f"\n\nNote: This advice is general. Based on your recent diagnosis of '{diagnosis_context['ai_diagnosis']}', some specifics may vary. Consult your doctor for personalized guidance."
        return best_match + context_note

    if diagnosis_context and diagnosis_context.get("ai_diagnosis"):
        return (
            f"I don't have a specific answer for that question, but based on your diagnosis of "
            f"'{diagnosis_context['ai_diagnosis']}', I recommend discussing this with your healthcare provider "
            f"who can give you personalized advice. In the meantime, follow the medication and lifestyle "
            f"recommendations provided in your diagnosis report.\n\n"
            f"You can ask me about: medication timing, side effects, diet, exercise, "
            f"when to see a doctor, pregnancy safety, or general health tips."
        )

    return (
        "I'm not sure about that specific question. I can help with topics like:\n\n"
        "- Taking medications with food or milk\n"
        "- Alcohol interactions\n"
        "- Side effects\n"
        "- Recovery timeline\n"
        "- Pregnancy/breastfeeding safety\n"
        "- Missed doses\n"
        "- Diet and nutrition\n"
        "- Exercise advice\n"
        "- Emergency signs\n\n"
        "Try rephrasing your question, or consult your healthcare provider for specific medical advice."
    )

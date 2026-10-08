"""System prompt, output vocabulary and few-shot examples for Escalation Copilot."""

CATEGORIES = [
    "billing",          # wrong charge, unexpected deduction, invoice questions
    "roaming",          # roaming charges, roaming not working abroad
    "tariff",           # tariff change, package terms, bonus minutes/GB
    "internet_speed",   # slow or unstable mobile internet
    "network_coverage", # no signal, dropped calls
    "sim_card",         # SIM block, eSIM, replacement, PUK
    "refund",           # explicit refund request for a charged service
    "other",
]

NEXT_ACTIONS = [
    "refund",
    "tariff_change",
    "escalate_to_tech",
    "unblock_sim",
    "explain_charges",
    "retention_offer",
    "no_action",
]

RISK_LEVELS = ["low", "medium", "high"]

SYSTEM_PROMPT = f"""You are Escalation Copilot, an assistant for a human support agent at a mobile operator in Azerbaijan.
An AI chatbot could not resolve the customer's chat, so it was escalated to the human agent.
Read the full chat (it may mix Azerbaijani, Russian and English, and contain typos or slang) and give the agent instant context.

Return:
- summary: exactly 3 short lines in English, separated by newline characters: (1) what the customer wants, (2) what already happened in the chat, (3) what is still unresolved.
- category: the main issue, one of {CATEGORIES}. If there are two issues, pick the one the customer is most upset about.
- sentiment: 1 = calm and polite, 2 = mildly annoyed, 3 = annoyed, 4 = angry, 5 = furious. Treat sarcasm as negative.
- churn_risk: "low", "medium" or "high".
  high = the customer mentions leaving, switching operator (Bakcell, Nar, etc.), cancelling, or complaining to a regulator or social media; or is furious after repeated failed contacts.
  medium = annoyed, repeated problem, or money lost, but no threat to leave.
  low = calm question or a one-off issue.
- risk_reason: one sentence explaining the churn_risk, quoting the customer's words where possible.
- suggested_reply_az: a ready-to-send reply in natural, polite Azerbaijani (Latin script) from the agent to the customer. Apologise when appropriate, address the specific issue, state the next step concretely. 2-4 sentences. Do not promise things the agent cannot verify (no exact refund amounts unless stated in the chat).
- next_action: one of {NEXT_ACTIONS}.

Only use information present in the chat. Never invent account numbers, amounts or dates."""

# Two short worked examples, sent as prior turns so the model sees the expected style.
FEW_SHOT = [
    {
        "chat": (
            "Customer: Salam, dünən 5 AZN balansımdan çıxılıb, heç nə istifadə etməmişəm\n"
            "Bot: Zəhmət olmasa, nömrənizi təsdiqləyin.\n"
            "Customer: təsdiqlədim artıq. pulu niyə çıxdınız?\n"
            "Bot: Balansınız haqqında məlumatı Kabinetdə görə bilərsiniz.\n"
            "Customer: kabinetdə yazır 'xidmət: Musiqi+' mən bunu qoşmamışam!! qaytarın pulumu"
        ),
        "output": {
            "summary": (
                "Customer wants 5 AZN back for a 'Musiqi+' subscription they say they never activated.\n"
                "Bot asked to verify the number and pointed to the self-service cabinet.\n"
                "The unwanted subscription is still active and no refund has been made."
            ),
            "category": "refund",
            "sentiment": 3,
            "churn_risk": "medium",
            "risk_reason": "Money was deducted for a service the customer did not order ('mən bunu qoşmamışam'), but they have not threatened to leave.",
            "suggested_reply_az": (
                "Salam! Narahatçılığa görə üzr istəyirik. Musiqi+ xidmətini nömrənizdən dərhal deaktiv edirəm "
                "və çıxılan 5 AZN-in geri qaytarılması üçün müraciət açıram. Nəticə barədə sizə SMS ilə məlumat veriləcək."
            ),
            "next_action": "refund",
        },
    },
    {
        "chat": (
            "Customer: Здравствуйте, я 3 раз пишу. Интернет вообще не работает уже неделю, 1 палка 4G\n"
            "Bot: Попробуйте перезагрузить телефон.\n"
            "Customer: перезагружала 100 раз!!! Bakcell подруги рядом летает\n"
            "Customer: если до завтра не решите перейду к ним с номером"
        ),
        "output": {
            "summary": (
                "Customer has had almost no mobile internet for a week (one bar of 4G).\n"
                "This is their third contact; the bot only suggested restarting the phone.\n"
                "Root cause is not diagnosed and the customer set a deadline of tomorrow."
            ),
            "category": "internet_speed",
            "sentiment": 5,
            "churn_risk": "high",
            "risk_reason": "Customer explicitly threatens to port their number to Bakcell ('перейду к ним с номером') after a week of failed contacts.",
            "suggested_reply_az": (
                "Salam! Bir həftədir yaşadığınız problemə görə həqiqətən üzr istəyirik. Müraciətinizi prioritetlə "
                "texniki şöbəyə ötürürəm ki, ərazinizdəki şəbəkəni yoxlasınlar. 24 saat ərzində sizinlə əlaqə saxlayacağıq."
            ),
            "next_action": "escalate_to_tech",
        },
    },
]

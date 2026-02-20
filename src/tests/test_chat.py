import requests
import uuid
import time
from datetime import datetime

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

ENDPOINT_URL = "http://127.0.0.1:8000/api/detect"
API_KEY = "PUT_YOUR_KEY_HERE"  # Replace with your actual API key
CODE_QUALITY_SCORE = 8  # Adjust manually (0–10)

# -------------------------------------------------
# 5 SCENARIOS (Weights sum to 100)
# -------------------------------------------------

SCENARIOS = [
    {
        "name": "Bank Fraud",
        "weight": 25,
        "messages": [
            "URGENT: Your SBI account blocked.",
            "Share OTP immediately.",
            "Call +919876543210.",
            "Transfer to 1234567890123456.",
            "Use UPI scammer@fakeupi.",
            "Account will be closed soon.",
            "Confirm once done.",
            "Time limited offer.",
            "Failure leads to suspension.",
            "Reply now."
        ],
        "fakeData": {
            "phoneNumbers": ["+919876543210"],
            "bankAccounts": ["1234567890123456"],
            "upiIds": ["scammer@fakeupi"]
        }
    },
    {
        "name": "Phishing Link",
        "weight": 20,
        "messages": [
            "Complete KYC immediately.",
            "Visit http://fake-kyc.com",
            "Email support@fakebank.com",
            "Account suspended.",
            "Respond within 10 minutes.",
            "Click the link now.",
            "Verification mandatory.",
            "Do not delay.",
            "Final warning issued.",
            "Immediate action required."
        ],
        "fakeData": {
            "phishingLinks": ["http://fake-kyc.com"],
            "emailAddresses": ["support@fakebank.com"]
        }
    },
    {
        "name": "Job Scam",
        "weight": 20,
        "messages": [
            "Overseas job offer available.",
            "Salary 2 lakh monthly.",
            "Pay visa processing fee.",
            "Transfer to 555566667777.",
            "Mail hr@fakecompany.com",
            "Limited openings.",
            "Respond quickly.",
            "Confirm interest.",
            "Immediate joining.",
            "Offer expires today."
        ],
        "fakeData": {
            "bankAccounts": ["555566667777"],
            "emailAddresses": ["hr@fakecompany.com"]
        }
    },
    {
        "name": "Electricity Bill Scam",
        "weight": 20,
        "messages": [
            "Electricity bill unpaid.",
            "Service disconnect tonight.",
            "Pay to 987654321012.",
            "Avoid penalty charges.",
            "Immediate payment required.",
            "Respond ASAP.",
            "Late fee applicable.",
            "Account suspension warning.",
            "Final reminder.",
            "Confirm after payment."
        ],
        "fakeData": {
            "bankAccounts": ["987654321012"]
        }
    },
    {
        "name": "Investment Scam",
        "weight": 15,
        "messages": [
            "Guaranteed crypto returns.",
            "Double money in 7 days.",
            "Invest via UPI invest@fakefund.",
            "Call +918765432109 for guidance.",
            "Transfer to 888899991111.",
            "Limited time opportunity.",
            "Register on http://fake-invest.com",
            "Send confirmation after transfer.",
            "High profit assured.",
            "Act fast before slots fill."
        ],
        "fakeData": {
            "upiIds": ["invest@fakefund"],
            "phoneNumbers": ["+918765432109"],
            "bankAccounts": ["888899991111"],
            "phishingLinks": ["http://fake-invest.com"]
        }
    }
]

# -------------------------------------------------
# SCORING FUNCTIONS
# -------------------------------------------------

def score_scam_detection(final_output):
    return 20 if final_output.get("scamDetected") else 0


def score_extraction(final_output, fake_data):
    extracted = final_output.get("extractedIntelligence", {})
    total_fields = sum(len(v) for v in fake_data.values())
    if total_fields == 0:
        return 0
    points_per_item = 30 / total_fields
    score = 0
    for key, values in fake_data.items():
        for val in values:
            if any(val in str(v) for v in extracted.get(key, [])):
                score += points_per_item
    return min(round(score, 2), 30)


def score_conversation_quality(history):
    assistant_msgs = [m["text"] for m in history if m["sender"] == "assistant"]
    total_turns = len(history) // 2
    score = 0

    # Turn count
    if total_turns >= 8:
        score += 8
    elif total_turns >= 6:
        score += 6
    elif total_turns >= 4:
        score += 3

    # Questions
    q_count = sum(msg.count("?") for msg in assistant_msgs)
    if q_count >= 5:
        score += 4
    elif q_count >= 3:
        score += 2
    elif q_count >= 1:
        score += 1

    # Investigative
    investigative = sum(
        any(k in msg.lower() for k in ["verify", "who", "where", "confirm", "official"])
        for msg in assistant_msgs
    )
    if investigative >= 3:
        score += 3
    elif investigative >= 2:
        score += 2
    elif investigative >= 1:
        score += 1

    # Red Flags
    red_flags = sum(
        any(k in msg.lower() for k in ["urgent", "otp", "fee", "link", "transfer", "blocked"])
        for msg in assistant_msgs
    )
    if red_flags >= 5:
        score += 8
    elif red_flags >= 3:
        score += 5
    elif red_flags >= 1:
        score += 2

    # Elicitation
    elicitation = sum(
        any(k in msg.lower() for k in ["account", "number", "email", "id", "send", "share"])
        for msg in assistant_msgs
    )
    score += min(elicitation * 1.5, 7)

    return min(round(score, 2), 30)


def score_engagement(final_output):
    duration = final_output.get("engagementDurationSeconds", 0)
    messages = final_output.get("totalMessagesExchanged", 0)
    score = 0
    if duration > 0:
        score += 1
    if duration > 60:
        score += 2
    if duration > 180:
        score += 1
    if messages > 0:
        score += 2
    if messages >= 5:
        score += 3
    if messages >= 10:
        score += 1
    return score


def score_structure(final_output):
    score = 0
    required = ["sessionId", "scamDetected", "extractedIntelligence"]
    optional = ["agentNotes", "scamType", "confidenceLevel"]

    for f in required:
        if f in final_output:
            score += 2

    if "totalMessagesExchanged" in final_output and "engagementDurationSeconds" in final_output:
        score += 1

    for f in optional:
        if f in final_output and final_output[f]:
            score += 1

    return score


# -------------------------------------------------
# RUN EVALUATION
# -------------------------------------------------

def run_all():
    total_weighted_score = 0
    print("\n🔥 5-SCENARIO FINAL EVALUATION")
    print("=" * 70)

    for scenario in SCENARIOS:
        session_id = str(uuid.uuid4())
        history = []
        final_output = None

        print(f"\n🧪 Scenario: {scenario['name']} (Weight {scenario['weight']}%)")

        for turn, msg in enumerate(scenario["messages"]):
            payload = {
                "sessionId": session_id,
                "message": {
                    "sender": "scammer",
                    "text": msg,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                },
                "conversationHistory": history
            }

            response = requests.post(
                ENDPOINT_URL,
                headers={"x-api-key": API_KEY},
                json=payload,
                timeout=30
            )

            data = response.json()
            reply = data.get("reply")

            history.append(payload["message"])
            history.append({
                "sender": "assistant",
                "text": reply,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })

            if data.get("finalCallback") and turn >= 7:
                final_output = data["finalCallback"]
                break

            time.sleep(1)

        if not final_output:
            print("❌ No final output after required turns.")
            continue

        sd = score_scam_detection(final_output)
        ei = score_extraction(final_output, scenario["fakeData"])
        cq = score_conversation_quality(history)
        eq = score_engagement(final_output)
        rs = score_structure(final_output)

        scenario_score = sd + ei + cq + eq + rs
        weighted = scenario_score * scenario["weight"] / 100
        total_weighted_score += weighted

        print(f"Scam Detection: {sd}/20")
        print(f"Extraction: {ei}/30")
        print(f"Conversation Quality: {cq}/30")
        print(f"Engagement: {eq}/10")
        print(f"Structure: {rs}/10")
        print(f"Scenario Total: {scenario_score}/100")
        print(f"Weighted Contribution: {weighted:.2f}")

    print("\n" + "=" * 70)
    print(f"Scenario Aggregate Score: {total_weighted_score:.2f}")

    final_score = (total_weighted_score * 0.9) + CODE_QUALITY_SCORE
    print(f"Final Score = ({total_weighted_score:.2f} × 0.9) + {CODE_QUALITY_SCORE}")
    print(f"🔥 FINAL SCORE: {final_score:.2f}")
    print("=" * 70)


if __name__ == "__main__":
    run_all()
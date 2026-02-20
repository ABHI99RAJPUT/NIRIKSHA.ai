````md
<p align="center">
  <img src="https://img.shields.io/badge/Project-NIRIKSHA.ai-blueviolet?style=for-the-badge&logo=shield" alt="NIRIKSHA.ai"/>
  <img src="https://img.shields.io/badge/India%20AI%20Impact-Buildathon%202026-orange?style=for-the-badge" alt="Buildathon"/>
</p>

<h1 align="center">🛡️ NIRIKSHA.ai | Agentic Honeypot for Scam Detection and Intelligence Extraction</h1>

<p align="center">
  <b>An autonomous, multi-turn AI honeypot that chats like a real person, keeps scammers busy, and quietly collects useful scam intelligence.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Groq-Llama%203.3%2070B-FF6F00?style=flat-square&logo=meta&logoColor=white" />
  <img src="https://img.shields.io/badge/Deployed-Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white" />
</p>

---

## Quickstart for the evaluator

- **Endpoint:** `POST /api/detect`
- **Success response must be HTTP 200** and JSON like this:
  ```json
  { "status": "success", "reply": "..." }
````

* The evaluator looks for the reply field in this order: `reply`, then `message`, then `text`.
* Keep the total response time under **30 seconds**.

**Live endpoint (Railway):**
`https://agentichoneypot-production-12fb.up.railway.app/api/detect`

---

## Table of contents

* [What is NIRIKSHA.ai?](#what-is-nirikshaai)
* [What it does](#what-it-does)
* [How it works](#how-it-works)
* [API reference](#api-reference)
* [Final output report](#final-output-report)
* [Repo structure](#repo-structure)
* [Setup and run locally](#setup-and-run-locally)
* [Testing](#testing)
* [Deployment notes](#deployment-notes)
* [Example scam types](#example-scam-types)
* [Team](#team)
* [License](#license)

---

## What is NIRIKSHA.ai?

NIRIKSHA.ai is an agentic honeypot that pretends to be a normal person when a scammer sends a message.

Most systems block scammers quickly. That can stop one attempt, but it usually does not help you learn anything about who is behind it. NIRIKSHA.ai takes a different approach:

* It keeps the scammer talking using believable replies.
* It quietly extracts the details scammers tend to reveal when they think a victim is cooperating.
* It produces a clean, structured report at the end of a session so that the data can be used later.

The scammer should never feel like they are talking to a bot, and the system never reveals that it is analyzing them.

---

## What it does

### 1) It engages scammers across multiple turns

NIRIKSHA.ai responds like a cautious, slightly confused person. That simple persona works well because scammers stay invested when they believe a victim is willing to follow instructions.

Replies are generated using:

* **Groq**
* **Meta Llama 3.3 70B** (`llama-3.3-70b-versatile` by default)

### 2) It detects scam intent using generic signals

This is not based on one fixed script. It looks for common scam behaviors and patterns such as:

* urgency and threats (blocked, suspended, final warning, immediately)
* credential theft attempts (share OTP, PIN, CVV, password)
* payment pressure (pay, transfer, send)
* suspicious artifacts (UPI IDs, phone numbers, URLs, bank account numbers)

### 3) It extracts intelligence silently and cleans it up

The extraction runs on the full conversation (history + latest message). It deduplicates and normalizes results.

It extracts:

* `phoneNumbers`
* `bankAccounts`
* `upiIds`
* `phishingLinks`
* `emailAddresses`
* `caseIds`
* `policyNumbers`
* `orderNumbers`
* `referenceIds`

### 4) It stays safe and believable

* It never shares OTP/PIN/CVV/password.
* It avoids words that break the illusion (scam, fraud, AI, bot, honeypot).
* It keeps replies short, usually 1 to 2 sentences.
* It asks at most one question in a reply.

### 5) It generates a structured final report

On later turns (turn 10, or sometimes earlier if enough intelligence is collected), the API returns a final report object in:

* `finalCallback`
* `finalOutput` (same object, kept for compatibility)

The normal evaluator requirement is still satisfied because every call returns `status` and `reply`.

---

## How it works

A simple walkthrough of one request:

1. The API receives `sessionId`, `message`, and `conversationHistory`.
2. It initializes or updates in-memory session state for that `sessionId`.
3. It computes scam signals (scam score is used for confidence and fallback decisions).
4. It extracts intelligence from the full conversation text.
5. It chooses a natural "next hint" topic (reference number, link, email, phone, UPI, account) so the LLM asks for missing details in a normal way.
6. It generates a reply via Groq and sanitizes it.
7. If the session hits the finalization condition, it builds the final report and returns it.

---

## API reference

### Endpoint

`POST /api/detect`

### Headers

| Header         | Value                            | Required              |
| -------------- | -------------------------------- | --------------------- |
| `Content-Type` | `application/json`               | Yes                   |
| `x-api-key`    | must match your `API_SECRET_KEY` | Yes (in current code) |

### Request body (evaluator-compatible)

```json
{
  "sessionId": "uuid-v4-string",
  "message": {
    "sender": "scammer",
    "text": "URGENT: Your account has been compromised...",
    "timestamp": "2025-02-11T10:30:00Z"
  },
  "conversationHistory": [
    { "sender": "scammer", "text": "Previous message...", "timestamp": 1739269800000 },
    { "sender": "user", "text": "Previous reply...", "timestamp": 1739269860000 }
  ],
  "metadata": { "channel": "SMS", "language": "English", "locale": "IN" }
}
```

Notes:

* `sessionId` is accepted as `sessionId`, `sessionld`, or `session_id`.
* `conversationHistory` is accepted as `conversationHistory` or `conversation_history`.
* `metadata` is optional.

### Success response (required)

```json
{
  "status": "success",
  "reply": "Oh no, that sounds serious. What is the reference number for this?"
}
```

### Optional fields returned during finalization

When the final report is generated, the API may include:

* `finalCallback`: final report object
* `finalOutput`: same object (compatibility)

If not finalized yet, both fields will be null.

### Error responses

| Status | When it happens              | Example                                |
| ------ | ---------------------------- | -------------------------------------- |
| 403    | missing or incorrect API key | `{"detail":"Invalid API Key"}`         |
| 422    | invalid request shape        | `{"detail":[...validation errors...]}` |

### cURL example

```bash
curl -X POST "https://agentichoneypot-production-12fb.up.railway.app/api/detect" \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_SECRET_KEY" \
  -d '{
    "sessionId": "test-001",
    "message": {
      "sender": "scammer",
      "text": "Your account is blocked. Send OTP now.",
      "timestamp": "2025-02-11T10:30:00Z"
    },
    "conversationHistory": []
  }'
```

---

## Final output report

When the session is finalized, the API returns a structured report like this:

```json
{
  "sessionId": "abc123-session-id",
  "status": "completed",
  "scamDetected": true,
  "totalMessagesExchanged": 18,
  "engagementDurationSeconds": 240,
  "scamType": "bank_fraud",
  "confidenceLevel": 0.92,
  "extractedIntelligence": {
    "phoneNumbers": ["+91-9876543210"],
    "bankAccounts": ["1234567890123456"],
    "upiIds": ["scammer@fakeupi"],
    "phishingLinks": ["http://fake-site.com"],
    "emailAddresses": ["support@fakebank.com"],
    "caseIds": ["CASE-12345"],
    "policyNumbers": [],
    "orderNumbers": [],
    "referenceIds": ["CASE-12345"]
  },
  "engagementMetrics": {
    "totalMessagesExchanged": 18,
    "engagementDurationSeconds": 240
  },
  "agentNotes": "Session completed. scamType=bank_fraud."
}
```

A couple of important notes:

* `scamType` and `confidenceLevel` are produced by an LLM classification call and may fall back to safe defaults if parsing fails.
* The evaluator-critical part is still the normal API response: `status` and `reply`.

---

## Repo structure

This README matches your GitHub structure:

```text
NIRIKSHA.ai/
└── src/
    ├── main.py
    ├── requirements.txt
    ├── .env.example
    ├── .gitignore
    └── tests/
        └── test_chat.py
```

---

## Setup and run locally

### Requirements

* Python 3.10+
* Groq API key

### Install

```bash
git clone https://github.com/ABHI99RAJPUT/NIRIKSHA.ai.git
cd NIRIKSHA.ai

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r src/requirements.txt
```

### Configure environment variables

Create `src/.env` (you can copy `src/.env.example`).

```env
GROQ_API_KEY=your_groq_key_here
API_SECRET_KEY=your_api_key_here

# Optional
GROQ_MODEL=llama-3.3-70b-versatile
MIN_HUMAN_DELAY_S=0.10
MAX_HUMAN_DELAY_S=0.28
PORT=8000
```

Important:

* In your current `main.py`, the API key check is strict. If `API_SECRET_KEY` is empty or missing, requests will fail with 403.
* Every request must include the same value in the `x-api-key` header.

### Run the server

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Local endpoint:

* `http://127.0.0.1:8000/api/detect`

---

## Testing

Only one test file is kept:

```bash
python src/tests/test_chat.py
```

What to change inside `test_chat.py` before you run it:

* `ENDPOINT_URL` (local or deployed)
* `API_KEY` (must match `API_SECRET_KEY`)

If you want `test_chat.py` to be a simple interactive chat runner (no scoring, no weighted scenarios), tell me and I will rewrite it in a cleaner format while keeping it as a single file.

---

## Deployment notes

Before submitting:

* Verify the URL is public and HTTPS works.
* Confirm success responses return HTTP 200 and valid JSON with `status` and `reply`.
* Keep latency under 30 seconds.
* Avoid hardcoding scenario strings or special-case logic.

---

## Example scam types

NIRIKSHA.ai is designed to handle common patterns such as:

* bank impersonation and OTP theft
* UPI payment and cashback scams
* phishing links and fake verification pages
* KYC update scams
* job, investment, lottery, and utility bill scam patterns

---

## Team

<table>
  <tr>
    <td align="center"><b>Vanshaj Garg</b><br/>📧 <a href="mailto:official.vanshaj.garg@gmail.com">official.vanshaj.garg@gmail.com</a><br/>🔗 <a href="https://www.linkedin.com/in/vanshajgargg">LinkedIn</a></td>
    <td align="center"><b>Abhishek Rajput</b><br/>📧 <a href="mailto:rajputabhishek512@gmail.com">rajputabhishek512@gmail.com</a><br/>🔗 <a href="https://www.linkedin.com/in/abhi-99-rajput/">LinkedIn</a></td>
    <td align="center"><b>Abhay Raj Yadav</b><br/>📧 <a href="mailto:19abhay26@gmail.com">19abhay26@gmail.com</a><br/>🔗 <a href="https://www.linkedin.com/in/contactabhayraj">LinkedIn</a></td>
  </tr>
</table>

---

## License

Built for the India AI Impact Buildathon 2026 organized by HCL GUVI under the India AI Impact Summit.

<p align="center">
  <b>🛡️ NIRIKSHA.ai</b><br/>
  <i>Because the best defense is making the attacker's offense work against them.</i><br/><br/>
  <b>Fighting scams. Extracting intelligence. Wasting scammer time.</b>
</p>
```

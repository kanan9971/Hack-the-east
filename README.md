# ContractLens — AI Legal Companion

Analyze any Terms of Service, privacy policy, contract, or legal document. ContractLens provides plain-English summaries, risk flags, clause-by-clause breakdowns, persona-tailored insights, and an AI privacy advisor — powered by MiniMax AI.

Use it via the **Chrome extension** (analyze pages as you browse) or the **web dashboard** (paste text or enter a URL).

---

## Features

### Chrome Extension

- **Analyze any page** — Click the ContractLens icon on a ToS, privacy policy, or contract page; the side panel opens with instant analysis.
- **Paste text manually** — Use the clipboard button to paste and analyze text from anywhere.
- **Re-analyze from page** — Re-extract and analyze the current page with one click.
- **Summary** — Plain-English overview of the document.
- **Risks** — Flagged clauses with severity (high/medium/low) and explanations.
- **Details** — Section-by-section breakdown with labels (data use, termination, liability, etc.).
- **For You** — Persona-tailored insights (Student, Employee, Freelancer, Tenant).
- **Vault** — Seal analysis to a “Quantum Vault” receipt (content hash, vault ID).
- **Student Advisor** — AI chat agent for HK students & parents on privacy and legal questions.
- **Dashboard** — Quick link to open the web dashboard in a new tab.

### Web Dashboard

- **URL analysis** — Enter a URL; the backend fetches the page, extracts text, and analyzes it.
- **Paste text** — Paste contract or legal text directly (min 50 characters).
- **Same analysis** — Summary, Key Points, Entities, Risks, Details, For You, and Vault tabs.
- **Standalone use** — No extension needed; works in any browser at `http://localhost:8000/dashboard`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Chrome Extension (React + Vite + MV3)                           │
│  • Content script extracts page text                             │
│  • Background worker relays to API                               │
│  • Side panel: Summary, Risks, Details, For You, Vault, Agent    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│  Web Dashboard (static HTML) │  http://localhost:8000/dashboard  │
│  • URL input or paste text   │                                    │
│  • Same analysis UI          │                                    │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (AWS Lambda + API Gateway)                      │
│  • parser → classifier → analyzer → risk_flagger                 │
│  • insights, vault, agent/chat                                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    MiniMax API (MiniMax-M2.1)
```

---

## Prerequisites

- **Node.js** >= 18
- **Python** >= 3.11
- **MiniMax API key** — sign up at [platform.minimax.io](https://platform.minimax.io) and create a key
- **AWS SAM CLI** (for deployment) — [install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- **AWS credentials** configured (`aws configure`)

---

## Quick Start (Local Development)

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy .env.example to .env and add your keys (or set env vars)
# cp .env.example .env   # then edit .env with MINIMAX_API_KEY and optional AWS/Bedrock vars
export MINIMAX_API_KEY="your-key-here"   # Windows: set MINIMAX_API_KEY=your-key-here

# Run the server
uvicorn main:app --reload --port 8000
```

The API runs at `http://localhost:8000`. Test with:

```bash
curl http://localhost:8000/health
```

### 2. Web Dashboard

With the backend running, open:

```
http://localhost:8000/dashboard
```

- Add a URL or paste text in the left column
- Click **Analyze**
- View Summary, Risks, Details, For You, and Vault tabs

### 3. Chrome Extension

```bash
cd extension
npm install
npm run build
```

Load in Chrome:

1. Open `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `extension/dist` folder

**Use it:**

- Go to any ToS, privacy policy, or contract page
- Click the ContractLens icon → side panel opens with analysis
- Or use the paste button to analyze copied text
- Use the Dashboard button to open the web UI
- Use **Ask My Privacy Agent** for AI chat

---

## Deploy to AWS

**Prerequisites:** [Install AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) (e.g. `brew install aws-sam-cli` on macOS) and run `aws configure` with your AWS credentials.

**Deploy the backend:**

```bash
cd backend
# MINIMAX_API_KEY is read from .env (copy from .env.example if needed)
./deploy.sh --guided   # first time: sets stack name, region, etc.
./deploy.sh            # later deploys (no --guided)
```

**Get your API URL** (from deploy output, or):

```bash
sam list endpoints --stack-name <your-stack-name>
# or
aws cloudformation describe-stacks --stack-name <your-stack-name> \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text
```

**Build the extension for the hosted API:**

```bash
cd extension
VITE_API_BASE=https://YOUR_API_ID.execute-api.YOUR_REGION.amazonaws.com npm run build
```

Then load `extension/dist` in Chrome as usual. The extension will call your AWS-hosted API.

## Project Structure

```
├── extension/                 Chrome extension (React + Vite + Manifest V3)
│   ├── src/
│   │   ├── background/        Service worker — relays messages, calls API
│   │   ├── content/           Content script — detects legal pages, extracts text
│   │   ├── sidepanel/         React UI (Summary, Risks, Details, For You, Vault, Agent)
│   │   └── shared/            Shared types and API client
│   ├── public/                manifest.json + icons
│   └── dist/                  Built extension (load this in Chrome)
├── backend/                   Python FastAPI backend
│   ├── main.py                App entry, routes, Lambda handler
│   ├── config.py              MiniMax / AWS configuration
│   ├── schemas.py             Pydantic request/response models
│   ├── static/                Web dashboard (index.html)
│   ├── services/
│   │   ├── parser.py          Text segmentation into sections
│   │   ├── classifier.py      Heuristic clause classification
│   │   ├── analyzer.py        MiniMax LLM analysis
│   │   ├── risk_flagger.py    Risk detection and flagging
│   │   ├── insights.py        Persona-tailored insights
│   │   ├── vault.py           Quantum Vault receipt generation
│   │   └── agent.py           Student Advisor chat
│   └── template.yaml          AWS SAM deployment template
└── README.md
```

---

## API

### `GET /health`

Returns `{"status": "ok"}`.

### `POST /analyze`

Analyze pasted text.

**Request:**

```json
{
  "text": "Full text of the legal document...",
  "doc_type": "tos",
  "persona": "student"
}
```

### `POST /analyze_url`

Fetch a URL, extract text, and analyze it.

**Request:**

```json
{
  "url": "https://example.com/terms",
  "doc_type": "tos",
  "persona": "student"
}
```

### `POST /insights`

Generate persona-tailored insights from an analysis.

**Request:**

```json
{
  "analysis": { /* AnalyzeResponse */ },
  "user_context": {
    "persona": "student",
    "primary_concerns": ["data_sharing"],
    "document_context": "terms of service"
  }
}
```

### `POST /vault`

Seal analysis to a Quantum Vault receipt (content hash, vault ID).

**Request:**

```json
{
  "analysis": {
    "summary": "...",
    "key_points": ["..."],
    "risks": [...],
    "entities": {...}
  }
}
```

### `POST /agent/chat`

Chat with the Student Advisor AI.

**Request:**

```json
{
  "session_id": "optional-session-id",
  "message": "What should I watch out for?",
  "page_text": "Optional document text for context"
}
```

### `POST /analyze` & `POST /analyze_url` — Response

```json
{
  "summary": "Plain-English summary of the document.",
  "key_points": ["Point 1", "Point 2", "..."],
  "risks": [
    {
      "category": "data_sharing",
      "severity": "high",
      "clause_excerpt": "We may share your data with...",
      "explanation": "Your data may be sold to third parties."
    }
  ],
  "sections": [
    { "title": "Data Collection", "body": "...", "labels": ["data_use"] }
  ],
  "entities": {
    "parties": ["Acme Corp", "User"],
    "dates": ["January 1, 2026"],
    "amounts": ["$9.99/month"]
  },
  "persona_notes": ["As a student, pay attention to..."]
}
```

---

## License

MIT

# ContractLens — AI Legal Companion (Chrome Extension)

Analyze any Terms of Service, privacy policy, contract, or legal document in your browser. ContractLens provides plain-English summaries, risk flags, clause-by-clause breakdowns, and persona-tailored insights.

## Architecture

```
Chrome Extension (React + Vite + MV3)
  │
  │  content script extracts page text
  │  background worker relays to API
  │  side panel displays results
  │
  └──▶ FastAPI Backend (AWS Lambda + API Gateway)
          │
          │  parser → classifier → analyzer → risk flagger
          │
          ├──▶ MiniMax API (summary + key points on /analyze)
          └──▶ AWS Bedrock (advisor follow-up Q&A on /agent)
```

## Prerequisites

- **Node.js** >= 18
- **Python** >= 3.11
- **MiniMax API key** — used for page summary generation (`/analyze`)
- **AWS Bedrock access** — used for stronger follow-up advisor chat (`/agent`)
- **AWS SAM CLI** (for deployment) — [install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- **AWS credentials** configured (`aws configure`)

## Setup on a New Computer

Follow these steps from a fresh machine.

### 1. Clone and enter the project

```bash
git clone https://github.com/kanan9971/Hack-the-east.git
cd Hack-the-east
```

### 2. Backend setup

```bash
cd backend
py -m pip install -r requirements.txt
```

Create `backend/.env`:

```env
MINIMAX_API_KEY=your-real-minimax-key
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
# Optional (if not using default AWS credential chain):
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_SESSION_TOKEN=
ALLOWED_ORIGINS=*
ALLOW_CREDENTIALS=false
```

Run backend:

```bash
py -m uvicorn main:app --reload --port 8000
```

Verify backend:

```bash
curl http://127.0.0.1:8000/health
```

### 3. Extension setup

Open a second terminal:

```bash
cd extension
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.production
npm run build
```

### 4. Load extension in Chrome

1. Open `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the `extension/dist` folder
5. Click **Reload** in `chrome://extensions/` after any new build

### 5. Run it

- Open a Terms/Privacy/contract page
- Click the ContractLens extension icon
- Check the side panel for analysis output

## Quick Start (Local Development)

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set your MiniMax API key
export MINIMAX_API_KEY="your-key-here"

# Run the server
uvicorn main:app --reload --port 8000
```

The API is now running at `http://localhost:8000`. Test with:

```bash
curl http://localhost:8000/health
```

### 2. Chrome Extension

```bash
cd extension
npm install
# Set production API endpoint for build output
# Windows (PowerShell): echo "VITE_API_BASE_URL=https://your-api.example.com" > .env.production
# macOS/Linux: echo 'VITE_API_BASE_URL=https://your-api.example.com' > .env.production
npm run build
```

Then load in Chrome:

1. Open `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `extension/dist` folder

### 3. Use it

- Navigate to any Terms of Service or privacy policy page
- Click the ContractLens icon in the toolbar
- The side panel opens with analysis results
- Or paste text manually using the clipboard button in the header

## Deploy to AWS

```bash
cd backend

sam build
sam deploy --guided \
  --parameter-overrides MiniMaxApiKey="your-key-here"
```

After deploy, set `extension/.env.production` with your API Gateway URL as `VITE_API_BASE_URL` and rebuild the extension.

## Project Structure

```
├── extension/                 Chrome extension (React + Vite + Manifest V3)
│   ├── src/
│   │   ├── background/        Service worker — relays messages, calls API
│   │   ├── content/           Content script — detects legal pages, extracts text
│   │   ├── sidepanel/         React side panel UI (Summary, Risks, Details, For You)
│   │   └── shared/            Shared types and API client
│   ├── public/                manifest.json + icons
│   └── dist/                  Built extension (load this in Chrome)
├── backend/                   Python FastAPI backend
│   ├── main.py                App entry + Lambda handler
│   ├── config.py              MiniMax / AWS configuration
│   ├── schemas.py             Pydantic request/response models
│   ├── services/
│   │   ├── parser.py          Text segmentation into sections
│   │   ├── classifier.py      Heuristic clause classification
│   │   ├── analyzer.py        MiniMax LLM analysis
│   │   └── risk_flagger.py    Risk detection and flagging
│   └── template.yaml          AWS SAM deployment template
└── README.md
```

## API

### `GET /health`

Returns `{"status": "ok"}`.

### `POST /analyze`

**Request:**

```json
{
  "text": "Full text of the legal document...",
  "doc_type": "tos",
  "persona": "student"
}
```

**Response:**

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
    "amounts": ["$9.99/month"],
    "obligations": ["User must not reverse-engineer..."]
  },
  "persona_notes": ["As a student, pay attention to..."]
}
```

## License

MIT

# ContractLens — AI Legal Companion (Chrome Extension)

Analyze any Terms of Service, privacy policy, contract, or legal document in your browser. ContractLens provides plain-English summaries, risk flags, clause-by-clause breakdowns, and persona-tailored insights — powered by MiniMax AI.

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
          └──▶ MiniMax API (MiniMax-M2.1 via Anthropic SDK)
```

## Prerequisites

- **Node.js** >= 18
- **Python** >= 3.11
- **MiniMax API key** — sign up at [platform.minimax.io](https://platform.minimax.io) and create a key
- **AWS SAM CLI** (for deployment) — [install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- **AWS credentials** configured (`aws configure`)

## Quick Start (Local Development)

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy .env.example to .env and add your keys (or set env vars)
# cp .env.example .env   # then edit .env with MINIMAX_API_KEY and optional AWS/Bedrock vars
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

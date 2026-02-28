# Deploying the ContractLens Backend on AWS

The backend is designed to run on **AWS Lambda** behind **API Gateway HTTP API**, using **AWS SAM** for deployment. This gives you a fully hosted, serverless API with no servers to manage.

## What Gets Deployed

- **Lambda function** (Python 3.12): runs the FastAPI app via Mangum.
- **API Gateway HTTP API**: public HTTPS endpoint with CORS enabled for the extension and dashboard.
- **IAM role** for the function: allows calling **Bedrock** (Student Privacy Agent). No need to put AWS keys in env; the role is used automatically.

## Prerequisites

1. **AWS account** with permissions to create Lambda, API Gateway, IAM roles, and CloudFormation stacks.
2. **AWS CLI** installed and configured:
   ```bash
   aws configure
   ```
3. **SAM CLI** installed:
   ```bash
   brew install aws-sam-cli
   ```
4. **Bedrock access**: In the AWS console, enable Bedrock in your region (e.g. **us-east-1**) and ensure the model `anthropic.claude-3-haiku-20240307-v1:0` (or your chosen model) is available. The template grants the Lambda role permission to invoke Bedrock foundation models.

## IAM for Deploy (Your User/Role)

Deploying with SAM creates a Lambda execution role and an HTTP API. If deploy fails with an IAM error (e.g. tagging the role), add **`iam:TagRole`** and **`iam:UntagRole`** to the IAM policy used by the user/role running `sam deploy`. See **AWS_SAM_POLICY.md** in this folder for the exact policy snippet.

## Deployment Steps

### 1. Set secrets (do not commit)

Ensure `backend/.env` contains at least:

- `MINIMAX_API_KEY` — required for document analysis and insights.

Optional (Bedrock is configured via Lambda role; these are only for local runs or overrides):

- `AWS_REGION` — e.g. `us-east-1` (Lambda uses the deployment region by default).
- `BEDROCK_MODEL_ID` — default in the template is `anthropic.claude-3-haiku-20240307-v1:0`.

`.env` is excluded from the Lambda package via `.samignore`.

### 2. First-time deploy (guided)

From the **backend** directory:

```bash
cd backend
./deploy.sh --guided
```

You will be prompted for:

- **Stack name** (e.g. `contractlens-api`)
- **AWS Region** (e.g. `us-east-1`)
- **Confirm changes before deploy**
- **Allow SAM CLI IAM role creation**
- **Disable rollback** (optional)
- **Save arguments to configuration file** — choose **Y** so future deploys use the same stack name and region.

The script passes `MiniMaxApiKey` (and optionally `BedrockModelId`) as CloudFormation parameters; they are not stored in your repo.

### 3. Subsequent deploys

```bash
cd backend
./deploy.sh
```

This uses the saved `samconfig.toml` (stack name, region, etc.) and the same parameter overrides.

### 4. Get the API URL

After a successful deploy, the script will try to print the API URL. If not, run:

```bash
sam list endpoints --stack-name <your-stack-name>
```

Or:

```bash
aws cloudformation describe-stacks --stack-name <your-stack-name> \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text
```

Example base URL: `https://abc123xyz.execute-api.us-east-1.amazonaws.com`

### 5. Verify the API

- Health: `GET https://<your-api-url>/health` → `{"status":"ok"}`
- The extension and dashboard should call this base URL (no trailing slash).

### 6. Build the extension for production

Point the extension at your deployed API when building:

```bash
cd extension
VITE_API_BASE=https://<your-api-url> npm run build
```

Then load the built extension from `extension/dist` in Chrome (or pack and publish).

## Summary

| Item        | Where it lives on AWS                          |
|------------|-------------------------------------------------|
| API        | API Gateway HTTP API (public URL)               |
| App logic  | Lambda (FastAPI + Mangum)                       |
| Bedrock    | Invoked by Lambda using its execution role      |
| Secrets    | MiniMax key passed as CloudFormation parameter  |

The backend is fully hosted on AWS; you only need to run `./deploy.sh` when you change code or config, and to set `VITE_API_BASE` when building the extension.

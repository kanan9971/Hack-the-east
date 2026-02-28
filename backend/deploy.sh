#!/usr/bin/env bash
# Deploy ContractLens backend to AWS (Lambda + API Gateway).
# Prerequisites: AWS CLI configured (aws configure), SAM CLI installed (brew install aws-sam-cli).
# First time: run ./deploy.sh --guided to set stack name and region.

set -e
cd "$(dirname "$0")"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

if [[ -z "$MINIMAX_API_KEY" ]]; then
  echo "MINIMAX_API_KEY is not set. Add it to backend/.env or export it."
  exit 1
fi

# Optional: override Bedrock model (default is in template.yaml)
BEDROCK_MODEL_ID="${BEDROCK_MODEL_ID:-anthropic.claude-3-haiku-20240307-v1:0}"
PARAMS="MiniMaxApiKey=$MINIMAX_API_KEY BedrockModelId=$BEDROCK_MODEL_ID"

echo "Building..."
sam build

if [[ "$1" == "--guided" ]]; then
  echo "Deploying (guided — you'll be prompted for stack name, region, etc.)..."
  sam deploy --guided --parameter-overrides "$PARAMS"
else
  echo "Deploying..."
  sam deploy --parameter-overrides "$PARAMS"
fi

# Try to show API URL if we have a stack name (from samconfig.toml)
STACK_NAME=""
if [[ -f samconfig.toml ]]; then
  STACK_NAME=$(grep -E '^\s*stack_name\s*=' samconfig.toml | head -1 | sed -E "s/.*[\"']([^\"']+)[\"'].*/\1/")
fi
if [[ -n "$STACK_NAME" ]]; then
  API_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text 2>/dev/null || true)
  if [[ -n "$API_URL" ]]; then
    echo ""
    echo "---"
    echo "API URL: $API_URL"
    echo "Health:  $API_URL/health"
    echo "---"
    echo "Build extension for production: cd extension && VITE_API_BASE=$API_URL npm run build"
  fi
fi

echo ""
echo "If the URL is not above, get it with: sam list endpoints --stack-name <your-stack-name>"
echo "IAM note: If deploy failed on IAM, add iam:TagRole and iam:UntagRole to your SAM policy (see AWS_SAM_POLICY.md)."

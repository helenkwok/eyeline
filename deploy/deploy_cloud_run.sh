#!/usr/bin/env bash
# ==============================================================================
# Eyeline — Google Cloud Run Deployment Script
# Deploys the zero-credential Eyeline container to Google Cloud Run with
# public unauthenticated access so hackathon judges have a zero-install live URL.
# ==============================================================================

set -e

echo "=== Eyeline Cloud Run Deployment ==="

# Check gcloud installation
if ! command -v gcloud &> /dev/null; then
  echo "Error: gcloud CLI is not installed."
  echo "Install via Homebrew: brew install --cask gcloud-cli"
  echo "Or download from: https://cloud.google.com/sdk/docs/install"
  exit 1
fi

# Determine GCP Project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
  echo "No active GCP project set in gcloud."
  read -r -p "Enter your Google Cloud Project ID: " PROJECT_ID
  gcloud config set project "$PROJECT_ID"
fi

REGION="us-central1"
SERVICE_NAME="eyeline"

echo "Deploying to Project: $PROJECT_ID | Region: $REGION | Service: $SERVICE_NAME"

# Build and deploy directly from source via Cloud Build & Cloud Run
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2

echo "Deployment complete! Live Judge & Review Station URL:"
gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --format 'value(status.url)'

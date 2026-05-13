#!/bin/bash
# TXG Financial Chatbot — Startup Script (Grok / xAI)
# -------------------------------------------------------
# PREREQUISITES:
#   pip install flask openai pandas openpyxl
#
# SETUP:
#   1. Open app.py and paste your Grok API key on line 16
#      OR set it as an environment variable (see below)
#   2. Run this script: bash run.sh
# -------------------------------------------------------

if [ -z "$GROK_API_KEY" ]; then
  echo "WARNING: GROK_API_KEY env var not set."
  echo "Make sure you pasted your key directly in app.py (line 16),"
  echo "or run: export GROK_API_KEY='xai-your-key-here'"
  echo ""
fi

echo "Starting TXG Financial Chatbot..."
echo "Open your browser at: http://localhost:5000"
echo ""
python app.py

#!/bin/bash
set -e
set -a          # auto-export all variables
source .env
set +a          # turn off auto-export

# Kill all child processes when this script exits (Ctrl+C or error)
trap "kill 0" EXIT

echo "Starting MCP server..."
uv run python -m mcp_server.server &

sleep 2
echo "Starting FastAPI..."
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 &

sleep 1
echo "Starting Streamlit..."
uv run streamlit run ui/app.py --server.address 0.0.0.0 --server.port 8501 &

echo "All services running. Press Ctrl+C to stop."
wait
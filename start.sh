#!/bin/bash
set -e

echo "Starting MyAlexa FastMCP Server on port ${PORT:-8000}..."
python -m daybreak.mcp_server.server &
MCP_PID=$!

echo "Waiting for MCP server to start up..."
sleep 2

echo "Starting MyAlexa Web UI Simulator on port ${UI_PORT:-3000}..."
python -m daybreak.ui.app &
UI_PID=$!

# Trap signals and forward shutdown
trap "kill -TERM $MCP_PID $UI_PID" SIGTERM SIGINT

wait -n $MCP_PID $UI_PID

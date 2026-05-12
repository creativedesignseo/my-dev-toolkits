#!/bin/bash
LOG="/tmp/mcp-gmail-$(date +%s).log"
echo "[START] $(date) PID=$$ PWD=$(pwd)" >> "$LOG"
echo "[CMD] /Users/aimac/.nvm/versions/node/v20.20.2/bin/node /Users/aimac/Documents/Workspace/mcp-toolkits/repo/google-gmail-manager/mcp-server.js" >> "$LOG"
/Users/aimac/.nvm/versions/node/v20.20.2/bin/node /Users/aimac/Documents/Workspace/mcp-toolkits/repo/google-gmail-manager/mcp-server.js >> "$LOG" 2>&1
EXIT=$?
echo "[EXIT] $(date) code=$EXIT" >> "$LOG"

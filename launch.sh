#!/bin/bash
# Start the Fabric Web Interface
cd /home/james/fabric-web

# Start server in background
python app.py &

# Wait a moment for the server to be ready, then open the browser
sleep 2
xdg-open http://localhost:5050 &

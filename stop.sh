#!/bin/bash

# Stop all Python services running on ports
# This script finds and kills processes using network ports, with a focus on Python services

echo "🔍 Checking for services using common Python ports..."

# Common ports used by Python services
PORTS="5000 5001 5005 8000 8080 8081 8888"

# Find processes using these ports
for PORT in $PORTS; do
    PID=$(lsof -ti :$PORT)
    if [ ! -z "$PID" ]; then
        echo "🛑 Found process using port $PORT (PID: $PID)"
        echo "   Process info: $(ps -p $PID -o command=)"
        kill -9 $PID 2>/dev/null
        echo "   ✓ Killed process $PID"
    else
        echo "ℹ️ Port $PORT is available"
    fi
done

# Kill any Python processes that might be running our services
echo "\n🔄 Cleaning up any remaining Python processes..."
pkill -f "python.*(run_rtu_output|modapi|flask|gunicorn|rtu|tcp|rest|api)" 2>/dev/null

# Double check for any remaining Python processes
REMAINING=$(pgrep -f "python")
if [ ! -z "$REMAINING" ]; then
    echo "\n⚠️  The following Python processes are still running:"
    ps -p $REMAINING -o pid,command
    echo "\nTo forcefully stop them, run: kill -9 $REMAINING"
else
    echo "\n✅ All Python services have been stopped."
fi

# Show current network status
echo "\n🌐 Current network status on common ports:"
for PORT in $PORTS; do
    lsof -i :$PORT || echo "  Port $PORT is free"
done

echo "\n🔍 Current Python processes:"
ps aux | grep -i python | grep -v grep || echo "  No Python processes found"

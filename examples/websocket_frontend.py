#!/usr/bin/env python3
"""
WebSocket Frontend Example for Modbus RTU Communication
Demonstrates persistent connection management with WebSockets
"""

import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modapi.api.ws import run_ws_server

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run WebSocket server with default settings
    # This will auto-detect the Modbus device and start a WebSocket server
    # with a built-in HTML client interface
    run_ws_server(
        port=None,  # Auto-detect
        baudrate=57600,
        timeout=1.0,
        host='0.0.0.0',
        api_port=5005,
        debug=True
    )

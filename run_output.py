#!/usr/bin/env python3
"""
Run the Modbus Output Module

This script starts the Modbus Output Module which provides a web interface
for visualizing and controlling Modbus coils (digital outputs).
"""

import os
import argparse
from modapi.output import create_output_app

def main():
    """Main function to run the Output Module"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Modbus Output Module')
    parser.add_argument('--port', type=str, default=None,
                      help='Modbus serial port (default: auto-detect)')
    parser.add_argument('--baudrate', type=int, default=9600,
                      help='Baud rate (default: 9600)')
    parser.add_argument('--timeout', type=float, default=1.0,
                      help='Timeout in seconds (default: 1.0)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                      help='Host to bind the web interface (default: 0.0.0.0)')
    parser.add_argument('--web-port', type=int, default=5002,
                      help='Port for the web interface (default: 5002)')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Start the output module
    print(f"Starting Modbus Output Module on http://{args.host}:{args.web_port}")
    print(f"Connecting to Modbus device on {args.port or 'auto-detect'}")
    
    app = create_output_app(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        host=args.host,
        api_port=args.web_port,
        debug=args.debug
    )
    
    try:
        app.run(host=args.host, port=args.web_port, debug=args.debug)
    except KeyboardInterrupt:
        print("\nShutting down Output Module...")

if __name__ == '__main__':
    main()

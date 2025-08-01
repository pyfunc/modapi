"""
modapi - Main entry point for running as a module
"""

import os
import sys
import argparse
import logging

from . import load_env_files
from .api import create_rest_app, start_mqtt_broker, interactive_mode, execute_command
from .client import auto_detect_modbus_port

# Configure logging
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the modapi module"""
    # Load environment variables
    load_env_files()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='modapi - Unified API for Modbus communication')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # REST API command
    rest_parser = subparsers.add_parser('rest', help='Run REST API server')
    rest_parser.add_argument('--host', default='0.0.0.0', help='Host to bind the server')
    rest_parser.add_argument('--port', type=int, default=int(os.environ.get('modapi_PORT', 5000)), 
                           help='Port to bind the server')
    rest_parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    rest_parser.add_argument('--modbus-port', help='Modbus serial port')
    rest_parser.add_argument('--baudrate', type=int, help='Baud rate')
    rest_parser.add_argument('--timeout', type=float, help='Timeout in seconds')
    
    # MQTT command
    mqtt_parser = subparsers.add_parser('mqtt', help='Run MQTT client')
    mqtt_parser.add_argument('--broker', default=os.environ.get('MQTT_BROKER', 'localhost'), 
                           help='MQTT broker address')
    mqtt_parser.add_argument('--port', type=int, default=int(os.environ.get('MQTT_PORT', 1883)), 
                           help='MQTT broker port')
    mqtt_parser.add_argument('--topic-prefix', default=os.environ.get('MQTT_TOPIC_PREFIX', 'modapi'), 
                           help='MQTT topic prefix')
    mqtt_parser.add_argument('--modbus-port', help='Modbus serial port')
    mqtt_parser.add_argument('--baudrate', type=int, help='Baud rate')
    mqtt_parser.add_argument('--timeout', type=float, help='Timeout in seconds')
    
    # Shell command
    shell_parser = subparsers.add_parser('shell', help='Run interactive shell')
    shell_parser.add_argument('--modbus-port', help='Modbus serial port')
    shell_parser.add_argument('--baudrate', type=int, help='Baud rate')
    shell_parser.add_argument('--timeout', type=float, help='Timeout in seconds')
    shell_parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    # Direct command execution
    cmd_parser = subparsers.add_parser('cmd', help='Execute Modbus command directly')
    cmd_parser.add_argument('--modbus-port', help='Modbus serial port')
    cmd_parser.add_argument('--baudrate', type=int, help='Baud rate')
    cmd_parser.add_argument('--timeout', type=float, help='Timeout in seconds')
    cmd_parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    cmd_parser.add_argument('command', help='Command: wc (write coil), rc (read coil), etc.')
    cmd_parser.add_argument('args', nargs='*', help='Command arguments')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for Modbus devices')
    
    args = parser.parse_args()
    
    # Run the selected command
    if args.command == 'rest':
        app = create_rest_app(
            port=args.modbus_port,
            baudrate=args.baudrate,
            timeout=args.timeout,
            host=args.host,
            api_port=args.port,
            debug=args.debug
        )
        app.run(host=args.host, port=args.port, debug=args.debug)
    elif args.command == 'mqtt':
        start_mqtt_broker(
            port=args.modbus_port,
            baudrate=args.baudrate,
            timeout=args.timeout,
            broker=args.broker,
            mqtt_port=args.port,
            topic_prefix=args.topic_prefix
        )
    elif args.command == 'shell':
        # Run interactive shell
        interactive_mode(
            port=args.modbus_port,
            baudrate=args.baudrate,
            timeout=args.timeout,
            verbose=args.verbose
        )
    elif args.command == 'cmd':
        # Execute command directly
        if not args.args:
            print("Error: No arguments provided for command")
            sys.exit(1)
            
        # For cmd subcommand, we need to use the nested 'command' argument 
        # as the actual modbus command (wc, rc, etc.)
        success, response = execute_command(
            command=args.command,
            args=args.args,
            port=args.modbus_port,
            baudrate=args.baudrate,
            timeout=args.timeout,
            verbose=args.verbose
        )
        
        # Output response as JSON
        import json
        print(json.dumps(response, indent=2))
        
        # Exit with appropriate status code
        sys.exit(0 if success else 1)
    elif args.command == 'scan':
        # Scan for Modbus devices
        port = auto_detect_modbus_port()
        if port:
            print(f"Modbus device found: {port}")
            sys.exit(0)
        else:
            print("No Modbus device found")
            sys.exit(1)
    else:
        # Default to help if no command specified
        parser.print_help()

if __name__ == '__main__':
    main()

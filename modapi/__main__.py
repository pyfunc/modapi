"""
modapi - Main entry point for running as a module
"""

import os
import sys
import argparse
import logging

from . import load_env_files
from .api import create_rest_app, start_mqtt_broker
from .shell import main as shell_main

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
    shell_parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    shell_parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    shell_parser.add_argument('command', nargs='*', help='Command to run')
    
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
            broker=args.broker,
            port=args.port,
            topic_prefix=args.topic_prefix,
            modbus_port=args.modbus_port,
            baudrate=args.baudrate,
            timeout=args.timeout
        )
    elif args.command == 'shell':
        # Convert args to sys.argv format for shell_main
        sys_argv = ['modapi']
        if args.interactive:
            sys_argv.append('--interactive')
        if args.verbose:
            sys_argv.append('--verbose')
        if args.modbus_port:
            sys_argv.extend(['--port', args.modbus_port])
        if args.baudrate:
            sys_argv.extend(['--baudrate', str(args.baudrate)])
        if args.timeout:
            sys_argv.extend(['--timeout', str(args.timeout)])
        sys_argv.extend(args.command)
        
        # Run shell main
        sys.argv = sys_argv
        shell_main()
    else:
        # Default to help if no command specified
        parser.print_help()

if __name__ == '__main__':
    main()

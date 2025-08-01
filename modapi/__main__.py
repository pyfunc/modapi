"""
modapi - Main entry point for running as a module
"""

import os
import sys
import argparse
import logging
import json

from . import load_env_files
from .api.rest import create_rest_app
from .api.mqtt import start_mqtt_broker
from .api.shell import interactive_mode
from .api.cmd import execute_command
from .client import auto_detect_modbus_port, find_serial_ports, test_modbus_port

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
    cmd_parser.add_argument('modbus_command', help='Command: wc (write coil), rc (read coil), etc.')
    cmd_parser.add_argument('args', nargs='*', help='Command arguments')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for Modbus devices')
    scan_parser.add_argument('--debug', action='store_true', help='Enable debug output')
    scan_parser.add_argument('--port', help='Specify a specific port to test')
    scan_parser.add_argument('--baudrate', type=int, help='Specify a specific baud rate to test')
    scan_parser.add_argument('--unit', type=int, help='Specify a specific unit ID to test')
    
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
        if not hasattr(args, 'modbus_command') or not args.modbus_command:
            print("Error: No Modbus command provided")
            sys.exit(1)
            
        # Pass the modbus_command and args to execute_command
        success, response = execute_command(
            command=args.modbus_command,
            args=args.args,
            port=args.modbus_port,
            baudrate=args.baudrate,
            timeout=args.timeout,
            verbose=args.verbose
        )
        
        # Output response as JSON
        print(json.dumps(response, indent=2))
        
        # Exit with appropriate status code
        sys.exit(0 if success else 1)
    elif args.command == 'scan':
        # Configure logging based on debug flag
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
            logger.setLevel(logging.INFO)
            
        # If a specific port is provided, test just that port
        if args.port:
            print(f"🔍 Testing specified port: {args.port}")
            baudrates = [args.baudrate] if args.baudrate else [9600, 19200, 38400, 57600, 115200]
            
            for baudrate in baudrates:
                print(f"  ⚙️  {baudrate} baud...", end=" ")
                success, result = test_modbus_port(
                    port=args.port,
                    baudrate=baudrate,
                    unit_id=args.unit,
                    debug=args.debug
                )
                if success:
                    print("✅ Device found!")
                    if args.debug:
                        print(f"    Details: {result}")
                    sys.exit(0)
                else:
                    if args.debug:
                        print(f"❌ {result.get('error', 'No response')}")
                    else:
                        print("❌")
            
            print(f"\n❌ No Modbus device found on {args.port}")
            sys.exit(1)
        else:
            # Scan all ports
            result = auto_detect_modbus_port(
                baudrates=[args.baudrate] if args.baudrate else None,
                debug=args.debug,
                unit_id=args.unit
            )
            if result:
                print(f"\n✅ Found Modbus device on {result.get('port')}")
                if args.debug:
                    print(f"    Details: {result}")
                sys.exit(0)
            else:
                print("\n❌ No Modbus devices found!")
                if args.debug:
                    print("    Make sure the device is properly connected and powered on.")
                    print("    Try specifying a different baud rate with --baudrate")
                    print("    or a specific unit ID with --unit")
                sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()

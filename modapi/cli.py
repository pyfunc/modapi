"""
modapi.cli - Command-line interface for Modbus operations
"""

import argparse
import sys
import json
import logging
from typing import List, Optional, Dict, Any, Tuple

from modapi.api.cmd import execute_command
from modapi.rtu import find_serial_ports, test_rtu_connection

# Configure logging
logger = logging.getLogger(__name__)

def setup_parser() -> argparse.ArgumentParser:
    """
    Set up the argument parser for the CLI
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(description='Modbus CLI Tool')
    
    # Global options
    parser.add_argument('--port', '-p', help='Serial port (e.g., /dev/ttyACM0)')
    parser.add_argument('--baudrate', '-b', type=int, default=57600, 
                       help='Baud rate (default: 57600)')
    parser.add_argument('--timeout', '-t', type=float, default=1.0,
                       help='Timeout in seconds (default: 1.0)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    # Subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for Modbus devices')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test Modbus connection')
    test_parser.add_argument('--unit-id', '-u', type=int, default=1,
                           help='Unit ID to test (default: 1)')
    
    # Command subparser
    cmd_parser = subparsers.add_parser('cmd', help='Execute a Modbus command')
    cmd_parser.add_argument('command_name', help='Command to execute (rc, wc, ri, rh, wh)')
    cmd_parser.add_argument('args', nargs=argparse.REMAINDER, 
                          help='Command arguments')
    
    # Shell command (interactive mode)
    subparsers.add_parser('shell', help='Start interactive shell')
    
    return parser

def handle_scan(args: argparse.Namespace) -> int:
    """Handle the scan command"""
    print("Scanning for Modbus devices...")
    ports = find_serial_ports()
    
    if not ports:
        print("No serial ports found")
        return 1
    
    print(f"Found {len(ports)} serial ports:")
    for port in ports:
        print(f"  - {port}")
    
    return 0

def handle_test(args: argparse.Namespace) -> int:
    """Handle the test command"""
    if not args.port:
        print("Error: Port not specified. Use --port to specify a port.")
        return 1
    
    print(f"Testing connection to {args.port} at {args.baudrate} baud...")
    success, result = test_rtu_connection(
        port=args.port,
        baudrate=args.baudrate,
        unit_id=args.unit_id
    )
    
    if success:
        print("Connection successful!")
        print(f"Device type: {result.get('device_type', 'Unknown')}")
        return 0
    else:
        print("Connection failed!")
        if 'error' in result:
            print(f"Error: {result['error']}")
        return 1

def handle_cmd(args: argparse.Namespace) -> int:
    """Handle the cmd command"""
    if not args.port:
        print("Error: Port not specified. Use --port to specify a port.")
        return 1
    
    success, result = execute_command(
        command=args.command_name,
        args=args.args,
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        verbose=args.verbose
    )
    
    if success:
        print(json.dumps(result, indent=2))
        return 0
    else:
        print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        return 1

def handle_shell(args: argparse.Namespace) -> int:
    """Handle the shell command"""
    print("Starting interactive shell...")
    from modapi.api.shell import interactive_mode
    return interactive_mode()

def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI
    
    Args:
        args: Command-line arguments (default: None, uses sys.argv)
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    parser = setup_parser()
    
    if args is None:
        args = sys.argv[1:]
    
    # If no arguments, show help
    if not args:
        parser.print_help()
        return 0
    
    parsed_args = parser.parse_args(args)
    
    # Configure logging
    log_level = logging.DEBUG if parsed_args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Dispatch to appropriate handler
    if parsed_args.command == 'scan':
        return handle_scan(parsed_args)
    elif parsed_args.command == 'test':
        return handle_test(parsed_args)
    elif parsed_args.command == 'cmd':
        return handle_cmd(parsed_args)
    elif parsed_args.command == 'shell':
        return handle_shell(parsed_args)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())

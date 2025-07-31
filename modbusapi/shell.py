"""
ModbusAPI Shell - Command Line Interface for Modbus operations
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, Any, List, Optional, Union

from .client import ModbusClient, auto_detect_modbus_port

# Configure logging
logger = logging.getLogger(__name__)


def create_response(command: str) -> Dict[str, Any]:
    """
    Create a base response dictionary
    
    Args:
        command: Command string
        
    Returns:
        Response dictionary with basic fields
    """
    return {
        'command': command,
        'success': False,
        'timestamp': None,
        'operation': None,
        'error': None
    }


def output_json(data: Dict[str, Any]):
    """
    Output data as formatted JSON
    
    Args:
        data: Data to output
    """
    print(json.dumps(data, indent=2))


def print_command_help():
    """Print help for command-line usage"""
    print("""
Modbus API Command Line Tool

Usage:
  modbusapi [options] <command> [args...]

Options:
  -v, --verbose    Enable verbose logging output
  -h, --help       Show this help message
  -p, --port PORT  Specify Modbus port (default: auto-detect or from .env)
  -b, --baud BAUD  Specify baud rate (default: from .env or 9600)
  -t, --timeout T  Specify timeout in seconds (default: from .env or 1.0)

Commands:
  rc <address> <count> [unit]  Read coils
  wc <address> <value> [unit]  Write coil (value: 0/1, true/false, on/off)
  ri <address> <count> [unit]  Read discrete inputs
  rh <address> <count> [unit]  Read holding registers
  wh <address> <value> [unit]  Write holding register
  --interactive                Start interactive mode
  --scan                       Scan for Modbus devices

Examples:
  modbusapi -v rc 0 8 1        # Read 8 coils with verbose logging
  modbusapi wc 0 on 1          # Turn on coil at address 0, unit 1
  modbusapi rh 0 5 1           # Read 5 holding registers
  modbusapi -p /dev/ttyACM0 wc 0 1  # Specify port explicitly
""")


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Modbus API Command Line Tool',
        add_help=False  # We'll handle help manually for more control
    )
    
    # Options
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('-h', '--help', action='store_true', help='Show help message')
    parser.add_argument('-p', '--port', help='Specify Modbus port')
    parser.add_argument('-b', '--baud', type=int, help='Specify baud rate')
    parser.add_argument('-t', '--timeout', type=float, help='Specify timeout in seconds')
    
    # Special modes
    parser.add_argument('--interactive', action='store_true', help='Start interactive mode')
    parser.add_argument('--scan', action='store_true', help='Scan for Modbus devices')
    
    # Command and arguments
    parser.add_argument('command', nargs='?', help='Modbus command (rc, wc, ri, rh, wh)')
    parser.add_argument('args', nargs='*', help='Command arguments')
    
    return parser.parse_args()


def interactive_mode(port: Optional[str] = None, baudrate: Optional[int] = None, 
                    timeout: Optional[float] = None, verbose: bool = False):
    """
    Start interactive command mode
    
    Args:
        port: Serial port (default: auto-detect)
        baudrate: Baud rate (default: from .env or 9600)
        timeout: Timeout in seconds (default: from .env or 1.0)
        verbose: Enable verbose logging
    """
    print("Modbus API Interactive Mode")
    print("Type 'help' for available commands, 'exit' to quit")
    
    # Auto-detect port if not specified
    if not port:
        port = auto_detect_modbus_port()
        if not port:
            print("No Modbus device found! Please connect a device and try again.")
            return
            
    # Create client
    client = ModbusClient(port=port, baudrate=baudrate, timeout=timeout, verbose=verbose)
    if not client.connect():
        print(f"Failed to connect to {port}")
        return
        
    print(f"Connected to Modbus device on {port}")
    
    try:
        while True:
            try:
                cmd_input = input("\nmodbus> ").strip()
                
                if not cmd_input:
                    continue
                    
                if cmd_input.lower() in ('exit', 'quit'):
                    break
                    
                if cmd_input.lower() in ('help', '?'):
                    print_command_help()
                    continue
                    
                # Parse command
                args = cmd_input.split()
                cmd = args[0].lower()
                
                # Process commands
                if cmd == 'rc' and len(args) >= 3:
                    address = int(args[1])
                    count = int(args[2])
                    unit = int(args[3]) if len(args) > 3 else 1
                    
                    result = client.read_coils(address, count, unit)
                    if result is not None:
                        print(f"Coils {address}-{address+count-1}:")
                        for i, val in enumerate(result):
                            print(f"  {address+i}: {'ON' if val else 'OFF'}")
                    else:
                        print("Failed to read coils")
                        
                elif cmd == 'wc' and len(args) >= 3:
                    address = int(args[1])
                    value = args[2].lower() in ('1', 'true', 'on')
                    unit = int(args[3]) if len(args) > 3 else 1
                    
                    if client.write_coil(address, value, unit):
                        print(f"Coil {address} set to {'ON' if value else 'OFF'}")
                    else:
                        print(f"Failed to write coil {address}")
                        
                elif cmd == 'ri' and len(args) >= 3:
                    address = int(args[1])
                    count = int(args[2])
                    unit = int(args[3]) if len(args) > 3 else 1
                    
                    result = client.read_discrete_inputs(address, count, unit)
                    if result is not None:
                        print(f"Discrete inputs {address}-{address+count-1}:")
                        for i, val in enumerate(result):
                            print(f"  {address+i}: {'ON' if val else 'OFF'}")
                    else:
                        print("Failed to read discrete inputs")
                        
                elif cmd == 'rh' and len(args) >= 3:
                    address = int(args[1])
                    count = int(args[2])
                    unit = int(args[3]) if len(args) > 3 else 1
                    
                    result = client.read_holding_registers(address, count, unit)
                    if result is not None:
                        print(f"Holding registers {address}-{address+count-1}:")
                        for i, val in enumerate(result):
                            print(f"  {address+i}: {val} (0x{val:04X})")
                    else:
                        print("Failed to read holding registers")
                        
                elif cmd == 'wh' and len(args) >= 3:
                    address = int(args[1])
                    value = int(args[2])
                    unit = int(args[3]) if len(args) > 3 else 1
                    
                    if client.write_register(address, value, unit):
                        print(f"Register {address} set to {value} (0x{value:04X})")
                    else:
                        print(f"Failed to write register {address}")
                        
                else:
                    print(f"Unknown command or invalid arguments: {cmd_input}")
                    print("Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                break
                
            except Exception as e:
                print(f"Error: {e}")
                
    finally:
        client.disconnect()
        print("Disconnected from Modbus device")


def command_line_mode(args: argparse.Namespace) -> bool:
    """
    Process command line arguments and execute commands
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        True if command succeeded, False otherwise
    """
    # Show help if requested or no command provided
    if args.help or (not args.command and not args.scan and not args.interactive):
        print_command_help()
        return True
        
    # Scan for devices
    if args.scan:
        port = auto_detect_modbus_port()
        return port is not None
        
    # Interactive mode
    if args.interactive:
        interactive_mode(port=args.port, baudrate=args.baud, 
                        timeout=args.timeout, verbose=args.verbose)
        return True
        
    # Regular command mode
    command = args.command
    command_args = args.args
    
    # Create response for JSON output
    response = create_response(f"{command} {' '.join(command_args)}")
    response['verbose'] = args.verbose
    
    try:
        # Use the configured port or auto-detect
        port = args.port
        if not port:
            port = os.getenv('MODBUS_PORT')
            if not port:
                port = auto_detect_modbus_port()
                if not port:
                    response['error'] = "Could not auto-detect Modbus port"
                    output_json(response)
                    return False
                response['port_source'] = 'auto_detected'
            else:
                response['port_source'] = 'env_file'
        else:
            response['port_source'] = 'command_line'
            
        response['port'] = port
        
        # Initialize modbus client
        modbus = ModbusClient(
            port=port,
            baudrate=args.baud,
            timeout=args.timeout,
            verbose=args.verbose
        )
        
        if not modbus.connect():
            response['error'] = f"Failed to connect to port {port}"
            output_json(response)
            return False
            
        # Process commands
        cmd = command.lower()
        response['operation'] = cmd
        
        if cmd == 'rc':  # Read coils
            if len(command_args) < 2:
                response['error'] = "Usage: rc <address> <count> [unit]"
                output_json(response)
                return False
                
            address = int(command_args[0])
            count = int(command_args[1])
            unit = int(command_args[2]) if len(command_args) > 2 else 1
            
            response.update({
                'address': address,
                'count': count,
                'unit': unit,
                'register_type': 'coil'
            })
            
            result = modbus.read_coils(address, count, unit)
            if result is not None:
                response.update({
                    'success': True,
                    'data': {
                        'start_address': address,
                        'end_address': address + count - 1,
                        'values': result,
                        'values_dict': {str(i): val for i, val in enumerate(result, address)}
                    }
                })
            else:
                response['error'] = "Failed to read coils"
                
        elif cmd == 'wc':  # Write coil
            if len(command_args) < 2:
                response['error'] = "Usage: wc <address> <value> [unit]"
                output_json(response)
                return False
                
            address = int(command_args[0])
            value = command_args[1].lower() in ('1', 'true', 'on')
            unit = int(command_args[2]) if len(command_args) > 2 else 1
            
            response.update({
                'address': address,
                'value': value,
                'value_display': 'ON' if value else 'OFF',
                'unit': unit,
                'register_type': 'coil'
            })
            
            if modbus.write_coil(address, value, unit):
                response.update({
                    'success': True,
                    'message': f"Coil {address} set to {'ON' if value else 'OFF'}",
                    'data': {
                        'address': address,
                        'value': value,
                        'value_display': 'ON' if value else 'OFF'
                    }
                })
            else:
                response['error'] = f"Failed to write coil {address}"
                
        elif cmd == 'ri':  # Read discrete inputs
            if len(command_args) < 2:
                response['error'] = "Usage: ri <address> <count> [unit]"
                output_json(response)
                return False
                
            address = int(command_args[0])
            count = int(command_args[1])
            unit = int(command_args[2]) if len(command_args) > 2 else 1
            
            response.update({
                'address': address,
                'count': count,
                'unit': unit,
                'register_type': 'discrete_input'
            })
            
            result = modbus.read_discrete_inputs(address, count, unit)
            if result is not None:
                response.update({
                    'success': True,
                    'data': {
                        'address': address,
                        'count': count,
                        'values': [bool(v) for v in result],
                        'values_display': ['ON' if v else 'OFF' for v in result]
                    },
                    'message': f"Read {count} discrete inputs starting at address {address}"
                })
            else:
                response['error'] = "Failed to read discrete inputs"
                
        elif cmd == 'rh':  # Read holding registers
            if len(command_args) < 2:
                response['error'] = "Usage: rh <address> <count> [unit]"
                output_json(response)
                return False
                
            address = int(command_args[0])
            count = int(command_args[1])
            unit = int(command_args[2]) if len(command_args) > 2 else 1
            
            response.update({
                'address': address,
                'count': count,
                'unit': unit,
                'register_type': 'holding_register'
            })
            
            result = modbus.read_holding_registers(address, count, unit)
            if result is not None:
                response.update({
                    'success': True,
                    'data': {
                        'start_address': address,
                        'end_address': address + count - 1,
                        'values': result,
                        'values_dict': {str(i): val for i, val in enumerate(result, address)},
                        'hex_values': [f"0x{val:04X}" for val in result],
                        'binary_values': [f"{val:016b}" for val in result]
                    }
                })
            else:
                response['error'] = "Failed to read holding registers"
                
        elif cmd == 'wh':  # Write holding register
            if len(command_args) < 2:
                response['error'] = "Usage: wh <address> <value> [unit]"
                output_json(response)
                return False
                
            address = int(command_args[0])
            value = int(command_args[1])
            unit = int(command_args[2]) if len(command_args) > 2 else 1
            
            response.update({
                'address': address,
                'value': value,
                'unit': unit,
                'register_type': 'holding_register',
                'value_hex': f"0x{value:04X}",
                'value_binary': f"{value:016b}"
            })
            
            if modbus.write_register(address, value, unit):
                response.update({
                    'success': True,
                    'message': f"Holding register {address} set to {value}",
                    'data': {
                        'address': address,
                        'value': value,
                        'value_hex': f"0x{value:04X}",
                        'value_binary': f"{value:016b}"
                    }
                })
            else:
                response['error'] = f"Failed to write holding register {address}"
                
        else:
            response['error'] = f"Unknown command: {cmd}"
            print_command_help()
            
    except Exception as e:
        response['error'] = str(e)
        
    finally:
        if 'modbus' in locals():
            modbus.disconnect()
            
        # Output response as JSON
        output_json(response)
        
        # Return success status
        return response.get('success', False)


def main():
    """Main entry point for the command line interface"""
    args = parse_args()
    success = command_line_mode(args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

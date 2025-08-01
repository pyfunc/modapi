"""
modapi.api.shell - Interactive shell for Modbus communication
"""

import json
import logging
from typing import Dict, Any, Optional

from .rtu import ModbusRTU, test_rtu_connection
from .tcp import ModbusTCP, test_tcp_connection, scan_modbus_network

def auto_detect_modbus_port():
    """Auto-detect Modbus RTU port"""
    from ..api.rtu import find_serial_ports, test_modbus_port
    ports = find_serial_ports()
    for port in ports:
        if test_modbus_port(port):
            return port
    return None

# Configure logging
logger = logging.getLogger(__name__)

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
  modapi [options] <command> [args...]

Options:
  -v, --verbose    Enable verbose logging output
  -h, --help       Show this help message
  -p, --port PORT  Specify Modbus port (default: auto-detect or from .env)
  -b, --baud BAUD  Specify baud rate (default: from .env or 9600)
  -t, --timeout T  Specify timeout in seconds (default: from .env or 1.0)

Commands:
  cmd wc <address> <value> [unit]  Write coil (value: 0/1, true/false, on/off)
  cmd rc <address> <count> [unit]  Read coils
  cmd ri <address> <count> [unit]  Read discrete inputs
  cmd rh <address> <count> [unit]  Read holding registers
  cmd wh <address> <value> [unit]  Write holding register
  shell                            Start interactive mode
  scan                             Scan for Modbus devices

Examples:
  modapi -v cmd rc 0 8 1        # Read 8 coils with verbose logging
  modapi cmd wc 0 on 1          # Turn on coil at address 0, unit 1
  modapi cmd rh 0 5 1           # Read 5 holding registers
  modapi -p /dev/ttyACM0 cmd wc 0 1  # Specify port explicitly
""")

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
        print("Auto-detecting Modbus port...")
        port = auto_detect_modbus_port()
        if not port:
            print("Error: Could not auto-detect Modbus port. Please specify with --port")
            return
    
    # Initialize client
    client = ModbusRTU(
        port=port,
        baudrate=baudrate or 9600,
        timeout=timeout or 1.0
    )
    
    if not client.connect():
        print(f"Error: Could not connect to {port}")
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

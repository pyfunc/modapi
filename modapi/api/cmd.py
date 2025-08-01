"""
modapi.api.cmd - Direct command execution for Modbus communication
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple

from modapi.rtu import ModbusRTU, test_rtu_connection

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
        'error': None,
        'port': None,  # Add port field to response
        'baudrate': None  # Add baudrate field to response
    }

def output_json(data: Dict[str, Any]):
    """
    Output data as formatted JSON
    
    Args:
        data: Data to output
    """
    print(json.dumps(data, indent=2))

def execute_command(command: str, args: List[str], port: Optional[str] = None,
                   baudrate: Optional[int] = None, timeout: Optional[float] = None,
                   verbose: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """
    Execute a Modbus command
    
    Args:
        command: Command to execute (rc, wc, ri, rh, wh)
        args: Command arguments
        port: Modbus serial port (default: auto-detect)
        baudrate: Baud rate (default: from .env or 9600)
        timeout: Timeout in seconds (default: from .env or 1.0)
        verbose: Enable verbose logging
        
    Returns:
        Tuple of (success, response_data)
    """
    # Create response for JSON output
    response = create_response(f"{command} {' '.join(args)}")
    response['verbose'] = verbose
    
    try:
        # Use the configured port or auto-detect
        if not port:
            port_found, _ = test_rtu_connection()
            if port_found:
                port = '/dev/ttyACM0'  # Default port from test_rtu_connection
                response['port_source'] = 'auto_detected'
            else:
                response['error'] = "Could not auto-detect Modbus port"
                return False, response
        else:
            response['port_source'] = 'command_line'
            
        # Add port to response
        response['port'] = port
        
        # Initialize modbus client
        modbus = ModbusRTU(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            verbose=verbose
        )
        
        # Add baudrate to response
        response['baudrate'] = modbus.baudrate
        
        if not modbus.connect():
            response['error'] = f"Failed to connect to port {port}"
            return False, response
            
        # Process commands
        cmd = command.lower()
        response['operation'] = cmd
        
        try:
            if cmd == 'rc':  # Read coils
                if len(args) < 2:
                    response['error'] = "Usage: rc <address> <count> [unit]"
                    return False, response
                    
                address = int(args[0])
                count = int(args[1])
                unit = int(args[2]) if len(args) > 2 else 1
                
                response.update({
                    'address': address,
                    'count': count,
                    'unit': unit,
                    'register_type': 'coil'
                })
                
                result = modbus.read_coils(address, count, unit=unit)  # Use unit as kwarg
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
                if len(args) < 2:
                    response['error'] = "Usage: wc <address> <value> [unit]"
                    return False, response
                    
                address = int(args[0])
                value = args[1].lower() in ('1', 'true', 'on')
                unit = int(args[2]) if len(args) > 2 else 1
                
                response.update({
                    'address': address,
                    'value': value,
                    'value_display': 'ON' if value else 'OFF',
                    'unit': unit,
                    'register_type': 'coil'
                })
                
                if modbus.write_coil(address, value, unit=unit):  # Use unit as kwarg
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
                if len(args) < 2:
                    response['error'] = "Usage: ri <address> <count> [unit]"
                    return False, response
                    
                address = int(args[0])
                count = int(args[1])
                unit = int(args[2]) if len(args) > 2 else 1
                
                response.update({
                    'address': address,
                    'count': count,
                    'unit': unit,
                    'register_type': 'discrete_input'
                })
                
                result = modbus.read_discrete_inputs(address, count, unit=unit)  # Use unit as kwarg
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
                if len(args) < 2:
                    response['error'] = "Usage: rh <address> <count> [unit]"
                    return False, response
                    
                address = int(args[0])
                count = int(args[1])
                unit = int(args[2]) if len(args) > 2 else 1
                
                response.update({
                    'address': address,
                    'count': count,
                    'unit': unit,
                    'register_type': 'holding_register'
                })
                
                result = modbus.read_holding_registers(address, count, unit=unit)  # Use unit as kwarg
                if result is not None:
                    response.update({
                        'success': True,
                        'data': {
                            'address': address,
                            'count': count,
                            'values': result,
                            'values_hex': [hex(v) for v in result],
                            'values_bin': [bin(v) for v in result]
                        },
                        'message': f"Read {count} holding registers starting at address {address}"
                    })
                else:
                    response['error'] = "Failed to read holding registers"
                    
            elif cmd == 'wh':  # Write holding register
                if len(args) < 2:
                    response['error'] = "Usage: wh <address> <value> [unit]"
                    return False, response
                    
                address = int(args[0])
                value = int(args[1])
                unit = int(args[2]) if len(args) > 2 else 1
                
                response.update({
                    'address': address,
                    'value': value,
                    'value_hex': hex(value),
                    'value_bin': bin(value),
                    'unit': unit,
                    'register_type': 'holding_register'
                })
                
                if modbus.write_register(address, value, unit=unit):  # Use unit as kwarg
                    response.update({
                        'success': True,
                        'message': f"Register {address} set to {value}",
                        'data': {
                            'address': address,
                            'value': value,
                            'value_hex': hex(value),
                            'value_bin': bin(value)
                        }
                    })
                else:
                    response['error'] = f"Failed to write register {address}"
                    
            else:
                response['error'] = f"Unknown command: {cmd}"
                return False, response
                
        finally:
            if 'modbus' in locals() and hasattr(modbus, 'disconnect'):
                modbus.disconnect()
                
        # Return success status
        return response.get('success', False), response
        
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        response['error'] = str(e)
        return False, response

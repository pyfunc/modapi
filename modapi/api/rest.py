"""
modapi.api.rest - REST API implementation for Modbus communication
"""

import logging
from typing import Optional

from ..api.rtu import ModbusRTU, test_rtu_connection
from ..api.ws import ModbusConnectionPool

# Configure logging
logger = logging.getLogger(__name__)

# Try to import Flask for REST API
try:
    from flask import Flask, request, jsonify
except ImportError:
    logger.warning("Flask not installed. REST API will not be available.")
    Flask = None

def require_flask(func):
    """Decorator to check if Flask is available"""
    def wrapper(*args, **kwargs):
        if Flask is None:
            raise ImportError(
                "Flask is required for REST API. Install with: pip install flask"
            )
        return func(*args, **kwargs)
    return wrapper

@require_flask
def create_rest_app(port: Optional[str] = None, 
                   baudrate: Optional[int] = None,
                   timeout: Optional[float] = None,
                   host: str = '0.0.0.0',
                   api_port: int = 5000,
                   debug: bool = False) -> Flask:
    """
    Create Flask application for REST API
    
    Args:
        port: Modbus serial port (default: auto-detect)
        baudrate: Baud rate (default: from .env or 9600)
        timeout: Timeout in seconds (default: from .env or 1.0)
        host: Host to bind the API server (default: 0.0.0.0)
        api_port: Port to bind the API server (default: 5000)
        debug: Enable debug mode (default: False)
        
    Returns:
        Flask application
    """
    app = Flask(__name__)
    
    # Configure logging
    if not debug:
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
    
    # Create connection pool for persistent connections
    connection_pool = ModbusConnectionPool()
    
    # Determine port to use
    if port is None:
        # Try to auto-detect port
        port_found, _ = test_rtu_connection()
        if port_found:
            port = '/dev/ttyACM0'  # Default port from test_rtu_connection
        else:
            logger.error("No Modbus device found! REST API will not work correctly.")
            port = '/dev/ttyACM0'  # Use default even if not found
    
    # Store connection parameters for later use
    modbus_params = {
        'port': port,
        'baudrate': baudrate or DEFAULT_BAUDRATE,
        'timeout': timeout or 1.0
    }
    
    # Remove the before_request handler that was connecting/disconnecting
    # We'll use the connection pool instead to get a persistent connection
    
    @app.after_request
    def add_cors_headers(response):
        """Add CORS headers to allow cross-origin requests"""
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    @app.route('/api/status', methods=['GET'])
    def get_status():
        """Get Modbus connection status"""
        try:
            # Get a connection from the pool to check status
            client = connection_pool.get_connection(**modbus_params)
            is_connected = client.is_connected()
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            return jsonify({
                'status': 'connected' if is_connected else 'disconnected',
                'port': modbus_params['port'],
                'baudrate': modbus_params['baudrate'],
                'connection_type': 'persistent_pool'
            })
        except Exception as e:
            logger.error(f"Error checking connection status: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e),
                'port': modbus_params['port'],
                'baudrate': modbus_params['baudrate']
            }), 500
    
    @app.route('/api/coils/<int:address>', methods=['GET'])
    def read_coil(address):
        """Read single coil"""
        try:
            unit_id = int(request.args.get('unit', 1))
            
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Read the coil
            result = client.read_coils(unit_id=unit_id, address=address, count=1)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if result is None:
                return jsonify({'error': 'Failed to read coil'}), 500
                
            return jsonify({'value': result[0] if result else None})
        except Exception as e:
            logger.error(f"Error reading coil {address}: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/coils/<int:address>/<int:count>', methods=['GET'])
    def read_coils(address, count):
        """Read multiple coils"""
        unit = request.args.get('unit', default=1, type=int)
        try:
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Read the coils
            result = client.read_coils(unit_id=unit, address=address, count=count)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if result is None:
                return jsonify({'error': 'Failed to read coils'}), 500
                
            return jsonify({
                'address': address,
                'count': count,
                'values': result,
                'values_dict': {str(i): val for i, val in enumerate(result, address)},
                'unit': unit
            })
        except Exception as e:
            logger.error(f"Error reading coils {address}-{address+count-1}: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/coils/<int:address>', methods=['POST', 'PUT'])
    def write_coil(address):
        """Write single coil"""
        try:
            data = request.get_json()
            if data is None:
                return jsonify({'error': 'Invalid JSON data'}), 400
                
            value = data.get('value')
            if value is None:
                return jsonify({'error': 'Missing value parameter'}), 400
                
            unit_id = int(data.get('unit', 1))
            value = bool(value)
            
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Write the coil
            result = client.write_single_coil(unit_id=unit_id, address=address, value=value)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if not result:
                return jsonify({'error': 'Failed to write coil'}), 500
                
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Error writing coil {address}: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/toggle/<int:address>', methods=['POST'])
    def toggle_coil(address):
        """Toggle coil state"""
        try:
            # Try to get data from JSON, but don't require it
            data = request.get_json(silent=True) or {}
            
            # Get unit from JSON data or query parameter
            unit_id = int(data.get('unit', request.args.get('unit', default=1, type=int)))
            
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Read current state
            result = client.read_coils(unit_id=unit_id, address=address, count=1)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if result is None:
                return jsonify({'error': f'Failed to read coil {address}'}), 500
                
            # Toggle value
            current_value = result[0]
            new_value = not current_value
            
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Write new value
            result = client.write_single_coil(unit_id=unit_id, address=address, value=new_value)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if not result:
                return jsonify({'error': f'Failed to toggle coil {address}'}), 500
                
            return jsonify({
                'success': True,
                'address': address,
                'previous_value': current_value,
                'previous_value_display': 'ON' if current_value else 'OFF',
                'new_value': new_value,
                'new_value_display': 'ON' if new_value else 'OFF',
                'unit': unit_id
            })
        except Exception as e:
            logger.error(f"Error toggling coil {address}: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/discrete_inputs/<int:address>', methods=['GET'])
    def read_discrete_input(address):
        """Read single discrete input"""
        try:
            unit_id = int(request.args.get('unit', 1))
            
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Read the discrete input
            result = client.read_discrete_inputs(unit_id=unit_id, address=address, count=1)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if result is None:
                return jsonify({'error': 'Failed to read discrete input'}), 500
                
            return jsonify({
                'address': address,
                'value': result[0],
                'value_display': 'ON' if result[0] else 'OFF',
                'unit': unit_id
            })
        except Exception as e:
            logger.error(f"Error reading discrete input {address}: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/discrete_inputs/<int:address>/<int:count>', methods=['GET'])
    def read_discrete_inputs(address, count):
        """Read multiple discrete inputs"""
        unit = request.args.get('unit', default=1, type=int)
        try:
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Read the discrete inputs
            result = client.read_discrete_inputs(unit_id=unit, address=address, count=count)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if result is None:
                return jsonify({'error': 'Failed to read discrete inputs'}), 500
                
            return jsonify({
                'address': address,
                'count': count,
                'values': result,
                'values_dict': {str(i): val for i, val in enumerate(result, address)},
                'unit': unit
            })
        except Exception as e:
            logger.error(f"Error reading discrete inputs {address}-{address+count-1}: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/holding_registers/<int:address>', methods=['GET'])
    def read_holding_register(address):
        """Read single holding register"""
        try:
            unit_id = int(request.args.get('unit', 1))
            
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Read the holding register
            result = client.read_holding_registers(unit_id=unit_id, address=address, count=1)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if result is None:
                return jsonify({'error': 'Failed to read holding register'}), 500
                
            return jsonify({
                'address': address,
                'value': result[0],
                'value_hex': hex(result[0]),
                'unit': unit_id
            })
        except Exception as e:
            logger.error(f"Error reading holding register {address}: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/holding_registers/<int:address>/<int:count>', methods=['GET'])
    def read_holding_registers(address, count):
        """Read multiple holding registers"""
        unit = request.args.get('unit', default=1, type=int)
        try:
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Read the holding registers
            result = client.read_holding_registers(unit_id=unit, address=address, count=count)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if result is None:
                return jsonify({'error': 'Failed to read holding registers'}), 500
                
            return jsonify({
                'address': address,
                'count': count,
                'values': result,
                'values_hex': [hex(v) for v in result],
                'unit': unit
            })
        except Exception as e:
            logger.error(f"Error reading holding registers {address}-{address+count-1}: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/holding_registers/<int:address>', methods=['POST', 'PUT'])
    def write_holding_register(address):
        """Write single holding register"""
        try:
            data = request.get_json()
            if data is None:
                return jsonify({'error': 'Invalid JSON data'}), 400
                
            value = data.get('value')
            if value is None:
                return jsonify({'error': 'Missing value parameter'}), 400
                
            unit_id = int(data.get('unit', 1))
            value = int(value)
            
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Write the holding register
            result = client.write_register(unit_id=unit_id, address=address, value=value)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if not result:
                return jsonify({'error': f'Failed to write register {address}'}), 500
                
            return jsonify({
                'success': True,
                'address': address,
                'value': value,
                'value_hex': hex(value),
                'unit': unit_id
            })
        except Exception as e:
            logger.error(f"Error writing holding register {address}: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/input_registers/<int:address>', methods=['GET'])
    def read_input_register(address):
        """Read single input register"""
        try:
            unit_id = int(request.args.get('unit', 1))
            
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Read the input register
            result = client.read_input_registers(unit_id=unit_id, address=address, count=1)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if result is None:
                return jsonify({'error': 'Failed to read input register'}), 500
                
            return jsonify({
                'address': address,
                'value': result[0],
                'value_hex': hex(result[0]),
                'unit': unit_id
            })
        except Exception as e:
            logger.error(f"Error reading input register {address}: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/input_registers/<int:address>/<int:count>', methods=['GET'])
    def read_input_registers(address, count):
        """Read multiple input registers"""
        try:
            unit = request.args.get('unit', default=1, type=int)
            
            # Get a connection from the pool
            client = connection_pool.get_connection(**modbus_params)
            
            # Read the input registers
            result = client.read_input_registers(unit_id=unit, address=address, count=count)
            
            # Release the connection back to the pool
            connection_pool.release_connection(modbus_params['port'], modbus_params['baudrate'])
            
            if result is None:
                return jsonify({'error': 'Failed to read input registers'}), 500
                
            return jsonify({
                'address': address,
                'count': count,
                'values': result,
                'values_hex': [hex(v) for v in result],
                'unit': unit
            })
        except Exception as e:
            logger.error(f"Error reading input registers {address}-{address+count-1}: {e}")
            return jsonify({'error': str(e)}), 500
    
    return app

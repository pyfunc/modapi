"""
modapi - REST and MQTT API implementations
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from functools import wraps

from .client import ModbusClient, auto_detect_modbus_port

# Configure logging
logger = logging.getLogger(__name__)

# Try to import Flask for REST API
try:
    from flask import Flask, request, jsonify, Response
except ImportError:
    logger.warning("Flask not installed. REST API will not be available.")
    Flask = None

# Try to import Paho MQTT for MQTT API
try:
    import paho.mqtt.client as mqtt
except ImportError:
    logger.warning("Paho MQTT not installed. MQTT API will not be available.")
    mqtt = None


def require_flask(func):
    """Decorator to check if Flask is available"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if Flask is None:
            raise ImportError(
                "Flask is required for REST API. Install with: pip install flask"
            )
        return func(*args, **kwargs)
    return wrapper


def require_mqtt(func):
    """Decorator to check if Paho MQTT is available"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if mqtt is None:
            raise ImportError(
                "Paho MQTT is required for MQTT API. Install with: pip install paho-mqtt"
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
    
    # Create Modbus client
    if port is None:
        port = auto_detect_modbus_port()
        if port is None:
            logger.error("No Modbus device found! REST API will not work correctly.")
    
    modbus_client = ModbusClient(port=port, baudrate=baudrate, timeout=timeout)
    
    @app.before_request
    def connect_modbus():
        """Connect to Modbus device before each request"""
        if not hasattr(modbus_client, '_connected') or not modbus_client._connected:
            modbus_client.connect()
    
    @app.after_request
    def add_cors_headers(response):
        """Add CORS headers to allow cross-origin requests"""
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    @app.route('/api/status', methods=['GET'])
    def get_status():
        """Get Modbus connection status"""
        return jsonify({
            'connected': hasattr(modbus_client, '_connected') and modbus_client._connected,
            'port': modbus_client.port,
            'baudrate': modbus_client.baudrate
        })
    
    @app.route('/api/coils/<int:address>', methods=['GET'])
    def read_coil(address):
        """Read single coil"""
        unit = request.args.get('unit', default=1, type=int)
        result = modbus_client.read_coils(address, 1, unit)
        
        if result is None:
            return jsonify({'error': 'Failed to read coil'}), 500
            
        return jsonify({
            'address': address,
            'value': result[0],
            'value_display': 'ON' if result[0] else 'OFF',
            'unit': unit
        })
    
    @app.route('/api/coils/<int:address>/<int:count>', methods=['GET'])
    def read_coils(address, count):
        """Read multiple coils"""
        unit = request.args.get('unit', default=1, type=int)
        result = modbus_client.read_coils(address, count, unit)
        
        if result is None:
            return jsonify({'error': 'Failed to read coils'}), 500
            
        return jsonify({
            'address': address,
            'count': count,
            'values': result,
            'values_dict': {str(i): val for i, val in enumerate(result, address)},
            'unit': unit
        })
    
    @app.route('/api/coils/<int:address>', methods=['POST'])
    def write_coil(address):
        """Write single coil"""
        data = request.get_json()
        if data is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
            
        if 'value' not in data:
            return jsonify({'error': 'Missing value parameter'}), 400
            
        # Parse value (accept boolean, integer, or string)
        value = data['value']
        if isinstance(value, str):
            value = value.lower() in ('1', 'true', 'on')
        else:
            value = bool(value)
            
        unit = data.get('unit', 1)
        
        if modbus_client.write_coil(address, value, unit):
            return jsonify({
                'success': True,
                'address': address,
                'value': value,
                'value_display': 'ON' if value else 'OFF',
                'unit': unit
            })
        else:
            return jsonify({'error': f'Failed to write coil {address}'}), 500
    
    @app.route('/api/toggle/<int:address>', methods=['POST'])
    def toggle_coil(address):
        """Toggle coil state"""
        unit = request.args.get('unit', default=1, type=int)
        
        # Read current state
        result = modbus_client.read_coils(address, 1, unit)
        if result is None:
            return jsonify({'error': 'Failed to read coil'}), 500
            
        # Toggle state
        current_state = result[0]
        new_state = not current_state
        
        if modbus_client.write_coil(address, new_state, unit):
            return jsonify({
                'success': True,
                'address': address,
                'previous_value': current_state,
                'previous_display': 'ON' if current_state else 'OFF',
                'value': new_state,
                'value_display': 'ON' if new_state else 'OFF',
                'unit': unit
            })
        else:
            return jsonify({'error': f'Failed to toggle coil {address}'}), 500
    
    @app.route('/api/discrete_inputs/<int:address>/<int:count>', methods=['GET'])
    def read_discrete_inputs(address, count):
        """Read discrete inputs"""
        unit = request.args.get('unit', default=1, type=int)
        result = modbus_client.read_discrete_inputs(address, count, unit)
        
        if result is None:
            return jsonify({'error': 'Failed to read discrete inputs'}), 500
            
        return jsonify({
            'address': address,
            'count': count,
            'values': result,
            'values_dict': {str(i): val for i, val in enumerate(result, address)},
            'unit': unit
        })
    
    @app.route('/api/holding_registers/<int:address>/<int:count>', methods=['GET'])
    def read_holding_registers(address, count):
        """Read holding registers"""
        unit = request.args.get('unit', default=1, type=int)
        result = modbus_client.read_holding_registers(address, count, unit)
        
        if result is None:
            return jsonify({'error': 'Failed to read holding registers'}), 500
            
        return jsonify({
            'address': address,
            'count': count,
            'values': result,
            'values_dict': {str(i): val for i, val in enumerate(result, address)},
            'hex_values': [f"0x{val:04X}" for val in result],
            'unit': unit
        })
    
    @app.route('/api/holding_registers/<int:address>', methods=['POST'])
    def write_holding_register(address):
        """Write holding register"""
        data = request.get_json()
        if data is None:
            return jsonify({'error': 'Invalid JSON data'}), 400
            
        if 'value' not in data:
            return jsonify({'error': 'Missing value parameter'}), 400
            
        value = int(data['value'])
        unit = data.get('unit', 1)
        
        if modbus_client.write_register(address, value, unit):
            return jsonify({
                'success': True,
                'address': address,
                'value': value,
                'value_hex': f"0x{value:04X}",
                'unit': unit
            })
        else:
            return jsonify({'error': f'Failed to write register {address}'}), 500
    
    @app.route('/api/input_registers/<int:address>/<int:count>', methods=['GET'])
    def read_input_registers(address, count):
        """Read input registers"""
        unit = request.args.get('unit', default=1, type=int)
        result = modbus_client.read_input_registers(address, count, unit)
        
        if result is None:
            return jsonify({'error': 'Failed to read input registers'}), 500
            
        return jsonify({
            'address': address,
            'count': count,
            'values': result,
            'values_dict': {str(i): val for i, val in enumerate(result, address)},
            'hex_values': [f"0x{val:04X}" for val in result],
            'unit': unit
        })
    
    @app.route('/api/scan', methods=['GET'])
    def scan_devices():
        """Scan for Modbus devices"""
        port = auto_detect_modbus_port()
        return jsonify({
            'success': port is not None,
            'port': port
        })
    
    @app.route('/api/docs', methods=['GET'])
    def get_docs():
        """Get API documentation"""
        return jsonify({
            'endpoints': [
                {
                    'path': '/api/status',
                    'method': 'GET',
                    'description': 'Get Modbus connection status'
                },
                {
                    'path': '/api/coils/<address>',
                    'method': 'GET',
                    'description': 'Read single coil',
                    'params': ['unit (query, optional)']
                },
                {
                    'path': '/api/coils/<address>/<count>',
                    'method': 'GET',
                    'description': 'Read multiple coils',
                    'params': ['unit (query, optional)']
                },
                {
                    'path': '/api/coils/<address>',
                    'method': 'POST',
                    'description': 'Write single coil',
                    'body': {'value': 'boolean/int/string', 'unit': 'int (optional)'}
                },
                {
                    'path': '/api/toggle/<address>',
                    'method': 'POST',
                    'description': 'Toggle coil state',
                    'params': ['unit (query, optional)']
                },
                {
                    'path': '/api/discrete_inputs/<address>/<count>',
                    'method': 'GET',
                    'description': 'Read discrete inputs',
                    'params': ['unit (query, optional)']
                },
                {
                    'path': '/api/holding_registers/<address>/<count>',
                    'method': 'GET',
                    'description': 'Read holding registers',
                    'params': ['unit (query, optional)']
                },
                {
                    'path': '/api/holding_registers/<address>',
                    'method': 'POST',
                    'description': 'Write holding register',
                    'body': {'value': 'int', 'unit': 'int (optional)'}
                },
                {
                    'path': '/api/input_registers/<address>/<count>',
                    'method': 'GET',
                    'description': 'Read input registers',
                    'params': ['unit (query, optional)']
                },
                {
                    'path': '/api/scan',
                    'method': 'GET',
                    'description': 'Scan for Modbus devices'
                }
            ]
        })
    
    def run_server():
        """Run the Flask server"""
        app.run(host=host, port=api_port, debug=debug)
    
    # Add run method to app
    app.run_server = run_server
    
    return app


@require_mqtt
def start_mqtt_broker(port: Optional[str] = None,
                     baudrate: Optional[int] = None,
                     timeout: Optional[float] = None,
                     mqtt_broker: str = 'localhost',
                     mqtt_port: int = 1883,
                     mqtt_topic_prefix: str = 'modbus',
                     client_id: str = 'modapi',
                     username: Optional[str] = None,
                     password: Optional[str] = None):
    """
    Start MQTT client for Modbus API
    
    Args:
        port: Modbus serial port (default: auto-detect)
        baudrate: Baud rate (default: from .env or 9600)
        timeout: Timeout in seconds (default: from .env or 1.0)
        mqtt_broker: MQTT broker address (default: localhost)
        mqtt_port: MQTT broker port (default: 1883)
        mqtt_topic_prefix: Prefix for MQTT topics (default: modbus)
        client_id: MQTT client ID (default: modapi)
        username: MQTT username (default: None)
        password: MQTT password (default: None)
    """
    # Create Modbus client
    if port is None:
        port = auto_detect_modbus_port()
        if port is None:
            logger.error("No Modbus device found! MQTT API will not work correctly.")
            return None
    
    modbus_client = ModbusClient(port=port, baudrate=baudrate, timeout=timeout)
    if not modbus_client.connect():
        logger.error(f"Failed to connect to Modbus device on {port}")
        return None
    
    # Create MQTT client
    client = mqtt.Client(client_id=client_id)
    
    # Set username and password if provided
    if username and password:
        client.username_pw_set(username, password)
    
    # Define callback for when the client receives a CONNACK response from the server
    def on_connect(client, userdata, flags, rc):
        logger.info(f"Connected to MQTT broker with result code {rc}")
        
        # Subscribe to command topics
        client.subscribe(f"{mqtt_topic_prefix}/command/#")
        
        # Publish connection status
        client.publish(
            f"{mqtt_topic_prefix}/status",
            json.dumps({
                'connected': True,
                'port': modbus_client.port,
                'baudrate': modbus_client.baudrate
            }),
            qos=1,
            retain=True
        )
    
    # Define callback for when a PUBLISH message is received from the server
    def on_message(client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        logger.info(f"Received message on topic {topic}: {payload}")
        
        # Parse command from topic
        # Format: modbus/command/<command_type>/<address>[/<count>]
        parts = topic.split('/')
        if len(parts) < 4:
            logger.error(f"Invalid topic format: {topic}")
            return
            
        command_type = parts[2]
        address = int(parts[3])
        
        try:
            # Parse payload as JSON
            data = json.loads(payload)
            unit = data.get('unit', 1)
            
            response_topic = topic.replace('command', 'response')
            
            if command_type == 'read_coil':
                count = int(parts[4]) if len(parts) > 4 else 1
                result = modbus_client.read_coils(address, count, unit)
                
                if result is not None:
                    response = {
                        'success': True,
                        'address': address,
                        'count': count,
                        'values': result,
                        'values_dict': {str(i): val for i, val in enumerate(result, address)},
                        'unit': unit
                    }
                else:
                    response = {'error': 'Failed to read coils'}
                    
                client.publish(response_topic, json.dumps(response), qos=1)
                
            elif command_type == 'write_coil':
                value = data.get('value')
                if value is None:
                    logger.error("Missing value parameter")
                    return
                    
                # Parse value (accept boolean, integer, or string)
                if isinstance(value, str):
                    value = value.lower() in ('1', 'true', 'on')
                else:
                    value = bool(value)
                    
                if modbus_client.write_coil(address, value, unit):
                    response = {
                        'success': True,
                        'address': address,
                        'value': value,
                        'value_display': 'ON' if value else 'OFF',
                        'unit': unit
                    }
                else:
                    response = {'error': f'Failed to write coil {address}'}
                    
                client.publish(response_topic, json.dumps(response), qos=1)
                
            elif command_type == 'toggle_coil':
                # Read current state
                result = modbus_client.read_coils(address, 1, unit)
                if result is None:
                    response = {'error': 'Failed to read coil'}
                    client.publish(response_topic, json.dumps(response), qos=1)
                    return
                    
                # Toggle state
                current_state = result[0]
                new_state = not current_state
                
                if modbus_client.write_coil(address, new_state, unit):
                    response = {
                        'success': True,
                        'address': address,
                        'previous_value': current_state,
                        'previous_display': 'ON' if current_state else 'OFF',
                        'value': new_state,
                        'value_display': 'ON' if new_state else 'OFF',
                        'unit': unit
                    }
                else:
                    response = {'error': f'Failed to toggle coil {address}'}
                    
                client.publish(response_topic, json.dumps(response), qos=1)
                
            elif command_type == 'read_discrete_input':
                count = int(parts[4]) if len(parts) > 4 else 1
                result = modbus_client.read_discrete_inputs(address, count, unit)
                
                if result is not None:
                    response = {
                        'success': True,
                        'address': address,
                        'count': count,
                        'values': result,
                        'values_dict': {str(i): val for i, val in enumerate(result, address)},
                        'unit': unit
                    }
                else:
                    response = {'error': 'Failed to read discrete inputs'}
                    
                client.publish(response_topic, json.dumps(response), qos=1)
                
            elif command_type == 'read_holding_register':
                count = int(parts[4]) if len(parts) > 4 else 1
                result = modbus_client.read_holding_registers(address, count, unit)
                
                if result is not None:
                    response = {
                        'success': True,
                        'address': address,
                        'count': count,
                        'values': result,
                        'values_dict': {str(i): val for i, val in enumerate(result, address)},
                        'hex_values': [f"0x{val:04X}" for val in result],
                        'unit': unit
                    }
                else:
                    response = {'error': 'Failed to read holding registers'}
                    
                client.publish(response_topic, json.dumps(response), qos=1)
                
            elif command_type == 'write_holding_register':
                value = data.get('value')
                if value is None:
                    logger.error("Missing value parameter")
                    return
                    
                value = int(value)
                
                if modbus_client.write_register(address, value, unit):
                    response = {
                        'success': True,
                        'address': address,
                        'value': value,
                        'value_hex': f"0x{value:04X}",
                        'unit': unit
                    }
                else:
                    response = {'error': f'Failed to write register {address}'}
                    
                client.publish(response_topic, json.dumps(response), qos=1)
                
            elif command_type == 'read_input_register':
                count = int(parts[4]) if len(parts) > 4 else 1
                result = modbus_client.read_input_registers(address, count, unit)
                
                if result is not None:
                    response = {
                        'success': True,
                        'address': address,
                        'count': count,
                        'values': result,
                        'values_dict': {str(i): val for i, val in enumerate(result, address)},
                        'hex_values': [f"0x{val:04X}" for val in result],
                        'unit': unit
                    }
                else:
                    response = {'error': 'Failed to read input registers'}
                    
                client.publish(response_topic, json.dumps(response), qos=1)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            client.publish(
                topic.replace('command', 'error'),
                json.dumps({'error': str(e)}),
                qos=1
            )
    
    # Define callback for when the client disconnects
    def on_disconnect(client, userdata, rc):
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")
        
        # Publish disconnection status
        try:
            client.publish(
                f"{mqtt_topic_prefix}/status",
                json.dumps({'connected': False}),
                qos=1,
                retain=True
            )
        except:
            pass
            
        # Disconnect Modbus client
        modbus_client.disconnect()
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Connect to MQTT broker
    try:
        client.connect(mqtt_broker, mqtt_port, 60)
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        modbus_client.disconnect()
        return None
    
    # Start the loop
    client.loop_start()
    
    logger.info(f"MQTT client started, listening on {mqtt_topic_prefix}/command/#")
    
    return client

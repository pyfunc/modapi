"""
modapi.api.mqtt - MQTT API implementation for Modbus communication
"""

import json
import logging
import time
from typing import Optional, Dict, Any

from ..client import ModbusClient, auto_detect_modbus_port

# Configure logging
logger = logging.getLogger(__name__)

# Try to import Paho MQTT for MQTT API
try:
    import paho.mqtt.client as mqtt
except ImportError:
    logger.warning("Paho MQTT not installed. MQTT API will not be available.")
    mqtt = None

def require_mqtt(func):
    """Decorator to check if Paho MQTT is available"""
    def wrapper(*args, **kwargs):
        if mqtt is None:
            raise ImportError(
                "Paho MQTT is required for MQTT API. Install with: pip install paho-mqtt"
            )
        return func(*args, **kwargs)
    return wrapper

@require_mqtt
def start_mqtt_broker(port: Optional[str] = None,
                     baudrate: Optional[int] = None,
                     timeout: Optional[float] = None,
                     broker: str = 'localhost',
                     mqtt_port: int = 1883,
                     topic_prefix: str = 'modbus',
                     client_id: str = 'modapi',
                     username: Optional[str] = None,
                     password: Optional[str] = None):
    """
    Start MQTT client for Modbus API
    
    Args:
        port: Modbus serial port (default: auto-detect)
        baudrate: Baud rate (default: from .env or 9600)
        timeout: Timeout in seconds (default: from .env or 1.0)
        broker: MQTT broker address (default: localhost)
        mqtt_port: MQTT broker port (default: 1883)
        topic_prefix: Prefix for MQTT topics (default: modbus)
        client_id: MQTT client ID (default: modapi)
        username: MQTT username (default: None)
        password: MQTT password (default: None)
    """
    # Create Modbus client
    if port is None:
        port = auto_detect_modbus_port()
        if port is None:
            logger.error("No Modbus device found! MQTT API will not work correctly.")
    
    modbus_client = ModbusClient(port=port, baudrate=baudrate, timeout=timeout)
    
    # Create MQTT client
    client = mqtt.Client(client_id=client_id)
    
    # Set username and password if provided
    if username is not None and password is not None:
        client.username_pw_set(username, password)
    
    # Set up callbacks
    def on_connect(client, userdata, flags, rc):
        """Callback for when the client connects to the broker"""
        logger.info(f"Connected to MQTT broker with result code {rc}")
        
        # Subscribe to command topics
        client.subscribe(f"{topic_prefix}/command/#")
        client.subscribe(f"{topic_prefix}/request/#")
        
        # Publish connection status
        client.publish(f"{topic_prefix}/status", json.dumps({
            'status': 'connected',
            'port': port,
            'baudrate': baudrate,
            'timestamp': time.time()
        }))
    
    def on_message(client, userdata, msg):
        """Callback for when a message is received from the broker"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        logger.debug(f"Received message on topic {topic}: {payload}")
        
        try:
            # Parse JSON payload
            data = json.loads(payload)
            
            # Process command
            if topic.startswith(f"{topic_prefix}/command/"):
                process_command(client, topic, data)
            elif topic.startswith(f"{topic_prefix}/request/"):
                process_request(client, topic, data)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload: {payload}")
            client.publish(f"{topic_prefix}/error", json.dumps({
                'error': 'Invalid JSON payload',
                'topic': topic,
                'payload': payload
            }))
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            client.publish(f"{topic_prefix}/error", json.dumps({
                'error': str(e),
                'topic': topic
            }))
    
    def process_command(client, topic, data):
        """Process a command message"""
        # Extract command from topic
        command = topic.split('/')[-1]
        
        # Get parameters from data
        address = data.get('address')
        value = data.get('value')
        unit = data.get('unit', 1)
        
        if address is None:
            client.publish(f"{topic_prefix}/error", json.dumps({
                'error': 'Missing address parameter',
                'command': command
            }))
            return
        
        # Connect to Modbus device if not connected
        if not modbus_client.is_connected():
            modbus_client.connect()
        
        # Process command
        result: Dict[str, Any] = {
            'command': command,
            'address': address,
            'unit': unit,
            'timestamp': time.time()
        }
        
        if command == 'write_coil':
            if value is None:
                client.publish(f"{topic_prefix}/error", json.dumps({
                    'error': 'Missing value parameter',
                    'command': command
                }))
                return
                
            # Parse value (accept boolean, integer, or string)
            if isinstance(value, str):
                value = value.lower() in ('1', 'true', 'on')
            else:
                value = bool(value)
                
            success = modbus_client.write_coil(address, value, unit=unit)
            result.update({
                'success': success,
                'value': value,
                'value_display': 'ON' if value else 'OFF'
            })
            
        elif command == 'write_register':
            if value is None:
                client.publish(f"{topic_prefix}/error", json.dumps({
                    'error': 'Missing value parameter',
                    'command': command
                }))
                return
                
            value = int(value)
            success = modbus_client.write_register(address, value, unit=unit)
            result.update({
                'success': success,
                'value': value,
                'value_hex': f"0x{value:04X}"
            })
            
        elif command == 'toggle':
            # Read current state
            coil_value = modbus_client.read_coils(address, 1, unit=unit)
            if coil_value is None:
                client.publish(f"{topic_prefix}/error", json.dumps({
                    'error': 'Failed to read coil',
                    'command': command,
                    'address': address
                }))
                return
                
            # Toggle state
            current_state = coil_value[0]
            new_state = not current_state
            
            success = modbus_client.write_coil(address, new_state, unit=unit)
            result.update({
                'success': success,
                'previous': current_state,
                'current': new_state,
                'value': new_state,
                'value_display': 'ON' if new_state else 'OFF'
            })
            
        else:
            client.publish(f"{topic_prefix}/error", json.dumps({
                'error': f'Unknown command: {command}',
                'topic': topic
            }))
            return
            
        # Publish result
        client.publish(f"{topic_prefix}/result/{command}", json.dumps(result))
    
    def process_request(client, topic, data):
        """Process a request message"""
        # Extract request from topic
        request = topic.split('/')[-1]
        
        # Get parameters from data
        address = data.get('address')
        count = data.get('count', 1)
        unit = data.get('unit', 1)
        
        if address is None:
            client.publish(f"{topic_prefix}/error", json.dumps({
                'error': 'Missing address parameter',
                'request': request
            }))
            return
        
        # Connect to Modbus device if not connected
        if not modbus_client.is_connected():
            modbus_client.connect()
        
        # Process request
        result: Dict[str, Any] = {
            'request': request,
            'address': address,
            'count': count,
            'unit': unit,
            'timestamp': time.time()
        }
        
        if request == 'read_coils':
            coil_values = modbus_client.read_coils(address, count, unit=unit)
            if coil_values is None:
                client.publish(f"{topic_prefix}/error", json.dumps({
                    'error': 'Failed to read coils',
                    'request': request,
                    'address': address,
                    'count': count
                }))
                return
                
            result.update({
                'success': True,
                'values': coil_values,
                'values_dict': {str(i): val for i, val in enumerate(coil_values, address)},
                'values_display': ['ON' if val else 'OFF' for val in coil_values]
            })
            
        elif request == 'read_discrete_inputs':
            input_values = modbus_client.read_discrete_inputs(address, count, unit=unit)
            if input_values is None:
                client.publish(f"{topic_prefix}/error", json.dumps({
                    'error': 'Failed to read discrete inputs',
                    'request': request,
                    'address': address,
                    'count': count
                }))
                return
                
            result.update({
                'success': True,
                'values': input_values,
                'values_dict': {str(i): val for i, val in enumerate(input_values, address)},
                'values_display': ['ON' if val else 'OFF' for val in input_values]
            })
            
        elif request == 'read_holding_registers':
            register_values = modbus_client.read_holding_registers(address, count, unit=unit)
            if register_values is None:
                client.publish(f"{topic_prefix}/error", json.dumps({
                    'error': 'Failed to read holding registers',
                    'request': request,
                    'address': address,
                    'count': count
                }))
                return
                
            result.update({
                'success': True,
                'values': register_values,
                'values_dict': {str(i): val for i, val in enumerate(register_values, address)},
                'hex_values': [f"0x{val:04X}" for val in register_values]
            })
            
        elif request == 'read_input_registers':
            register_values = modbus_client.read_input_registers(address, count, unit=unit)
            if register_values is None:
                client.publish(f"{topic_prefix}/error", json.dumps({
                    'error': 'Failed to read input registers',
                    'request': request,
                    'address': address,
                    'count': count
                }))
                return
                
            result.update({
                'success': True,
                'values': register_values,
                'values_dict': {str(i): val for i, val in enumerate(register_values, address)},
                'hex_values': [f"0x{val:04X}" for val in register_values]
            })
            
        elif request == 'status':
            is_connected = modbus_client.is_connected()
            result.update({
                'success': True,
                'status': 'connected' if is_connected else 'disconnected',
                'port': port,
                'baudrate': baudrate
            })
            
        elif request == 'scan':
            detected_port = auto_detect_modbus_port()
            result.update({
                'success': detected_port is not None,
                'port': detected_port
            })
            
        else:
            client.publish(f"{topic_prefix}/error", json.dumps({
                'error': f'Unknown request: {request}',
                'topic': topic
            }))
            return
            
        # Publish result
        client.publish(f"{topic_prefix}/response/{request}", json.dumps(result))
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Connect to broker
    try:
        client.connect(broker, mqtt_port, 60)
        
        # Start the loop
        client.loop_start()
        
        logger.info(f"MQTT client started, connected to {broker}:{mqtt_port}")
        logger.info(f"Modbus device: {port}")
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping MQTT client...")
            client.loop_stop()
            modbus_client.disconnect()
            
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        raise

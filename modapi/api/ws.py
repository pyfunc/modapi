"""
modapi.api.ws - WebSocket API implementation for Modbus communication
Provides persistent connection to Modbus devices
"""

import logging
import json
import threading
import time
from typing import Dict, Any, Optional, List, Callable

from ..api.rtu import ModbusRTU

# Configure logging
logger = logging.getLogger(__name__)

# Try to import Flask-SocketIO for WebSocket API
try:
    from flask import Flask
    from flask_socketio import SocketIO, emit
except ImportError:
    logger.warning("Flask-SocketIO not installed. WebSocket API will not be available.")
    Flask = None
    SocketIO = None

# Connection pool for persistent Modbus connections
class ModbusConnectionPool:
    """Manages persistent connections to Modbus devices"""
    
    def __init__(self):
        """Initialize connection pool"""
        self.connections: Dict[str, ModbusRTU] = {}
        self.lock = threading.Lock()
        self.last_used: Dict[str, float] = {}
        self._cleanup_thread = None
        self._running = False
    
    def get_connection(self, port: str, baudrate: int = 9600, 
                      timeout: float = 1.0, **kwargs) -> ModbusRTU:
        """
        Get a connection from the pool or create a new one
        
        Args:
            port: Serial port path
            baudrate: Baud rate
            timeout: Timeout in seconds
            **kwargs: Additional ModbusRTU parameters
            
        Returns:
            ModbusRTU: Connected client
        """
        key = f"{port}:{baudrate}"
        
        with self.lock:
            # Check if connection exists and is connected
            if key in self.connections and self.connections[key].is_connected():
                client = self.connections[key]
                self.last_used[key] = time.time()
                return client
            
            # Create new connection
            client = ModbusRTU(port=port, baudrate=baudrate, timeout=timeout, **kwargs)
            success = client.connect()
            
            if success:
                self.connections[key] = client
                self.last_used[key] = time.time()
                
                # Start cleanup thread if not running
                if not self._running:
                    self._start_cleanup_thread()
                
                return client
            else:
                logger.error(f"Failed to connect to {port}")
                raise ConnectionError(f"Failed to connect to {port}")
    
    def release_connection(self, port: str, baudrate: int = 9600):
        """
        Mark connection as no longer in use
        
        Args:
            port: Serial port path
            baudrate: Baud rate
        """
        key = f"{port}:{baudrate}"
        with self.lock:
            if key in self.connections:
                self.last_used[key] = time.time()
    
    def close_connection(self, port: str, baudrate: int = 9600):
        """
        Close and remove a connection
        
        Args:
            port: Serial port path
            baudrate: Baud rate
        """
        key = f"{port}:{baudrate}"
        with self.lock:
            if key in self.connections:
                try:
                    self.connections[key].disconnect()
                except Exception as e:
                    logger.warning(f"Error closing connection {key}: {e}")
                
                del self.connections[key]
                if key in self.last_used:
                    del self.last_used[key]
    
    def close_all(self):
        """Close all connections in the pool"""
        with self.lock:
            for key, client in list(self.connections.items()):
                try:
                    client.disconnect()
                except Exception as e:
                    logger.warning(f"Error closing connection {key}: {e}")
            
            self.connections.clear()
            self.last_used.clear()
            self._running = False
    
    def _cleanup_idle_connections(self, max_idle_time: int = 300):
        """
        Close connections that have been idle for too long
        
        Args:
            max_idle_time: Maximum idle time in seconds
        """
        current_time = time.time()
        
        with self.lock:
            for key in list(self.last_used.keys()):
                if current_time - self.last_used[key] > max_idle_time:
                    logger.info(f"Closing idle connection: {key}")
                    self.close_connection(*key.split(':'))
    
    def _start_cleanup_thread(self):
        """Start background thread to clean up idle connections"""
        def cleanup_worker():
            self._running = True
            while self._running and self.connections:
                time.sleep(60)  # Check every minute
                try:
                    self._cleanup_idle_connections()
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def __del__(self):
        """Ensure connections are closed when pool is destroyed"""
        self._running = False
        self.close_all()


# Global connection pool
connection_pool = ModbusConnectionPool()


def require_socketio(func):
    """Decorator to check if Flask-SocketIO is available"""
    def wrapper(*args, **kwargs):
        if Flask is None or SocketIO is None:
            raise ImportError(
                "Flask-SocketIO is required for WebSocket API. "
                "Install with: pip install flask flask-socketio"
            )
        return func(*args, **kwargs)
    return wrapper


@require_socketio
def create_ws_app(port: Optional[str] = None,
                 baudrate: Optional[int] = None,
                 timeout: Optional[float] = None,
                 host: str = '0.0.0.0',
                 api_port: int = 5005,
                 debug: bool = False,
                 cors_allowed_origins: List[str] = None) -> tuple:
    """
    Create Flask application with SocketIO for WebSocket API
    
    Args:
        port: Modbus serial port (default: auto-detect)
        baudrate: Baud rate (default: 9600)
        timeout: Timeout in seconds (default: 1.0)
        host: Host to bind the API server (default: 0.0.0.0)
        api_port: Port to bind the API server (default: 5005)
        debug: Enable debug mode (default: False)
        cors_allowed_origins: CORS allowed origins (default: *)
        
    Returns:
        tuple: (Flask application, SocketIO instance)
    """
    app = Flask(__name__)
    
    # Configure CORS
    if cors_allowed_origins is None:
        cors_allowed_origins = "*"
    
    # Configure SocketIO
    socketio = SocketIO(app, cors_allowed_origins=cors_allowed_origins, 
                        async_mode='threading')
    
    # Configure logging
    if not debug:
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
    
    # Default port and baudrate
    if port is None:
        port = '/dev/ttyACM0'
    
    if baudrate is None:
        baudrate = 9600
    
    if timeout is None:
        timeout = 1.0
    
    # SocketIO event handlers
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info("Client connected")
        emit('status', {'connected': True})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info("Client disconnected")
    
    @socketio.on('read_coil')
    def handle_read_coil(data):
        """Handle read coil request"""
        try:
            address = int(data.get('address', 0))
            unit_id = int(data.get('unit', 1))
            
            # Get connection from pool
            client = connection_pool.get_connection(port, baudrate, timeout)
            
            # Read coil
            result = client.read_coils(unit_id, address, 1)
            connection_pool.release_connection(port, baudrate)
            
            if result is None:
                emit('error', {'message': f'Failed to read coil {address}'})
                return
            
            emit('coil_data', {
                'address': address,
                'value': result[0],
                'value_display': 'ON' if result[0] else 'OFF',
                'unit': unit_id
            })
            
        except Exception as e:
            logger.error(f"Error reading coil: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('write_coil')
    def handle_write_coil(data):
        """Handle write coil request"""
        try:
            address = int(data.get('address', 0))
            unit_id = int(data.get('unit', 1))
            
            # Parse value
            value = data.get('value')
            if isinstance(value, str):
                value = value.lower() in ('1', 'true', 'on')
            else:
                value = bool(value)
            
            # Get connection from pool
            client = connection_pool.get_connection(port, baudrate, timeout)
            
            # Write coil
            success = client.write_single_coil(unit_id, address, value)
            connection_pool.release_connection(port, baudrate)
            
            if not success:
                emit('error', {'message': f'Failed to write coil {address}'})
                return
            
            emit('coil_written', {
                'address': address,
                'value': value,
                'value_display': 'ON' if value else 'OFF',
                'unit': unit_id
            })
            
        except Exception as e:
            logger.error(f"Error writing coil: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('read_register')
    def handle_read_register(data):
        """Handle read register request"""
        try:
            address = int(data.get('address', 0))
            unit_id = int(data.get('unit', 1))
            register_type = data.get('type', 'holding')
            
            # Get connection from pool
            client = connection_pool.get_connection(port, baudrate, timeout)
            
            # Read register based on type
            if register_type == 'holding':
                result = client.read_holding_registers(unit_id, address, 1)
            elif register_type == 'input':
                result = client.read_input_registers(unit_id, address, 1)
            else:
                emit('error', {'message': f'Invalid register type: {register_type}'})
                return
            
            connection_pool.release_connection(port, baudrate)
            
            if result is None:
                emit('error', {'message': f'Failed to read {register_type} register {address}'})
                return
            
            emit('register_data', {
                'address': address,
                'value': result[0],
                'value_hex': hex(result[0]),
                'type': register_type,
                'unit': unit_id
            })
            
        except Exception as e:
            logger.error(f"Error reading register: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('write_register')
    def handle_write_register(data):
        """Handle write register request"""
        try:
            address = int(data.get('address', 0))
            value = int(data.get('value', 0))
            unit_id = int(data.get('unit', 1))
            
            # Get connection from pool
            client = connection_pool.get_connection(port, baudrate, timeout)
            
            # Write register
            success = client.write_single_register(unit_id, address, value)
            connection_pool.release_connection(port, baudrate)
            
            if not success:
                emit('error', {'message': f'Failed to write register {address}'})
                return
            
            emit('register_written', {
                'address': address,
                'value': value,
                'value_hex': hex(value),
                'unit': unit_id
            })
            
        except Exception as e:
            logger.error(f"Error writing register: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('test_connection')
    def handle_test_connection(data):
        """Handle test connection request"""
        try:
            unit_id = int(data.get('unit', 1))
            test_port = data.get('port', port)
            test_baudrate = int(data.get('baudrate', baudrate))
            
            # Get connection from pool
            client = connection_pool.get_connection(test_port, test_baudrate, timeout)
            
            # Test connection
            success, result = client.test_connection(unit_id)
            connection_pool.release_connection(test_port, test_baudrate)
            
            emit('connection_test', {
                'success': success,
                'result': result
            })
            
        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('close_connection')
    def handle_close_connection():
        """Handle close connection request"""
        try:
            connection_pool.close_connection(port, baudrate)
            emit('connection_closed', {'success': True})
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
            emit('error', {'message': str(e)})
    
    # Add a route to serve a simple client
    @app.route('/')
    def index():
        """Serve WebSocket client"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Modbus WebSocket Client</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
            <script>
                document.addEventListener('DOMContentLoaded', function() {
                    const socket = io();
                    
                    socket.on('connect', function() {
                        console.log('Connected to server');
                        document.getElementById('status').textContent = 'Connected';
                    });
                    
                    socket.on('disconnect', function() {
                        console.log('Disconnected from server');
                        document.getElementById('status').textContent = 'Disconnected';
                    });
                    
                    socket.on('error', function(data) {
                        console.error('Error:', data.message);
                        document.getElementById('result').textContent = 'Error: ' + data.message;
                    });
                    
                    socket.on('coil_data', function(data) {
                        console.log('Coil data:', data);
                        document.getElementById('result').textContent = 
                            'Coil ' + data.address + ': ' + data.value_display;
                    });
                    
                    socket.on('coil_written', function(data) {
                        console.log('Coil written:', data);
                        document.getElementById('result').textContent = 
                            'Coil ' + data.address + ' set to ' + data.value_display;
                    });
                    
                    socket.on('register_data', function(data) {
                        console.log('Register data:', data);
                        document.getElementById('result').textContent = 
                            data.type + ' Register ' + data.address + ': ' + 
                            data.value + ' (' + data.value_hex + ')';
                    });
                    
                    socket.on('register_written', function(data) {
                        console.log('Register written:', data);
                        document.getElementById('result').textContent = 
                            'Register ' + data.address + ' set to ' + 
                            data.value + ' (' + data.value_hex + ')';
                    });
                    
                    socket.on('connection_test', function(data) {
                        console.log('Connection test:', data);
                        document.getElementById('result').textContent = 
                            'Connection test: ' + (data.success ? 'Success' : 'Failed');
                        if (data.result) {
                            document.getElementById('result').textContent += 
                                ' - ' + JSON.stringify(data.result);
                        }
                    });
                    
                    // Read coil button
                    document.getElementById('readCoil').addEventListener('click', function() {
                        const address = parseInt(document.getElementById('address').value);
                        const unit = parseInt(document.getElementById('unit').value);
                        
                        socket.emit('read_coil', {
                            address: address,
                            unit: unit
                        });
                    });
                    
                    // Write coil button
                    document.getElementById('writeCoil').addEventListener('click', function() {
                        const address = parseInt(document.getElementById('address').value);
                        const value = document.getElementById('value').value === 'true';
                        const unit = parseInt(document.getElementById('unit').value);
                        
                        socket.emit('write_coil', {
                            address: address,
                            value: value,
                            unit: unit
                        });
                    });
                    
                    // Read register button
                    document.getElementById('readRegister').addEventListener('click', function() {
                        const address = parseInt(document.getElementById('address').value);
                        const unit = parseInt(document.getElementById('unit').value);
                        const type = document.getElementById('registerType').value;
                        
                        socket.emit('read_register', {
                            address: address,
                            unit: unit,
                            type: type
                        });
                    });
                    
                    // Write register button
                    document.getElementById('writeRegister').addEventListener('click', function() {
                        const address = parseInt(document.getElementById('address').value);
                        const value = parseInt(document.getElementById('registerValue').value);
                        const unit = parseInt(document.getElementById('unit').value);
                        
                        socket.emit('write_register', {
                            address: address,
                            value: value,
                            unit: unit
                        });
                    });
                    
                    // Test connection button
                    document.getElementById('testConnection').addEventListener('click', function() {
                        const unit = parseInt(document.getElementById('unit').value);
                        
                        socket.emit('test_connection', {
                            unit: unit
                        });
                    });
                });
            </script>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 800px; margin: 0 auto; }
                .card { border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 20px; }
                .form-group { margin-bottom: 10px; }
                label { display: block; margin-bottom: 5px; }
                input, select { padding: 5px; width: 100%; box-sizing: border-box; }
                button { padding: 8px 12px; background-color: #4CAF50; color: white; border: none; cursor: pointer; margin-right: 5px; }
                button:hover { background-color: #45a049; }
                .status { font-weight: bold; }
                .result { margin-top: 20px; padding: 10px; background-color: #f5f5f5; border-radius: 3px; }
                .button-group { margin-top: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Modbus WebSocket Client</h1>
                
                <div class="card">
                    <h2>Connection Status</h2>
                    <p>Status: <span id="status" class="status">Disconnected</span></p>
                </div>
                
                <div class="card">
                    <h2>Modbus Controls</h2>
                    
                    <div class="form-group">
                        <label for="address">Address:</label>
                        <input type="number" id="address" value="0" min="0">
                    </div>
                    
                    <div class="form-group">
                        <label for="unit">Unit ID:</label>
                        <input type="number" id="unit" value="1" min="1">
                    </div>
                    
                    <div class="form-group">
                        <label for="value">Coil Value:</label>
                        <select id="value">
                            <option value="true">ON</option>
                            <option value="false">OFF</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="registerType">Register Type:</label>
                        <select id="registerType">
                            <option value="holding">Holding Register</option>
                            <option value="input">Input Register</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="registerValue">Register Value:</label>
                        <input type="number" id="registerValue" value="0" min="0">
                    </div>
                    
                    <div class="button-group">
                        <button id="readCoil">Read Coil</button>
                        <button id="writeCoil">Write Coil</button>
                        <button id="readRegister">Read Register</button>
                        <button id="writeRegister">Write Register</button>
                        <button id="testConnection">Test Connection</button>
                    </div>
                </div>
                
                <div class="card">
                    <h2>Result</h2>
                    <div id="result" class="result">No data yet</div>
                </div>
            </div>
        </body>
        </html>
        """
    
    return app, socketio


def run_ws_server(port: Optional[str] = None,
                 baudrate: Optional[int] = None,
                 timeout: Optional[float] = None,
                 host: str = '0.0.0.0',
                 api_port: int = 5005,
                 debug: bool = False):
    """
    Run WebSocket server
    
    Args:
        port: Modbus serial port (default: auto-detect)
        baudrate: Baud rate (default: 9600)
        timeout: Timeout in seconds (default: 1.0)
        host: Host to bind the API server (default: 0.0.0.0)
        api_port: Port to bind the API server (default: 5005)
        debug: Enable debug mode (default: False)
    """
    app, socketio = create_ws_app(port, baudrate, timeout, host, api_port, debug)
    
    try:
        socketio.run(app, host=host, port=api_port, debug=debug)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        # Clean up connections
        connection_pool.close_all()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    run_ws_server(debug=True)

"""
modapi Output Module - SVG widget for Modbus digital outputs
"""

import os
import re
import json
import logging
from typing import Dict, Any, Optional, Union, Tuple
from datetime import datetime
from flask import Flask, Response, request, jsonify

from .client import ModbusClient, auto_detect_modbus_port

# Configure logging
logger = logging.getLogger(__name__)


def parse_coil_status(text: str) -> Tuple[Optional[int], Optional[bool]]:
    """
    Parse coil status message to get address and status
    
    Args:
        text: Status message (e.g., 'Coil 0 set to ON' or 'Coil 5 set to OFF')
    
    Returns:
        tuple: (address: int, status: bool) or (None, None) if parsing fails
    """
    match = re.match(r'Coil\s+(\d+)\s+set\s+to\s+(ON|OFF)', text, re.IGNORECASE)
    if match:
        address = int(match.group(1))
        status = match.group(2).upper() == 'ON'
        return address, status
    return None, None


def parse_coil_output(output: str, channel: int) -> Optional[bool]:
    """
    Parse coil read output to get boolean state for a specific channel
    
    Args:
        output: Raw output from mod.py or JSON response
        channel: The channel number to get the state for
    
    Returns:
        bool: The state of the specified channel, or None if parsing fails
    """
    try:
        # First try to parse as JSON
        try:
            data = json.loads(output)
            if 'data' in data and 'values' in data['data']:
                values = data['data']['values']
                if isinstance(values, list) and channel < len(values):
                    return bool(values[channel])
        except (json.JSONDecodeError, TypeError):
            pass
            
        # Try to parse as a status message (e.g., 'Coil 0 set to ON')
        if 'set to' in output:
            addr, status = parse_coil_status(output)
            if addr is not None and addr == channel:
                return status
        
        # Fall back to parsing as a list of states
        start = output.find('[') + 1
        end = output.rfind(']')
        if start > 0 and end > start:
            # Get the list of states as a string, remove whitespace, and split by commas
            states_str = output[start:end].strip()
            # Handle both '[True, False]' and 'True, False' formats
            if states_str.startswith('[') and states_str.endswith(']'):
                states_str = states_str[1:-1]
            states = [s.strip().lower() == 'true' for s in states_str.split(',')]
            
            # Return the state of the requested channel if it exists
            if 0 <= channel < len(states):
                return states[channel]
    except (ValueError, IndexError, AttributeError) as e:
        logger.error(f"Error parsing coil output: {e}")
    
    return None


def generate_svg(channel: int, state: bool, config: Dict[str, Any] = None) -> str:
    """
    Generate SVG content for the output module
    
    Args:
        channel: Channel number
        state: Current state (True for ON, False for OFF)
        config: Optional configuration dictionary
        
    Returns:
        SVG content as string
    """
    if config is None:
        config = {}
        
    # Default configuration
    default_config = {
        'api': {
            'baseUrl': os.getenv('MODBUS_API', 'http://localhost:5000'),
            'status': 'active'
        },
        'ui': {
            'refreshInterval': os.getenv('AUTO_REFRESH_INTERVAL', '3000'),
            'lastUpdated': datetime.now().strftime('%H:%M:%S'),
            'error': '',
            'theme': os.getenv('UI_THEME', 'dark')
        },
        'widget': {
            'channel': channel,
            'state': str(state).lower(),
            'name': f'DO{channel}'
        },
        'debug': os.getenv('DEBUG', 'false').lower() == 'true'
    }
    
    # Merge with provided config
    for section, values in config.items():
        if section in default_config and isinstance(values, dict):
            default_config[section].update(values)
        else:
            default_config[section] = values
            
    config = default_config
    
    # Dynamic channel-specific calculations
    channel_name = config['widget']['name']
    status_color = "#28a745" if state else "#6c757d"
    status_text = "ON" if state else "OFF"
    now = config['ui']['lastUpdated']
    debug_mode = config['debug']
    theme = config['ui']['theme']
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="120" height="100" viewBox="0 0 120 100">
    <defs>
        <!-- Application Configuration -->
        <script type="application/json" id="app-config">
        {json.dumps(config, indent=2)}
        </script>

        <!-- Initialize JavaScript -->
        <script><![CDATA[
            // Parse the configuration
            const config = JSON.parse(document.getElementById('app-config').textContent);
            
            function toggleOutput(channel) {{
                fetch(`${{config.api.baseUrl}}/api/toggle/${{channel}}`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}}
                }}).then(response => {{
                    if (response.ok) {{
                        setTimeout(() => window.location.reload(), 500);
                    }} else {{
                        console.error('Toggle failed:', response.statusText);
                    }}
                }}).catch(error => {{
                    console.error('Toggle error:', error);
                }});
            }}
            
            // Auto-refresh based on config
            setTimeout(() => {{
                window.location.reload();
            }}, parseInt(config.ui.refreshInterval));
            
            // Debug logging if enabled
            if ({str(debug_mode).lower()}) {{
                console.log('Widget Config:', config);
                console.log('Last Updated:', config.ui.lastUpdated);
            }}
        ]]></script>
        
        <style>
            .output-widget {{ 
                cursor: pointer; 
                transition: all 0.3s;
                filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
            }}
            .output-widget:hover {{ 
                transform: scale(1.05); 
            }}
            .output-widget:active {{ 
                transform: scale(0.95); 
            }}
            .output-active {{ 
                fill: {status_color}; 
                stroke: #1e7e34; 
                stroke-width: 2;
            }}
            .output-inactive {{ 
                fill: #6c757d; 
                stroke: #495057; 
                stroke-width: 2;
            }}
            .text {{ 
                fill: white; 
                font-family: 'Segoe UI', Arial, sans-serif; 
                font-size: 16px; 
                font-weight: bold; 
                text-anchor: middle; 
                pointer-events: none;
            }}
            .status-text {{ 
                fill: white; 
                font-family: 'Segoe UI', Arial, sans-serif; 
                font-size: 12px; 
                font-weight: normal; 
                text-anchor: middle; 
                pointer-events: none;
            }}
            .label {{
                fill: #333;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10px;
                text-anchor: middle;
            }}
            .timestamp {{
                fill: #999;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 8px;
                text-anchor: end;
            }}
        </style>
    </defs>

    <!-- Main widget rectangle -->
    <rect x="10" y="10" width="100" height="70" rx="8" 
          class="output-widget {'output-active' if state else 'output-inactive'}" 
          onclick="toggleOutput({channel})"/>

    <!-- Widget content -->
    <text x="60" y="35" class="text">{channel_name}</text>
    <text x="60" y="55" class="status-text">{status_text}</text>
    <text x="60" y="95" class="label">Click to toggle</text>
    
    <!-- Timestamp -->
    <text x="115" y="8" class="timestamp">{now}</text>
</svg>'''


def create_output_app(port: Optional[str] = None,
                     baudrate: Optional[int] = None,
                     timeout: Optional[float] = None,
                     host: str = '0.0.0.0',
                     api_port: int = 5002,
                     debug: bool = False) -> Flask:
    """
    Create Flask application for Output Module
    
    Args:
        port: Modbus serial port (default: auto-detect)
        baudrate: Baud rate (default: from .env or 9600)
        timeout: Timeout in seconds (default: from .env or 1.0)
        host: Host to bind the API server (default: 0.0.0.0)
        api_port: Port to bind the API server (default: 5002)
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
            logger.error("No Modbus device found! Output Module will not work correctly.")
    
    modbus_client = ModbusClient(port=port, baudrate=baudrate, timeout=timeout)
    
    # Configuration
    MODBUS_UNIT = int(os.getenv('MODBUS_DEVICE_ADDRESS', '1'))
    
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
    
    @app.route('/module/output/<int:channel>')
    def output_module(channel):
        """Endpoint for the output module SVG"""
        # Read current state
        result = modbus_client.read_coils(channel, 1, MODBUS_UNIT)
        
        if result is None:
            state = False
            error_msg = "Failed to read coil state"
            logger.error(error_msg)
        else:
            state = result[0]
            error_msg = ""
            
        # Generate configuration
        config = {
            'api': {
                'baseUrl': request.host_url.rstrip('/'),
                'status': 'active' if result is not None else 'error'
            },
            'ui': {
                'refreshInterval': os.getenv('AUTO_REFRESH_INTERVAL', '3000'),
                'lastUpdated': datetime.now().strftime('%H:%M:%S'),
                'error': error_msg,
                'theme': os.getenv('UI_THEME', 'dark')
            },
            'widget': {
                'channel': channel,
                'state': str(state).lower(),
                'name': f'DO{channel}'
            },
            'debug': os.getenv('DEBUG', 'false').lower() == 'true'
        }
        
        # Generate and return SVG
        svg = generate_svg(channel, state, config)
        return Response(svg, mimetype='image/svg+xml')
    
    @app.route('/module/input/<int:channel>')
    def toggle_module(channel):
        """Endpoint to toggle output and return updated SVG"""
        # Read current state
        result = modbus_client.read_coils(channel, 1, MODBUS_UNIT)
        
        if result is None:
            return f"Error reading coil {channel}: Could not read state", 500
            
        # Toggle state
        current_state = result[0]
        new_state = not current_state
        
        # Write new state
        if not modbus_client.write_coil(channel, new_state, MODBUS_UNIT):
            return f"Error toggling coil {channel}: Write failed", 500
            
        # Read state again to confirm
        result = modbus_client.read_coils(channel, 1, MODBUS_UNIT)
        if result is None:
            state = new_state  # Assume it worked
            error_msg = "Could not confirm new state"
        else:
            state = result[0]
            error_msg = "" if state == new_state else "Toggle failed to change state"
            
        # Generate configuration
        config = {
            'api': {
                'baseUrl': request.host_url.rstrip('/'),
                'status': 'active' if not error_msg else 'warning'
            },
            'ui': {
                'refreshInterval': os.getenv('AUTO_REFRESH_INTERVAL', '3000'),
                'lastUpdated': datetime.now().strftime('%H:%M:%S'),
                'error': error_msg,
                'theme': os.getenv('UI_THEME', 'dark')
            },
            'widget': {
                'channel': channel,
                'state': str(state).lower(),
                'name': f'DO{channel}'
            },
            'debug': os.getenv('DEBUG', 'false').lower() == 'true'
        }
        
        # Generate and return SVG
        svg = generate_svg(channel, state, config)
        return Response(svg, mimetype='image/svg+xml')
    
    @app.route('/config')
    def get_config():
        """Return configuration for JavaScript clients"""
        return jsonify({
            'api': {
                'baseUrl': request.host_url.rstrip('/'),
                'status': 'active' if modbus_client.is_connected() else 'inactive',
                'port': modbus_client.port,
                'baudrate': modbus_client.baudrate
            },
            'ui': {
                'refreshInterval': os.getenv('AUTO_REFRESH_INTERVAL', '3000'),
                'theme': os.getenv('UI_THEME', 'dark')
            },
            'modbus': {
                'unit': MODBUS_UNIT
            }
        })
    
    def run_server():
        """Run the Flask server"""
        app.run(host=host, port=api_port, debug=debug)
    
    # Add run method to app
    app.run_server = run_server
    
    return app

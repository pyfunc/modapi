# modapi

Unified API for Modbus communication with multiple interfaces: Shell CLI, REST API, and MQTT.

## Features

- **Modbus RTU Client** - Core functionality for communicating with Modbus devices
- **Auto-detection** - Automatically detect Modbus devices on serial ports
- **Multiple APIs**:
  - **Shell CLI** - Command line interface for direct Modbus operations
  - **REST API** - HTTP API for web applications
  - **MQTT API** - MQTT interface for IoT applications
- **Interactive Mode** - Interactive shell for manual Modbus operations
- **JSON Output** - Structured JSON output for easy parsing
- **Modular Architecture** - Separate modules for different interfaces (REST, MQTT, Shell, Command)

## Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management.

1. Install Poetry if you haven't already:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/yourusername/modapi.git
   cd modapi
   poetry install  # Install all dependencies
   
   # Or install with specific groups:
   poetry install --only main,rest  # Only REST API
   poetry install --only main,mqtt  # Only MQTT API
   poetry install --with dev        # Development tools
   ```

3. Activate the virtual environment:
   ```bash
   poetry shell
   ```

## Development

- Install development dependencies:
  ```bash
  poetry install --with dev
  ```

- Run tests:
  ```bash
  poetry run pytest
  ```

- Run with coverage:
  ```bash
  poetry run pytest --cov=modapi tests/
  ```

## Building and Publishing

- Build the package:
  ```bash
  poetry build
  ```

- Publish to PyPI:
  ```bash
  poetry publish --build
  ```

## Modbus Simulator

For testing without physical hardware, a Modbus RTU simulator is included. This creates a virtual Modbus device that responds to read/write requests.

### Setting Up the Simulator

1. First, install the required dependencies:
   ```bash
   poetry add "pymodbus[repl,serial]"
   ```

2. Create virtual serial ports (in a separate terminal):
   ```bash
   socat -d -d pty,raw,echo=0,link=/tmp/ptyp0 pty,raw,echo=0,link=/tmp/ttyp0
   ```

3. In another terminal, start the simulator:
   ```bash
   poetry run python simulate_modbus.py
   ```

   The simulator will start with these test values:
   - Coils 0-3: `[1, 0, 1, 0]`
   - Holding Registers 0-2: `[1234, 5678, 9012]`

4. Configure your `.env` file to use the virtual port:
   ```ini
   MODBUS_PORT=/tmp/ttyp0
   MODBUS_BAUDRATE=9600
   MODBUS_TIMEOUT=0.1
   ```

5. You can now run the API server or CLI commands to interact with the simulator.

## Usage

### Command Line Interface

The modapi CLI supports multiple subcommands:

```bash
# Direct command execution
modapi cmd wc 0 1       # Write value 1 to coil at address 0
modapi cmd rc 0 8       # Read 8 coils starting at address 0
modapi cmd rh 0 5       # Read 5 holding registers starting at address 0
modapi cmd wh 0 42      # Write value 42 to holding register at address 0

# Interactive shell
modapi shell

# REST API server
modapi rest --host 0.0.0.0 --port 5000

# MQTT client
modapi mqtt --broker localhost --port 1883

# Scan for Modbus devices
modapi scan

# With options
modapi cmd --verbose rc 0 8    # Verbose mode
modapi cmd --modbus-port /dev/ttyACM0 wc 0 1  # Specify port
```

For backward compatibility, you can also use the direct command format:
```bash
# These are automatically converted to the new format
./run_cli.py wc 0 1       # Equivalent to: modapi cmd wc 0 1
./run_cli.py rc 0 8       # Equivalent to: modapi cmd rc 0 8
```

### REST API

```python
from modapi.api.rest import create_rest_app

# Create and run Flask app
app = create_rest_app(port='/dev/ttyACM0', api_port=5000)
app.run(host='0.0.0.0', port=5000)
```

#### REST API Endpoints

- `GET /api/status` - Get connection status
- `GET /api/coils/<address>` - Read a single coil
- `GET /api/coils/<address>/<count>` - Read multiple coils
- `PUT /api/coils/<address>` - Write to a coil
- `GET /api/discrete_inputs/<address>/<count>` - Read discrete inputs
- `GET /api/holding_registers/<address>/<count>` - Read holding registers
- `PUT /api/holding_registers/<address>` - Write to a holding register
- `GET /api/input_registers/<address>/<count>` - Read input registers
- `GET /api/scan` - Scan for Modbus devices

### MQTT API

```python
from modapi.api.mqtt import start_mqtt_broker

# Start MQTT client
start_mqtt_broker(
    port='/dev/ttyACM0',
    broker='localhost',
    mqtt_port=1883,
    topic_prefix='modbus'
)
```

#### MQTT Topics

- Subscribe to `modbus/command/#` to send commands
- Subscribe to `modbus/request/#` to send requests
- Publish to `modbus/command/write_coil` with payload `{"address": 0, "value": true}` to write to a coil
- Publish to `modbus/request/read_coils` with payload `{"address": 0, "count": 8}` to read coils
- Results are published to `modbus/result/<command>` and `modbus/response/<request>`

### Direct API Usage

```python
from modapi.api.cmd import execute_command
from modapi.api.shell import interactive_mode

# Execute a command directly
success, response = execute_command('wc', ['0', '1'], port='/dev/ttyACM0')
print(response)

# Start interactive mode
interactive_mode(port='/dev/ttyACM0', verbose=True)
```

## Project Structure

```
modapi/
├── api/
│   ├── __init__.py    # Exports main API functions
│   ├── cmd.py         # Direct command execution
│   ├── mqtt.py        # MQTT broker client
│   ├── rest.py        # REST API Flask app
│   └── shell.py       # Interactive shell
├── client.py          # Modbus client implementation
├── __main__.py        # CLI entry point
└── ...
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

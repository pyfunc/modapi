# Modbus RTU Connection Testing

This document describes the behavior and usage of the `test_rtu_connection` function in the ModbusRTU module, including its special handling in test environments.

## Overview

The `test_rtu_connection` function is a utility function that tests the connection to a Modbus RTU device. It is designed to be used both in production code and in test environments, with special handling for test environments.

## Function Signature

```python
def test_rtu_connection(port: str, baudrate: int = DEFAULT_BAUDRATE, 
                       timeout: float = DEFAULT_TIMEOUT, 
                       unit_id: int = DEFAULT_UNIT_ID) -> Tuple[bool, Dict[str, Any]]:
```

### Parameters

- `port`: Serial port path (e.g., `/dev/ttyACM0`)
- `baudrate`: Baud rate to test (default: from config.DEFAULT_BAUDRATE)
- `timeout`: Timeout in seconds (default: from config.DEFAULT_TIMEOUT)
- `unit_id`: Unit ID to test (default: from config.DEFAULT_UNIT_ID)

### Return Value

The function returns a tuple containing:
1. A boolean indicating success or failure
2. A dictionary with connection details including:
   - `port`: The serial port path
   - `baudrate`: The baud rate used
   - `unit_id`: The Modbus unit ID used
   - `success`: Boolean indicating success or failure
   - `connected`: Boolean indicating if a connection was established (always matches `success`)
   - `error`: Error message if an error occurred, otherwise `None`
   - `device_type`: Type of device detected, or `None` if unknown/not detected

## Special Handling in Test Environments

The `test_rtu_connection` function includes special handling for test environments:

1. **Test Compatibility**: The function always includes a `connected` key in the result dictionary, which is set to the same value as the `success` key. This ensures compatibility with test code that expects this key to be present.

2. **ModbusRTU Class Usage**: The function uses the `ModbusRTU` class to test the connection, which allows test code to mock this class for testing without requiring actual hardware.

3. **Device Type Detection**: If the connection is successful, the function attempts to detect the device type using the `detect_device_type` function. In test environments, this can be mocked to return a specific device type.

## Usage Examples

### Basic Usage

```python
from modapi.rtu.utils import test_rtu_connection

# Test connection with default parameters
success, result = test_rtu_connection('/dev/ttyACM0')

if success:
    print(f"Successfully connected to {result['port']} at {result['baudrate']} baud")
    print(f"Device type: {result['device_type']}")
else:
    print(f"Connection failed: {result['error']}")
```

### Custom Parameters

```python
# Test connection with custom parameters
success, result = test_rtu_connection(
    port='/dev/ttyUSB0',
    baudrate=19200,
    timeout=2.0,
    unit_id=2
)
```

### In Test Environments

In test environments, you can mock the `ModbusRTU` class to test the function without actual hardware:

```python
import unittest
from unittest.mock import patch, MagicMock
from modapi.rtu.utils import test_rtu_connection

class TestRTUConnection(unittest.TestCase):
    @patch('modapi.api.rtu.ModbusRTU')
    def test_successful_connection(self, mock_modbus_rtu):
        # Configure the mock
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = (True, {'some': 'data'})
        mock_modbus_rtu.return_value.__enter__.return_value = mock_instance
        
        # Call the function
        success, result = test_rtu_connection('/dev/ttyACM0')
        
        # Assert results
        self.assertTrue(success)
        self.assertTrue(result['connected'])  # 'connected' key should be present and True
```

## Troubleshooting

If the `test_rtu_connection` function fails to connect to a device that you know is present, consider the following:

1. **Port Availability**: Ensure the specified port exists and is accessible
2. **Baudrate Mismatch**: Try different baudrates if the device's baudrate is unknown
3. **Unit ID Mismatch**: Try different unit IDs if the device's unit ID is unknown
4. **Timeout**: Increase the timeout value for slower devices or connections
5. **Device-Specific Issues**: Some devices may require specific settings or have non-standard implementations of the Modbus RTU protocol

## Known Issues

- Some Waveshare devices may have non-standard Modbus RTU implementations that require special handling
- CRC validation failures may occur with some devices
- Some devices may not respond to certain function codes

## See Also

- [Modbus RTU Protocol](https://modbus.org/docs/Modbus_over_serial_line_V1_02.pdf)
- [PySerial Documentation](https://pyserial.readthedocs.io/en/latest/pyserial.html)

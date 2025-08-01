# Modbus Device State Tracking

This document explains the device state tracking functionality implemented in the ModbusRTU module.

## Overview

The device state tracking system provides a virtual representation of Modbus device states, allowing for:

1. Real-time tracking of coil and register values
2. Diagnostic information about communication quality
3. Persistence of device state for offline analysis
4. Support for multiple devices on the same bus

## Components

### ModbusDeviceState

The `ModbusDeviceState` class (in `modapi/rtu/device_state.py`) represents the state of a single Modbus device:

- Device identification (unit ID, port, baudrate)
- Current state of coils and registers
- Communication statistics (success/error/timeout counts)
- Timestamps for last successful communication

### ModbusDeviceStateManager

The global `device_manager` instance (in `modapi/rtu/device_state.py`) manages multiple device states:

- Tracks all active device states
- Provides methods to add, retrieve, and remove device states
- Supports dumping all device states to JSON files

### Integration with ModbusRTU

The `ModbusRTU` class has been enhanced to:

- Create and maintain device states for each unit ID it communicates with
- Update device states automatically after successful reads/writes
- Track communication errors and timeouts
- Provide methods to dump device states to JSON files

## Usage

### Enabling Device State Tracking

Device state tracking is enabled by default. To disable it:

```python
rtu = ModbusRTU(port='/dev/ttyACM0', enable_state_tracking=False)
```

### Accessing Device States

```python
# Get summary of all device states
summary = rtu.get_device_state_summary()

# Get state of a specific device
device_state = rtu.get_device_state_summary(unit_id=1)
```

### Dumping Device States

```python
# Dump all device states to JSON files
rtu.dump_device_states()

# Dump current device state to JSON file
rtu.dump_current_device_state()
```

### Custom Directory for State Dumps

```python
# Specify custom directory for state dumps
rtu.dump_device_states(directory='/path/to/custom/directory')
```

## JSON Format

Device states are dumped in the following JSON format:

```json
{
  "unit_id": 1,
  "port": "/dev/ttyACM0",
  "baudrate": 57600,
  "last_updated": 1627984512.345,
  "coils": {
    "0": true,
    "1": false,
    "2": true
  },
  "discrete_inputs": {},
  "holding_registers": {
    "0": 123,
    "1": 456
  },
  "input_registers": {},
  "request_count": 10,
  "success_count": 8,
  "error_count": 1,
  "timeout_count": 1,
  "crc_error_count": 0,
  "last_error": "Timeout waiting for response",
  "last_error_time": 1627984510.123
}
```

## Benefits

1. **Resilience**: Even if communication is lost, the last known state is preserved
2. **Diagnostics**: Track communication quality and identify problematic devices
3. **Offline Analysis**: Analyze device behavior without requiring physical connection
4. **Debugging**: Identify issues with specific registers or coils

## Implementation Details

- Device states are updated automatically after each successful read/write operation
- Communication errors and timeouts are tracked and associated with specific devices
- Device states are stored in memory and can be dumped to JSON files for persistence
- The highest baudrate is always used for communication to minimize latency

## Log Files

Detailed logs are stored in:
- `~/.modbus_logs/<port_name>/` for device-specific logs
- `~/.modbus_logs/device_states/` for device state dumps

## Future Enhancements

- Web interface for viewing device states
- Automatic recovery of device states after communication loss
- Historical trending of register/coil values
- Alerting on communication issues

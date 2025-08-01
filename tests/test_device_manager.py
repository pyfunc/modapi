"""Tests for the Modbus device manager module."""
import pytest
from unittest.mock import Mock, patch

from modapi.rtu.device_manager import device_manager, ModbusDeviceState


def test_device_manager_singleton():
    """Test that device_manager is a singleton."""
    from modapi.rtu.device_manager import device_manager as dm1
    from modapi.rtu.device_manager import device_manager as dm2
    assert dm1 is dm2


def test_add_and_get_device():
    """Test adding and retrieving a device state."""
    # Clear any existing devices
    device_manager.devices.clear()
    
    # Create a test device state
    test_device = ModbusDeviceState(
        unit_id=1,
        port="/dev/ttyUSB0",
        baudrate=9600
    )
    
    # Add the device
    device_manager.add_device(test_device)
    
    # Retrieve the device
    retrieved_device = device_manager.get_device("/dev/ttyUSB0", 1)
    
    # Verify
    assert retrieved_device is test_device
    assert len(device_manager.devices) == 1


def test_get_nonexistent_device():
    """Test getting a non-existent device returns None."""
    # Clear any existing devices
    device_manager.devices.clear()
    
    # Try to get a non-existent device
    device = device_manager.get_device("/dev/nonexistent", 99)
    
    assert device is None


def test_dump_device_states(tmp_path):
    """Test dumping device states to a file."""
    # Clear any existing devices
    device_manager.devices.clear()
    
    # Create a test device state
    test_device = ModbusDeviceState(
        unit_id=1,
        port="/dev/ttyUSB0",
        baudrate=9600
    )
    test_device.coils[0] = True
    test_device.holding_registers[0] = 1234
    
    # Add the device
    device_manager.add_device(test_device)
    
    # Dump to file
    output_file = tmp_path / "device_state.json"
    test_device.dump_to_file(str(output_file))
    
    # Verify file was created and has content
    assert output_file.exists()
    assert output_file.stat().st_size > 0
    
    # Verify file content by parsing JSON and checking structure
    import json
    with open(output_file, 'r') as f:
        data = json.load(f)
        assert data['unit_id'] == 1
        assert data['port'] == "/dev/ttyUSB0"
        assert data['coils']['0'] is True  # JSON keys are always strings
        assert data['holding_registers']['0'] == 1234  # JSON keys are always strings


def test_load_device_states(tmp_path):
    """Test loading device states from a file."""
    # Clear any existing devices
    device_manager.devices.clear()
    
    # Create a test JSON file
    test_data = """
    {
        "unit_id": 1,
        "port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "coils": {"0": true},
        "holding_registers": {"0": 1234}
    }
    """
    
    input_file = tmp_path / "test_device.json"
    with open(input_file, 'w') as f:
        f.write(test_data)
    
    # Create a new device and load from file
    device = ModbusDeviceState(unit_id=1, port="/dev/ttyUSB0", baudrate=9600)
    device.load_from_file(str(input_file))
    
    # Add to device manager
    device_manager.add_device(device)
    
    # Verify the device was loaded correctly
    assert device.port == "/dev/ttyUSB0"
    assert device.unit_id == 1
    # Check that coils and registers are accessible with string keys (from JSON)
    assert '0' in device.coils
    assert device.coils['0'] is True
    assert '0' in device.holding_registers
    assert device.holding_registers['0'] == 1234
    
    # Verify we can retrieve it from device manager
    retrieved_device = device_manager.get_device("/dev/ttyUSB0", 1)
    assert retrieved_device is device

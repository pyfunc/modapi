#!/usr/bin/env python3
"""
Test script for the refactored Modbus RTU module
"""

import logging
import sys
from modapi.api.rtu import ModbusRTU, test_rtu_connection, create_rtu_client
from modapi.api.rtu.utils import find_serial_ports, scan_for_devices
from modapi.api.rtu.devices import WaveshareIO8CH, WaveshareAnalogInput8CH

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test importing all components"""
    logger.info("✅ Successfully imported all components")
    return True

def test_find_ports():
    """Test finding serial ports"""
    ports = find_serial_ports()
    logger.info(f"Found serial ports: {ports}")
    return len(ports) > 0

def test_connection():
    """Test connection to RTU device"""
    port = '/dev/ttyACM0'  # Default port
    success, result = test_rtu_connection(port)
    
    if success:
        logger.info(f"✅ Connection successful: {result}")
    else:
        logger.warning(f"❌ Connection failed: {result}")
    
    return success

def test_client_creation():
    """Test creating RTU client"""
    try:
        client = create_rtu_client()
        logger.info("✅ Client created successfully")
        client.disconnect()
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create client: {e}")
        return False

def test_auto_detect():
    """Test auto-detection of RTU devices"""
    client = ModbusRTU()
    config = client.auto_detect()
    
    if config:
        logger.info(f"✅ Auto-detection successful: {config}")
        return True
    else:
        logger.warning("❌ Auto-detection failed")
        return False

def test_device_classes():
    """Test device-specific classes"""
    try:
        # Just test instantiation, don't connect to hardware
        io_device = WaveshareIO8CH(port=None)
        analog_device = WaveshareAnalogInput8CH(port=None)
        logger.info("✅ Device classes instantiated successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to instantiate device classes: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting RTU module tests...")
    
    tests = [
        ("Import Test", test_imports),
        ("Port Detection Test", test_find_ports),
        ("Device Class Test", test_device_classes)
    ]
    
    # Only run hardware tests if --hardware flag is provided
    if "--hardware" in sys.argv:
        tests.extend([
            ("Connection Test", test_connection),
            ("Client Creation Test", test_client_creation),
            ("Auto-detection Test", test_auto_detect)
        ])
    
    results = []
    for name, test_func in tests:
        logger.info(f"Running {name}...")
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            logger.error(f"Test {name} raised exception: {e}")
            results.append((name, False))
    
    # Print summary
    logger.info("\n--- Test Results ---")
    all_passed = True
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {name}")
        all_passed = all_passed and success
    
    if all_passed:
        logger.info("\n✅ All tests passed!")
        return 0
    else:
        logger.warning("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

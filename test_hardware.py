#!/usr/bin/env python3
"""
Simple script to test Modbus RTU communication with actual hardware
"""

import logging
import sys
import time
from modapi.rtu import ModbusRTU
from modapi.__main__ import auto_detect_modbus_port
from modapi.config import (
    DEFAULT_BAUDRATE, DEFAULT_TIMEOUT, DEFAULT_UNIT_ID,
    PRIORITIZED_BAUDRATES, HIGHEST_PRIORITIZED_BAUDRATE, AUTO_DETECT_UNIT_IDS
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_hardware_connection():
    """Test connection to the Modbus RTU hardware"""
    logger.info("🔍 Attempting to auto-detect Modbus RTU device...")
    
    # Try auto-detection first
    device_config = auto_detect_modbus_port(debug=True)
    
    if device_config and device_config.get('success'):
        logger.info(f"✅ Device detected: {device_config}")
        port = device_config.get('port')
        baudrate = device_config.get('baudrate')
        unit_id = device_config.get('unit_id', DEFAULT_UNIT_ID)
    else:
        logger.warning("⚠️ Auto-detection failed, using default configuration")
        port = '/dev/ttyACM0'  # Default port for USB-to-RS485 adapters
        baudrate = HIGHEST_PRIORITIZED_BAUDRATE
        unit_id = DEFAULT_UNIT_ID
    
    logger.info(f"📡 Connecting to device on {port} at {baudrate} baud, unit ID {unit_id}")
    
    # Create ModbusRTU instance and test connection
    try:
        with ModbusRTU(port=port, baudrate=baudrate, timeout=DEFAULT_TIMEOUT) as rtu:
            # Test connection
            logger.info("🔌 Testing connection...")
            success, result = rtu.test_connection(unit_id)
            
            if success:
                logger.info(f"✅ Connection successful: {result}")
                
                # Read coils
                logger.info("📖 Reading coils 0-7...")
                coils = rtu.read_coils(unit_id, 0, 8)
                logger.info(f"Coils 0-7: {coils}")
                
                # Read input registers (if available)
                try:
                    logger.info("📖 Reading input registers 0-3...")
                    registers = rtu.read_input_registers(unit_id, 0, 4)
                    logger.info(f"Input registers 0-3: {registers}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to read input registers: {e}")
                
                # Toggle coil 0 (if allowed)
                try:
                    logger.info("🔄 Toggling coil 0...")
                    current_state = coils[0] if coils else False
                    logger.info(f"Current state of coil 0: {current_state}")
                    
                    # Write opposite state
                    rtu.write_single_coil(unit_id, 0, not current_state)
                    logger.info(f"Set coil 0 to {not current_state}")
                    
                    # Read back to verify
                    time.sleep(0.5)  # Small delay
                    new_state = rtu.read_coils(unit_id, 0, 1)[0]
                    logger.info(f"New state of coil 0: {new_state}")
                    
                    # Restore original state
                    rtu.write_single_coil(unit_id, 0, current_state)
                    logger.info(f"Restored coil 0 to {current_state}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to toggle coil: {e}")
                
                return True
            else:
                logger.error(f"❌ Connection failed: {result}")
                return False
    
    except Exception as e:
        logger.error(f"❌ Error connecting to device: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting Modbus RTU hardware test")
    success = test_hardware_connection()
    
    if success:
        logger.info("✅ Hardware test completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Hardware test failed")
        sys.exit(1)

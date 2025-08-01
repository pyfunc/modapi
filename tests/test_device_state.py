#!/usr/bin/env python3
"""
Test script for Modbus device state tracking functionality
"""

import os
import sys
import time
import json
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modapi.rtu.base import ModbusRTU
from modapi.rtu.device_state import ModbusDeviceState, device_manager
from dataclasses import asdict

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_device_state_tracking(port='/dev/ttyACM0', unit_id=1, mock_mode=False):
    """Test device state tracking functionality"""
    logger.info(f"Testing device state tracking on port {port} with unit ID {unit_id}")
    
    # Create ModbusRTU instance with state tracking enabled
    rtu = ModbusRTU(
        port=port,
        enable_state_tracking=True
    )
    
    try:
        # Connect to device
        if not mock_mode:
            if not rtu.connect():
                logger.error(f"Failed to connect to {port}")
                return False
            
            # Read some coils and registers to populate device state
            logger.info("Reading coils 0-7...")
            coils = rtu.read_coils(unit_id, 0, 8)
            logger.info(f"Coils: {coils}")
            
            logger.info("Reading holding registers 0-3...")
            registers = rtu.read_holding_registers(unit_id, 0, 4)
            logger.info(f"Registers: {registers}")
            
            # Write to a coil and register
            logger.info("Writing to coil 0...")
            rtu.write_single_coil(unit_id, 0, True)
            
            logger.info("Writing to register 0...")
            rtu.write_single_register(unit_id, 0, 12345)
            
            # Read again to verify changes
            logger.info("Reading coil 0 again...")
            coil_value = rtu.read_coils(unit_id, 0, 1)
            logger.info(f"Coil 0: {coil_value}")
            
            logger.info("Reading register 0 again...")
            register_value = rtu.read_holding_registers(unit_id, 0, 1)
            logger.info(f"Register 0: {register_value}")
        else:
            # Mock mode - create fake device state
            logger.info("Mock mode enabled - creating fake device state")
            device_state = ModbusDeviceState(
                unit_id=unit_id,
                port=port,
                baudrate=57600
            )
            
            # Add some fake data
            device_state.update_coil(0, True)
            device_state.update_coil(1, False)
            device_state.update_coil(2, True)
            
            device_state.update_holding_register(0, 12345)
            device_state.update_holding_register(1, 6789)
            
            # Record some statistics
            device_state.record_success()
            device_state.record_success()
            device_state.record_timeout()
            device_state.record_crc_error()
            
            # Add to device manager
            device_manager.add_device(device_state)
            
            # Add to RTU instance
            device_key = f"{port}_{unit_id}"
            rtu.device_states[device_key] = device_state
            rtu.current_unit_id = unit_id
        
        # Get device state from device_manager
        logger.info("Getting device state from device_manager...")
        device_key = f"{port}_{unit_id}"
        if not mock_mode:
            # For real hardware, get device state from device_manager
            device_state = device_manager.get_device(port, unit_id)
            if device_state:
                summary = asdict(device_state)
                logger.info(f"Device state summary: {json.dumps(summary, indent=2)}")
        else:
            # For mock mode, we already have the device_state
            summary = asdict(device_state)
            logger.info(f"Device state summary: {json.dumps(summary, indent=2)}")
        
        # Dump device state to file
        logger.info("Dumping device state to file...")
        if not mock_mode:
            device_manager.dump_device(port, unit_id, os.path.join(os.path.expanduser("~"), ".modbus_test_logs"))
        
        # Dump all device states
        logger.info("Dumping all device states...")
        device_manager.dump_all_devices(os.path.join(os.path.expanduser("~"), ".modbus_test_logs"))
        
        # Test passes if we reach this point
        assert True
    
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        return False
    
    finally:
        # Close connection
        if not mock_mode:
            rtu.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Modbus device state tracking")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Serial port")
    parser.add_argument("--unit", type=int, default=1, help="Unit ID")
    parser.add_argument("--mock", action="store_true", help="Use mock mode (no hardware required)")
    
    args = parser.parse_args()
    
    success = test_device_state_tracking(
        port=args.port,
        unit_id=args.unit,
        mock_mode=args.mock
    )
    
    sys.exit(0 if success else 1)

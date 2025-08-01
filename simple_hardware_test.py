#!/usr/bin/env python3
"""
Simplified script to test Modbus RTU hardware connection
"""

import logging
import sys
import time
import serial

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_serial_port(port='/dev/ttyACM0', baudrate=57600, timeout=1.0):
    """Test if a serial port is available and can be opened"""
    try:
        logger.info(f"Testing serial port {port} at {baudrate} baud...")
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        if ser.is_open:
            logger.info(f"✅ Successfully opened {port} at {baudrate} baud")
            ser.close()
            return True
        else:
            logger.error(f"❌ Failed to open {port}")
            return False
    except Exception as e:
        logger.error(f"❌ Error opening {port}: {e}")
        return False

def test_modbus_read_coils(port='/dev/ttyACM0', baudrate=57600, unit_id=1):
    """Test reading coils from a Modbus device"""
    try:
        logger.info(f"Testing Modbus read coils on {port}, unit ID {unit_id}...")
        
        # Open serial port
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=1.0)
        
        # Build Modbus RTU request to read coils 0-7 (function code 1)
        # Format: [unit_id, function_code, address_hi, address_lo, count_hi, count_lo, crc_lo, crc_hi]
        request = bytearray([unit_id, 1, 0, 0, 0, 8])
        
        # Calculate CRC (simple implementation)
        crc = 0xFFFF
        for b in request:
            crc ^= b
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        
        # Add CRC to request (little endian)
        request.append(crc & 0xFF)
        request.append((crc >> 8) & 0xFF)
        
        logger.info(f"Sending request: {request.hex()}")
        
        # Send request
        ser.write(request)
        
        # Wait for response
        time.sleep(0.1)
        
        # Read response
        if ser.in_waiting:
            response = ser.read(ser.in_waiting)
            logger.info(f"Received response: {response.hex()}")
            
            # Check if response is valid
            if len(response) >= 4 and response[0] == unit_id and response[1] == 1:
                logger.info("✅ Valid Modbus response received")
                
                # Parse coil states if response format is correct
                if len(response) >= 4 and response[2] == 1:  # Byte count
                    coil_byte = response[3]
                    coils = []
                    for i in range(8):
                        coils.append(bool(coil_byte & (1 << i)))
                    logger.info(f"Coil states: {coils}")
                
                return True
            else:
                logger.warning("⚠️ Invalid or unexpected response format")
                return False
        else:
            logger.error("❌ No response received")
            return False
    except Exception as e:
        logger.error(f"❌ Error in Modbus communication: {e}")
        return False
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

def scan_ports_and_test():
    """Scan common serial ports and test for Modbus devices"""
    ports = ['/dev/ttyACM0', '/dev/ttyUSB0', '/dev/ttyS0']
    baudrates = [9600, 19200, 38400, 57600, 115200]
    unit_ids = [1, 2, 3, 0, 255]
    
    logger.info("🔍 Scanning for Modbus devices...")
    
    # First check which ports are available
    available_ports = []
    for port in ports:
        if test_serial_port(port, 9600):
            available_ports.append(port)
    
    if not available_ports:
        logger.error("❌ No serial ports available")
        return False
    
    # Try each combination of port, baudrate, and unit ID
    for port in available_ports:
        for baudrate in baudrates:
            logger.info(f"Testing {port} at {baudrate} baud...")
            for unit_id in unit_ids:
                if test_modbus_read_coils(port, baudrate, unit_id):
                    logger.info(f"✅ Found Modbus device on {port} at {baudrate} baud, unit ID {unit_id}")
                    return True
    
    logger.error("❌ No Modbus devices found")
    return False

if __name__ == "__main__":
    logger.info("🚀 Starting simplified Modbus RTU hardware test")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--scan":
        success = scan_ports_and_test()
    else:
        # Default test on common port
        success = test_serial_port() and test_modbus_read_coils()
    
    if success:
        logger.info("✅ Hardware test completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Hardware test failed")
        sys.exit(1)

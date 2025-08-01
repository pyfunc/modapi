#!/usr/bin/env python3
import serial
import time
from typing import Optional, Tuple

# Configuration
PORT = '/dev/ttyACM0'
BAUDRATES = [9600, 19200, 38400, 57600, 115200]
UNIT_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 16, 247]  # Common Modbus unit IDs
TIMEOUT = 1  # seconds

def calculate_crc16(data: bytes) -> bytes:
    """Calculate Modbus RTU CRC16"""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little')

def build_modbus_request(unit_id: int, function_code: int, address: int, count: int = 1) -> bytes:
    """Build a Modbus RTU request"""
    # Modbus PDU: function code (1 byte) + start address (2 bytes) + count (2 bytes)
    pdu = bytes([
        function_code,              # Function code
        (address >> 8) & 0xFF,     # Start address high byte
        address & 0xFF,            # Start address low byte
        (count >> 8) & 0xFF,       # Count high byte
        count & 0xFF               # Count low byte
    ])
    
    # Modbus RTU: unit ID + PDU + CRC
    request = bytes([unit_id]) + pdu
    crc = calculate_crc16(request)
    return request + crc

def test_modbus_connection(port: str, baudrate: int, unit_id: int, function_code: int = 3) -> Tuple[bool, Optional[bytes]]:
    """Test Modbus connection with specific parameters"""
    try:
        # Open serial port
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=TIMEOUT
        )
        
        # Clear any existing data in the buffer
        if ser.in_waiting > 0:
            ser.read(ser.in_waiting)
        
        # Build and send the Modbus request
        request = build_modbus_request(unit_id, function_code, 0, 1)
        ser.write(request)
        
        # Wait for response (with timeout)
        start_time = time.time()
        while ser.in_waiting < 5 and (time.time() - start_time) < TIMEOUT:
            time.sleep(0.01)
        
        # Read the response
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            # Verify response length and CRC
            if len(response) >= 5:  # Minimum response length
                # Verify CRC
                crc = calculate_crc16(response[:-2])
                if crc == response[-2:]:
                    return True, response
                else:
                    print(f"  ⚠️  Invalid CRC in response")
            return True, response
        
        return False, None
        
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
        return False, None
        
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

def main():
    print(f"🔍 Testing Modbus device at {PORT}")
    print("================================")
    
    for baudrate in BAUDRATES:
        print(f"\n🔧 Testing baudrate: {baudrate}")
        print("-" * 30)
        
        # Try different function codes
        for function_code, func_name in [
            (3, "Read Holding Registers"),
            (4, "Read Input Registers"),
            (1, "Read Coils"),
            (2, "Read Discrete Inputs")
        ]:
            print(f"\n  📡 Function Code 0x{function_code:02X} ({func_name})")
            print("  " + "-" * 28)
            
            for unit_id in UNIT_IDS:
                print(f"  Testing Unit ID: {unit_id:3d}... ", end="", flush=True)
                success, response = test_modbus_connection(PORT, baudrate, unit_id, function_code)
                
                if success:
                    if response:
                        print(f"✅ Success! Response: {response.hex()}")
                        print(f"  🎉 Found working configuration: baudrate={baudrate}, unit_id={unit_id}, function_code={function_code}")
                        return  # Exit on first success
                    else:
                        print("❌ No response")
                else:
                    print("❌ Failed")
                
                # Small delay between tests
                time.sleep(0.1)
    
    print("\n❌ No working configuration found. Please check your connection and device settings.")

if __name__ == "__main__":
    main()

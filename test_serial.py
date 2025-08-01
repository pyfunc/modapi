#!/usr/bin/env python3
import serial
import time

def test_serial(port, baudrate=9600, timeout=1):
    """Test basic serial communication with the device"""
    try:
        print(f"Testing {port} at {baudrate} baud...")
        
        # Open serial port
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=timeout
        )
        
        # Clear any existing data
        if ser.in_waiting > 0:
            print(f"Clearing buffer: {ser.read(ser.in_waiting).hex()}")
        
        # Send a simple command (Modbus read holding registers for unit 1)
        # This is just to test if we get any response
        command = b'\x01\x03\x00\x00\x00\x01\x84\x0A'  # Read holding register 0 from unit 1
        print(f"Sending: {command.hex()}")
        ser.write(command)
        
        # Wait for response
        time.sleep(0.1)
        
        # Read response
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"Response: {response.hex()}")
            print(f"Response length: {len(response)} bytes")
        else:
            print("No response received")
        
        # Close the port
        ser.close()
        print("Port closed")
        
    except Exception as e:
        print(f"Error: {e}")
        if 'ser' in locals() and hasattr(ser, 'is_open') and ser.is_open:
            ser.close()
            print("Port closed due to error")

if __name__ == "__main__":
    port = "/dev/ttyACM0"
    baudrates = [9600, 19200, 38400]
    
    for baudrate in baudrates:
        test_serial(port, baudrate)
        print("\n" + "="*50 + "\n")

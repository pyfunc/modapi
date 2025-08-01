# Waveshare Modbus RTU Implementation Notes

This document describes the non-standard aspects of Waveshare's Modbus RTU implementation and the workarounds implemented in our custom RTU module to handle these quirks.

## Overview

Waveshare produces a variety of Modbus RTU devices including relay modules, analog I/O modules, and other industrial control components. While these devices are advertised as Modbus RTU compatible, they implement several non-standard behaviors that require special handling for reliable communication.

## Non-Standard Behaviors

### 1. CRC Calculation Variations

Standard Modbus RTU uses CRC-16 with polynomial 0xA001 (reversed 0x8005) and initial value 0xFFFF. Waveshare devices exhibit the following CRC variations:

- **Byte Order Swapping**: Some devices return CRC bytes in big-endian order instead of the standard little-endian order
- **Alternative Initial Values**: Some devices use 0x0000 as the initial CRC value instead of 0xFFFF
- **Alternative Polynomials**: Some devices use 0x8408 as the polynomial
- **Reversed Data Bytes**: Some devices calculate CRC on reversed data bytes

Our implementation tries multiple CRC calculation methods to accommodate these variations.

### 2. Function Code Handling

Waveshare devices often respond with different function codes than what was requested:

- Responding to function code 0x03 (Read Holding Registers) with 0x04 (Read Input Registers) or vice versa
- Using custom function codes in the range 0x41-0x44 and 0x65-0x68
- Sometimes responding with function code 0x00 (zero)
- Off-by-one errors in function codes (e.g., responding to 0x03 with 0x02 or 0x04)

Our implementation includes mappings for these non-standard function code responses.

### 3. Unit ID Handling

Waveshare devices sometimes respond with:

- Unit ID 0 (broadcast address) regardless of the requested unit ID
- Unexpected unit IDs that don't match the request
- Multiple devices responding on the same bus with different unit IDs

Our implementation allows processing responses despite unit ID mismatches in certain cases.

### 4. Timing and Response Characteristics

Waveshare devices have specific timing requirements:

- **Variable Response Timing**: Devices may need longer delays between request and response
- **Chunked Responses**: Some devices send data in chunks with small delays between chunks
- **Buffer Clearing Requirements**: Devices may require more thorough buffer clearing between requests
- **Exponential Backoff**: Devices may respond better with progressively longer delays between retries

Our implementation uses adaptive timing and exponential backoff for retries.

## Implemented Workarounds

### CRC Validation

```python
# Try multiple CRC calculation methods
# 1. Standard CRC calculation (little-endian)
# 2. Swapped byte order (big-endian)
# 3. Alternative initial value (0x0000)
# 4. Alternative polynomial (0x8408)
# 5. Reversed data bytes
```

### Function Code Compatibility

```python
# Compatible function code pairs for Waveshare devices
compatible_pairs = [
    # Standard Modbus compatible pairs
    (FUNC_READ_HOLDING_REGISTERS, FUNC_READ_INPUT_REGISTERS),
    
    # Waveshare-specific mappings
    (0x41, FUNC_READ_HOLDING_REGISTERS),
    (0x42, FUNC_READ_INPUT_REGISTERS),
    # ... and more
]
```

### Adaptive Retry Mechanism

```python
# Scale wait time based on retry count
wait_scale = 1.0 + (retries * 0.5)  # Increase by 50% each retry
wait_time = max(0.1, transmission_time * 2 * wait_scale)
```

## Troubleshooting Common Issues

### CRC Errors

If you encounter persistent CRC errors:
- Try different baud rates (9600 is most common for Waveshare)
- Ensure proper grounding and wiring
- Try shorter cable lengths
- Add a small delay (10-50ms) between requests

### Function Code Mismatches

If function code mismatches occur:
- Verify the device supports the requested function
- Check the device documentation for supported function codes
- Try alternative function codes (e.g., use 0x04 instead of 0x03)

### Timeout Issues

If timeout errors persist:
- Increase the timeout value (default is 1 second)
- Try a lower baud rate
- Increase the number of retries
- Add longer delays between retries

## Device-Specific Notes

### Relay Modules

- Often respond with function code 0x00 for read coil operations
- May require multiple write attempts for reliable operation
- Sometimes report success even when the operation failed

### Analog Input Modules

- May use non-standard register mapping
- Often require specific data formats for configuration
- May have timing-sensitive calibration procedures

### RS485 Adapters

- USB-to-RS485 adapters may require specific drivers
- Some adapters have poor buffer handling requiring longer delays
- Automatic flow control may interfere with Modbus timing

## Conclusion

While Waveshare Modbus RTU devices don't fully comply with the standard protocol, our custom implementation handles these quirks to provide reliable communication. The module includes extensive logging to help diagnose issues and implements multiple fallback mechanisms for robust operation.

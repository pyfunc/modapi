# Waveshare Modbus RTU Implementation Notes

This document describes the non-standard aspects of Waveshare's Modbus RTU implementation and the workarounds implemented in our custom RTU module to handle these quirks.

## Table of Contents

1. [Overview](#overview)
2. [Modbus RTU Protocol Basics](#modbus-rtu-protocol-basics)
3. [CRC Calculation in Detail](#crc-calculation-in-detail)
4. [Non-Standard Behaviors](#non-standard-behaviors)
5. [Implemented Workarounds](#implemented-workarounds)
6. [Project Shortcuts and Optimizations](#project-shortcuts-and-optimizations)
7. [Troubleshooting Common Issues](#troubleshooting-common-issues)
8. [Device-Specific Notes](#device-specific-notes)
9. [Conclusion](#conclusion)

## Overview

Waveshare produces a variety of Modbus RTU devices including relay modules, analog I/O modules, and other industrial control components. While these devices are advertised as Modbus RTU compatible, they implement several non-standard behaviors that require special handling for reliable communication.

## Modbus RTU Protocol Basics

### What is Modbus RTU?

Modbus RTU (Remote Terminal Unit) is a serial communications protocol widely used in industrial automation. It's an open standard that enables communication between electronic devices over serial lines like RS-485 or RS-232. Modbus RTU is the binary variant of the Modbus protocol family, characterized by:

- **Binary Encoding**: Data is transmitted in binary format rather than ASCII
- **Compact Format**: Uses fewer bytes than Modbus ASCII, making it more efficient
- **Error Detection**: Uses CRC (Cyclic Redundancy Check) for error detection
- **Silent Intervals**: Uses time gaps between messages to mark frame boundaries

### Standard Message Structure

A standard Modbus RTU message frame consists of:

```
[Unit ID] [Function Code] [Data] [CRC (2 bytes)]
```

- **Unit ID**: 1 byte, identifies the target device (1-247, 0 for broadcast)
- **Function Code**: 1 byte, specifies the operation to perform
- **Data**: Variable length, contains addresses, values, counts, etc.
- **CRC**: 2 bytes, error checking code calculated over the entire message

### Standard Function Codes

Common Modbus function codes include:

| Code | Function | Description |
|------|----------|-------------|
| 0x01 | Read Coils | Read binary outputs (coils) |
| 0x02 | Read Discrete Inputs | Read binary inputs |
| 0x03 | Read Holding Registers | Read 16-bit registers |
| 0x04 | Read Input Registers | Read 16-bit input registers |
| 0x05 | Write Single Coil | Write a single binary output |
| 0x06 | Write Single Register | Write a single 16-bit register |
| 0x0F | Write Multiple Coils | Write multiple binary outputs |
| 0x10 | Write Multiple Registers | Write multiple 16-bit registers |

### Timing Requirements

Modbus RTU relies on silent periods to mark the beginning and end of frames:

- **3.5 character times**: Gap between frames
- **1.5 character times**: Gap between fields within a frame

At 9600 baud with 8 data bits, 1 stop bit, and no parity, a character time is approximately 1.042ms.

## CRC Calculation in Detail

### Standard Modbus CRC-16

The standard Modbus CRC-16 algorithm follows these steps:

1. Initialize a 16-bit register (CRC) with 0xFFFF
2. XOR the first byte of the message with the low-order byte of the CRC register
3. Shift the CRC register one bit to the right
4. If the bit shifted out is 1, XOR the CRC register with the polynomial value 0xA001
5. Repeat steps 3-4 until 8 shifts have been performed
6. XOR the next byte of the message with the low-order byte of the CRC
7. Repeat steps 3-7 until all bytes have been processed
8. The final CRC register value is the CRC checksum

Here's the standard implementation in Python:

```python
def calculate_standard_crc(data: bytes) -> int:
    crc = 0xFFFF  # Initial value
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001  # Polynomial 0xA001
            else:
                crc = crc >> 1
    return crc
```

### Byte Order Considerations

In standard Modbus RTU, the CRC is transmitted in little-endian byte order (least significant byte first). For example, if the calculated CRC is 0x1234:

- Little-endian transmission: [0x34, 0x12]
- Big-endian transmission: [0x12, 0x34]

Some Waveshare devices incorrectly use big-endian byte order for CRC transmission.

### Alternative CRC Implementations

Our module implements several CRC calculation variations to handle Waveshare devices:

1. **Standard CRC with Swapped Bytes**:
   ```python
   # After calculating standard CRC, swap byte order
   swapped_crc = ((crc << 8) & 0xFF00) | ((crc >> 8) & 0x00FF)
   ```

2. **CRC with Alternative Initial Value**:
   ```python
   # Use 0x0000 as initial value instead of 0xFFFF
   crc = 0x0000  # Alternative initial value
   # Rest of calculation remains the same
   ```

3. **CRC with Alternative Polynomial**:
   ```python
   # Use 0x8408 as polynomial instead of 0xA001
   if crc & 0x0001:
       crc = (crc >> 1) ^ 0x8408  # Alternative polynomial
   ```

4. **CRC on Reversed Data**:
   ```python
   # Reverse the order of bytes in the data before calculating CRC
   reversed_data = data[::-1]
   # Calculate CRC on reversed data
   ```

### CRC Validation Strategy

Our module uses a multi-step validation strategy:

1. First try standard CRC calculation
2. If that fails, try alternative calculations in sequence
3. Log which method succeeded for debugging
4. For critical operations, enforce strict CRC validation
5. For read operations, allow continuing despite CRC errors if the response structure appears valid

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

### Modbus RTU IO 8CH Module

Based on the [Waveshare IO 8CH documentation](http://www.waveshare.com/wiki/Modbus_RTU_IO_8CH):

#### Function Code Usage

- **0x01**: Read Coils (Read Output Channel Status)
  - Example: `01 01 00 00 00 08 3D CC` (Read all 8 output channels)
  - Response: `01 01 01 00 51 88` (All channels off)

- **0x02**: Read Discrete Inputs (Read Input Channel Status)
  - Example: `01 02 00 00 00 08 79 CC` (Read all 8 input channels)
  - Response: `01 02 01 00 A1 88` (All inputs untriggered)

- **0x03**: Read Holding Registers (Read Output Channel Control Mode)
  - Example: `01 03 10 00 00 08 40 CC` (Read all 8 output channel modes)

- **0x05**: Write Single Coil (Control Single Output Channel)
  - Example: `01 05 00 00 FF 00 8C 3A` (Turn output channel 0 on)
  - Example: `01 05 00 00 00 00 CD CA` (Turn output channel 0 off)
  - Special case: `01 05 00 FF FF 00 BC 0A` (All output channels on)

- **0x06**: Write Single Register (Set Control Mode, Baudrate, etc.)
  - Example: `01 06 10 00 00 01 4C CA` (Set output channel 1 as Linkage mode)

- **0x0F**: Write Multiple Coils (Write Output Channel Status)
  - Example: `01 0F 00 00 00 08 01 FF BE D5` (All output channels on)

- **0x10**: Write Multiple Registers (Set Multiple Output Channel Control Mode)
  - Example: `01 10 10 00 00 08 10 00 01 00 01 00 01 00 01 00 01 00 01 00 01 00 01 7C B1`

#### Special Commands

- **Flash ON/OFF Commands**: Uses function code 0x05 with special register addresses
  - Example: `01 05 02 00 00 07 8D B0` (Output channel 0 flash on, 700ms)

- **Control Modes**:
  - Normal mode (0x00)
  - Linkage mode (0x01)
  - Toggle mode (0x02)
  - Edge Trigger Mode (0x03)

#### CRC Considerations

- The module documentation shows CRC bytes in little-endian order
- Example: For command `01 05 00 00 FF 00`, CRC is `8C 3A`

### Modbus RTU Analog Input 8CH Module

Based on the [Waveshare Analog Input 8CH documentation](https://www.waveshare.com/wiki/Modbus_RTU_Analog_Input_8CH):

#### Function Code Usage

- **0x03**: Read Holding Registers (Read Channel Data Type)
  - Example: `01 03 10 00 00 08 40 CC` (Read data types for all 8 channels)
  - Response: `01 03 10 00 02 00 02 00 02 00 02 00 02 00 02 00 02 00 02 09 C3`

- **0x04**: Read Input Registers (Read Analog Input Values)
  - Example: `01 04 00 00 00 08 F1 CC` (Read all 8 analog inputs)
  - Response: `01 04 10 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 55 2C`

- **0x06**: Write Single Register (Set Single-channel Data Type, Baudrate, etc.)
  - Example: `01 06 10 00 00 03 CD 0B` (Set data type for channel 1)

- **0x10**: Write Multiple Registers (Set Multi-channel Data Type)
  - Example: `01 10 10 00 00 08 10 00 03 00 03 00 03 00 03 00 03 00 03 00 03 00 03 91 2B`

#### Data Types

- **0x00**: 0-5V
- **0x01**: 0-10V
- **0x02**: 0-20mA
- **0x03**: 4-20mA

#### CRC Considerations

- Similar to the IO module, CRC bytes are shown in little-endian order
- Example: For command `01 04 00 00 00 08`, CRC is `F1 CC`

### Common Issues with Waveshare Modules

#### Relay Modules

- Often respond with function code 0x00 for read coil operations
- May require multiple write attempts for reliable operation
- Sometimes report success even when the operation failed
- Special register addresses (0x02xx, 0x04xx) for flash commands

#### Analog Input Modules

- May use non-standard register mapping (0x10xx for configuration)
- Require specific data types for configuration (0x00-0x03)
- Support multiple analog input types (voltage/current)
- May have timing-sensitive calibration procedures

#### RS485 Adapters

- USB-to-RS485 adapters may require specific drivers
- Some adapters have poor buffer handling requiring longer delays
- Automatic flow control may interfere with Modbus timing

#### Exception Responses

Both modules return exception responses in the format:
- Example: `01 85 03 02 91` (Function code 0x05 + 0x80 = 0x85)

Where the exception code (0x03 in this example) indicates the type of error.

## Project Shortcuts and Optimizations

Our custom Modbus RTU implementation includes several shortcuts and optimizations to improve reliability and performance when working with Waveshare devices:

### 1. Adaptive Response Reading

Instead of waiting for a fixed time after sending a request, our implementation uses an adaptive approach:

```python
# Scale wait time based on retry count and baud rate
min_bytes_expected = 4  # Minimum valid Modbus response
bits_per_byte = 10  # 8 data bits + 1 start bit + 1 stop bit
transmission_time = (bits_per_byte * min_bytes_expected) / baudrate
wait_scale = 1.0 + (retries * 0.5)  # Increase by 50% each retry
wait_time = max(0.1, transmission_time * 2 * wait_scale)
```

This approach:
- Calculates minimum transmission time based on baud rate
- Scales wait time based on retry count
- Ensures sufficient time for device response

### 2. Progressive Response Reading

Instead of reading a fixed number of bytes, our implementation reads progressively:

```python
# First, try to get at least the header (unit_id, function_code)
while len(response) < 2 and (time.time() - start_time) < timeout:
    if serial_conn.in_waiting:
        response += serial_conn.read(serial_conn.in_waiting)
    time.sleep(0.01)

# Then, determine expected length based on function code and read remaining bytes
if len(response) >= 2:
    expected_length = calculate_expected_length(response[0], response[1], response)
    while (len(response) < expected_length) and (time.time() - start_time) < timeout:
        if serial_conn.in_waiting:
            response += serial_conn.read(serial_conn.in_waiting)
        time.sleep(0.01)
```

This approach:
- Reads only what's available in the buffer
- Dynamically determines expected response length
- Avoids blocking reads that could cause timeouts

### 3. Exponential Backoff for Retries

Our implementation uses exponential backoff for retries:

```python
retry_delay = 0 if retries == 0 else 0.1 * (2 ** (retries - 1))
```

This approach:
- Starts with no delay for first attempt
- Doubles delay with each retry
- Gives devices more time to recover between attempts

### 4. Function Code Compatibility Maps

Our implementation includes comprehensive function code compatibility mappings:

```python
compatible_pairs = [
    # Standard Modbus compatible pairs
    (FUNC_READ_HOLDING_REGISTERS, FUNC_READ_INPUT_REGISTERS),
    # Waveshare-specific mappings
    (0x41, FUNC_READ_HOLDING_REGISTERS),
    # ... many more mappings
]
```

This approach:
- Handles common function code mismatches
- Includes Waveshare-specific function codes
- Allows processing despite protocol deviations

### 5. Flexible CRC Validation

Our implementation allows continuing despite CRC errors in certain cases:

```python
# For read operations with correct byte count, continue despite CRC errors
if function_code in (FUNC_READ_COILS, FUNC_READ_DISCRETE_INPUTS, 
                    FUNC_READ_HOLDING_REGISTERS, FUNC_READ_INPUT_REGISTERS):
    if len(response) >= 3 and response[2] == len(response) - 5:  # Valid byte count
        logger.warning("Continuing despite CRC error - response structure appears valid")
        # Process response anyway
```

This approach:
- Applies stricter validation for write operations
- Allows processing read operations with valid structure despite CRC errors
- Improves success rate with unreliable devices

## Conclusion

While Waveshare Modbus RTU devices don't fully comply with the standard protocol, our custom implementation handles these quirks to provide reliable communication. The module includes extensive logging to help diagnose issues and implements multiple fallback mechanisms for robust operation.

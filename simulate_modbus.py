#!/usr/bin/env python3
"""
Modbus RTU Server Simulator
"""
from pymodbus.server.sync import StartSerialServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock

def run_simulator(port: str = "/tmp/ptyp0", baudrate: int = 9600):
    """Run a Modbus RTU server simulator"""
    # Initialize data stores
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0]*100),  # Discrete Inputs
        co=ModbusSequentialDataBlock(0, [0]*100),  # Coils
        hr=ModbusSequentialDataBlock(0, [0]*100),  # Holding Registers
        ir=ModbusSequentialDataBlock(0, [0]*100)   # Input Registers
    )
    
    context = ModbusServerContext(slaves=store, single=True)
    
    # Set some test values
    store.setValues(1, 0, [1, 0, 1, 0])  # Coils 0-3
    store.setValues(3, 0, [1234, 5678, 9012])  # Holding Registers 0-2
    
    print(f"Starting Modbus RTU simulator on {port} at {baudrate} baud")
    print("Test values set:")
    print("  - Coils 0-3: [1, 0, 1, 0]")
    print("  - Holding Registers 0-2: [1234, 5678, 9012]")
    
    # Start the server
    StartSerialServer(
        context,
        port=port,
        baudrate=baudrate,
        timeout=0.1
    )

if __name__ == "__main__":
    run_simulator()

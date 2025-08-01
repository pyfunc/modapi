#!/usr/bin/env python3
"""
Test script for Modbus API with simulator
"""
import time
import subprocess
import requests
import signal
import sys
from pathlib import Path

# Configuration
MODBUS_PORT = "/tmp/ptyp0"
API_URL = "http://localhost:5000/api"

def start_simulator():
    """Start the Modbus simulator in a subprocess"""
    print("Starting Modbus simulator...")
    return subprocess.Popen(
        ["python", "simulate_modbus.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

def start_api_server():
    """Start the API server in a subprocess"""
    print("Starting API server...")
    return subprocess.Popen(
        ["python", "-m", "modapi.api"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

def wait_for_server(url, timeout=10):
    """Wait for the server to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/status", timeout=1)
            if response.status_code == 200:
                print("Server is ready!")
                return True
        except (requests.exceptions.RequestException, ConnectionError):
            time.sleep(0.5)
    print("Timed out waiting for server")
    return False

def test_api():
    """Test the API endpoints"""
    print("\nTesting API endpoints...")
    
    # Test status endpoint
    print("\n1. Testing /api/status...")
    response = requests.get(f"{API_URL}/status")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test reading coils
    print("\n2. Testing /api/coils/0/4...")
    response = requests.get(f"{API_URL}/coils/0/4")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test reading holding registers
    print("\n3. Testing /api/holding_registers/0/3...")
    response = requests.get(f"{API_URL}/holding_registers/0/3")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def main():
    """Main function"""
    # Start the simulator
    simulator = start_simulator()
    time.sleep(2)  # Give the simulator time to start
    
    try:
        # Start the API server
        api_server = start_api_server()
        
        # Wait for the server to be ready
        if not wait_for_server(API_URL):
            print("Failed to start server")
            return 1
        
        # Test the API
        test_api()
        
        # Keep the server running until interrupted
        print("\nPress Ctrl+C to stop the server...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Clean up
        print("Stopping API server...")
        api_server.terminate()
        print("Stopping Modbus simulator...")
        simulator.terminate()
        
        # Wait for processes to terminate
        api_server.wait()
        simulator.wait()
        
        print("Done!")

if __name__ == "__main__":
    sys.exit(main())

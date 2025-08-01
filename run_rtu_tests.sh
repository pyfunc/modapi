#!/bin/bash

# Navigate to the project root directory
cd "$(dirname "$0")"

# Run the RTU integration tests
echo "Running RTU integration tests..."
python3 -m unittest test_rtu_integration.py -v

# Run the unit tests as well
echo -e "\nRunning unit tests..."
python3 -m unittest discover -s tests -p "test_rtu*.py" -v

echo -e "\nTest execution complete."

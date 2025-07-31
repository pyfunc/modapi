"""
ModbusAPI - Main entry point for running as a module
"""

import sys
from modbusapi.modbusapi.__main__ import main

if __name__ == '__main__':
    sys.exit(main())

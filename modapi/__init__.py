"""
modapi - Unified API for Modbus communication
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

__version__ = '0.1.0'

# Configure logging
logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format=os.environ.get(
        'LOG_FORMAT',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
)
logger = logging.getLogger(__name__)

# Load environment variables from .env files
def load_env_files():
    """Load environment variables from .env files in project directories"""
    # Try to load from current directory
    if load_dotenv(dotenv_path='.env'):
        logger.debug('Loaded .env from current directory')
    
    # Try to load from parent directory (project root)
    parent_env = Path(__file__).parent.parent.parent / '.env'
    if parent_env.exists() and load_dotenv(dotenv_path=parent_env):
        logger.debug(f'Loaded .env from {parent_env}')
    
    # Try to load from hyper directory
    hyper_env = Path(__file__).parent.parent.parent / 'hyper' / '.env'
    if hyper_env.exists() and load_dotenv(dotenv_path=hyper_env):
        logger.debug(f'Loaded .env from {hyper_env}')

# Load environment variables
load_env_files()

# Import components after environment is configured
from .client import ModbusClient
from .api import create_rest_app, start_mqtt_broker
from .shell import main as shell_main

__all__ = ['ModbusClient', 'create_rest_app', 'start_mqtt_broker', 'shell_main', 'load_env_files']

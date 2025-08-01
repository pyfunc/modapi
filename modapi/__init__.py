"""
modapi - Unified API for Modbus communication
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

__version__ = '0.1.6'

# Configure logging
logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format=os.environ.get(
        'LOG_FORMAT',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
)
logger = logging.getLogger(__name__)


def load_env_files():
    """Load environment variables from .env files in project directories."""
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
# Import rest first to avoid circular imports
from modapi.api.rest import create_rest_app  # noqa: E402
from modapi.api.mqtt import start_mqtt_broker  # noqa: E402
from modapi.api.cmd import execute_command  # noqa: E402
from modapi.api.rtu import ModbusRTU, create_rtu_client, test_rtu_connection  # noqa: E402
from modapi.api.tcp import ModbusTCP, create_tcp_client, test_tcp_connection  # noqa: E402

# Import shell last to avoid circular imports
from modapi.api.shell import interactive_mode as shell_main  # noqa: E402


__all__ = [
    'create_rest_app',
    'shell_main',
    'start_mqtt_broker',
    'execute_command',
    'ModbusRTU',
    'create_rtu_client',
    'test_rtu_connection',
    'ModbusTCP',
    'create_tcp_client',
    'test_tcp_connection',
]

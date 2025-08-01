#!/usr/bin/env python3
"""
run_cli.py - Helper script to run modapi CLI with proper Python environment
"""

import os
import sys
import subprocess
import shlex

def main():
    """
    Main entry point for CLI runner
    
    This script ensures the modapi package is run with the correct Python
    interpreter and environment variables.
    """
    # Get the path to the current Python interpreter
    python_exe = sys.executable
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set PYTHONPATH to include the project root
    env = os.environ.copy()
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{script_dir}:{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = script_dir
    
    # Check if we have command line arguments
    if len(sys.argv) > 1:
        # Process the command line arguments
        args = sys.argv[1:]
        
        # Check if the first argument is a direct Modbus command (wc, rc, etc.)
        direct_commands = ['wc', 'rc', 'ri', 'rh', 'wh']
        if args[0] in direct_commands:
            # Convert to new format: modapi cmd <command> <args>
            cmd = [python_exe, '-m', 'modapi', 'cmd', args[0]] + args[1:]
        else:
            # Pass arguments as is
            cmd = [python_exe, '-m', 'modapi'] + args
    else:
        # No arguments, run the shell by default
        cmd = [python_exe, '-m', 'modapi', 'shell']
    
    # Print the command being run (for debugging)
    cmd_str = ' '.join(shlex.quote(arg) for arg in cmd)
    print(f"Running: {cmd_str}")
    
    # Execute the command
    try:
        return subprocess.call(cmd, env=env)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1

if __name__ == '__main__':
    sys.exit(main())

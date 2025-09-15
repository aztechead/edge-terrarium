"""
Shell command execution utilities.
"""

import subprocess
import shlex
import logging
from typing import List, Optional, Tuple, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class ShellError(Exception):
    """Exception raised when shell command fails."""
    pass


def run_command(
    command: Union[str, List[str]],
    cwd: Optional[Union[str, Path]] = None,
    capture_output: bool = True,
    check: bool = True,
    timeout: Optional[int] = None,
    env: Optional[dict] = None
) -> subprocess.CompletedProcess:
    """
    Run a shell command.
    
    Args:
        command: Command to run (string or list)
        cwd: Working directory
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit
        timeout: Command timeout in seconds
        env: Environment variables
        
    Returns:
        CompletedProcess object
        
    Raises:
        ShellError: If command fails and check=True
    """
    if isinstance(command, str):
        command = shlex.split(command)
    
    logger.debug(f"Running command: {' '.join(command)}")
    if cwd:
        logger.debug(f"Working directory: {cwd}")
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=capture_output,
            check=check,
            timeout=timeout,
            env=env,
            text=True
        )
        
        if capture_output and result.stdout:
            logger.debug(f"Command output: {result.stdout}")
        if capture_output and result.stderr:
            logger.debug(f"Command stderr: {result.stderr}")
            
        return result
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed with exit code {e.returncode}: {' '.join(command)}"
        if e.stdout:
            error_msg += f"\nStdout: {e.stdout}"
        if e.stderr:
            error_msg += f"\nStderr: {e.stderr}"
        
        logger.error(error_msg)
        raise ShellError(error_msg) from e
        
    except subprocess.TimeoutExpired as e:
        error_msg = f"Command timed out after {timeout} seconds: {' '.join(command)}"
        logger.error(error_msg)
        raise ShellError(error_msg) from e


def run_command_async(
    command: Union[str, List[str]],
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[dict] = None
) -> subprocess.Popen:
    """
    Run a shell command asynchronously.
    
    Args:
        command: Command to run (string or list)
        cwd: Working directory
        env: Environment variables
        
    Returns:
        Popen object
    """
    if isinstance(command, str):
        command = shlex.split(command)
    
    logger.debug(f"Running async command: {' '.join(command)}")
    if cwd:
        logger.debug(f"Working directory: {cwd}")
    
    return subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


def check_command_exists(command: str) -> bool:
    """
    Check if a command exists in PATH.
    
    Args:
        command: Command name to check
        
    Returns:
        True if command exists, False otherwise
    """
    try:
        run_command(f"which {command}", check=True)
        return True
    except ShellError:
        return False


def get_command_output(
    command: Union[str, List[str]],
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[int] = None
) -> str:
    """
    Get the output of a command.
    
    Args:
        command: Command to run
        cwd: Working directory
        timeout: Command timeout
        
    Returns:
        Command output as string
    """
    result = run_command(command, cwd=cwd, timeout=timeout)
    return result.stdout.strip()

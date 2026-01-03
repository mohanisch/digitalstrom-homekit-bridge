import errno
import os
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

import yaml


def read_config(path):
    with open(path, 'r') as file:
        try:
            cur_yaml = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            print(exc)

    return cur_yaml


def write_config(path, data):
    cur_yaml = {}
    if isWritable(path):
        # Read existing config if file exists
        if os.path.exists(path):
            with open(path, 'r') as file:
                try:
                    cur_yaml = yaml.safe_load(file)
                except yaml.YAMLError as exc:
                    print(exc)

        if cur_yaml is None:
            cur_yaml = {}

        cur_yaml.update(data)
        # Write config with secure permissions (0o600 = read/write for owner only)
        # Use os.open to set permissions atomically
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode=0o600)
        try:
            with os.fdopen(fd, 'w') as file:
                yaml.safe_dump(cur_yaml, file, indent=2)
        except Exception:
            # If writing fails, close the fd and re-raise
            os.close(fd)
            raise


# Global thread pool executor for async operations
# Limited to 10 threads to prevent resource exhaustion
_thread_pool_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="dsbridge")


def threaded(fn):
    """
    Decorator to run a function in a thread pool executor.
    Uses ThreadPoolExecutor instead of unlimited daemon threads to prevent resource exhaustion.
    Returns None to avoid JSON serialization issues with Future objects.
    
    Args:
        fn: Function to execute asynchronously
        
    Returns:
        Decorated function that returns None (fire-and-forget)
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Submit task to thread pool
        future = _thread_pool_executor.submit(fn, *args, **kwargs)
        # Return None to maintain backward compatibility
        # The future will be handled by the executor
        return None
    
    return wrapper


def shutdown_thread_pool():
    """
    Shutdown the global thread pool executor.
    Should be called during application shutdown.
    """
    global _thread_pool_executor
    _thread_pool_executor.shutdown(wait=True, timeout=5)


def remove_control_characters(s):
    return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")


def isWritable(path):
    """
    Check if a file path is writable.
    
    Args:
        path: File path to check
        
    Returns:
        True if path is writable, False otherwise
    """
    # Handle empty path or path without directory component
    if not path:
        return False
    
    dir_path = os.path.dirname(path)
    
    # If path has no directory component (e.g., just filename), use current directory
    if not dir_path:
        dir_path = os.getcwd()
    
    # Check if directory exists and is writable using os.access
    if not os.path.exists(dir_path):
        # Try to create parent directories if they don't exist
        try:
            os.makedirs(dir_path, mode=0o700, exist_ok=True)
        except OSError:
            return False
    
    # Check write permission on directory
    if not os.access(dir_path, os.W_OK):
        return False
    
    # If file exists, check if it's writable
    if os.path.exists(path):
        if not os.access(path, os.W_OK):
            return False
    
    # Try to open file in append mode to verify write access without creating temp files
    try:
        with open(path, 'a'):
            pass
        return True
    except (OSError, IOError) as e:
        if e.errno == errno.EACCES:
            return False
        # For other errors (e.g., permission denied), return False
        return False


def wait_until(somepredicate, timeout=600, period=0.25, *args, **kwargs):
    mustend = time.time() + timeout
    while time.time() < mustend:

        if somepredicate(*args, **kwargs):
            return True
        time.sleep(period)
    return False

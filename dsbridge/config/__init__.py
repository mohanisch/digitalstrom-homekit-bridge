import argparse
import os
import logging

import yaml

from ..const import RESTART_EXIT_CODE

ENV_PERSIST_FILE_PATH = os.environ.get('PERSIST_FILE_PATH')
ENV_HOMEKIT_ADDRESS = os.environ.get('HOMEKIT_ADDRESS')
ENV_HOMEKIT_PORT = os.environ.get('HOMEKIT_PORT')

DEFAULT_DATA_PATH = ENV_PERSIST_FILE_PATH if ENV_PERSIST_FILE_PATH else '/tmp'
DEFAULT_HOMEKIT_ADDRESS = ENV_HOMEKIT_ADDRESS if ENV_HOMEKIT_ADDRESS else None
DEFAULT_HOMEKIT_PORT = ENV_HOMEKIT_PORT if ENV_HOMEKIT_PORT else 51826


def get_arguments() -> argparse.Namespace:
    import sys

    # Handle Docker case where arguments might be passed as single strings with spaces
    # e.g., "--config-path /config" instead of "--config-path", "/config"
    processed_args = []
    for arg in sys.argv[1:]:
        # If argument contains space and starts with --, split it
        if arg.startswith('--') and ' ' in arg:
            parts = arg.split(' ', 1)
            processed_args.extend(parts)
        else:
            processed_args.append(arg)

    # Temporarily replace sys.argv for argparse
    original_argv = sys.argv
    sys.argv = [sys.argv[0]] + processed_args

    try:
        parser = argparse.ArgumentParser(
            description="Homekit bridge for digitalStrom",
            epilog=f"If restart is requested, exits with code {RESTART_EXIT_CODE}",
        )
        parser.add_argument(
            "--dss-hostname", help="Hostname or ip-address of digitalStrom server",
            default=os.environ.get('DSS_HOSTNAME')
        )
        parser.add_argument(
            "--dss-http-port", help="Port to reach digitalStrom http server, default 8080", default="8080"
        )
        parser.add_argument(
            "--ws-port", help="Port to reach digitalStrom websocket, default 8090", default="8090"
        )
        parser.add_argument(
            "--homekit-bridge-name", help="Name how the bridge should be appear in Home", default="dS Homebridge"
        )
        parser.add_argument(
            "--homekit-address", help="IP address of host on which the bridge is running",
            default=DEFAULT_HOMEKIT_ADDRESS
        )
        parser.add_argument(
            "--homekit-port", help="Port number homekit is working on", default=DEFAULT_HOMEKIT_PORT
        )
        parser.add_argument(
            "--persit-file-name", help="Name for persist file, default is 'home.state'", default="home.state"
        )
        parser.add_argument(
            "--persit-file-path", help="Path to persist file, default is '/tmp'", default=DEFAULT_DATA_PATH
        )
        parser.add_argument(
            "--loglevel", help="Loglevel: INFO, DEBUG", default="INFO"
        )
        parser.add_argument(
            "--token", help="Token created on dss", default="xxx"
        )
        required_named = parser.add_argument_group('required named arguments')
        required_named.add_argument(
            "--config-path", help="Path to config.yml", default=os.environ.get('CONFIG_PATH'), required=True
        )
        arguments = parser.parse_args()

        return arguments
    finally:
        # Restore original sys.argv
        sys.argv = original_argv


_config_cache = None
_config_cache_time = 0
_config_cache_ttl = 2
_config_file_path = None


def read_config_file(force_reload=False):
    """
    Read config file with caching to reduce I/O on Raspberry Pi.
    
    Args:
        force_reload: If True, bypass cache and reload from file
        
    Returns:
        Config dictionary
    """
    global _config_cache, _config_cache_time, _config_file_path

    import time

    # Initialize file path on first call
    if _config_file_path is None:
        _config_file_path = args.config_path + "/config.yml"

    current_time = time.time()

    # Return cached config if still valid and not forcing reload
    if (not force_reload and
            _config_cache is not None and
            current_time - _config_cache_time < _config_cache_ttl):
        return _config_cache

    import os.path
    file_exists = os.path.isfile(_config_file_path)

    if not file_exists:
        # Create empty file if it doesn't exist and set secure permissions
        try:
            with open(_config_file_path, "w") as f:
                pass
            try:
                os.chmod(_config_file_path, 0o600)
            except Exception:
                logging.warning("Failed to set permissions on config file %s", _config_file_path)
        except Exception as e:
            logging.error("Error creating config file: %s", e)
            return {}

    _file = {}
    try:
        with open(_config_file_path, "r") as stream:
            _file = yaml.safe_load(stream)
            if _file is None:
                _file = {}
    except yaml.YAMLError as exc:
        logging.error("Error parsing config file: %s", exc)
        return _config_cache if _config_cache is not None else {}
    except Exception as e:
        logging.error("Error reading config file: %s", e, exc_info=True)
        return _config_cache if _config_cache is not None else {}

    # Update cache
    _config_cache = _file
    _config_cache_time = current_time

    return _file


def invalidate_config_cache():
    """Invalidate config cache to force reload on next read."""
    global _config_cache, _config_cache_time
    _config_cache = None
    _config_cache_time = 0


args = get_arguments()

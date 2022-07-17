import argparse
import os

import yaml
from ..const import RESTART_EXIT_CODE

ENV_PERSIST_FILE_PATH = os.environ.get('PERSIST_FILE_PATH')
DEFAULT_DATA_PATH = ENV_PERSIST_FILE_PATH if ENV_PERSIST_FILE_PATH else '/tmp'

def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Homekit bridge for digitalStrom",
        epilog=f"If restart is requested, exits with code {RESTART_EXIT_CODE}",
    )
    parser.add_argument(
        "--hostname", help="Hostname or ip-address of digitalStrom server", default=os.environ.get('HOSTNAME')
    )
    parser.add_argument(
        "--http-port", help="Port to reach digitalStrom http server, default 8080", default="8080"
    )
    parser.add_argument(
        "--ws-port", help="Port to reach digitalStrom websocket, default 8090", default="8090"
    )
    parser.add_argument(
        "--homekit-bridge-name", help="Name how the bridge should be appear in Home", default="dS Homebridge"
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


def read_config_file():
    _configfile = args.config_path + "/config.yml"

    import os.path
    file_exists = os.path.isfile(_configfile)

    if not file_exists:
        open(_configfile, "w")

    _file = {}
    with open(_configfile, "r") as stream:
        try:
            _file = yaml.safe_load(stream)
            if _file is None:
                _file = {}
        except yaml.YAMLError as exc:
            print(exc)

    return _file


args = get_arguments()


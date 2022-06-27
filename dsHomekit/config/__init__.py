import argparse
import yaml
from dsHomekit.const import RESTART_EXIT_CODE


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Homekit bridge for digitalStrom",
        epilog=f"If restart is requested, exits with code {RESTART_EXIT_CODE}",
    )
    parser.add_argument(
        "--hostname", help="Hostname or ip-address of digitalStrom server", default="dss.local"
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
        "--persit-file-path", help="Path to persist file, default is '/tmp'", default="/tmp"
    )
    parser.add_argument(
        "--loglevel", help="Loglevel: INFO, DEBUG", default="INFO"
    )
    parser.add_argument(
        "--token", help="Token created on dss", default="xxx"
    )
    required_named = parser.add_argument_group('required named arguments')
    required_named.add_argument(
        "--config-path", help="Path to config.yml", default="", required=True
    )
    arguments = parser.parse_args()

    return arguments


def read_config_file():
    _file = {}
    with open(args.config_path + "/config.yml", "r") as stream:
        try:
            _file = yaml.safe_load(stream)
            if _file is None:
                _file = {}
        except yaml.YAMLError as exc:
            print(exc)

    return _file


args = get_arguments()


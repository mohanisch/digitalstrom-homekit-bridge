import argparse
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from dsHomekit import dswebsocket, digitalstrom
from dsHomekit.homekit import homekit

from .const import REQUIRED_PYTHON_VER


def validate_python() -> None:
    if sys.version_info[:3] < REQUIRED_PYTHON_VER:
        print(
            f"{REQUIRED_PYTHON_VER[0]}.{REQUIRED_PYTHON_VER[1]}.{REQUIRED_PYTHON_VER[2]}"
        )
        sys.exit(1)


def check_threads() -> None:
    """Check if there are any lingering threads."""
    try:
        nthreads = sum(
            thread.is_alive() and not thread.daemon for thread in threading.enumerate()
        )
        if nthreads > 1:
            sys.stderr.write(f"Found {nthreads} non-daemonic threads.\n")

    except AssertionError:
        sys.stderr.write("Failed to count non-daemonic threads.\n")


def run_io_tasks_in_parallel(tasks):
    with ThreadPoolExecutor() as executor:
        running_tasks = [executor.submit(task) for task in tasks]
        for running_task in running_tasks:
            running_task.result()


def main():
    validate_python()

    dsdevices = digitalstrom.collector.get_devices()

    for dsdevice in dsdevices:
        homekit.add_bridge_accessory(dsdevice)

    run_io_tasks_in_parallel([
        lambda: homekit.start(),
        lambda: dswebsocket.start(),
    ])

    check_threads()


if __name__ == '__main__':
    sys.exit(main())

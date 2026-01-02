import errno
import os
import tempfile
import threading
import time
import unicodedata

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
        with open(path, 'r') as file:
            try:
                cur_yaml = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print(exc)

        if cur_yaml is None:
            cur_yaml = {}

        cur_yaml.update(data)
        with open(path, 'w') as file:
            yaml.safe_dump(cur_yaml, file, indent=2)


def threaded(fn):
    """
    Decorator to run a function in a separate thread.
    Returns None to avoid JSON serialization issues with Thread objects.
    """

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return None  # Don't return thread object to avoid JSON serialization issues

    return wrapper


def remove_control_characters(s):
    return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")


def isWritable(path):
    wkspFldr = os.path.dirname(path)
    try:
        testfile = tempfile.TemporaryFile(dir=wkspFldr)
        testfile.close()
    except OSError as e:
        if e.errno == errno.EACCES:  # 13
            return False
        e.filename = path
        raise
    return True


def wait_until(somepredicate, timeout=600, period=0.25, *args, **kwargs):
    mustend = time.time() + timeout
    while time.time() < mustend:

        if somepredicate(*args, **kwargs):
            return True
        time.sleep(period)
    return False

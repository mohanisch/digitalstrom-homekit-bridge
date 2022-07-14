import threading
import tempfile
import errno
import time
import unicodedata
import yaml
import os


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
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

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


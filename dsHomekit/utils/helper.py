import threading
import tempfile
import errno
import unicodedata


def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


def remove_control_characters(s):
    return "".join(ch for ch in s if unicodedata.category(ch)[0]!="C")


def isWritable(path):
    try:
        testfile = tempfile.TemporaryFile(dir = path)
        testfile.close()
    except OSError as e:
        if e.errno == errno.EACCES:  # 13
            return False
        e.filename = path
        raise
    return True
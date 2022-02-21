import os
from collections import deque
from os.path import expanduser
from threading import Lock

START = deque()
END = deque()
LOCK = Lock()
LOADED = False


def load_data(func):
    global LOADED, LOCK
    if not LOADED:
        with LOCK:
            if not LOADED:
                with open(expanduser("~/wordlist.txt"), "r") as f:
                    data = f.read().splitlines()
                    split = data.index("#split")
                    START.extend(w[0].upper() + w[1:] for w in data[:split])
                    END.extend(w[0].upper() + w[1:] for w in data[split + 1:])
                LOADED = True
    return func


@load_data
def generate():
    start = START.popleft()
    end = END.popleft()
    START.append(start)
    END.append(end)
    return (
        f"{start}{end}#{int.from_bytes(os.urandom(3), byteorder='big', signed=False):x}"
    )


__all__ = ["generate"]

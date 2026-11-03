"""The one discipline for writing a judgement file a person edits by hand (T63's asset types, T36's definitions and rules):
an exclusive fcntl lock on a lock file beside it, the change computed on what is on disk under that lock, the new text
written to a temporary file in the same folder (a dot name ending .tmp, which no loader globs) and moved into place with
os.replace, so a reader never sees half a file; then an optional check of the result, which on failure puts the old
text back (or removes a file that did not exist) and re-raises."""
from __future__ import annotations

import fcntl
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def locked(lock: Path):
    with open(lock, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def replace_text(dest: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, dest)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def safe_write(dest: Path, lock: Path, mutate, verify=None) -> bool:
    """Under `lock`: `mutate(old_text or None)` returns the new text, or None for nothing to write (it raises to refuse,
    having checked what it needs on that snapshot). The text replaces `dest` atomically; then `verify()` runs, and if it
    raises, `dest` goes back to the old text (or is removed when it did not exist) before the error propagates."""
    with locked(lock):
        old = dest.read_text() if dest.exists() else None
        new = mutate(old)
        if new is None:
            return False
        replace_text(dest, new)
        if verify is not None:
            try:
                verify()
            except BaseException:
                if old is None:
                    dest.unlink(missing_ok=True)
                else:
                    replace_text(dest, old)
                raise
        return True

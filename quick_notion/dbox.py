import contextlib
import datetime
import os
import time

import dropbox


def upload(dbx: dropbox.Dropbox, fullname, folder, subfolder, name, overwrite=False):
    """Upload a file.

    Return the request response, or None in case of error.
    """
    path = "/%s/%s/%s" % (folder, subfolder.replace(os.path.sep, "/"), name)
    while "//" in path:
        path = path.replace("//", "/")
    mode = (
        dropbox.files.WriteMode.overwrite if overwrite else dropbox.files.WriteMode.add
    )
    mtime = os.path.getmtime(fullname)
    with open(fullname, "rb") as f:
        data = f.read()
    with stopwatch("upload %d bytes" % len(data)):
        try:
            res = dbx.files_upload(
                data,
                path,
                mode,
                client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                mute=True,
            )
        except dropbox.exceptions.ApiError as err:
            print("*** API error", err)
            return None
    print("uploaded as", res.name.encode("utf8"))
    return res


@contextlib.contextmanager
def stopwatch(message):
    """Context manager to print how long a block of code took."""
    t0 = time.time()
    try:
        yield
    finally:
        t1 = time.time()
        print("Total elapsed time for %s: %.3f" % (message, t1 - t0))

#!python2
"""Watch an automatic-save folder and place the resulting PDF."""

import os
import shutil
import time
import uuid

from System.IO import File, FileMode, FileAccess, FileShare


POLL_SECONDS = 0.5
STABLE_SECONDS = 2.0
PDF_WAIT_TIMEOUT_SECONDS = 1800


def file_signature(path):
    try:
        if not os.path.isfile(path):
            return None
        file_stat = os.stat(path)
    except OSError:
        return None

    return file_stat.st_size, file_stat.st_mtime, file_stat.st_ctime


def _pdf_is_complete(path, expected_size):
    try:
        with open(path, "rb") as handle:
            if handle.read(5) != "%PDF-":
                return False
            handle.seek(-min(2048, expected_size), os.SEEK_END)
            if not handle.read().rstrip().endswith("%%EOF"):
                return False

        stream = File.Open(path, FileMode.Open, FileAccess.Read, FileShare.None)
        try:
            return stream.Length == expected_size
        finally:
            stream.Close()
    except Exception:
        return False


def wait_for_named_output(path, previous_signature,
                          timeout_seconds=PDF_WAIT_TIMEOUT_SECONDS):
    """Wait for the expected PDF to finish writing and release its handle."""
    deadline = time.time() + timeout_seconds
    stable_signature = None
    stable_since = None

    while time.time() < deadline:
        signature = file_signature(path)
        if signature is not None and signature != previous_signature and signature[0]:
            if signature != stable_signature:
                stable_signature = signature
                stable_since = time.time()
            elif time.time() - stable_since >= STABLE_SECONDS:
                if _pdf_is_complete(path, signature[0]):
                    if file_signature(path) == signature:
                        return path
        else:
            stable_signature = None
            stable_since = None

        time.sleep(POLL_SECONDS)

    raise IOError('PDF output was not ready within {} seconds at "{}".'
                  .format(timeout_seconds, path))


def copy_output(source_path, target_path):
    """Copy to a sibling file, then replace the destination in one step."""
    if os.path.normcase(os.path.abspath(source_path)) == os.path.normcase(
        os.path.abspath(target_path)
    ):
        return False

    target_dir = os.path.dirname(os.path.abspath(target_path))
    staging_path = os.path.join(
        target_dir, ".print_{}.tmp".format(uuid.uuid4().hex)
    )
    try:
        source_size = os.path.getsize(source_path)
        shutil.copy2(source_path, staging_path)
        if (os.path.getsize(source_path) != source_size or
                os.path.getsize(staging_path) != source_size):
            raise IOError('Source changed while copying "{}".'.format(source_path))
        if os.path.isfile(target_path):
            File.Replace(staging_path, target_path, None)
        else:
            File.Move(staging_path, target_path)
    finally:
        if os.path.isfile(staging_path):
            os.remove(staging_path)

    return True


def place_output(source_path, target_path):
    if copy_output(source_path, target_path):
        os.remove(source_path)

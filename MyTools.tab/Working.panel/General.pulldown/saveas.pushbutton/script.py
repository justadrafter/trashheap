# -*- coding: utf-8 -*-
"""
Copy the current cloud-workshared model's cached file from
CollaborationCache into C:\temp, naming it:
copy_<project_title>.rvt

Warn if the cached file is older than 5 minutes.
"""

import os
import shutil
import time
from pyrevit import revit, DB

__title__ = "Save Cloud Cache Copy"
__author__ = "Adam Shaw"

doc = revit.doc


def main():
    if not doc.IsWorkshared:
        print("Not a workshared model.")
        return

    cmp = doc.GetCloudModelPath()
    model_guid = cmp.GetModelGUID().ToString()
    project_guid = cmp.GetProjectGUID().ToString()
    userid = doc.Application.LoginUserId

    revit_ver = doc.Application.VersionName
    local_appdata = os.environ.get("LOCALAPPDATA")

    cache_file = os.path.join(
        local_appdata,
        "Autodesk",
        "Revit",
        revit_ver,
        "CollaborationCache",
        userid,
        project_guid,
        model_guid + ".rvt"
    )

    if not os.path.exists(cache_file):
        print("Cached model not found:\n{}".format(cache_file))
        return

    # *** Date Modified Check ***
    modified_ts = os.path.getmtime(cache_file)
    age_seconds = time.time() - modified_ts

    if age_seconds > 300:
        print("*********************************************")
        print("WARNING: Cached file is older than 5 minutes.")
        print("*********************************************")

    # Destination path
    dst_dir = r"C:\temp"
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    safe_title = doc.Title.replace(" ", "_")
    dst_filename = "copy_{0}.rvt".format(safe_title)
    dst_path = os.path.join(dst_dir, dst_filename)

    shutil.copy2(cache_file, dst_path)
    print("Copied to {}".format(dst_path))


if __name__ == "__main__":
    main()

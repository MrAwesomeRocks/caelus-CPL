# -*- coding: utf-8 -*-

"""\
CPL Version
"""

import os
import subprocess
import shlex

_basic_version = "v0.0.2"

def git_describe():
    """Get version from git-describe"""
    dirname = os.path.dirname(__file__)
    cwd = os.getcwd()
    try:
        os.chdir(dirname)
        cmdline = "git describe --tags --dirty"
        cmd = shlex.split(cmdline)
        task = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, _ = task.communicate()
        git_ver = _basic_version
        if task.poll() == 0:
            git_ver = out.strip().decode('ascii')
    finally:
        os.chdir(cwd)
    return git_ver

#: Version string
version = git_describe()

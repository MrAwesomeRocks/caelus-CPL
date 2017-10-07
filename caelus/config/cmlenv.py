# -*- coding: utf-8 -*-

"""\
Caelus CML Environment Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:mod:`~caelus.config.cmlenv` serves as a replacement for Caelus/OpenFOAM bashrc
files, providing ways to discover installed versions as well as interact with
the installed Caelus CML versions. By default, :mod:`cmlenv` attempts to locate
installed Caelus versions in standard locations:
:file:`~/Caelus/caelus-VERSION` on Unix-like systems, and in :file:`C:\Caelus`
in Windows systems. Users can override the default behavior and point to
non-standard locations by customizing their Caelus Python configuration file.

"""

import os
import glob
import itertools
import logging
from distutils.version import LooseVersion
from .config import CaelusCfg, get_caelus_root, get_config

_lgr = logging.getLogger(__name__)

def discover_versions(root=None):
    """Discover Caelus versions if no configuration is provided.

    If no root directory is provided, then the function attempts to search in
    path provided by :func:`~caelus.config.config.get_caelus_root`.

    Args:
        root (path): Absolute path to root directory to be searched

    """
    def path_to_cfg(caelus_dirs):
        """Convert Caelus directories to configuration objects"""
        for cpath in caelus_dirs:
            bname = os.path.basename(cpath)
            tmp = bname.split("-")
            if tmp:
                version = tmp[-1]
                yield CaelusCfg(version=version,
                                path=cpath)

    rpath = root or get_caelus_root()
    cdirs = glob.glob(os.path.join(rpath, "caelus-*"))
    return list(path_to_cfg(cdirs))

def _filter_invalid_versions(cml_cfg):
    """Process user configuration and filter invalid versions

    Args:
        cml_cfg (list): List of CML configuration entries
    """
    root_default = get_caelus_root()
    for ver in cml_cfg:
        vid = ver.get("version", None)
        if vid is None:
            continue
        # Ensure that the version is not interpreted as a number by YAML
        ver.version = str(vid)
        pdir = ver.get("path",
                       os.path.join(root_default, "caelus-%s"%vid))
        if os.path.exists(pdir):
            yield ver


def _determine_platform_dir(root_path):
    """Determine the build type platform option"""
    basepath = os.path.join(root_path, "platforms")
    if not os.path.exists(basepath):
        return None

    ostype = (os.uname()[0].lower()
              if os.name != 'nt' else "windows")
    arch_types = ['64', '32']
    compilers = ['g++', 'icpc', 'clang++']
    prec_types = ['DP', 'SP']
    opt_types = ['Opt', 'Prof', 'Debug']

    for at, pt, ot, ct in itertools.product(
            arch_types, prec_types, opt_types, compilers):
        bdir_name = "%s%s%s%s%s"%(ostype, at, ct, pt, ot)
        bdir_path = os.path.join(basepath, bdir_name)
        if os.path.exists(bdir_path):
            return bdir_path

class CMLEnv(object):
    """CML Environment Interface.

    This class provides an interface to an installed Caelus CML version.
    """

    _root_dir = ""     # Root directory
    _project_dir = ""  # Project directory
    _version = ""      # Version

    def __init__(self, cfg):
        """
        Args:
            cfg (CaelusCfg): The CML configuration object
        """
        self._cfg = cfg
        self._version = cfg.version
        self._project_dir = cfg.get(
            "path",
            os.path.join(get_caelus_root(), "caelus-%s"%self.version))
        self._root_dir = os.path.dirname(self._project_dir)

        # Determine build dir
        build_dir = cfg.get(
            "platform_install",
            _determine_platform_dir(self._project_dir))
        if not build_dir:
            _lgr.debug("Cannot find platform directory: %s"%
                       self._project_dir)
            self._build_dir = ""
        else:
            self._build_dir = build_dir

    @property
    def root(self):
        """Return the root path for the Caelus install

        Typically on Linux/OSX this is the :file:`~/Caelus` directory.
        """
        return self._root_dir

    @property
    def project_dir(self):
        """Return the project directory path

        Typically :file:`~/Caelus/caelus-VERSION`
        """
        return self._project_dir

    @property
    def version(self):
        """Return the Caelus version"""
        return self._version

    @property
    def build_dir(self):
        """Return the build platform directory"""
        if not self._build_dir or not os.path.exists(self._build_dir):
            raise IOError("Cannot find Caelus platform directory: %s"%
                          self._build_dir)
        return self._build_dir

    @property
    def bin_dir(self):
        """Return the bin directory for executable"""
        return os.path.join(self.build_dir, "bin")

    @property
    def lib_dir(self):
        """Return the bin directory for executable"""
        return os.path.join(self.build_dir, "lib")

def _cml_env_mgr():
    """Caelus CML versions manager"""
    cml_versions = {}
    did_init = [False]

    def _init_cml_versions():
        """Initialize versions based on user configuration"""
        cfg = get_config()
        cml_opts = cfg.caelus.caelus_cml.versions
        if cml_opts:
            cml_filtered = list(_filter_invalid_versions(cml_opts))
            if cml_opts and not cml_filtered:
                _lgr.warn(
                    "No valid versions provided; check configuration file."
                    " Attempting to discover installed versions.")
            for cml in cml_filtered:
                cenv = CMLEnv(cml)
                cml_versions[cenv.version] = cenv
        else:
            cml_discovered = discover_versions()
            for cml in cml_discovered:
                cenv = CMLEnv(cml)
                cml_versions[cenv.version] = cenv
        did_init[0] = True

    def _get_latest_version():
        """Get the CML environment for the latest version available.

        Returns:
            CMLEnv: The environment object
        """
        if not cml_versions and did_init[0]:
            raise RuntimeError("No valid Caelus CML versions found")
        else:
            _init_cml_versions()
        vkeys = [LooseVersion(x) for x in cml_versions]
        vlist = sorted(vkeys, reverse=True)
        return cml_versions[vlist[0].vstring]

    def _get_version(version=None):
        """Get the CML environment for the version requested

        If version is None, then it returns the version set as default in the
        configuration file.

        Args:
            version (str): Version string

        Returns:
            CMLEnv: The environment object
        """
        if not cml_versions and did_init[0]:
            raise RuntimeError("No valid Caelus CML versions found")
        else:
            _init_cml_versions()
        cfg = get_config()
        vkey = version or cfg.caelus.caelus_cml.get("default", "")
        if vkey == "latest":
            return _get_latest_version()
        if not vkey in cml_versions:
            raise KeyError("Invalid CML version requested")
        else:
            return cml_versions[vkey]

    return _get_latest_version, _get_version

cml_get_latest_version, cml_get_version = _cml_env_mgr()
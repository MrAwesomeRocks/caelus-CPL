# -*- coding: utf-8 -*-

"""\
Caelus/OpenFOAM Input File Interface
-------------------------------------
"""

import os
import logging
import six

from ..utils import osutils
from . import caelusdict
from . import parser
from . import printer

_lgr = logging.getLogger(__name__)

class DictMeta(type):
    """Create property methods and add validation for properties.

    This metaclass implements the boilerplate code necessary to add
    getter/setters for various entries found in a Caelus input file. It expects
    a class variable ``_dict_properties`` that contains tuples for the various
    entries in the input file. The tuple can be of two forms:

      - (name, default_value)
      - (name, default_value, valid_values)

    If the default_value is not None, then this value will be used to
    automatically initialize the particular entry by
    :ref:`~caelus.io.dictfile.DictFile.create_default_entries` method. If
    ``valid_values`` are provided, any attempt to set/modify this value will be
    checked to ensure that only the allowed values are used.
    """
    # pylint: disable=no-value-for-parameter

    def __init__(cls, name, bases, cdict):
        super(DictMeta, cls).__init__(name, bases, cdict)
        if "_dict_properties" in cdict:
            cls.process_properties(cdict["_dict_properties"])
            cls.process_defaults(cdict["_dict_properties"])

    def process_defaults(cls, proplist):
        """Process default entries"""
        def create_default_entries(self):
            """Create defaults from property list"""
            data = self.data
            for plist in proplist:
                name = plist[0]
                value = plist[1]
                if value is not None:
                    data[name] = value
        setattr(cls, "create_default_entries", create_default_entries)

    def process_properties(cls, proplist):
        """Create getters/setters for properties"""
        for plist in proplist:
            cls.process_property(plist)

    def process_property(cls, plist):
        """Process a property"""
        name = plist[0]
        options = plist[2] if len(plist) == 3 else None
        doc = "%s"%name
        def getter(self):
            """Getter"""
            return self.data.get(name, None)
        if options:
            def setter(self, value):
                """Setter"""
                if not value in options:
                    raise ValueError(
                        "%s: Invalid option for %s"%(
                            cls.__name__, name))
                self.data[name] = value
        else:
            def setter(self, value):
                "Setter"
                self.data[name] = value
        setattr(cls, name, property(getter, setter, doc=doc))

@six.add_metaclass(DictMeta)
class DictFile(object):
    """Caelus/OpenFOAM input file reader/writer

    The default constructor does not read a file, but instead creates a new
    input file object. If a property list is provided, this is used to
    initialize the default entries. To read an existing file, the use of
    :ref:`DictFile.read_if_present` method is recommended.
    """

    #: Default filename for the file type (to be overriden by subclasses)
    _default_filename = "dictionary"
    #: File sizes to limit parsing to (to avoid parsing large field files)
    _size_limit = 10 * (1 << 20)

    _default_header = [
        ("version", "2.0"),
        ("format", "ascii"),
        ("class", "dictionary"),]

    def __init__(self, filename=None, populate_defaults=True):
        """
        Args:
            filename (path): Path to the input file
        """
        #: File to read/write data
        self.filename = filename or self._default_filename
        #: Contents of the FoamFile sub-dictionary in the file
        self.header = self.create_header()
        #: Contents of the file as a dictionary suitable for manipulation
        self.data = caelusdict.CaelusDict()
        if populate_defaults:
            self.create_default_entries()

    @classmethod
    def load(cls, filename=None, debug=False):
        """Load a Caelus input file from disk

        Args:
            filename (path): Path to the input files
            debug (bool): Turn on detailed errors
        """
        name = filename or cls._default_filename
        entries = caelusdict.CaelusDict()
        header = None
        need_default_header = True
        if not os.path.exists(name):
            raise IOError("Cannot find file: %s"%name)
        if os.path.getsize(name) > cls._size_limit:
            _lgr.warning("%s size is > 5MB, will only parse header")
        else:
            cparse = parser.CaelusParser()
            with open(name) as fh:
                txt = fh.read()
                entries = cparse.parse(txt, name, debuglevel=debug)
                header = entries.pop("FoamFile", None)
                need_default_header = False
        obj = cls.__new__(cls)
        obj.filename = name
        if header:
            obj.header = header
        elif need_default_header:
            obj.header = obj.create_header()
        else:
            obj.header = None
        obj.data = entries
        return obj

    @classmethod
    def read_if_present(cls, casedir=None, filename=None, debug=False):
        """Read the file if present, else create object with default values

        Args:
            casedir (path): Path to the case directory
            filename (path): Filename to read
            debug (bool): Turn on detailed errors
        """
        cdir = osutils.abspath(casedir or os.getcwd())
        name = filename or cls._default_filename
        with osutils.set_work_dir(cdir):
            if os.path.exists(name):
                return cls.load(filename, debug)
            obj = cls.__new__(cls)
            obj.filename = name
            obj.header = obj.create_header()
            obj.data = caelusdict.CaelusDict()
            return obj

    def create_default_entries(self):
        """Create default entries for this file"""
        pass

    def create_header(self):
        """Create a default header"""
        obj = os.path.basename(self.filename)
        location = os.path.dirname(self.filename)
        default_header = caelusdict.CaelusDict([
            ("version", "2.0"),
            ("format", "ascii"),
            ("class", "dictionary"),])
        if location:
            default_header.location = '"%s"'%location
        default_header['object'] = '"%s"'%obj
        return default_header

    def write(self, filename=None,
              update_object=True,
              write_header=True):
        """Write a formatted Caelus input file

        Args:
            filename (path): Path to file
            update_object (bool): Ensure object type is consistent
            write_header (bool): Write header for the file
        """
        self.filename = filename or self.filename
        header = None
        if write_header:
            header = self.create_header() if update_object else self.header
        _lgr.info("Writing Caelus input file: %s", self.filename)
        with printer.foam_writer(self.filename, header) as fh:
            fh(self.data)

    def merge(self, *args):
        """Merge entries from one dictionary to another"""
        self.data.merge(*args)

    def __str__(self):
        strbuf = six.StringIO()
        pprint = printer.DictPrinter(strbuf)
        pprint(self.data)
        return strbuf.getvalue()

    def __repr__(self):
        return "<%s: %s>"%(self.__class__.__name__,
                           self.filename)


class ControlDict(DictFile):
    """system/controlDict interface"""

    _default_filename = "system/controlDict"

    _dict_properties = [
        ("application", "pisoSolver"),
        ("startFrom", "latestTime",
         ("firstTime", "startTime", "latestTime")),
        ("startTime", 0),
        ("stopAt", "endTime",
         ("endTime", "writeNow", "noWriteNow", "nextWrite")),
        ("endTime", None),
        ("deltaT", None),
        ("writeControl", "timeStep",
         ("timeStep", "runTime", "adjustableRunTime",
          "cpuTime", "clockTime")),
        ("writeInterval", None),
        ("purgeWrite", 0),
        ("writeFormat", "ascii", ("ascii", "binary")),
        ("writePrecision", 6),
        ("writeCompression", True),
        ("timeFormat", "general",
         ("fixed", "scientific", "general")),
        ("timePrecision", 6),
        ("graphFormat", None),
        ("adjustTimeStep", None),
        ("maxCo", None),
        ("runTimeModifiable", True),
    ]

class DecomposeParDict(DictFile):
    """system/decomposeParDict interface"""

    _default_filename = "system/decomposeParDict"

    _dict_properties = [
        ("numberOfSubdomains", 4),
        ("method", "scotch",
         ("scotch", "metis", "simple", "hierarchical", "manual")),
    ]

class TransportProperties(DictFile):
    """constant/transportProperties interface"""

    _default_filename = "constant/transportProperties"

    _dict_properties = [
        ("transportModel", "Newtonian"),
    ]

class TurbulenceProperties(DictFile):
    """constant/turbulenceProperties interface"""

    _default_filename = "constant/turbulenceProperties"

    _dict_properties = [
        ("simulationType", "laminar",
         ("laminar", "RASModel", "LESModel")),
    ]

class TurbModelProps(DictFile):
    """Common interface for LES/RAS models"""

    _dict_properties = [
        ("turbulence", "on",
         ("on", "off", "yes", "no", True, False)),
        ("printCoeffs", "on",
         ("on", "off", "yes", "no", True, False)),
    ]

    _model_name = "NONE"

    @property
    def model(self):
        """Turbulence model

        Depending on the type (RANS or LES), this is the entry RASModel or
        LESModel respectively in the RASProperties and LESProperties file. To
        simplify access, it is simply named model here.
        """
        return self.data.get(self._model_name, None)

    @model.setter
    def model(self, value):
        self.data[self._model_name] = value
        # trigger generation of coeffs dictionary if not present
        _ = self.coeffs

    @property
    def coeffs(self):
        """Turbulence model coefficients

        This represents the sub-dictionary (e.g., kOmegaSSTCoeffs,
        SmagorinksyCoeffs) containing the additional parameters necessary for
        the turbulence model. The accessor automatically populates the right
        name when generating the dictionary depending on the turbulence model
        selected.
        """
        key = self.data[self._model_name] + "Coeffs"
        if not key in self.data:
            self.data[key] = caelusdict.CaelusDict()
        return self.data[key]

class RASProperties(TurbModelProps):
    """constant/RASProperties interface"""

    _default_filename = "constant/RASProperties"

class LESProperties(TurbModelProps):
    """constant/LESProperties interface"""

    _default_filename = "constant/LESProperties"

    def create_default_entries(self):
        """Create the default turbulence model entries

        In addition to the default options specified in turbulence properties
        class, this also triggers the default entries for delta.
        """
        super(LESProperties, self).create_default_entries()
        self.delta = "cubeRootVol"

    @property
    def delta(self):
        """LES delta"""
        return self.data.delta

    @delta.setter
    def delta(self, value):
        """LES delta"""
        self.data.delta = value
        key = value + "Coeffs"
        if key not in self.data:
            coeffs = caelusdict.CaelusDict()
            if value == "cubeRootVol":
                coeffs.deltaCoeff = 1
            self.data[key] = coeffs
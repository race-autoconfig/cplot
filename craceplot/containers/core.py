import os
import re
import ast
import sys
import json
import traceback
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Literal, Union, Optional, get_args, get_origin

import craceplot.settings.description as info
from craceplot.utils.const import WIDTH
from craceplot.utils.format import format_string
from craceplot.utils.base import check_type, parse_range_list

CPLOT_HOME=os.path.dirname(os.path.dirname(__file__))

bold = '\033[1m'
underline = '\033[4m'
reset = '\033[0m'


############################# Error information #############################
#                                 CplotError                                #
#                                 OptionError                               #
#                          ParameterDefinitionError                         #
#                             ParameterValueError                           #
#                                 ModelError                                #
#                                  FileError                                #
#                              CplotExecutionError                          #
#                                  ExitError                                #
#############################################################################
class CplotError(Exception):
    """Exceptions for crace-plot"""

    def __init__(self, message="No message provided."):
        super().__init__(message)
    pass

class OptionError(CplotError):
    """Exception for option type """
    def __init__(self, message="No message provided."):
        super().__init__(message)
    pass

class ParameterDefinitionError(CplotError):
    """Exception for option type """
    def __init__(self, message="No message provided."):
        super().__init__(message)
    pass

class ParameterValueError(CplotError):
    """Exception for option type """
    def __init__(self, message="No message provided."):
        super().__init__(message)
    pass

class ModelError(CplotError):
    """Exception for option type """
    def __init__(self, message="No message provided."):
        super().__init__(message)
    pass

class FileError(CplotError):
    """ Errors related to files (not found or invalid"""
    def __init__(self, message="No message provided."):
        super().__init__(message)
    pass

class CplotExecutionError(CplotError):
    """
    Errors related to the execution of jobs
    """
    def __init__(self, message="No message provided."):
        super().__init__(message)
    pass

class ExitError(CplotError):
    """Exit without error"""
    def __init__(self, message="No message provided."):
        super().__init__(message)
    pass

class Errors:
    """
    Namespace wrapper so users can import all errors via:
        from file import Errors
        raise Errors.Option("...")
    """

    CplotError               = CplotError
    OptionError              = OptionError
    ParameterDefinitionError = ParameterDefinitionError
    ParameterValueError      = ParameterValueError
    ModelError               = ModelError
    FileError                = FileError
    CplotExecutionError      = CplotExecutionError
    ExitError                = ExitError



################################ Option rules ###############################
#                              _option_decoder                              #
#                                IntegerOption                              #
#                                  RealOption                               #
#                             ParameterValueError                           #
#                                 StringOption                              #
#                                BooleanOption                              #
#                                  FileOption                               #
#                                  ExeOption                                #
#                                EnablerOption                              #
#                                  ListOption                               #
#                                  UnionOption                              #
#############################################################################
def _option_decoder(obj):
    """
    instantiates the correct class for an option
    :param obj: option (dictionary) obtained from the json settings definition
    :return: an instance of the Option class
    :raises OptionError: if type attribute is not found in obj or if type was not recognized
    """
    o = None
    if not ('type' in obj):
        raise OptionError("Option has no type.")
    if obj['type'] == 'i':
        o = IntegerOption(obj)
    if obj['type'] == 'r':
        o = RealOption(obj)
    if obj['type'] == 'b':
        o = BooleanOption(obj)
    if obj['type'] == 's':
        o = StringOption(obj)
    if obj['type'] == 'p':
        o = FileOption(obj)
    if obj['type'] == 'x':
        o = ExeOption(obj)
    if obj['type'] == 'e':
        o = EnablerOption(obj)
    if obj['type'] == 'l':
        o = ListOption(obj)
    if obj['type'] == 'u':
        o = UnionOption(obj)

    if o is None:
        raise OptionError(f"Option cannot be read: {underline}{obj['name']}{reset}")

    return o

class Option(ABC):
    """
    Class Option handles options of the configurator
    :var general_options: List of variables associated with an Option
       name: option name
       type: option type (see option_types)
       short: short flag
       long: long flag
       section: section (group) to which the option belongs
       vignettes: text for the documentation of the option
       description: general description of the option
    :var option_types: List of option types available
       e: enabler option (activates behaviour)
       i: integer option
       r: real option
       s: string option
       b: boolean option
       p: file path option
       x: script file or function to be parsed. Both should be executable
       u: union option

    :ivar value: option value
    :ivar default: option default value
    """

    general_options = ["name", "type", "short", "long", "section", "vignettes", "description", "critical"]

    option_types = ["e", "i", "r", "s", "b", "p", "x", "l", "u"]

    def __init__(self):
        """
        Creates an Option object
        """
        self.value = None
        self.default = None

    @staticmethod
    def _check_general_options(obj):
        """
        checks that all options in Options.general_options are defined in obj
        :param obj: Dictionary of options read from the json settings file
        :return: none
        :raises OptionError: if an option is not included in obj
        """
        for key in Option.general_options:
            if not (key in obj.keys()):
                raise OptionError(f"All craceplot options must define attribute {underline}{key}{reset}")

    def _set_general_options(self, obj):
        """
        Creates variables in Option.general_options list and assigns
        the values for these variables in  obj
        :param obj: Dictionary of variable values, keys are the names
                    in Option.general_options
        """
        for key in Option.general_options:
            if key == "critical":
                setattr(self, key, int(obj[key]))
            elif key in ["vignettes", "description"]:
                setattr(self, key, obj[key])
            else:
                setattr(self, key, obj[key].replace(".", ""))

    def is_set(self):
        return not (self.value is None)

    def set_value(self, value):
        """
        sets the value of the option and validates it
        :param value: the value to be set
        :return: none
        """
        self.value = self.parse_value(value, True)

    def is_default(self):
        """
        Returns True if value assigned is the default value
        """
        return self.value == self.default

    @abstractmethod
    def parse_value(self, value: str, check: bool = False):
        """
        parses the option value from a string
        :param value: string that has the value of the option
        :param check: boolean that indicates if the value must be validated
        :return: parsed value. If the value is None or empty, the default value is returned
        :raises OptionError: if value is not integer
        """

    def parse_default(self, value: str):
        """
        parse the default value of the option, no validation is performed
        :param value: string with the default value
        :return: the parsed value (integer) or None if default is None or empty
        """

    def check_value(self, value):
        """
        checks a value has the correct type (integer) and is in the option domain
        :param value: value to be checked
        :return: none
        :raises OptionError: if value is no integer o value is not within domain
        """

    def parse_domain(self, domain: str):
        """
        parses the domain of an option
        :param domain: string that defines the domain in the format (lower, upper)
        :return: returns a list of size two with first element the lower bound and second element the upper bound [lower, upper]
        :raises OptionError: if the provided domain cannot be parsed, or if the domain is not correct lower > upper
        """

class IntegerOption(Option):
    """
    class the handles integer craceplot options
    :ivar domain: domain of the option as a two element list [lower, upper]
    """
    def __init__(self, obj):
        """
        Creates an Integer Option
        :param obj: dictionary of the option read from the json setting file
        """
        # add general variables
        super()._check_general_options(obj)
        super()._set_general_options(obj)

        # other variables
        self.domain = self.parse_domain(obj['domain'])
        self.default = self.parse_default(obj['default'])
        self.value = self.default

    def parse_value(self, value: str, check: bool = False):
        """
        parses the option value from a string
        :param value: string that has the value of the option
        :param check: boolean that indicates if the value must be validated
        :return: parsed value. If the value is None or empty, the default value is returned
        :raises OptionError: if value is not integer
        """
        # if value is empty return default
        if value is None or value == "":
            v = self.default
        elif value.lower() == 'none':
            v = self.default
        elif isinstance(value, str):
            try:
                v = eval(value)
            except Exception as e:
                raise ValueError(f"Option {underline}{self.name}{reset} "
                                 f"must be integer but has value {bold}{value}{bold}")
            if not isinstance(v, int):
                raise OptionError(f"Option {underline}{self.name}{reset} "
                                  f"must be integer but has value/default: {bold}{value}{reset}")
        else:
            v = value

        if check:
            self.check_value(v)
        return v

    def parse_default(self, value: str):
        """
        parse the default value of the option, no validation is performed
        :param value: string with the default value
        :return: the parsed value (integer) or None if default is None or empty
        """
        if value is None or value == "":
            return None
        elif isinstance(value, str):
            return eval(value)
        else:
            return value

    def check_value(self, value):
        """
        checks a value has the correct type (integer) and is in the option domain
        :param value: value to be checked
        :return: none
        :raises OptionError: if value is no integer o value is not within domain
        """
        if value == self.default:
            return
        if not isinstance(value, int):
            raise OptionError(f"Option {underline}{self.name}{reset} type error value "
                              f"{bold}{str(value)}{reset} is not int")
        elif (value < self.domain[0]) or (value > self.domain[1]):
            raise OptionError(f"Option {underline}{self.name}{reset} value/default: "
                              f"{bold}{str(value)}{reset} is not within its integer domain "
                              f"({str(self.domain[0])}, {str(self.domain[1])})")

    def parse_domain(self, domain: str):
        """
        parses the domain of an option
        :param domain: string that defines the domain in the format (lower, upper)
        :return: returns a list of size two with first element the lower bound and second element the upper bound [lower, upper]
        :raises OptionError: if the provided domain cannot be parsed, or if the domain is not correct lower > upper
        """
        if not domain: return None
        p = re.compile("(?P<d1>\d+),(?P<d2>\d+)")
        m = p.match(domain.strip("()"))
        if m is None:
            raise OptionError(f"Domain for integer option "
                              f"{underline}{self.name}{reset} is not correct : {domain}")
        d = [eval(m.group("d1")), eval(m.group("d2"))]
        if d[0] > d[1]:
            raise OptionError(f"Domain for integer option "
                              f"{underline}{self.name}{reset} is not correct : {domain}")
        return d

class RealOption(Option):
    """
    class the handles real valued craceplot options

    :ivar domain: domain of the option as a two element list [lower, upper]
    """
    def __init__(self, obj):
        """
        Creates a Real Option object
        :param obj: dictionary of the option read from the json setting file
        """
        # add general variables
        super()._check_general_options(obj)
        super()._set_general_options(obj)

        # other variables
        self.domain = self.parse_domain(obj['domain'])
        self.default = self.parse_default(obj['default'])
        self.value = self.default

    def parse_value(self, value: str, check: bool = False):
        """
        parses the option value from a string
        :param value: string that has the value of the option
        :param check: boolean that indicates if the value must be validated
        :return: parsed value. If the value is None or empty, the default value is returned
        :raises OptionError: if value is not float
        """
        if value is None or value == "":
            return self.default
        if isinstance(value, str):
            try:
                v = float(eval(value))
            except Exception as e:
                raise ValueError(f"Option {underline}{self.name}{reset} "
                                 f"must be real but has value {bold}{value}{reset}")
            if not isinstance(v, float):
                raise OptionError(f"Option {underline}{self.name}{reset} "
                                  f"must be real but has value/default: {value}")

        else:
            v = value

        if check:
            self.check_value(v)
        return v

    def parse_default(self, value: str):
        """
        parse the default value of the option, no validation is performed
        :param value: string with the default value
        :return: the parsed value (float) or None if default is None or empty
        """
        if value is None or value == "":
            return None
        elif isinstance(value, str):
            return eval(value)
        else:
            return value

    def check_value(self, value):
        """
        checks a value has the correct type (float) and is in the option domain
        :param value: value to be checked
        :return: none
        :raises OptionError: if value is not float or value is not within domain
        """
        if not isinstance(value, float):
            raise OptionError(f"Option {underline}{self.name}{reset} type error value "
                              f"{bold}{str(value)}{reset} is not float")
        elif (value < self.domain[0]) or (value > self.domain[1]):
            raise OptionError(f"Option {underline}{self.name}{reset} value/default: "
                              f"{bold}{str(value)}{reset} is not within its real domain "
                              f"({str(self.domain[0])}, {str(self.domain[1])})")

    def parse_domain(self, domain: str):
        """
        parses the domain of an option
        :param domain: string that defines the domain in the format (lower, upper)
        :return: returns a list of size two with first element the lower bound and second element the upper bound [lower, upper]
        :raises OptionError: if the provided domain cannot be parsed, or if the domain is not correct lower > upper
        """
        if not domain: return None
        p = re.compile("(?P<d1>[0-9]+\.*[0-9]*),(?P<d2>[0-9]+\.*[0-9]*)")
        m = p.match(domain.strip("()"))
        if m is None:
            raise OptionError(f"Domain for real option "
                              f"{underline}{self.name}{reset} is not correct :{domain}")
        d = [eval(m.group("d1")), eval(m.group("d2"))]
        if d[0] > d[1]:
            raise OptionError(f"Domain for real option "
                              f"{underline}{self.name}{reset} is not correct :{domain}")
        return d

class StringOption(Option):
    """
    class the handles string craceplot options

    :ivar domain: domain of the option as list [value1, value2, value3,...]
    """
    def __init__(self, obj):
        """
        Creates a String Option object
        :param obj: dictionary of the option read from the json setting file
        """
        # add general variables
        super()._check_general_options(obj)
        super()._set_general_options(obj)

        # other variables
        # if obj['name'] in ('title', 'fileName', 'keyParameter', 'catx', 'caty'):
        if 'domain' not in obj.keys():
            self.domain = None
        else:
            self.domain = self.parse_domain(obj['domain'])
        self.default = self.parse_default(obj['default'])
        self.value = self.default

    def parse_value(self, value: str, check: bool = False):
        """
        parses the option value from a string
        :param value: string that has the value of the option
        :param check: boolean that indicates if the value must be validated
        :return: parsed value. If the value is None or empty, the default value is returned
        """
        if value is None or value == "":
            return self.default
        v = str(value)
        if check:
            self.check_value(v)
        return v.lower()

    def parse_default(self, value: str):
        """
        parse the default value of the option, no validation is performed
        :param value: string with the default value
        :return: the parses value or None if default is None or empty
        """
        if not value:
            return None
        elif not isinstance(value, str):
            return str(value).lower()
        else:
            return value.lower()

    def check_value(self, value):
        """
        checks a value is in the option domain
        :param value: value to be checked
        :return: none
        :raises OptionError: if value is not string or value is not within domain
        """
        if not isinstance(value, str):
            raise OptionError(f"Option {underline}{self.name}{reset} type error value "
                              f"{bold}{value}{reset} is not string")
        elif self.domain is None:
            return
        elif not (value.lower() in self.domain):
            raise OptionError(f"Option {underline}{self.name}{reset} value/default: "
                              f"{bold}{str(value)}{reset} is not within the domain ({', '.join(self.domain)})")

    def parse_domain(self, domain: str):
        """
        parses the domain of an option
        :param domain: string that defines the domain in the format (value1, value2, value3, ...)
        :return: returns a list of size N  with the different values [value1, value2, value3, ..., valueN]
        :raises OptionError: if the provided domain has repeated values or is empty
        """
        if not domain: return None
        d = domain.strip("()").split(",")
        # TODO: how to validate string craceplot option domains when some options do not have domain
        if d[0] == "":
            return None
        # if d[0]=="":
        #    raise OptionError(f"Domain for string option "
        #                      f"{underline}{self.name}{reset} is empty or cannot be parsed")
        if len(d) > len(set(d)):
            raise OptionError(f"Domain for string option {underline}{self.name}{reset} "
                              f"has repeated values in domain: {domain}")
        d = [x.strip().lower() for x in d]
        return d

class BooleanOption(Option):
    """
    class the handles boolean craceplot options

    """

    def __init__(self, obj):
        """
        Creates a Boolean Option object
        :param obj: dictionary of the option read from the json setting file
        """
        # add general variables
        super()._check_general_options(obj)
        super()._set_general_options(obj)

        # other variables
        self.default = self.parse_default(obj['default'])
        self.value = self.default

    def set_value(self, value: str):
        """
        sets the value of the option
        :param value: the value to be set
        :return: none
        """
        self.value = self.parse_value(value)

    def parse_value(self, value: str):
        """
        parses the option value from a string
        :param value: string that has the value of the option
        :return: parsed value. If the value is None or empty, the default value is returned
        """
        if value is None or value == "":
            return self.default
        elif not isinstance(value, bool):
            if isinstance(value, int):
                return bool(value)
            elif value.lower() == "true":
                return bool(True)
            elif value.lower() == "false":
                return bool(False)
            else:
                return bool(eval(value))
        else:
            return value

    def parse_default(self, value: str):
        """
        parse the default value of the option
        :param value: string with the default value
        :return: the parse value or None if default is None or empty
        """
        if value is None or value == "":
            return None
        elif not isinstance(value, bool):
            if isinstance(value, int):
                return bool(value)
            else:
                return bool(eval(value))
        else:
            return value

class FileOption(Option):
    """
    class the handles file and directory path craceplot options

    """
    def __init__(self, obj):
        """
        Creates a File Option object
        :param obj: dictionary of the option read from the json setting file
        """
        # add general variables
        super()._check_general_options(obj)
        super()._set_general_options(obj)

        # other variables
        self.input_value = obj['default']
        self.default = self.parse_default(obj['default'])
        self.value = self.default

    def set_value(self, value: str, check_file: bool = False, check_parent_dir: bool=True):
        """
        sets the value of the option and validates it
        :param value: the value to be set
        :param check_file: boolean that indicated if the file should be validated
        :return: none
        """
        self.input_value = value.strip()
        self.value = self.parse_value(value, check_file, check_parent_dir)

    def parse_value(self, value: str, check_file: bool = False, check_parent_dir: bool = True):
        """
        parses the option file or directory path from a string.
        :param value: string that has the path
        :param check_file: boolean that indicates the type of validation to be performed:
        - False: only the directory where the file/directory is located should be validated as existing
        - True: the file or directory should be validated as existing
        :return: parsed absolute path. If the value is None or empty, the default value is returned
        """
        if value is None or value == "":
            return None
        value = os.path.expanduser(value)
        fvalue = os.path.abspath(value)
        self.check_value(fvalue, check_file, check_parent_dir)
        return fvalue

    def parse_default(self, value: str):
        """
        parse the default path of the option, no validation is performed
        :param value: string with the default path
        :return: the parsed absolute path or None if default is None or empty
        """
        if value is None or value == "":
            return None
        fvalue = os.path.abspath(value)
        return fvalue

    def check_value(self, value, check_file: bool = False, check_parent_dir:bool =True):
        """
        checks if the file or directory provided exists
        :param value: path to be checked
        :param check_file:  boolean that indicates the type of validation to be performed:
        - False: only the directory where the file/directory is located should be validated as existing
        - True: the file or directory should be validated as existing
        :return: none
        :raises OptionError: if the directory/file does not exists
        """
        if value is None:
            return
        if value == "":
            raise OptionError(f"Option {underline}{self.name}{reset}: "
                              f"provided file {value} is not valid.")
        if check_file:
            if not os.path.exists(value):
                raise OptionError(f"Option {underline}{self.name}{reset}: "
                                  f"provided file {value} does not exist.")
        elif check_parent_dir:
            dir_path = os.path.dirname(value)
            if not os.path.exists(dir_path):
                raise OptionError(f"Option {underline}{self.name}{reset}: "
                                  f"provided directory {dir_path} does not exist (option value {value})")

    def exists_file(self):
        """
        checks if the file or directory set as option value exists
        :return: True if the value file or directory exists, else False
        """
        if os.path.exists(self.value):
            return True
        return False

    def check_value_dir(self, writable: bool = False):
        """
        checks if the parent directory of the file/directory set as option value exists and its writable
        :param writable: boolean that indicates if the directory should be checked for writing permissions
        :return: none
        :raises OptionError: if the directory does not exists or does not have writing permissions
        """
        dir_path = os.path.dirname(self.value)
        if not os.path.exists(dir_path):
            raise OptionError(f"Option {underline}{self.name}{reset}: "
                              f"directory {dir_path} does not exist (option value {self.value})")
        if writable and (not os.access(dir_path, os.W_OK)):
            raise OptionError(f"Option {underline}{self.name}{reset}: "
                              f"directory {dir_path} is not writable (option value {self.value})")

    def check_value_file(self, writable: bool = False):
        """
        checks if the file set as option value exists and its writable
        :param writable: boolean that indicates if the file should be checked for writing permissions
        :return: none
        :raises OptionError: if the file does not exists or does not have writing permissions
        """
        if not os.path.exists(self.value):
            raise OptionError(f"Option {underline}{self.name}{reset}: "
                              f"provided file {bold}{self.value}{reset} does not exist.")
        if writable and (not os.access(self.value, os.W_OK)):
            raise OptionError(f"Option {underline}{self.name}{reset}: "
                              f"provided directory {bold}{self.value}{reset} is not writable")

    def check_executable(self, executable: bool = False):
        """
        checks if the file set as option value exists and its executable
        :param executable: boolean that indicates if the file should be checked for executing permissions
        :return: none
        :raises OptionError: if the file does not exists or does not have executing permissions
        """
        if not os.path.exists(self.value):
            raise OptionError(f"Option {underline}{self.name}{reset}: "
                              f"provided file {bold}{self.value}{reset} does not exist.")
        if executable and (not os.access(self.value, os.X_OK)):
            raise OptionError(f"Option {underline}{self.name}{reset}: "
                              f"provided directory {bold}{self.value}{reset} is not executable")

class ExeOption(Option):
    """
    class the handles executable file path craceplot options

    """
    def __init__(self, obj):
        """
        Creates and Executable Option
        :param obj: dictionary of the option read from the json setting file
        """
        # add general variables
        super()._check_general_options(obj)
        super()._set_general_options(obj)

        # other variables
        self.default = self.parse_default(obj['default'])
        self.value = self.default


    def parse_value(self, value: str, check: bool = False):
        """
        parses the option file path from a string.
        :param value: string that has the path
        :param check: boolean that indicates if validation should be performed:
        :return: parsed absolute path. If the value is None or empty, the default value is returned
        """
        if value is None or value == "":
            return self.default
        if check:
            check_return,value_ = self.check_value(value)
            if check_return:
                return value_
        value = os.path.expanduser(value)
        fvalue = os.path.abspath(value)
        return fvalue

    def parse_default(self, value: str):
        """
        parse the default path of the option, no validation is performed
        :param value: string with the default path
        :return: the parsed absolute path or None if default is None or empty
        """
        if value is None or value == "":
            return None
        return str(value)

    def check_value(self, value):
        """
        checks if the file provided exists and it has execution permissions
        :param value: path to be checked
        :return: none
        :raises OptionError: if the file does not exists or does not have execution permissions
        """
        if re.search('def', value) == None:
            if not os.path.isfile(value):
                raise OptionError(f"Option {underline}{self.name}{reset} "
                                  f"provided file {value} does not exist.")
            if not os.access(value, os.X_OK):
                raise OptionError(f"Option {underline}{self.name}{reset} "
                                  f"provided file {value} does  not have correct permissions.")
        else:
            try:
                exec(value)
                return True,value
            except SyntaxError:
                raise OptionError(f"Option {underline}{self.name}{reset} "
                                  f"provided function {value} has syntax errors.")

class EnablerOption(Option):
    """
    class the handles craceplot options that signal execution modes (e.g. --help, --onlytest, --check, --version)

    """
    def __init__(self, obj):
        """
        Creates an Enabler Option object
        :param obj: dictionary of the option read from the json setting file
        """
        # add general variables
        super()._check_general_options(obj)
        super()._set_general_options(obj)

        # other variables
        self.value = False
        self.default = False

    def parse_value(self, value, check = False):
        self.value = value

class ListOption(Option):
    """
    class the handles string crace options in a list

    :ivar domain: domain of the option as list [value1, value2, value3,...]
    :ivar value: the selection/combination of choices from the list
    """
    def __init__(self, obj):
        """
        Creates a String Option object
        :param obj: dictionary of the option read from the json setting file
        """
        # add general variables
        super()._check_general_options(obj)
        super()._set_general_options(obj)

        # other variables
        self.domain = self.parse_domain(obj['domain'])
        self.default = self.parse_default(obj['default'])
        self.value = self.default

    def parse_value(self, value, check: bool = False):
        """
        parses the option value from a string
        :param value: string that has the value of the option
        :param check: boolean that indicates if the value must be validated
        :return: parsed value. If the value is None or empty, the default value is returned
        """
        if check:
            self.check_value(value)

        if isinstance(value, list):
            out = []
            for x in value:
                if isinstance(x, str):
                    parts = re.split(r"[, ]+", x.strip())
                else:
                    parts = [x]
                for p in parts:
                    if isinstance(p, str):
                        r = parse_range_list(p.strip())
                        if r is not None:
                            out.extend(r)
                        else:
                            out.append(p)
                    else:
                        out.append(p)
            return out

        elif isinstance(value, str):
            r = parse_range_list(value.strip())
            if r is not None:
                return r
            return value

        else:
            raise OptionError(
                f"Option {underline}{self.name}{reset} got wrong value {value}"
            )

    def parse_default(self, value):
        """
        parse the default value of the option, no validation is performed
        :param value: string with the default value
        :return: the parses value or None if default is None or empty
        """
        if value is None or value == "":
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            r = parse_range_list(value.strip())
            if r is not None:
                return r
            return value
        return value
        

    def check_value(self, value):
        """
        checks a value is in the option domain
        :param value: value to be checked
        :return: none
        :raises OptionError: if value is not string or value is not within domain
        """
        if len(value) > 0:
            for v in value:
                if self.domain is None:
                    return
                elif not (v in self.domain):
                    raise OptionError(f"Option {underline}{self.name}{reset} value/default:"
                                      f"{str(v)} is not within the domain ({','.join(self.domain)})")

    def parse_domain(self, domain: str):
        """
        parses the domain of an option
        :param domain: string that defines the domain in the format (value1, value2, value3, ...)
        :return: returns a list of size N  with the different values [value1, value2, value3, ..., valueN]
        :raises OptionError: if the provided domain has repeated values or is empty
        """
        if not domain is None:
            d = domain.strip("()").split(",")
            # TODO: how to validate string crace option domains when some options do not have domain
            if d[0] == "":
                return None
            if len(d) > len(set(d)):
                raise OptionError(f"Domain for string option {underline}{self.name}{reset} "
                                  f"has repeated values in domain: {domain}")
            d = [x.strip()for x in d]
            return d
        else:
            return None

class UnionOption(Option):
    """
    class the handles string crace options in a union

    :ivar domain: domain of the option as list [value1, value2, value3,...]
    :ivar value: the selection/combination of choices from the list
    """
    def __init__(self, obj):
        """
        Creates a String Option object
        :param obj: dictionary of the option read from the json setting file
        """
        # add general variables
        super()._check_general_options(obj)
        super()._set_general_options(obj)

        # other variables
        self.domain = self.parse_domain(obj['domain'])
        self.default = self.parse_default(obj['default'])
        self.value = self.default

    def parse_domain(self, domain: str):
        """
        parses the domain of an option
        :param domain: string that defines the domain in the format (value1, value2, value3, ...)
        :return: returns a list of size N  with the different values [value1, value2, value3, ..., valueN]
        :raises OptionError: if the provided domain has repeated values or is empty
        """
        if domain is None:
            raise OptionError(f"Union option {underline}{self.name}{reset} must include {bold}domain{reset}")

        try:
            new = eval(domain, {"Union": Union,
                                "Literal": Literal,
                                "Optional": Optional,
                                "bool": bool,
                                "List": list,
                                "list": list,
                                "str": str,
                                "int": int,
                                "float": float,
                                "None": None,})
        except:
            raise OptionError(f"Union option {underline}{self.name}{reset} including wrong {bold}domain{reset}")

        return new

    def parse_value(self, value, check: bool = False, check_default: bool=False):
        """
        parses the option value from a string
        :param value: string that has the value of the option
        :param check: boolean that indicates if the value must be validated
        :return: parsed value. If the value is None or empty, the default value is returned
        """
        if value is None or value == "":
            parsed = None
        else:
            parsed = self._parse_by_typing_domain(value, self.domain)

        if check:
            self.check_value(parsed, check_default)

        return parsed

    def parse_default(self, value):
        """
        parse the default value of the option, no validation is performed
        :param value: string with the default value
        :return: the parses value or None if default is None or empty
        """
        if value is None or value == "":
            return None
        return self.parse_value(value, True, True)

    def set_value(self, value: str):
        """
        sets the value of the option
        :param value: the value to be set
        :return: none
        """
        self.value = self.parse_value(value, check=True)

    def check_value(self, value, check_default: bool=False):
        """
        checks a value is in the option domain Union[Literal[..], ]
        :param value: value to be checked
        :return: none
        :raises OptionError: if value is not string or value is not within domain
        """
        if value is None or value == "":
            return None

        if not check_default and value == self.default: return

        check_type(value=value, expected=self.domain, name=self.name)

    def _parse_by_typing_domain(self, value, expected):
        """
        parse value as in the provided Union domain

        :param value: value to be checked
        :param expected: expected type for the value
        :return: none
        """
        origin = get_origin(expected)
        args = get_args(expected)


        # --------------------------------
        # Union / Optional
        # --------------------------------
        if origin is Union:
            last_error = None
            for t in args:
                try:
                    return self._parse_by_typing_domain(value, t)
                except Exception as e:
                    last_error = e
            raise last_error

        # --------------------------------
        # Literal
        # --------------------------------
        if origin is Literal:
            # case-insensitive for string literals
            if isinstance(value, str) and all(isinstance(a, str) for a in args):
                v = value.strip().lower()
                for a in args:
                    if v == a.lower():
                        # return canonical literal from domain
                        return a

            # fallback: non-str literals (int, bool, etc.)
            try:
                v = value
                if isinstance(value, str):
                    v = ast.literal_eval(value)
            except Exception:
                pass

            if v in args:
                return v

            raise OptionError(
                f"Option {underline}{self.name}{reset} value {bold}{value}{reset} "
                f"is not within domain {self.domain}"
            )

        # --------------------------------
        # list / list[T]
        # --------------------------------
        if origin is list or expected is list:
            print(f"in parse: {value}, {type(value)}, {origin}, {expected}")
            if isinstance(value, list):
                v = value
            elif isinstance(value, str):
                r = parse_range_list(value.strip())
                print("parsed list: ", r)
                if r is not None:
                    v = r
                else:
                    try:
                        v = ast.literal_eval(value)
                        if not isinstance(v, list):
                            v = value
                    except Exception:
                        v = value
            else:
                v = value

            # not a list -> single element
            if not isinstance(v, list):
                if len(args) == 1:
                    return self._parse_by_typing_domain(v, args[0])

                raise OptionError(
                    f"Option {underline}{self.name}{reset} value {bold}{value}{reset} "
                    f"is not within domain {self.domain}"
                )

            # real list
            if len(args) == 0:
                return v

            elem_type = args[0]
            return [self._parse_by_typing_domain(x, elem_type) for x in v]

        # --------------------------------
        # None
        # --------------------------------
        if expected is type(None):
            if value is None:
                return None

            if isinstance(value, str) and value.lower() == "none":
                return None

            raise OptionError(
                f"Option {underline}{self.name}{reset} value {bold}{value}{reset} "
                f"is not within domain {self.domain}"
            )

        # --------------------------------
        # basic types
        # --------------------------------
        if expected in (str, int, float, bool):

            # already correct type
            if isinstance(value, expected):
                return value

            # only parse from string
            if not isinstance(value, str):
                return value

            if expected is str:
                return value

            if expected is int:
                return int(value)

            if expected is float:
                return float(value)

            # bool
            v = value.lower()
            if v in ("true", "1", "yes", "y"):
                return True
            if v in ("false", "0", "no", "n"):
                return False

            raise OptionError(
                f"Option {underline}{self.name}{reset} expects bool, got {bold}{value}{reset}"
            )

        # --------------------------------
        # other object types (e.g. Colormap)
        # --------------------------------
        # Try python literal first
        if isinstance(value, str):
            try:
                v = ast.literal_eval(value)
                if isinstance(v, expected):
                    return v
            except Exception:
                pass

        # If already correct object
        if isinstance(value, expected):
            return value

        # last fallback: return as is (will be rejected by check later)
        return value


exclude_options = ['help', 'man', 'version', 'dpi', 'showfliers', 'showmeans', 'showscale', 'statisticalTest']
class ParseOptions:
    """
    Parse arguments from the input
    """
    def from_input(arguments=None, console=False, add=False):
        options = CplotOptions(arguments=arguments, console=console, add=add)

        return options

class CplotOptions:
    """
    Class contains the set of options that crace plot defined for the results analysis.
    The options are defined in a setting file provided by the package.
    The results are record from an exsiting Crace execution.
    """
    def __init__(self, arguments, console=False, add=False):
        """
        Initialization of an LoadOptions object. Arguments must be provided.

        :param arguments: command line arguments provided by the user (it is not None)
        """
        
        # TODO: option definition file should be set in the module/package.
        # load options definition from json file
        package_dir, _ = os.path.split(__file__)
        filename = os.path.dirname(package_dir) + "/settings/options.json"
        with open(filename, "r") as read_file:
            all_options = json.loads(read_file.read(), object_hook=_option_decoder)

        # create option variables (default values are put in place)
        self.options = []
        for o in all_options:
            self.options.append(o.name)
            setattr(self, o.name, o)

        # arguments is the whole line of input
        self.arguments = arguments

        # load option values
        try:
            self._load_options(arguments, console, add)
        except OptionError as err:
            print("#\n! There was an error while reading crace options :")
            print(f"!   {err}")
            print_info()
            sys.exit(1)
        except FileError as err:
            print("#\n! There was an error while reading crace options file :")
            print(f"!   {err}")
            sys.exit(1)
        except ExitError as err:
            if console:
                pass
            sys.exit(0)
        except Exception as err:
            print("#\n! There was an error: ")
            print(f"!   {err}")
            err = traceback.format_exc()
            print(err)
            sys.exit(1)

    def _load_options(self, arguments, console=False, add=False):
        """
        Load option values from arguments 

        :param arguments: command line arguments provided by the user (it is not None here)
        :return: none
        """
        # check arguments
        any_arg = False
        any_other_arg = False
        for o in self.options:
            if self._get_option(o).long in arguments or self._get_option(o).short in arguments:
                any_arg = True
                if self._get_option(o).name != 'logDir':
                    any_other_arg = True
                    break
        # if not any_arg:
        #     raise OptionError(f"Missing valid option(s)")

        # check for help command
        if self.help.long in arguments:
            print_help_long()
            raise ExitError("")

        # check for help command
        if self.help.short in arguments:
            print_help_short()
            raise ExitError("")

        # check for version command
        if self.version.short in arguments:
            print_version_short()
            raise ExitError("")

        if self.version.long in arguments:
            print_version_long()
            raise ExitError("")
        
        if self.man.long in arguments or self.man.short in arguments:
            index = arguments.index(self.man.long) if self.man.long in arguments else arguments.index(self.man.short)
            if len(arguments) > index+1:
                if arguments[index+1] not in self.options:
                    raise OptionError(f"{arguments[index+1]} is an incorrect crace option name.")
                else:
                    print_man(self._get_option(arguments[index+1]))
            else:
                raise OptionError(f"One option shoud be provided for man.")
            raise ExitError("")

        print(f"#{f'':-^{WIDTH-1}}")
        print("# Reading crace plot options...")
        print("# Arguments: {}".format(arguments))
        print("#\n# Loading crace plot options...")

        # check logDir
        try:
            if self.logDir.long in arguments:
                i = arguments.index(self.logDir.long)
                self.logDir.set_value(arguments[i+1])
            elif self.logDir.short in arguments:
                i = arguments.index(self.logDir.short)
                self.logDir.set_value(arguments[i+1])
            elif self.logDir.exists_file():
                print("# Default race_log folder was found in current directory.")
            else:
                # in this case, we remove the scenario file and assume parameters
                # will be handled manually
                raise OptionError(f"Option {underline}logDir(-l){reset} must be provided.")
        except Exception as e:
            if isinstance(e, IndexError):
                raise OptionError(f"Option {underline}logDir(-l){reset} has no value.")
            else:
                raise OptionError(e)

        if self.logDir.value and not self.logDir.exists_file():
            raise OptionError(f"The provided race_log folder {self.logDir.value} is not readable or does not exist.")

        if self.logDir.is_default():
            self.logDir.set_value(os.path.dirname(self.logDir.value))
        
        if console and not any_other_arg:
            return

        options_long = [self._get_option(x).long for x in self.options]
        options_short = [self._get_option(x).short for x in self.options]

        for o in self.options:
            if len(arguments) < 1:
                break
            if self._get_option(o).short in arguments:
                index = arguments.index(self._get_option(o).short)
            elif self._get_option(o).long in arguments:
                index = arguments.index(self._get_option(o).long)
            else:
                continue

            if isinstance(self._get_option(o), EnablerOption): 
                self._set_option(o, True)
                del arguments[index]
            elif isinstance(self._get_option(o), ListOption):
                s = []
                start = index
                end = start + 1
                while (end < len(arguments) and 
                        arguments[end] not in options_long and
                        arguments[end] not in options_short):
                    s.append(arguments[end])
                    end += 1
                for i in reversed(range(start, end)):
                    del arguments[i]
                self._set_option(o, s)
            else:
                try:
                    self._set_option(o, arguments[index + 1])
                    del arguments[index:(index + 2)]
                except Exception as e:
                    if isinstance(e, OptionError) or isinstance(e, ValueError):
                        raise OptionError(e)
                    else:
                        raise OptionError(f"{self._get_option(o).name} has no value.")

        if len(arguments) > 0:
            raise OptionError(f"Argument not recognized: {arguments[0]}")

        if self.fileName.value is None:
            current_time = datetime.now()
            formatted_time = current_time.strftime("Plot_%Y%m%d_%H%M%S")
            self.fileName.value = formatted_time

    def _get_option(self, option_name):
        """
        get a option in the LoadOption object
        :param option_name: name of the option to be returned
        :return: value of the option
        :raises OptionError: if the option name is unknown
        """
        if option_name not in self.options:
            raise OptionError(f"Attempt to get unknown option {underline}option_name{reset}")
        return getattr(self, option_name)

    def _set_option(self, option_name, option_value):
        """
        set the value of an option in the LoadOptions object
        :param option_name: name of the option
        :param option_value: value to be set
        :return: none
        :raises OptionError: if the option name is unknown
        """
        if option_name not in self.options:
            raise OptionError(f"Attempt to set unknown option {underline}option_name{reset} with value {bold}option_value{reset}")
        getattr(self, option_name).set_value(option_value)

    def _print_options(self):
        """
        Print all options
        """
        print('# Crace plot options: ')
        for o in self.options:
            v = self._get_option(o).value
            if o not in exclude_options:
                print("#   {}: {}".format(o, v))
        print(f"#{f'':-^{WIDTH-1}}")



################################ Print details ##############################
#                              print_cplot_header                           #
#                                 print_help                                #
#                                print_help_long                            #
#                               print_help_short                            #
#                                  print_man                                #
#                                  print_info                               #
#                              print_version_long                           #
#                              print_version_short                          #
#                                  print_args                               #
#############################################################################
def print_cplot_header():
    # TODO: make version automatic
    print(f"#{f'':-^{WIDTH-1}}")
    print(f'# {info.description}')
    print(f'# Version: {info.version}')
    print(f'# {info.copyright}')
    print('#')
    print('# Authors: ')
    for x in info.authors: print(f'#   {x}')
    print('#')
    print(f'# Contact:\n#   {info.contact} ({info.contact_email})')
    print('#')
    print(f'# Check more details at {info.url} ')
    line = format_string(info.license, hanging=0, space=True)
    print("\n".join(f"# {line}" for line in line.splitlines()))
    print('#')
    print(f'# installed at: {CPLOT_HOME}')

    print(f"#{f'':-^{WIDTH-1}}")


def print_help():
    """
    Print help information of crace-plot
    """
    print_cplot_header()
    print("# called with: --help (-h)")
    package_dir, _ = os.path.split(__file__)
    filename = os.path.dirname(package_dir) + "/settings/options.json"
    with open(filename, "r") as read_file:
        all_options = json.loads(read_file.read(), object_hook=_option_decoder)

    options = []
    for o in all_options:
        options.append(o.name)
        if o.short is not None and o.short != "":
            print("#\n# {:<4}, {:<29}{}".format(o.short, o.long, o.description))
        else:
            print("#\n# {:<6}{:<29}{}".format(o.short,o.long, o.description))
        if o.default is not None or o.default != "":
            print("# {:<35}Default: {}".format('', o.default))
        if o.type in ['i', 's']:
            print("# {:<35}Domain: {}".format('', o.domain))
    print(f"#\n#{f'':-^{WIDTH-1}}")


def print_help_long():
    print_cplot_header()
    package_dir, _ = os.path.split(__file__)
    filename = os.path.dirname(package_dir) + "/settings/options.json"
    with open(filename, "r") as read_file:
        all_options = json.loads(read_file.read(), object_hook=_option_decoder)

    from collections import defaultdict
    groups = defaultdict(list)
    for o in all_options:
        if o.critical > 1: continue
        groups[o.section].append(o)

    options = []
    for section, options_list in groups.items():
        print(f"\n  {f' {section.upper()} ':=^{WIDTH-4}}\n")

        for o in options_list:
            if o.critical > 1:
                continue
            options.append(o.name)

            print(f"{bold}# Name:{reset} {o.name}")
            print(f"  {bold}Long:{reset} {o.long if o.long else 'None'}")
            print(f"  {bold}Short:{reset} {o.short if o.short else 'None'}")
            if o.type in ['i', 's']:
                print(f"""  {format_string(f"{bold}Domain:{reset} {o.domain if o.domain else 'None'}", hanging=2)}""")
            if o.default is not None and o.default != "" and o.default != []:
                print(f"  {bold}Default:{reset} {o.default}")
            else:
                print(f"  {bold}Default:{reset} None")
            if o.description:
                print(f"""  {format_string(f"{bold}Description:{reset} {o.description}", hanging=2)}""")
            if o.vignettes:
                print(f"""  {format_string(f"{bold}Vignettes:{reset} {o.vignettes}", hanging=2, space=True)}""")
            print()

    print(f'\n# call with {bold}--man [option_name]{reset} to check the details of specified option')
    print(f"#{f'':-^{WIDTH-1}}")


def print_help_short():
    print_cplot_header()
    package_dir, _ = os.path.split(__file__)
    filename = os.path.dirname(package_dir) + "/settings/options.json"
    with open(filename, "r") as read_file:
        all_options = json.loads(read_file.read(), object_hook=_option_decoder)

    from collections import defaultdict
    groups = defaultdict(list)
    for o in all_options:
        if o.critical > 1: continue
        groups[o.section].append(o)

    max_name_l = max([len(o.name) for o in all_options if o.critical <= 1])
    max_short_l = max([len(o.short) for o in all_options if o.critical <= 1])
    max_long_l = max([len(o.long) for o in all_options if o.critical <= 1])
    sum_max_l = sum([max_name_l, max_short_l, max_long_l])

    options = []
    for section, options_list in groups.items():
        print(f"# {bold}{section}{reset}")

        for o in options_list:
            if o.critical > 1:
                continue
            options.append(o.name)
            format_de = format_string(o.description, width=WIDTH*1.2, hanging=sum_max_l+5) if o.description else ""
            print(f"  {o.name:<{max_name_l+1}}{o.short:<{max_short_l+1}}{o.long:<{max_long_l+1}}{format_de}")
        print()
    print(f'\n# call with {bold}--man [option_name]{reset} to check the details of specified option')
    print(f"#{f'':-^{WIDTH-1}}")


def print_man(o):
    """
    print selected options: critical <= 1
    """
    if o.critical > 1 and o.critical <= 4:
        print(f"Option {bold}{o.name}{reset} is not available in crace currently.")
        raise ExitError("")
    elif o.critical > 4 and o.critical <7:
        print(f"{bold}{o.name}{reset} is not an available crace option.")
        raise ExitError("")

    print(f"{bold}Name:{reset} {o.name}")
    print(f"{bold}Long:{reset} {o.long if o.long else 'None'}")
    print(f"{bold}Short:{reset} {o.short if o.short else 'None'}")
    if o.type in ['i', 's']:
        print(f"""\n{format_string(f"{bold}Domain:{reset} {o.domain if o.domain else 'None'}", hanging=0)}\n""")
    if o.default is not None and o.default != "" and o.default != []:
        print(f"{bold}Default:{reset} {o.default}")
    else:
        print(f"{bold}Default:{reset} None")
    print(f"""\n{format_string(f"{bold}Description:{reset} {o.description}", hanging=0)}\n""")
    print(f"""{format_string(f"{bold}Vignettes:{reset} {o.vignettes}", hanging=0, space=True)}""")


def print_info():
    print(f"!   You can check the information of HELP ({bold}-h, --help{reset}) "
          f"or man page ({bold}--man / -m{reset}).\n")


def print_version_long():
    print_cplot_header()
    print_cite_info()


def print_version_short():
    print(f"crace {info.version}")
    

def print_args(args):
    print(f"#{f'':-^{WIDTH-1}}")
    print('# Crace plot arguments: ')
    for name, value in vars(args).items():
        if name in ['data', 'options']: continue
        print(f"#   {name}: {value}")
    print(f"#{f'':-^{WIDTH-1}}")


def print_cite_info():
    cit = format_string(info.citiation, width=WIDTH, hanging=0, space=True)
    print("\n".join(f"# {line}" for line in cit.splitlines()))
    print(f"#{f'':-^{WIDTH-1}}")

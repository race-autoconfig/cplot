import os
import sys

def _setup_crace(crace_main_custom_file=None):
    if crace_main_custom_file is not None:
        for name in list(sys.modules):
            if name == "crace" or name.startswith("crace."):
                del sys.modules[name]
        crace_main_file = crace_main_custom_file
    else:
        crace_main_file = os.environ.get("CRACE_MAIN_FILE")

    # case 1: if CRACE_MAIN_FILE exists
    if crace_main_file and os.path.exists(crace_main_file):
        # from .../crace/scripts/main.py → return .../crace
        crace_home = os.path.dirname(os.path.dirname(os.path.dirname(crace_main_file)))

        # insert crace home to path
        if crace_home not in map(os.path.abspath, sys.path):
            sys.path.insert(0, str(crace_home))

    try:
        import crace
        return crace
    except ImportError as exc:
        if crace_main_file:
            raise RuntimeError(
                f"Failed to import crace from CRACE_MAIN_FILE directory:\n{crace_home}"
            ) from exc
        else:
            raise RuntimeError(
                "CRACE_MAIN_FILE is not set, and 'import crace' also failed.\n"
                "Please set CRACE_MAIN_FILE to point to crace/scripts/main.py, \n"
                "or provide the path to crace/scripts/main.py after --crace or -c in command line arguments."
            ) from exc

def get_crace(crace_main_file=None):
    return _setup_crace(crace_main_file)

def get_CraceResults():
    from crace.containers.crace_results import CraceResults
    return CraceResults
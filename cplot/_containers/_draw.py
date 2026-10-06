from __future__ import annotations

import re
import sys
import inspect
import traceback

from cplot._containers._core import CplotOptions, ParseOptions, Errors as CE
from cplot._plots.parameters import plot_parameters
from cplot._plots.quality import plot_experiments

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crace.containers.crace_results import CraceResults

def load_options(*kargs, arguments: list=None, _console: bool=True, _add: bool=True):
    """
    Load options for cplot: directly called by users
    """
    if arguments is not None and kargs:
        raise TypeError(
            "load_options() accepts either positional arguments "
            "or 'arguments=', not both")
    if arguments is not None:
        if not isinstance(arguments, list):
            if isinstance(arguments, str):
                arguments = re.split(r"[ ,]+", arguments)
    elif len(kargs) > 0:
        arguments = list(kargs)
    elif _console:
        arguments = []
    else:
        # arguments may be [] (not None)
        arguments = sys.argv[1:]

    scenario = None
    try:
        scenario = ParseOptions.from_input(arguments=arguments, console=_console, add=_add)
    except Exception as e:
        print("\nERROR: There was an error while loading crace results:")
        sys.tracebacklimit = 3
        traceback.print_exc()
        print(e)
    finally:
        if not _console: sys.exit(1)
        else: return scenario


def load_results(options: CplotOptions, data_home=None):
    """
    load crace results from data_home

    """
    results = None
    log_path = None

    if data_home:
        log_path = data_home
    elif options.logDir.value:
        log_path = options.logDir.value

    from cplot._utils._crace import get_crace
    crace = get_crace()
    results = crace.run(f'--read, {log_path}, --readlogs-in-cplot, 2')

    return results


class DrawPlot:
    """
    Class defines the procedure to select one drawMethod for drawing plot
    :ivar drawMethod: the method used to draw plot for provided Crace results
    """
    def __init__(self, reader: CplotOptions, src_data: CraceResults) -> None:
        """
        initialize for drawing plot

        src_data: class CraceResults
        scr_vars: list of parameters from the provided crace results
        """

        src_data = src_data
        options = reader

        draw_method = reader.drawMethod.value
        data_type = 'exps' if reader.dataType.value in ['experiments', 'quality', 'time'] else 'param'

        try:
            if data_type == 'param':
                plot_parameters(method=draw_method, data=src_data, options=options, _console=False)
            elif data_type == 'exps':
                plot_experiments(method=draw_method, data=src_data, options=options, _console=False)

            print('#\n# Succeeded! ')

        except Exception as e:
            if any(isinstance(e, cls) for cls in [x[1] for x in inspect.getmembers(CE, inspect.isclass)]):
                print("#\n! There was an error while plotting:")
                print(f"!   {e}")
            else:
                err = traceback.format_exc()
                print(err)
            sys.exit()

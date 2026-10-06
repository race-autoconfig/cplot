import os
import sys
import re
import inspect
import traceback

current_file = os.path.normpath(__file__)
CPLOT_HOME = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if CPLOT_HOME not in map(os.path.abspath, sys.path):
    sys.path.insert(0, os.path.abspath(CPLOT_HOME))

from cplot._containers._core import ParseOptions, Errors as CE
from cplot._containers._draw import DrawPlot, load_results

def start_cmdline(arguments=None, console: bool=True):
    """
    Function that executes the configuration procedure with arguments from the command line
    """

    data = None
    scenario = None
    current_dir = os.getcwd()

    try:
        scenario = ParseOptions.from_input(arguments=arguments, console=console)

        if scenario.logDir.value is not None:
            data = load_results(options=scenario.options, data_home=scenario.logDir.value)

        if data:
            if console:
                # check if there is any other options
                any_arg = False
                for o in scenario.options:
                    if scenario._get_option(o).long in arguments or scenario._get_option(o).short in arguments:
                        if scenario._get_option(o).name != 'logDir':
                            any_arg = True
                            break
                # if there is only one option logDir, return
                if not any_arg: return data, scenario
            # other cases:
            #   - not in console
            #   - including other options
            print(f"# Setting working directory: {scenario.logDir.value}\n#")
            if os.path.exists(scenario.logDir.value):
                os.chdir(scenario.logDir.value)
            if scenario.drawMethod.value is not None: DrawPlot(reader=scenario, src_data=data)
            os.chdir(current_dir)

        if console: return data, scenario

    except KeyboardInterrupt:
        print()

    except SystemExit:
        pass

    except Exception as e:
        if any(isinstance(e, cls) for cls in [x[1] for x in inspect.getmembers(CE, inspect.isclass)]):
            pass
        else:
            print("\nERROR: There was an error while executing cplot:")
            sys.tracebacklimit = 20
            traceback.print_exc()
            print(e)

    if not console: sys.exit(1)

    return


def _parse_args(*args):
    if len(args) == 1:
        args = args[0]
    if isinstance(args, list):
        outs = args
    elif isinstance(args, str):
        outs = re.split(r"[ ,]+", args)
    else:
        outs = list(args)
    return [str(x) for x in outs]


def start_cplot(*kargs, arguments: list=None, console: bool=True):
    """
    Allowed to be called: 1. by entry point, 
                          2. by crace_mpi 
                          3. in python console
    """
    if arguments is not None and kargs:
        raise TypeError(
            "load_options() accepts either positional arguments "
            "or 'arguments=', not both")
    if arguments is not None:
        arguments = _parse_args(arguments)
    elif len(kargs) > 0:
        arguments = _parse_args(*kargs)

    if not arguments:
        # arguments may be [] (not None)
        arguments = sys.argv[1:] # command line arguments as a list

    if ('--crace' in arguments) or ('-c' in arguments):
        index = arguments.index('--crace') if '--crace' in arguments else arguments.index('-c')
        try:
            from cplot._utils._crace import get_crace
            crace_main_file = arguments[index + 1]
            crace = get_crace(crace_main_file)
            print(f"# Loading crace from: {crace_main_file}")
            print(f"# crace version: {crace.__version__}")
            del arguments[index:index + 2]
        except IndexError:
            raise RuntimeError("Please provide the path to crace/scripts/main.py after --crace or -c")

    if len(arguments) == 0: return

    data = start_cmdline(arguments, console)

    if data: return data

def _parse_args(*args):
    if len(args) == 1:
        args = args[0]
    if isinstance(args, list):
        outs = args
    elif isinstance(args, str):
        outs = re.split(r"[ ,]+", args)
    else:
        outs = list(args)
    return [str(x) for x in outs]


if __name__ == '__main__':
    """
    Allowed to be called only by this file
    """
    start_cplot(console=False)

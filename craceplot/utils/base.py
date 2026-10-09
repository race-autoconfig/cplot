# craceplot.core.utils.py

import re
import copy
import inspect
import numpy as np
from functools import wraps
from typing import get_origin, get_args, Union, Literal, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

dispatch_table_param = {}
methods_table_param = {}
def register_param(names):
    if isinstance(names, str):
        names = [names]

    primary_name = names[0]

    def decorator(func):
        for name in names:
            if name not in dispatch_table_param.keys():
                dispatch_table_param[name] = func
            if name not in methods_table_param.keys():
                methods_table_param[name] = primary_name
        return func
    return decorator


dispatch_table_exps = {}
methods_table_exps = {}
def register_exps(names):
    if isinstance(names, str):
        names = [names]

    primary_name = names[0]

    def decorator(func):
        for name in names:
            if name not in dispatch_table_exps.keys():
                dispatch_table_exps[name] = func
            if name not in methods_table_exps.keys():
                methods_table_exps[name] = primary_name
        return func
    return decorator


def short_type(t):
    import builtins
    if t in vars(builtins).values():  # builtin types keep as-is
        return t

    class NewName:
        __name__ = t.__name__
        __qualname__ = t.__name__

    try:
        del NewName.__module__
    except Exception:
        NewName.__module__ = None

    return NewName


def enforce_types(func):
    sig = inspect.signature(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        for name, value in bound.arguments.items():
            if value is None:
                continue

            expected = sig.parameters[name].annotation

            if expected is inspect._empty:
                continue

            # Forward reference
            if isinstance(expected, str):
                if expected == "CraceResults":
                    from crace.containers.crace_results import CraceResults
                    expected = CraceResults
                else:
                    continue

            check_type(value, expected, name)

        return func(*args, **kwargs)

    wrapper.__signature__ = sig
    return wrapper


def check_type(value, expected, name):
    origin = get_origin(expected)
    args = get_args(expected)

    # ===== Union: try ALL branches =====
    if origin is Union:
        for t in args:
            try:
                check_type(value, t, name)
                return  # any branch ok
            except Exception:
                pass
        raise TypeError(
            f"Argument/Option '{name}' does not match any allowed type in {args}, "
            f"got {value!r}({type(value)})"
        )

    # ===== Literal =====
    if origin is Literal:
        if value not in args:
            raise ValueError(
                f"Argument/Option '{name}' must be one of {args}, got {value!r}"
            )
        return

    # --------------------------------
    # list / list[T]
    # --------------------------------
    if origin is list or expected is list:
        if not isinstance(value, list):
            raise TypeError(f"Argument/Option '{name}' must be list, got {type(value)}")

        if len(args) == 0:
            return

        elem_type = args[0]

        for v in value:
            check_type(v, elem_type, name)

        return

    # tuple[T, ...]
    if origin is tuple:
        if not isinstance(value, tuple):
            raise TypeError(f"Argument/Option '{name}' must be tuple")
        elem_types = args
        if len(elem_types) == 2 and elem_types[1] is Ellipsis:
            for v in value:
                check_type(v, elem_types[0], name)
        else:
            for v, t in zip(value, elem_types):
                check_type(v, t, name)
        return

    # ===== NoneType =====
    if expected is type(None):
        if value is not None:
            raise TypeError(f"Argument/Option '{name}' must be None")
        return

    # ===== normal class =====
    if isinstance(expected, type):
        if not isinstance(value, expected):
            raise TypeError(
                f"Argument/Option '{name}' expected {expected}, got {type(value)}"
            )
        return


def safe_copy(obj):
    try:
        return copy.deepcopy(obj)
    except Exception:
        return obj


def parse_range_list(s: str):
    """
    Parse '[start:stop]' or '[start:stop:step]' into list[int].
    Python range semantics: stop is exclusive.
    """
    re_format = re.compile(
        r'^\s*\[?\s*(-?\d+)\s*:\s*(-?\d+)(?:\s*:\s*(-?\d+(?:\.\d+)?))?\s*\]?\s*$')
    m = re_format.match(s)
    print(s, m)
    if not m:
        return None

    start = int(m.group(1))
    stop = int(m.group(2))
    step = m.group(3)

    if step is None:
        return np.arange(start, stop+1).tolist()
    else:
        step = eval(step)
        return np.arange(start, stop+step, step).tolist()

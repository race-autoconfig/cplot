# craceplot.plot.parameters.py

from __future__ import annotations

import os
import sys
import re
import random
import inspect
import math
import time
import traceback

import numpy as np
import pandas as pd
from types import SimpleNamespace
from matplotlib.colors import Colormap
from typing import TYPE_CHECKING, Union, Literal, Callable, TypeVar, ParamSpec, Optional

from craceplot.plots.core import *
from craceplot.utils.base import *
from craceplot.containers.core import bold, underline, reset, CplotOptions, Errors as CE

P = ParamSpec("P")
R = TypeVar("R")

if TYPE_CHECKING:
    from crace.containers.crace_results import CraceResults

__all__ = []

def export(func: Callable[P, R]) -> Callable[P, R]:
    """append func name to list __all__"""
    __all__.append(func.__name__)
    return func

exclude_cols = ['configuration_id', 'slice_sampled']
missing_label = "<NA>"

args = SimpleNamespace(
    # required parameters
    data=None,
    options=None,
    configs=None,
    sel_vars=None,
    sel_kvar=None,
    slice=True,
    out_dir=None,
    file_name=None,
    tile=None,
    cat=False,
    console=True,
    # optional parameters
    colorby=None,
    showscale=True,
    shownan=True,
    showfliers=False,
    showmeans=False,
    dpi=800,
    nbins=5,
)

def add_slice(data: pd.DataFrame, slice: pd.DataFrame):
    """add slice information to selected data"""
    last_configs = slice["last_config_id"].to_numpy(dtype=int)
    idx = np.searchsorted(last_configs, data["configuration_id"].values, side="right")
    new = data.assign(slice_sampled=idx + 1)

    return new

def sel_conf(data: pd.DataFrame, args, configs=None):
    """
    return a dataframe based on configuration types of IDs
    
    :param data: full experiments data
    :type data: pd.DataFrame
    :param configs: string or list
    """
    # configs:    Union[Literal['all', 'final', 'elites', 'else'], list[int], None]='all',

    if not configs: return data
    elif isinstance(configs, str):
        c =  configs.lower()
        if c == 'all': return data
        elif c == 'final':
            sel = args.data.elites
            return data[data['configuration_id'].isin(sel)]
        elif c == 'elites':
            sel = args.data.all_elites
            return data[data['configuration_id'].isin(sel)]
    elif isinstance(configs, list):
        return data[data['configuration_id'].isin(configs)]
    else:
        raise CE.OptionError(f"Failed to select data based on provided configuration value {configs}, "
                             f"please check {underline}configs{reset} or {underline}numConfigurations{reset}/{underline}selConfigurations{reset}")

def parse_parameters(parameters, data):
    """
    load the range of each parameter in the provided Crace results
    """
    # parse all parameters from log files
    all_parameters = {}
    tmp_params = parameters.get_names()
    for p in tmp_params:
        all_parameters[p] = {}
        all_parameters[p]['type'] = parameters.get_parameter(p).type
        all_parameters[p]['domain'] = parameters.get_parameter(p).domain

    # add user defined parameters
    all_parameters['configuration_id'] = {}
    all_parameters['configuration_id']['type'] = 'i'
    all_parameters['configuration_id']['domain'] = [int(data['configuration_id'].min()), int(data['configuration_id'].max())]
    all_parameters['slice_sampled'] = {}
    all_parameters['slice_sampled']['type'] = 'i'
    all_parameters['slice_sampled']['domain'] = [int(data['slice_sampled'].min()), int(data['slice_sampled'].max())]
    return all_parameters

@enforce_types
def _check_options(name: str, args: SimpleNamespace):
    """
    check options
    
    options provided by args have higher priority

    each option will be read from args when plotting

    ONLY modify args

    # required parameters
    data=None,
    options=None,
    sel_vars=None,
    sel_kvar=None,
    slice=True,
    out_dir=None,
    file_name=None,
    tile=None,
    cat=False,
    console=True,
    # optional parameters
    showscale=True,
    shownan=True,
    dpi=800,
    nbins=5,

    """
    # data must be provided
    if not args.data:
        raise CE.OptionError(f"{bold}data{reset} must be provided for plotting.")

    # check onlytest
    onlytest = args.data.options.onlytest.value
    if onlytest: raise CE.CplotError(
        f"The provided crace log files only has results for test part, "
        f"which is unavaliable for plotting parameters."
    )

    # slice:      bool=True
    # options.slice: Union[Literal['budget','b','experiment','e','exp','time','t','T'], bool, None]
    if args.options.slice.value is True or args.slice:
        args.slice = True 
    elif (args.options.slice.value is False
          or args.options.slice.value is None
          or not args.slice):
        args.slice = False
    else:
        print(f"#\n# Option {underline}slice{reset} value {bold}{args.options.slice.value}{reset} "
              f"is not avaliable when plotting for parameters\n"
              f"#    selected parameters: {', '.join(args.sel_vars)}")

    # showscale:  bool=True
    args.showscale = True if args.options.showscale.value or args.slice else False

    # dpi: int
    args.dpi = args.options.dpi.value if not args.options.dpi.is_default() else args.dpi

    # out_dir:    str=None
    if not args.out_dir and args.options.outDir.is_set():
        args.out_dir = args.options.outDir.value
    if not os.path.exists(args.out_dir):
        raise CE.OptionError(f"Provided {bold}outDir/out_dir{reset} is not exist.")

    # file_name:  str=None
    if not args.file_name and args.options.fileName.is_set():
        args.file_name = args.options.fileName.value

    # tile: str=None
    if not args.tile and args.options.title.is_set():
        args.tile = args.options.title.value

    # ===================================================================================
    # check multiParameters (args.sel_vars)
    multi_required = ['pair']
    key_required = ['pair']

    if not args.sel_vars:

        # random selected parameters only when multiParameters is [] and sel_vars is None
        if not args.options.multiParameters.value:
            if name == 'coord': k=10
            elif name == 'cat': k=2
            elif name == 'sun': k=6
            elif name == 'hist':
                if args.slice: k=1
                else: k=8
            elif name == 'box': k=1
            else:
                raise CE.OptionError(f"{underline}multiParamters/parameters/sel_vars{reset} must be provided here.")

            if name not in []:
                random.seed(time.time())
                args.sel_vars = sorted(random.sample(args.data.parameters.get_names(), k=k), key=str.lower)
                print(f"#\n# No parameters selected to draw plot, "
                      f"set to the default(random selected {k} parameters).\n"
                      f"#    selected parameters: {', '.join(args.sel_vars)}"
                )
    
        # check each parameters when multiParameters is provided
        # and assign valid multiParameters to args.sel_vars
        else:
            for x in args.options.multiParameters.value:
                if x not in args.data.parameters.get_names():
                        raise CE.ParameterValueError(f"Provided {bold}{x}{reset} is an invalid parameter.")
            args.sel_vars = args.options.multiParameters.value

    # check sel_vars for specific plots
    if name in ['cat', 'heat', 'joint'] and len(args.sel_vars) > 2:
        del args.sel_vars[2:]
        print(f"#\n# More than two parameters are provided for drawing plot.\n"
              f"#    selected parameters: {', '.join(args.sel_vars)}")

    if name in ['joint'] and len(args.sel_vars) == 1:
        print(f"#\n# Two parameters must be provided for drawing plot.\n")

    if name in ['pair', 'joint']:
        for x in args.sel_vars:
            if args.data.parameters.get_parameter(x).type == 'c':
                raise CE.OptionError(f"When {bold}{methods_table_param[name]}{reset} is selected, "
                                     f"{underline}multiParameters/sel_vars{reset} ({bold}{x}{reset}) must be numeric.")


    # ====================================================================================
    # check keyParameter (args.sel_kvar)
    # provided key parameter
    if args.sel_kvar is not None:
        key_v = args.sel_kvar
    elif args.options and args.options.keyParameter.is_set():
        key_v = args.options.keyParameter.value
    else:
        key_v = None

    # if key parameter is provided
    if key_v:
        if name == 'coord':
            print(f"#\n# Parameter {bold}{key_v}{reset} is used for colorscale.")
        if name == 'pair' and args.data.parameters.get_parameter(key_v).type != 'c':
            raise CE.OptionError(f"When {bold}pairplot{reset} is selected, {underline}keyParameter/sel_kvar{reset} must be categorical.")

    # if key parameter is not provided: set as default
    else:
        if name == 'coord':
            print(f"#\n# No {underline}keyParameter{reset} or {bold}sel_kvar{reset} provided, set colorscale as default.")
        elif name == 'box' and not args.sel_vars:
            raise  CE.OptionError(f"Either {underline}multiParamters/sel_vars{reset} or "
                                  f"{underline}keyParameter/hue/sel_kvar{reset} must be provided here "
                                  f"for {bold}{methods_table_param[name]}{reset}")


        elif name in key_required:
            raise CE.OptionError(f"{underline}keyParameter/hue/sel_kvar{reset} must be provided here.")

        if args.options.slice.value or args.slice:
            key_v = 'slice_sampled'
        else:
            key_v = 'configuration_id'
    
    args.sel_kvar = key_v if name not in ['heat', 'cat'] else None

    if name == 'pair' and args.data.parameters.get_parameter(args.sel_kvar).type != 'c':
        raise CE.OptionError(f"When {bold}pairplot{reset} is selected, {underline}keyParameter/sel_kvar{reset} must be categorical.")


    # check configurations
    if not args.configs:
        c = args.options.numConfigurations.value
        if c.lower() in ['all', 'final', 'elites']:
            args.configs = c
        elif c.lower() == 'else':
            args.configs = c
        else:
            args.configs = None


def _check_str_list(lst):
    import ast
    try:
        for x in lst:
            if not isinstance(x, str):
                return False
            v = ast.literal_eval(x)
            if not isinstance(v, (int, float)):
                return False
        return True
    except Exception:
        return False

@enforce_types
def _map_values(name: str, data: pd.DataFrame, ori_params, parameters, cat: bool=False, nbins: int=5, shownan: bool=True):
    """map parameter values"""
    data = data[list(parameters.keys())].copy()

    # print("#\n# The selected crace results:")
    # print(data)

    num = len(data)

    vars_dict = []
    vars_dict = safe_copy(parameters)

    # add ticktext
    for pname in parameters.keys():
        vars_dict[pname]['vals'] = safe_copy(vars_dict[pname]['domain'])
        vars_dict[pname]['text'] = safe_copy(vars_dict[pname]['domain'])

    map_dic = {}
    show_info = False
    print_info = True if name in ['cat', 'coord'] else False

    types = set(parameters[pname]['type'] for pname in ori_params.keys())
    max_l = max([len(x) for x in vars_dict.keys() if x not in exclude_cols])

    col = data[pname].copy()
    data[pname] = (col.replace(['null', 'NULL', 'none', 'None', 'missing', 'NA', 'NaN', None], np.nan))


    # ====================================================================================
    # replace NaN values
    if shownan:
        all_nan_cols = data.count() == 0
        ratios = [data[pname].isna().sum() / float(num) for pname in all_nan_cols.index]
        # if any (r > 0 for r in ratios): print("#\n# Replacig MISSING values..")

        for pname, per in zip(all_nan_cols.index, ratios):
            if pname not in vars_dict.keys(): continue
            if pname in exclude_cols: continue

            ptype = vars_dict[pname]['type']
            pdomain = safe_copy(vars_dict[pname]['domain'])

            if per > 0:
                # replace nan
                # === categorical / ordinal ===
                if ptype in ('c', 'o'):
                    # expand domain
                    if data[pname].isna().any() and missing_label not in pdomain:
                        vars_dict[pname]['domain'] = pdomain + [missing_label]
                        vars_dict[pname]['vals'] = pdomain + [missing_label]
                        vars_dict[pname]['text'] = pdomain + [missing_label]

                    col = data[pname].copy()
                    data[pname] = (col.fillna(missing_label))


                # === continuous ===
                else:
                    pmin, pmax = pdomain

                    minimo = pmin
                    maximo = round(pmax * 5 / 4, 1)

                    medio  = round(pmax / 4, 1)
                    medio2 = round(pmax / 2, 1)
                    medio3 = round(pmax * 3 / 4, 1)

                    vars_dict[pname]['domain'] = [minimo, maximo]
                    vars_dict[pname]['vals'] = [minimo, medio, medio2, medio3, pmax, maximo]
                    vars_dict[pname]['text'] = [minimo, medio, medio2, medio3, pmax, missing_label]

                    col = data[pname].copy()
                    data[pname] = (col.fillna(maximo).astype(float))

            elif ptype in ('i', 'i,log', 'r', 'r,log'):
                minimo, maximo = pdomain

                medio  = round(maximo / 4, 1)
                medio2 = round(maximo / 2, 1)
                medio3 = round(maximo * 3 / 4, 1)

                vars_dict[pname]['domain'] = [minimo, maximo]
                vars_dict[pname]['vals'] = vars_dict[pname]['text'] = [minimo, medio, medio2, medio3, maximo]


    # ====================================================================================
    # convert parameter type
    # if name not in ['hist', 'box', 'sun', 'coord']:
    if name in ['cat', 'heat', 'coord']:
        for pname in parameters.keys():
            if pname in exclude_cols: continue
            ptype = parameters[pname]['type']

            # continouse -> categorical
            if cat and ptype != 'c':
                old = vars_dict[pname]['domain']
                colmin = vars_dict[pname]['domain'][0]
                colmax = vars_dict[pname]['domain'][1]
                safe_max = np.nextafter(colmax, np.inf)
                safe_min = np.nextafter(colmin, -np.inf)
                # get sub-domains
                bins = np.linspace(safe_min, safe_max, nbins + 1)
                display_bins = np.linspace(colmin, colmax, nbins+1)
                # digitize
                # return 1..N_bins
                vals = data[pname].values
                binned = np.full_like(vals, fill_value=np.nan, dtype=float)
                mask = ~np.isnan(vals)
                # map value to sub-domains
                # from 0 to nbins-1
                res = np.digitize(vals[mask], bins, right=False) - 1
                res = np.clip(res, 0, nbins - 1)

                # 2. update data
                binned[mask] = res
                data[pname] = binned
                # 3. update domain and type
                if missing_label not in vars_dict[pname]['text']:
                    vars_dict[pname]['text'] = [f"[{display_bins[i]:.1f}, {display_bins[i+1]:.1f})" for i in range(nbins)]
                else:
                    vars_dict[pname]['text'] = [f"[{display_bins[i]:.1f}, {display_bins[i+1]:.1f})" for i in range(nbins-1)]+[missing_label]

                vars_dict[pname]['domain'] = list(range(0, nbins))
                vars_dict[pname]['vals'] = list(range(0, nbins))
                vars_dict[pname]['type'] = 'c'

                if not show_info:
                    print("#\n# Mapping parameter type..")
                    show_info = True
                print(f"#  (WARNING: convert parameter {bold}{pname}{reset}({ptype}) to categorical for plotting)")
                # print("#   %*s: old domain %s -> new domain %s " % (max_l, pname, old, vars_dict[pname]['text']))

            # catgorical -> continouse
            if not cat and ptype == 'c':
                old = list(vars_dict[pname]['domain'])
                map_dic[pname] = {v: int(i) for i, v in enumerate(old)}
                vals = list(map_dic[pname].values())

                col = data[pname].copy()
                data[pname] = (col.map(map_dic[pname]).astype(int))

                vars_dict[pname]['domain'] = [min(vals), max(vals)]
                vars_dict[pname]['vals'] = vals
                vars_dict[pname]['text'] = old

                if not show_info:
                    print("#\n# Mapping parameter type..")
                    show_info = True
                print(f"#  (WARNING: map values of parameter {bold}{pname}{reset}({ptype}) for ploltting)")
                # print("#   %*s: old domain %s -> new domain %s " % (max_l, pname, old, vars_dict[pname]['domain']))

    return data, vars_dict

@enforce_types
def _load_data(name: str, args: SimpleNamespace):
    """load data"""
    src_configs = args.data.configurations.print_all().kwargs['all']
    src_configs = src_configs.rename(columns={".ID": "configuration_id"})
    src_configs = src_configs.rename(columns={".PARENT": "parent_id"})

    src_pd = add_slice(data=src_configs, slice=args.data.training.slice)
    sel_pd = sel_conf(data=src_pd, configs=args.configs, args=args)

    src_vars = parse_parameters(args.data.parameters, sel_pd)

    # print("#\n# The original crace results:")
    # print(sel_pd)

    ori_dict = {}
    sel_dict = {}
    for x in args.sel_vars:
        ori_dict[x] = {}
        ori_dict[x] = safe_copy(src_vars[x])
        sel_dict[x] = {}
        sel_dict[x] = safe_copy(src_vars[x])
    if name in ['hist', 'box', 'coord'] or (args.sel_kvar and args.sel_kvar not in exclude_cols):
        sel_dict[args.sel_kvar] = {}
        sel_dict[args.sel_kvar] = safe_copy(src_vars[args.sel_kvar])
    if name == 'heat':
        for x in exclude_cols:
            if x not in sel_dict: sel_dict[x] = safe_copy(src_vars[x])

    new_data, new_vars = _map_values(name=name, data=sel_pd, ori_params=ori_dict, parameters=sel_dict, cat=args.cat, nbins=args.nbins, shownan=args.shownan)

    # print("#\n# The new Crace results:")
    # print(new_data)

    return new_data, src_vars, new_vars

@enforce_types
def _resolve_input(name: str, args: SimpleNamespace):
    """
    resolve input
    """
    new_data= None
    new_vars=None

    _check_options(name=name, args=args)

    new_data, src_vars, new_vars = _load_data(name=name, args=args)

    return new_data, src_vars, new_vars

def plot_parameters(method: str, **kwargs):
    """
    entrance to call plotting function from file _draw.py
    including try-except
    """
    # drawMethod: (boxplot, violinplot, parallelcoord, parallelcat, sunburst, pairplot, histplot, jointplot, heatmap)
        
    func = dispatch_table_param.get(method)

    try:
        if func: return func(**kwargs)
        else: raise ValueError(f"Method '{method}' is not defined in dispatch table.")

    except Exception as e:
        print("\n! There was an error while plotting for parameters:")
        if any(isinstance(e, cls) for cls in [x[1] for x in inspect.getmembers(CE, inspect.isclass)]):
            print(f"!   {e}")
        else:
            err = traceback.format_exc()
            print(err)
        if kwargs["_console"]: return None
        sys.exit(1)


@export
@enforce_types
def param_parallelcoord(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    colorby:    str=None,
    slice:      bool=True,
    out_dir:    str=None,
    file_name:  str=None,
    tile: str=None,
    _console:   bool=True,
    # optional parameters
    showscale:  bool=True,
    shownan:    bool=True,
    nbins:      int=5,
    # specific parameters
    width:      int=2560,
    height:     int=1440,
    colorscale: str='Tealrose',
    as_html:    bool=False,
):
    """
    Entrance to call parallel coord in python console
    
    :param data: object CraceResults that must be provided.
    :param options: object CplotOptions that must be provided.
    :param configs: Optional. Selected configurations for plotting, higher priority than option numConfigurations/selConfigurations. Supported values are 'all', 'final', 'elites' or a list of configuration IDs. Default is 'all'.
    :param parameters: A list of parameter names selected for plotting, higher priority than option multiParameters.
    :param colorby: A string of parameter name selected for plotting, higher priority than option keyParameter.
    :param showscale: Boolean used to enable/diable showing colorscale. 
    :param shownan: Boolean used to plot including/excluding missing values.
    :param colorscale: A string of palatte name for plotting.
    """
    kwargs = locals()
    plot_parameters(method='coord', **kwargs)

@enforce_types
@register_param(['parallelcoord', 'coord'])
def _parallel_coord(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    colorby:    str=None,
    slice:      bool=True,
    out_dir:    str=None,
    file_name:  str=None,
    tile: str=None,
    _console:   bool=True,
    # optional parameters
    showscale:  bool=True,
    shownan:    bool=True,
    nbins:      int=5,
    # specific parameters
    width:      int=2560,
    height:     int=1440,
    colorscale: str='Tealrose',
    as_html:    bool=False,
):
    """drawing parallel coord plot"""
    try:
        import plotly.graph_objects as go
    except ImportError as e:
        raise e

    if isinstance(parameters, str):
        parameters = [parameters]

    args = SimpleNamespace(
        data=safe_copy(data), options=safe_copy(options), sel_vars=safe_copy(parameters),
        sel_kvar=colorby, slice=slice,
        out_dir=out_dir, file_name=file_name, tile=tile,
        cat=False, console=_console,
        configs=configs,
        # optional parameters
        showscale=showscale, shownan=shownan,
        dpi=800, nbins=nbins,
        )

    new_data, src_vars, new_vars = _resolve_input(name='coord', args=args)

    # draw parallelcoord
    plot_dict = []
    dimensions = {}
    for name in new_vars.keys():
        if new_vars[name]['type'] != 'c':
            dimensions = dict(
                range = new_vars[name]['domain'],
                tickvals = new_vars[name]['vals'],
                ticktext = new_vars[name]['text'],
                label = name, 
                values = new_data[name]
            )
        else:
            dimensions = dict(
                range = new_vars[name]['domain'],
                tickvals = new_vars[name]['vals'],
                ticktext = new_vars[name]['text'],
                label = name, 
                values = new_data[name]
            )
        plot_dict.append(dimensions)

    if src_vars[args.sel_kvar]['type'] != 'c':
        cmin = src_vars[args.sel_kvar]['domain'][0]
        cmax = src_vars[args.sel_kvar]['domain'][1]
        data_key = pd.to_numeric(new_data[args.sel_kvar])

    else:
        cmin = 0
        cmax = len(src_vars[args.sel_kvar]['domain'])
        data_key = new_data[args.sel_kvar]

    fig = go.Figure(data=
    go.Parcoords(
        line = dict(color = data_key,
                    colorscale = colorscale,
                    showscale = showscale,
                    cmin = cmin,
                    cmax = cmax),
        dimensions = list([line for line in plot_dict])
    ))

    # if not _console:
    #     fig.write_image(f"{args.out_dir}/{args.file_name}", width=width, height=height)
    #     print("# {} has been saved in {}.".format(args.file_name+'.png', args.out_dir))
    
    if as_html: display(fig)
    else: fig.show()

# @export
@enforce_types
def param_parallelcat(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    sel_vars:   list=None,
    sel_kvar:   str=None,
    slice:      bool=True,
    out_dir:    str=None,
    file_name:  str=None,
    tile: str=None,
    _console:   bool=True,
    # optional parameters
    shownan:    bool=True,
    nbins:      int=5,
    # specific parameters
    width:      int=2560,
    height:     int=1440,
    as_html:    bool=False,
):
    kwargs = locals()
    plot_parameters(method='cat', **kwargs)

@enforce_types
# @register_param(['parallelcat', 'cat'])
def _parallel_cat(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    sel_vars:   list=None,
    sel_kvar:   str=None,
    slice:      bool=True,
    out_dir:    str=None,
    file_name:  str=None,
    tile: str=None,
    _console:   bool=True,
    # optional parameters
    shownan:    bool=True,
    nbins:      int=5,
    # specific parameters
    width:      int=2560,
    height:     int=1440,
    as_html:    bool=False,
):
    """drawing parallel cat"""

    try:
        import plotly.graph_objects as go
    except ImportError as e:
        raise e

    args = SimpleNamespace(
        data=safe_copy(data), options=safe_copy(options), sel_vars=safe_copy(sel_vars),
        sel_kvar=sel_kvar, slice=slice,
        out_dir=out_dir, file_name=file_name, tile=tile,
        cat=True, console=_console,
        configs=configs,
        # optional parameters
        showscale=False, shownan=shownan,
        dpi=800, nbins=nbins,
    )

    new_data, _, new_vars = _resolve_input(name='cat', args=args)

    if args.sel_vars:
        if len(args.sel_vars) > 2:
            raise CE.OptionError(f"When {bold}parallelcat{reset} is called, "
                                    f"two parameter names must be provided for option {underline}multiParameters{reset}!")
    else:
        args.sel_vars = list(new_vars.keys())

    catx = args.sel_vars[0]
    caty = args.sel_vars[1]

    plot_dict = []
    dimensions = {}
    for name in new_vars.keys():
        if new_vars[name]['type'] == 'c' and name not in exclude_cols:
            dimensions = dict(
                label = name, 
                values = new_data[name]
            )
            plot_dict.append(dimensions)
    
    color = np.zeros(len(plot_dict), dtype='uint8')
    colorscale = [[0, 'gray'], [1, 'firebrick']]
    
    # Build figure as FigureWidget
    fig = go.FigureWidget(data=[
    go.Scatter(
        x = new_data[catx],
        y = new_data[caty],
        marker={'color': 'gray'},
        mode='markers',
        selected={'marker': {'color': 'firebrick'}},
        unselected={'marker': {'opacity': 0.5}}
    ), 
    go.Parcats(
            domain={'y': [0, 0.4]}, 
            dimensions=list([line for line in plot_dict]),
            line={'colorscale': colorscale, 'cmin': 0, 'cmax': 1, 'color': color, 'shape': 'hspline'}),
    ])

    fig.add_trace(fig.data[0])
    fig.add_trace(fig.data[1])

    fig.update_layout(
        height=height, 
        xaxis={'title': catx},
        yaxis={'title': caty, 'domain': [0.6, 1]},
        dragmode='lasso', 
        hovermode='closest',
        overwrite=True)

    # Update color callback
    def update_color(trace, points, state):
        global color, color_numeric
        print("Event triggered", points.point_inds)

        for i in range(len(color)):
            color[i] = 'gray'
        for ind in points.point_inds:
            color[ind] = 'firebrick'

        color_numeric = [0 if c == 'gray' else 1 for c in color]
        fig.data[1].line.color = color_numeric
        fig.update_traces()

    # Register callback on scatter selection...
    fig.data[0].on_selection(update_color)
    # and parcats click
    fig.data[1].on_click(update_color)

    # if not _console:
    #     fig.write_image(f"{args.out_dir}/{args.file_name}", width=width, height=height)
    #     print("# {} has been saved in {}.".format(args.file_name+'.png', args.out_dir))
    
    if as_html: display(fig)
    else: fig.show()

@export
@enforce_types
def param_sunburst(
    # required parameters
    data:                   CraceResults=None,
    options:                CplotOptions=None,
    configs:                Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters:             Union[list[str], str, None]=None,
    _console:               bool=True,
    # optional paramters
    shownan:                bool=True,
    nbins:                  int=5,
    # specific parameters
    palette:                str='vlag',
    autosize:               bool=True,
    branchvalues:           str='total',
    maxdepth:               int=3,
    count:                  str='branches',
    insidetextorientation:  str='horizontal',
    textinfo:               str="label+value",
    as_html:                bool=False,
):
    """
    Entrance to call sunburst in python console
    
    :param data: object CraceResults that must be provided.
    :param options: object CplotOptions that must be provided.
    :param configs: Optional. Selected configurations for plotting, higher priority than option numConfigurations/selConfigurations. 
                    | Union[Literal['all', 'final', 'elites'], list[int], None]='all'
    :param parameters: A list of parameter names selected for plotting, higher priority than option multiParameters.
    :param shownan: Boolean used to plot including/excluding missing values.
    :param palette:  A string of palatte name for plotting.
    :param branchvalues: parameter of function Sunburst
    :param count: parameter of function Sunburst
    :param insidetextorientation: parameter of function Sunburst
    :param textinfo: paramter of function Sunburst
    """

    kwargs = locals()
    plot_parameters(method='sun', **kwargs)

@enforce_types
@register_param(['sunburst', 'sun'])
def _sun_burst(
    # required parameters
    data:                   CraceResults=None,
    options:                CplotOptions=None,
    configs:                Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters:             Union[list[str], str, None]=None,
    _console:               bool=True,
    # optional paramters
    shownan:                bool=True,
    nbins:                  int=5,
    # specific parameters
    palette:                str='vlag',
    autosize:               bool=True,
    branchvalues:           str='total',
    maxdepth:               int=3,
    count:                  str='branches',
    insidetextorientation:  str='horizontal',
    textinfo:               str="label+value",
    as_html:                bool=False,
):
    """drawing sun burst plot"""

    try:
        import plotly.graph_objects as go
        import seaborn as sns
    except ImportError as e:
        raise e

    if isinstance(parameters, str):
        parameters = [parameters]

    args = SimpleNamespace(
        data=safe_copy(data), options=safe_copy(options), sel_vars=safe_copy(parameters),
        sel_kvar=None, slice=True, out_dir=None, file_name=None, tile=None,
        cat=True, console=_console, configs=configs,
        # optional parameters
        showscale=False, shownan=shownan,
        dpi=800, nbins=nbins,
    )

    new_data, src_vars, new_vars = _resolve_input(name='sun', args=args)

    subgroup = {}
    for name in new_vars.keys():
        if name in exclude_cols: continue
        subgroup[name] = {}
        subgroup[name]['names'] = []
        subgroup[name]['props'] = []
        if new_vars[name]['type'] != 'c':
            # new_vars: new domain including parsed <NA>
            #           missing_label <--> round(pmax * 5 / 4, 1)
            new_data[name] = pd.to_numeric(new_data[name])
            left = src_vars[name]['domain'][0]
            right = src_vars[name]['domain'][1]
            tmp = (left+right)/3
            sub1 = '[{:.2f}, {:.2f}]'.format(left, tmp)
            sub2 = '[{:.2f}, {:.2f}]'.format(tmp, 2*tmp)
            sub3 = '[{:.2f}, {:.2f}]'.format(2*tmp, right)

            subgroup[name]['names'].append(sub1)
            s_bool = ((new_data[name] >= left) & (new_data[name] < tmp))
            subgroup[name]['props'].append(s_bool.sum())

            subgroup[name]['names'].append(sub2)
            s_bool = ((new_data[name] >= tmp) & (new_data[name] < 2*tmp))
            subgroup[name]['props'].append(s_bool.sum())

            subgroup[name]['names'].append(sub3)
            s_bool = ((new_data[name] >= 2*tmp) & (new_data[name] <= right))
            subgroup[name]['props'].append(s_bool.sum())

            if shownan and sum(subgroup[name]['props']) < len(new_data[name]):
                # considering <NA> values
                subgroup[name]['names'].append(missing_label)
                s_bool = (new_data[name] > right)
                subgroup[name]['props'].append(s_bool.sum())
            
        else:
            for x in new_vars[name]['domain']:
                subgroup[name]['names'].append(x)
                s_bool = new_data[name] == x
                subgroup[name]['props'].append(s_bool.sum())
            if shownan and sum(subgroup[name]['props']) < len(new_data[name]):
                subgroup[name]['names'].append(missing_label)
                s_bool = ~new_data[name].isin(new_vars[name]['domain'])
                subgroup[name]['props'].append(s_bool.sum())

    labels = []
    values = []
    parents = []
    for name in new_vars.keys():
        if name in exclude_cols: continue
        i = 0
        labels.append(name)
        # values.append(self.count_values(sun_data[name]))
        values.append(sum(subgroup[name]['props']))
        # values[0] += sum(subgroup[name]['props'])
        parents.append("")
        for label in subgroup[name]['names']:
            labels.append(label)
            values.append(subgroup[name]['props'][i])
            parents.append(name)
            i += 1
    ids = [f"{parent}/{label}" if parent else label for label, parent in zip(labels, parents)]

    # print(f'\nvalues: {values}')
    # print(f'\nlabels: {labels}')
    # print(f'\nparents: {parents}')

    mapped_palette = sns.color_palette(palette, len(labels)).as_hex()

    fig = go.Figure()
    fig.add_trace(go.Sunburst(
        ids=ids,
        labels = labels,
        parents = parents,
        values = values,
        branchvalues=branchvalues,
        maxdepth=maxdepth,
        count=count,
        insidetextorientation=insidetextorientation,
        insidetextfont=dict(size=12,color='black'),
        outsidetextfont=dict(size=12),
        textinfo=textinfo,
        marker=dict(colors=mapped_palette),
    ))

    fig.update_layout(
        margin = dict(t=0, l=0, r=0, b=0),
        uniformtext=dict(minsize=8, mode='hide'),
        autosize=autosize,
        )

    # if not _console:
    #     fig.write_image(f"{args.out_dir}/{args.file_name}", width=width, height=height)
    #     print("# {} has been saved in {}.".format(args.file_name+'.png', args.out_dir))
    
    if as_html: display(fig)
    else: fig.show()

@export
@enforce_types
def param_pairplot(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    slice:      bool=True,
    _console:   bool=True,
    # optional parameters
    shownan:    bool=True,
    dpi:        int=800,
    # specific parameters
    hue:        str=None,
    palette:    str='vlag',
    kind:       Literal['auto', 'hist', 'kde', None] = 'kde',
    height:     int=4
):
    """
    Entrance to call pairplot in python console
    
    :param data: object CraceResults that must be provided.
    :param options: object CplotOptions that must be provided.
    :param configs: Optional. Selected configurations for plotting, higher priority than option numConfigurations/selConfigurations. 
                    | Union[Literal['all', 'final', 'elites'], list[int], None]='all'
    :param parameters: A list of parameter names selected for plotting, higher priority than option multiParameters.
    :param hue: A string of parameter name selected for plotting.
    :param shownan: Boolean used to plot including/excluding missing values.
    :param palette: A string of palatte name for plotting.
    :param kind: A string from provided values for the type/shape of plots.
    """

    kwargs = locals()
    plot_parameters(method='pair', **kwargs)

@enforce_types
@register_param(['pairplot', 'pair'])
def _pair_plot(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    slice:      bool=True,
    _console:   bool=True,
    # optional parameters
    shownan:    bool=True,
    dpi:        int=800,
    # specific parameters
    hue:        str=None,
    palette:    str='deep',
    kind:       Literal['auto', 'hist', 'kde'] = 'kde',
    height:     int=4
):
    """drawing pair plot"""

    try:
        import seaborn as sns
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise e

    if isinstance(parameters, str):
        parameters = [parameters]

    args = SimpleNamespace(
        data=safe_copy(data), options=safe_copy(options), sel_vars=safe_copy(parameters),
        sel_kvar=hue, slice=slice,
        out_dir=None, file_name=None, tile=None,
        cat=False, console=_console,
        configs=configs,
        # optional parameters
        showscale=False, shownan=shownan,
        dpi=dpi, nbins=5
    )

    new_data, _, _ = _resolve_input(name='pair', args=args)

    init_plot_style(size=1.2)

    import warnings
    warnings.filterwarnings("ignore", message="Ignoring `palette` because no `hue` variable has been assigned.")

    levels = new_data[hue].unique()
    # auto canonicalize palette
    palette_dict = dict(zip(levels, sns.color_palette(palette, n_colors=len(levels))))
    # enforce categorical
    new_data[hue] = pd.Categorical(new_data[hue], categories=list(palette_dict.keys()))

    fig = sns.pairplot(data=new_data,
                        hue=hue,
                        vars=parameters,
                        palette=palette_dict,
                        diag_kind=kind,
                        height=height,
                        dropna=not(shownan),)

    # remove legend from pariplot
    if hasattr(fig, "_legend") and fig._legend is not None:
        fig._legend.remove()

    # add legend
    # especially for the case: no 
    import matplotlib.patches as mpatches
    handles = [mpatches.Patch(color=palette_dict[lvl], label=lvl) for lvl in palette_dict]
    fig._legend = fig.fig.legend(handles=handles, title=hue, loc='center right')
    fig._legend.get_frame().set_visible(False) 

    if not _console:
        fig.savefig(f"{args.out_dir}/{args.file_name}.png", dpi=args.dpi)
        print("# {} has been saved in {}.".format(args.file_name, args.out_dir))
    
    plt.show()

@export
@enforce_types
def param_heatmap(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    _console:   bool=True,
    # optional parameters
    shownan:    bool=True,
    nbins:      int=5,
    dpi:        int=800,
    # specific parameters
    colormap:   Optional[Union[str, list, Colormap]] = 'PuBu',
    fmt:        str='g',
):
    """
    Entrance to call heatmap in python console
    
    :param data: object CraceResults that must be provided.
    :param options: object CplotOptions that must be provided.
    :param configs: Optional. Selected configurations for plotting, higher priority than option numConfigurations/selConfigurations. 
                    | Union[Literal['all', 'final', 'elites'], list[int], None]='all'
    :param parameters: a list of parameter names selected for plotting, higher priority than option multiParameters.
    :param shownan: boolean used to plot including/excluding missing values.
    :param colormap: a string of matplotlib colormap name for plotting.
    :param nbins: integer used to split the domain for continouos paramters
    """
    kwargs = locals()
    plot_parameters(method='heat', **kwargs)

@enforce_types
@register_param(['heatmap', 'heat'])
def _heatmap(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    _console:   bool=True,
    # optional parameters
    shownan:    bool=True,
    nbins:      int=5,
    dpi:        int=800,
    # specific parameters
    colormap:   Optional[Union[str, list, Colormap]] = 'PuBu',
    fmt:        str='g',
):

    try:
        import seaborn as sns
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise e

    if isinstance(parameters, str):
        parameters = [parameters]

    args = SimpleNamespace(
        data=safe_copy(data), options=safe_copy(options),
        sel_vars=safe_copy(parameters),
        sel_kvar=None, slice=True,
        out_dir=None, file_name=None, tile=None,
        cat=True, console=_console,
        configs=configs,
        # optional parameters
        showscale=False, shownan=shownan,
        dpi=dpi, nbins=nbins,
    )

    new_data, _, new_vars = _resolve_input(name='heat', args=args)
    param_names = [x for x in new_vars.keys() if x not in exclude_cols]

    if len(param_names) == 1:
        index='slice_sampled'
        columns=param_names[0]
    else:
        index=param_names[0]
        columns=param_names[1]

    pivot_table = new_data.pivot_table(index=index, columns=columns, values='configuration_id', aggfunc='count')

    if pivot_table.empty:
        raise CE.CplotError(f"The selected two parameters are mutually exclusive, "
                            f"with no overlapping value combinations.")

    init_plot_style()

    fig = sns.heatmap(pivot_table, annot=True, cmap=colormap, fmt=fmt)

    # y_name, x_name = index, columns
    for name in param_names:

        if name == columns:
            cols = pivot_table.columns
            fig.set_xticklabels(new_vars[name]['text'])
        else:
            rows = pivot_table.index
            fig.set_yticklabels(new_vars[name]['text'])

    # if not _console:
    #     fig.savefig(f"{args.out_dir}/{args.file_name}.png", dpi=args.dpi)
    #     print("# {} has been saved in {}.".format(args.file_name, args.out_dir))

    plt.show()

@export
@enforce_types
def param_jointplot(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    slice:      bool=True,
    _console:   bool=True,
    # optional parameters
    shownan:    bool=True,
    nbins:      int=5,
    dpi:        int=800,
    # specific parameters
    kind:       Literal['scatter', 'kde', 'hist', 'hex', 'reg', 'resid']='hist',
    space:      float=0.1,
    ratio:      int=4,
    palette:    str='vlag',
    hue:        str=None,
    height:     int=5,
):
    """
    Entrance to call pairplot in python console
    
    :param data: object CraceResults that must be provided.
    :param options: object CplotOptions that must be provided.
    :param configs: Optional. Selected configurations for plotting, higher priority than option numConfigurations/selConfigurations. 
                    | Union[Literal['all', 'final', 'elites'], list[int], None]='all'
    :param parameters: A list of parameter names selected for plotting, higher priority than option multiParameters.
    :param hue: A string of parameter name selected for plotting.
    :param shownan: Boolean used to plot including/excluding missing values.
    :param palette: A string of palatte name for plotting.
    :param kind: A string from provided values for the type/shape of plots.
                 | Literal['scatter', 'kde', 'hist', 'hex', 'reg', 'resid']='hist'
    """

    kwargs = locals()
    plot_parameters(method='joint', **kwargs)

@enforce_types
@register_param(['jointplot', 'joint'])
def _jointplot(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    slice:      bool=True,
    _console:   bool=True,
    # optional parameters
    shownan:    bool=True,
    nbins:      int=5,
    dpi:        int=800,
    # specific parameters
    kind:       Literal['scatter', 'kde', 'hist', 'hex', 'reg', 'resid']='hist',
    space:      float=0.1,
    ratio:      int=4,
    palette:    str='vlag',
    hue:        str=None,
    height:     int=5,
):
    """drawing joint plot"""

    try:
        import seaborn as sns
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise e

    if isinstance(parameters, str):
        parameters = [parameters]

    args = SimpleNamespace(
        data=safe_copy(data), options=safe_copy(options), sel_vars=safe_copy(parameters),
        sel_kvar=hue, slice=slice,
        out_dir=None, file_name=None, tile=None,
        cat=False, console=_console,
        configs=configs,
        # optional parameters
        showscale=False, shownan=shownan,
        dpi=dpi, nbins=nbins,
    )

    new_data, _, new_vars = _resolve_input(name='joint', args=args)
    param_names = args.sel_vars

    x=param_names[0]
    y=param_names[1]

    init_plot_style()

    fig = sns.jointplot(data=new_data, x=x, y=y, hue=hue,
                        kind=kind, space=space, ratio=ratio,
                        palette=palette, height=height)

    xmin, xmax = new_vars[x]['domain']
    ymin, ymax = new_vars[y]['domain']
    fig.ax_joint.set_xlim(xmin, xmax)
    fig.ax_joint.set_ylim(ymin, ymax)
    fig.ax_marg_x.set_xlim(xmin, xmax)
    fig.ax_marg_y.set_ylim(ymin, ymax)

    # if not _console:
    #     fig.savefig(f"{args.out_dir}/{args.file_name}.png", dpi=args.dpi)
    #     print("# {} has been saved in {}.".format(args.file_name, args.out_dir))

    plt.show()

@export
@enforce_types
def param_histplot(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    slice:      bool=False,
    _console:   bool=True,
    # optional parameters
    shownan:    bool=True,
    nbins:      int=5,
    dpi:        int=1600,
    # specific parameters
    stat:       Literal['count', 'frequency', 'probability', 'percent', 'density']='percent',
    density:    bool=False,
    sharex:     bool=False,
    sharey:     bool=True,
):
    """
    Entrance to call histplot in python console
    
    :param data: object CraceResults that must be provided.
    :param options: object CplotOptions that must be provided.
    :param configs: Optional. Selected configurations for plotting, higher priority than option numConfigurations/selConfigurations. 
                    | Union[Literal['all', 'final', 'elites'], list[int], None]
    :param parameters: A list of parameter names selected for plotting, higher priority than option multiParameters.
    :param slice: A boolean value used to enable/disable mapping plot aspects to different slices.
    :param shownan: A boolean value used to plot including/excluding missing values.
    :param stat: A string from provided values for the type/shape of plots. 
                 | Literal['count', 'frequency', 'probability', 'percent', 'density']='percent'
    :param density: A boolean value used to enable/disable plotting the rugplot in addition.
    :param sharex: A boolean value used to enable/disable sharing x axis when plotting.
    :param sharey: A boolean value used to enable/disable sharing y axis when plotting.
    """

    kwargs = locals()
    plot_parameters(method='hist', **kwargs)

@enforce_types
@register_param(['histplot', 'hist'])
def _histplot(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    slice:      bool=False,
    _console:   bool=True,
    # optional parameters
    shownan:    bool=False,
    nbins:      int=5,
    dpi:        int=1600,
    # specific parameters
    stat:       Literal['count', 'frequency', 'probability', 'percent', 'density']='percent',
    density:    bool=False,
    sharex:     bool=False,
    sharey:     bool=True,
):

    try:
        import seaborn as sns
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise e

    if isinstance(parameters, str):
        parameters = [parameters]

    args = SimpleNamespace(
        data=safe_copy(data), options=safe_copy(options),
        configs=configs,
        sel_vars=safe_copy(parameters), sel_kvar=None,
        out_dir=None, file_name=None, tile=None,
        slice=slice, cat=False, console=_console,
        # optional parameters
        showscale=False, shownan=shownan,
        dpi=dpi, nbins=nbins,
    )

    new_data, src_vars, new_vars = _resolve_input(name='hist', args=args)
    param_names = [x for x in new_vars.keys() if x not in exclude_cols]

    if args.slice:
        init_plot_style(size=1.1)

        page_num = len(param_names)
        file_names = locals()
        for i in range(0, page_num):
            file_names['plot%s' % i] = args.file_name.split('.')[0]+str(i) if args.file_name else str(i)
            name = param_names[i]
            max_slice = max(new_data['slice_sampled'])
            fig, axis = plt.subplots(max_slice, 1, sharey=True, sharex=True, figsize=(max_slice/1.2, max_slice/1.2))

            for j in range(1, max_slice+1):
                ax = axis[j-1]
                kde = False
                if src_vars[name]['type'] != 'c':
                    kde=True

                # statstr
                # Aggregate statistic to compute in each bin.
                    # count: show the number of observations in each bin
                    # frequency: show the number of observations divided by the bin width
                    # probability or proportion: normalize such that bar heights sum to 1
                    # percent: normalize such that bar heights sum to 100
                    # density: normalize such that the total area of the histogram equals 1

                fig = sns.histplot(data=new_data[new_data['slice_sampled'] == j].sort_values(by=name, na_position='last', ascending=True),
                                   x=name, stat=stat, kde=kde, ax=ax)
                if kde and density:
                    fig = sns.rugplot(data=new_data[new_data['slice_sampled'] == j].sort_values(by=name, na_position='last', ascending=True), 
                                      linewidth=1.0, height=0.1, x=name, ax=ax)

                ax.set_ylabel(f'  {j}', rotation=0)
                ax.yaxis.set_label_position('right')

            fig.text(-0.07, 0.5*max_slice, stat, horizontalalignment='left', verticalalignment='baseline', rotation='vertical', transform=ax.transAxes)
            fig.text(1.05, 0.5*max_slice, 'slice', horizontalalignment='right', verticalalignment='baseline', rotation='vertical', transform=ax.transAxes)

            # plot = fig.get_figure()
            # file_name = file_names['plot%s' % i]
            # save_name = f"{args.out_dir}/{file_name}.png"
            # if not _console:
            #     plt.suptitle(args.tile, size=10)
            #     plot.savefig(save_name, dpi=args.dpi)
            #     print("# {} has been saved in {}.".format(file_name, args.out_dir))

            plt.show()

    else:
        init_plot_style(size=1.3)

        num = 8
        page_num = math.ceil(len(param_names)/num)
        params = locals()
        file_names = locals()
        start = 0
        for i in range(0, page_num):
            fig, axis = plt.subplots(2, 4, sharey=sharey, sharex=sharex, figsize=(16, 12))
            plt.subplots_adjust(hspace=0.3, wspace=0.25, bottom=0.2)
            # title = '\nPage ' + str(i+1) + ' of ' + str(page_num)
            
            if start+num-1 <= len(param_names):
                params['params%s' % i] = param_names[start:start+num]
            else:
                params['params%s' % i] = param_names[start:]              
            start = start+num
            file_names['plot%s' % i] = args.file_name.split('.')[0]+str(i) if args.file_name else str(i)

            page_plots = min(num, len(params['params%s' % i]))

            row = column = idx = 0
            for idx in range(num):
                ax = axis[row, column]
                if idx < page_plots:
                    name = params['params%s' % i][idx]
                    kde = False
                    if src_vars[name]['type'] != 'c':
                        kde = True

                    fig = sns.histplot(data=new_data.sort_values(by=name, na_position='last', ascending=True),
                                       x=name, stat=stat, kde=kde, ax=ax)
                    if kde and density:
                        fig = sns.rugplot(data=new_data.sort_values(by=name, na_position='last', ascending=True),
                                          linewidth=0.5, height=0.05, x=name, ax=ax)

                    if len(name) > 25:
                        name = re.sub(r"(.{25})", "\\1\n", name)
                    if column != 0:
                        fig.set_ylabel('')
                    fig.set_xlabel('\n'+name, rotation=0)
                else:
                    ax.axis('off')

                if column < 3:
                    column += 1
                else:
                    column = 0
                    row += 1 

            # plot = fig.get_figure()
            # file_name = file_names['plot%s' % i] 
            # save_name = f"{args.out_dir}/{file_name}.png"
            
            # if not _console:
            #     plot.savefig(save_name, dpi=args.dpi)
            #     print("# {} has been saved in {}.".format(file_name, args.out_dir))

            plt.show()


@export
@enforce_types
def param_boxplot(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    _console:   bool=True,
    # optional parameters
    shownan:        bool=True,
    nbins:          int=5,
    showfliers:     bool=False,
    showmeans:      bool=False,
    dpi:            int=800,
    # specific parameters
    y:              str='slice_sampled',
    palette:        str='vlag',
    fliersize:      float=.5,
    monochrome:     bool=True,
):
    """
    Entrance to call boxplot in python console
    
    :param data: object CraceResults that must be provided.
    :param options: object CplotOptions that must be provided.
    :param configs: Optional. Selected configurations for plotting, higher priority than option numConfigurations/selConfigurations. 
                    | Union[Literal['all', 'final', 'elites'], list[int], None]
    :param parameters: A list of parameter names selected for plotting, higher priority than option multiParameters.
    :param y: A string of parameter name used to map value aspects. 
              | str='slice_sampled'
    :param shownan: A boolean value used to plot including/excluding missing values.
    :param showfliers: A boolean value used to plot including/excluding outliers.
    :param showmeans: A boolean value used to plot including/excluding mean values.
    :param palette: A string of palatte name for plotting.
    :param monochrome: A boolean value used to enable/disable coloring the plot.
    """
    kwargs = locals()
    plot_parameters(method='box', **kwargs)

@enforce_types
@register_param(['boxplot', 'box'])
def _boxplot(
    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    configs:    Union[Literal['all', 'final', 'elites'], list[int], None]='all',
    parameters: Union[list[str], str, None]=None,
    _console:   bool=True,
    # optional parameters
    shownan:        bool=True,
    nbins:          int=5,
    showfliers:     bool=False,
    showmeans:      bool=False,
    dpi:            int=800,
    # specific parameters
    y:              str='slice_sampled',
    palette:        str='vlag',
    fliersize:      float=.5,
    monochrome:     bool=True,
):
    """drawing box plot"""

    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise e

    if isinstance(parameters, str):
        parameters = [parameters]

    args = SimpleNamespace(
        data=safe_copy(data), options=safe_copy(options), sel_vars=safe_copy(parameters),
        sel_kvar=y, slice=True,
        out_dir=None, file_name=None, tile=None,
        cat=True, console=_console,
        configs=configs,
        # optional parameters
        showscale=False, shownan=shownan, showfliers=showfliers, showmeans=showmeans,
        dpi=dpi, nbins=nbins,
    )

    new_data, _, new_vars = _resolve_input(name='box', args=args)
    param_names = args.sel_vars

    init_plot_style()

    if len(param_names) >= 6:
        num = 6
        page_num = math.ceil(len(param_names)/num)
        params = locals()
        file_names = locals()
        start = 0
        for i in range(0, page_num):
            fig, axis = plt.subplots(2, 3, sharey=False, sharex=False)
            plt.subplots_adjust(hspace=0.5, wspace=0.4, bottom=0.2)
            # title = '\nPage ' + str(i+1) + ' of ' + str(page_num)
            
            if start+num-1 <= len(param_names):
                params['params%s' % i] = param_names[start:start+num]
            else:
                params['params%s' % i] = param_names[start:]              
            start = start+num
            file_names['plot%s' % i] = args.file_name.split('.')[0]+str(i) if args.file_name else str(i)

            page_plots = min(num, len(params['params%s' % i]))

            row = column = idx = 0
            for idx in range(num):
                ax = axis[row, column]
                if idx < page_plots:
                    name = params['params%s' % i][idx]
                    if new_vars[name]['type'] != 'c':
                        fig = _sns_boxplot(data=new_data, x=name, y=y, hue=y, ax=ax,
                                           fliersize=fliersize, palette=palette, monochrome=monochrome, args=args)

                        if len(name) > 25:
                            name = re.sub(r"(.{25})", "\\1\n", name)
                        if column != 0:
                            fig.set_ylabel('')
                        fig.set_xlabel('\n'+name, rotation=0)

                    else:
                        _barh_plot(data=new_data, x=name, y=y, fliersize=fliersize, palette=palette, ax=ax, monochrome=monochrome)

                        if len(name) > 25:
                            name = re.sub(r"(.{25})", "\\1\n", name)
                        if column != 0:
                            ax.set_ylabel('')
                        else:
                            ax.set_ylabel(y, rotation=90)
                        ax.set_xlabel('\n'+name, rotation=0)

                else:
                    ax.axis('off')

                if column < 2:
                    column += 1
                else:
                    column = 0
                    row += 1 

            # plot = fig.get_figure()
            # file_name = file_names['plot%s' % i]
            # save_name = f"{args.out_dir}/{file_name}.png"

            # if not _console:
            #     plt.suptitle(args.tile, size=15)
            #     plot.savefig(save_name, dpi=args.dpi)
            #     print("# {} has been saved in {}.".format(file_name, args.out_dir))

            plt.show()

    else:
        page_num = len(param_names)
        file_names = locals()
        start = 0
        for i in range(0, page_num):
            plt.clf()
            ax = plt.gca()

            # title = '\nPage ' + str(i+1) + ' of ' + str(page_num)
            # file_names['plot%s' % i] = args.file_name.split('.')[0]+'-'+param_names[i] if args.file_name else str(param_names[i])
            name = param_names[i]

            if new_vars[name]['type'] != 'c':
                fig = _sns_boxplot(data=new_data, x=name, y=y, hue=y, ax=ax, args=args,
                                   fliersize=fliersize, palette=palette, monochrome=monochrome)
                if len(name) > 25:
                    name = re.sub(r"(.{25})", "\\1\n", name)
                fig.set_xlabel('\n'+name, rotation=0)

            else:
                _barh_plot(data=new_data, x=name, y=y, fliersize=fliersize, palette=palette, ax=ax, monochrome=monochrome)

                if len(name) > 25:
                    name = re.sub(r"(.{25})", "\\1\n", name)
                ax.set_xlabel('\n'+name, rotation=0)
                ax.set_ylabel(y, rotation=90)

            # plot = fig.get_figure()
            # file_name = file_names['plot%s' % i]
            # save_name = f"{args.out_dir}/{file_name}.png"

            # if not _console:
            #     plt.suptitle(title, size=15)
            #     plot.savefig(save_name, dpi=args.dpi)
            #     print("# {} has been saved in {}.".format(file_name, args.out_dir))

            plt.show()

def _sns_boxplot(data, x, y, hue, ax, fliersize, palette, monochrome, args):
    try:
        import seaborn as sns
    except ImportError as e:
        raise e

    if monochrome:
        fig = sns.boxplot(data=data, x=x, y=y, hue=hue, legend=None, ax=ax,
                          whis=0.5, showfliers=args.showfliers, fliersize=fliersize,
                          showmeans=args.showmeans, orient='h',
                          width=0.4, linewidth=2*fliersize,
                          palette=palette,
                          meanprops={"marker": "x",
                                     "markeredgecolor": "black",
                                     "markersize": 1,
                                     "linewidth": 2*fliersize},
                          boxprops=dict(facecolor="white"),
                          medianprops={"linewidth": 2*fliersize, "color": "black"},
                          whiskerprops={"linestyle": "--", "linewidth": 2*fliersize},
                          )
    else:
        fig = sns.boxplot(data=data, x=x, y=y, hue=hue, legend=None, ax=ax,
                          whis=0.5, showfliers=args.showfliers, fliersize=fliersize,
                          showmeans=args.showmeans, orient='h',
                          width=0.4, linewidth=2*fliersize,
                          palette=palette,)
    return fig

def _make_hatches(n, base=['//', '||', '--', '\\\\', '++', 'xx', '..',], max_repeat=7):
    hatches = []
    for r in range(1, max_repeat + 1):
        for b in base:
            hatches.append(b * r)
            if len(hatches) >= n:
                return hatches
    return hatches

def _barh_plot(data, x, y, ax, fliersize, palette, monochrome):
    """
    Draw 'boxplot' for categorical parameter
    """
    try:
        import seaborn as sns
    except ImportError as e:
        raise e

    new_data = (data.groupby([y, x]).size().reset_index(name="count"))
    new_data["ratio"] = new_data.groupby(y)["count"].transform(lambda x: x / x.sum())

    mat = new_data.pivot(index=y, columns=x, values="ratio").fillna(0)
    mat = mat.sort_index(ascending=False)

    y_new = np.arange(len(mat))
    left = np.zeros(len(mat))

    if monochrome:
        try:
            import matplotlib.patches as mpatches
        except ImportError as e:
            raise e

        hatches = _make_hatches(len(mat.columns))
        handles = []

        for i, col in enumerate(mat.columns):
            ax.barh(y_new, mat[col].values,
                    left=left, height=0.4,
                    facecolor="white",
                    edgecolor="black",
                    linewidth=2 * fliersize,
                    hatch=hatches[i])

            handles.append(
                mpatches.Patch(
                    facecolor="white",
                    edgecolor="black",
                    hatch=hatches[i],
                    label=str(col)
                )
            )

            left += mat[col].values

        ax.legend(
            handles=handles,
            title=x,
            bbox_to_anchor=(1.02, 0.5),
            loc="center left",
            frameon=False
        )

    else:
        levels = list(mat.columns)
        palette_dict = dict(zip(levels, sns.color_palette(palette, n_colors=len(levels))))

        for col in mat.columns:
            ax.barh(y_new, mat[col].values,
                    left=left, height=0.4,
                    facecolor=palette_dict[col],
                    edgecolor=None,
                    linewidth=2 * fliersize,
                    label=str(col))

            left += mat[col].values

        ax.legend(
            title=x,
            bbox_to_anchor=(1.02, 0.5),
            loc="center left",
            frameon=False
        )

    ax.set_xlim(0, 1)
    ax.set_yticks(y_new)
    ax.set_yticklabels(mat.index)

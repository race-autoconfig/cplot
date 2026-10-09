# craceplot._plot.parameters.py

from __future__ import annotations

import os
import sys
import re
import math
import inspect
import traceback

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.lines as mlines


from types import SimpleNamespace
from sklearn.utils import resample
from matplotlib.transforms import Bbox
from typing import TYPE_CHECKING, Union, Literal, Callable, TypeVar, ParamSpec


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

args = SimpleNamespace(
    # required parameters
    data=None,
    options=None,
    source=None,
    num=None,
    select=None,
    slice=True,
    out_dir=None,
    file_name=None,
    title=None,
    _console=True,
    # optional parameters
    showfliers=False,
    showmeans=False,
    stest=False,
    dpi=800,
)

def add_slice(data: pd.DataFrame, slice: pd.DataFrame):
    """add slice information to selected data"""

    end = slice['end_time'].values
    idx = np.searchsorted(end, data["end_time"].values, side="right")
    new = data.assign(slice_finished=idx + 1)

    return new

@enforce_types
def _check_options(name: str, args: SimpleNamespace):
    """
    check options
    
    options provided by args have higher priority

    each option will be read from args when plotting

    ONLY modify args

    # required parameters
    data:       CraceResults=None,
    options:    CplotOptions=None,
    select:     list=None,
    slice:      bool=True,
    out_dir:    str=None,
    file_name:  str=None,
    title:      str=None,
    num:        Literal['all', 'final', 'elites', None] = None,
    source:     Literal['training', 'test', 'testing', None] = None,
    _console:   bool=True,
    # optional parameters
    showfliers: bool=False,
    showmeans:  bool=False,
    stest:      bool=False,
    dpi:        int=800,
    """
    # data must be provided
    if not args.data:
        raise CE.OptionError(f"{bold}data{reset} must be provided for plotting.")

    # check onlytest
    onlytest = args.data.options.onlytest.value
    if onlytest:
        print(f"# The provided crace log files only has results for test part")
        args.source = 'testing'
        args.num = 'final'

    # ====================================================================================
    # slice:      bool=True
    if args.options.slice.value is True:
        args.slice = True
    # elif args

    # showfliers:  bool=True
    args.showfliers = True if args.options.showfliers.value or args.showfliers else False
    # showmeans:  bool=True
    args.showmeans = True if args.options.showmeans.value or args.showmeans else False
    # stest:  bool=True
    args.stest = True if args.options.statisticalTest.value or args.stest else False

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

    # title: str=None
    if not args.title and args.options.title.is_set():
        args.title = args.options.title.value

    # ====================================================================================
    # check num and source
    if not args.source and args.options.source.value:
        args.source = args.options.source.value

    if not args.source and not args.options.source.value:
        print(f"# WARNING: no data source provided, {bold}testing{reset} data is "
              f"selected as default when plotting for {bold}experiments{reset}.")
        args.source = 'testing'

    if args.source in ('test', 'testing') or args.options.source.value  in ('test', 'testing'):
        if args.num != 'final' or args.options.numConfigurations.value != 'final':
            print(f"# WARNING: when {bold}testing{reset} results selected as source, only {bold}final{reset} can be selected for {underline}num / numConfigurations{reset}")
            args.num = 'final'


    # check num and select
    select = args.select
    # select is provided only in options
    if not args.select and args.options.selConfigurations.value:
        select = args.options.selConfigurations.value
    # select is not provided
    elif not args.select and not args.options.selConfigurations.value:
        if not args.num and not args.options.numConfigurations.value:
            if name != 'heat':
                raise CE.OptionError(f"No {underline}num/numConfigurations{reset} or "
                    f"{underline}select/selConfigurations{reset} provided for plotting {bold}experiments{reset}.")
        if args.num == 'final' or args.options.numConfigurations.value == 'final':
            select = args.data.elites
        elif args.num == 'elites' or args.options.numConfigurations.value == 'elites':
            if 'elites' in args.data.slice.columns:
                tmp = [x[0] for x in args.data.slice.elites]
            elif args.data.all_elites is not None:
                tmp = args.data.all_elites
            tmp.append(args.data.best_id)
            select = list(dict.fromkeys(tmp))
        elif args.num == 'all' or args.options.numConfigurations.value == 'all':
            select = args.data.all_elites
        elif args.num == 'else' or args.options.numConfigurations.value == 'else':
            if not args.select or not args.options.selConfigurations.value:
                raise CE.OptionError(f"{underline}select{reset} / {underline}selConfigurations{reset} "
                                     f"must be provided when {bold}else{reset} is selected.")
    args.select = select


    if name == 'scat' and len(args.select) > 2:
        del args.select[2:]
        print(f"#\n# More than two configurations are selected for drawing scatter plot.\n"
              f"#    selected configurations: {args.select}")

@enforce_types
def _load_data(name: str, args: SimpleNamespace):
    """load data"""
    # load training results
    if args.source == 'training':
        src_quality = args.data.training.data.dropna()
    # load test results
    elif args.source in ('test', 'testing'):
        src_quality = args.data.testing.data.dropna()
    else:
        raise CE.OptionError(f"No {underline}source{reset} data provided plotting for {bold}experiments{reset}.")

    # select columns
    sel_cols = ['experiment_id', 'configuration_id', 'instance_id', 'quality', 'end_time']
    sel_pd = src_quality[sel_cols]

    if name == 'heat':
        return sel_pd
    elif name == 'scat':
        data = add_best(sel_pd)
        # select configurations
        # boxplot: may receive 2-dimensional select
        data = data[data['configuration_id'].isin(np.unique(args.select+[0]))]
        return data

    # select configurations
    new_pd = sel_pd[sel_pd['configuration_id'].isin(np.unique(args.select))]

    # include slice information
    new_pd = add_slice(data=new_pd, slice=args.data.slice)
    new_pd = add_elites(data=new_pd, slice=args.data.slice, final=args.data.elites, select=args.select)

    # remove extra information
    data = new_pd.drop(columns=['end_time'])

    # print(f"#\n# The original crace results:\n{new_pd}\n")

    return data

@enforce_types
def _resolve_input(name: str, args: SimpleNamespace):
    """
    resolve input
    """
    new_data= None

    _check_options(name=name, args=args)

    new_data = _load_data(name=name, args=args)

    return new_data

def plot_experiments(method: str, **kwargs):
    """
    entrance to call plotting function from file _draw.py
    including try-except
    """
    # drawMethod: (boxplot, violinplot, parallelcoord, parallelcat, sunburst, pairplot, histplot, jointplot, heatmap)
        
    func = dispatch_table_exps.get(method)

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
def qual_boxplot(
    # required parameters
    data:           CraceResults=None,
    options:        CplotOptions=None,
    select:         list=None,
    # slice:          bool=None,
    slice:          Union[Literal['budget', 'b', 'B', 'e', 'E', 'experiment', 'time', 't', 'T'
                                  ], bool, None]=None,
    out_dir:        str=None,
    file_name:      str=None,
    title:          str=None,
    num:            Literal['all', 'final', 'elites', None] = None,
    source:         Literal['training', 'test', 'testing', None] = None,
    _console:       bool=True,
    # optional parameters
    showfliers:     bool=False,
    showmeans:      bool=False,
    stest:          bool=False,
    dpi:            int=800,
    # specific parameters
    x:              str='configuration_id',
    y:              str='quality',
    hue:            str='configuration_id',
    palette:        str='vlag',
    fontsize:       int=12,
    fliersize:      float=.5,
    show_ori:       bool=False,
    errorbar:       Literal['ci', 'rpd'] = 'rpd',
    check_elites:   bool=False,
):
    """
    Entrance to generate boxplots for quality comparison.

    :param data: Object 'CraceResults' containing the quality results to be plotted.
    :param options: Object 'CplotOptions' containing the plotting options.
    :param select: Optional. A list of experiment, scenario, or method identifiers selected for plotting.
    :param slice: Optional. Selects how the results are sliced before plotting. Supported values are 'budget' ('b', 'B'), 'experiment' ('e', 'E'), and 'time' ('t', 'T'). A boolean can also be used to enable or disable slicing.
    :param out_dir: Output directory for the generated figure.
    :param file_name: File name of the generated figure.
    :param title: Optional title of the figure.
    :param num: Selects the configurations to include in the plot: 'all', 'final', or 'elites'.
    :param source: Selects the source of the results, either 'training' or 'test'/'testing'.
    :param showfliers: Whether to display outliers in the boxplots.
    :param showmeans: Whether to display the mean value.
    :param stest: Whether to perform statistical tests between the compared groups.
    :param dpi: Resolution of the output figure in dots per inch.
    :param palette: Name of the color palette used for the boxplots.
    :param fontsize: Font size used in the figure.
    :param fliersize: Marker size used for outliers.
    :param show_ori: Whether to show the original/default configuration.
    :param errorbar: Type of error bar to display. Supported values are 'ci' for confidence interval and 'rpd' for relative percentage deviation.
    :param check_elites: Whether to check and use elite configurations when generating the plot.
    """
    kwargs = locals()
    plot_experiments(method='box', **kwargs)

@enforce_types
@register_exps(['boxplot', 'box'])
def _boxplot(
    # required parameters
    data:           CraceResults=None,
    options:        CplotOptions=None,
    select:         list=None,
    # slice:          bool=None,
    slice:          Union[Literal['budget', 'b', 'B', 'e', 'E', 'experiment', 'time', 't', 'T'
                                  ], bool, None]=None,    out_dir:        str=None,
    file_name:      str=None,
    title:          str=None,
    num:            Literal['all', 'final', 'elites', None] = None,
    source:         Literal['training', 'test', 'testing', None] = None,
    _console:       bool=True,
    # optional parameters
    showfliers:     bool=False,
    showmeans:      bool=False,
    stest:          bool=False,
    dpi:            int=800,
    # specific parameters
    x:              str='configuration_id',
    y:              str='quality',
    hue:            str='configuration_id',
    palette:        str='vlag',
    fontsize:       int=12,
    fliersize:      float=.5,
    show_ori:       bool=False,
    errorbar:       Literal['ci', 'rpd'] = 'rpd',
    check_elites:   bool=False,
):
    """drawing box plot"""

    try:
        import scikit_posthocs as sp
        from statannotations.Annotator import Annotator
    except ImportError as e:
        raise e

    init_plot_style(size=1.2)

    args = SimpleNamespace(
        data=safe_copy(data), options=safe_copy(options), num=num, select=select,
        slice=slice, out_dir=out_dir, file_name=file_name, title=title,
        source=source, console=_console,
        # optional parameters
        showfliers=showfliers, showmeans=showmeans, stest=stest,
        dpi=dpi,
    )

    new_data = _resolve_input(name='box', args=args)

    # if args.console: print_args(args)
    # print(f"#\n# The original crace results:\n{new_data}\n")

    # ====================================================================================
    # draw plots for selected elite configurations
    #   in order to show the sampling
    if not args.slice:
        new_data = new_data[['experiment_id', 'configuration_id', 'instance_id', 'quality']].drop_duplicates()

        results1 = new_data.groupby(['configuration_id']).mean().T.to_dict()
        results2 = new_data.groupby(['configuration_id']).count().T.to_dict()
        results_mean = {}
        results_count = {}

        for id, item in results2.items():
            results_count[int(id)] = None
            results_count[int(id)] = item['instance_id']

        # mean based on Nins, when there is a tie on quality
        for id, item in results1.items():
            results_mean[int(id)] = None
            results_mean[int(id)] = item['quality']

        # Sort elite_ids based on results_count values
        #   1. num of instances, increase
        #   2. mean quality, decrease
        results_count_sorted = {k:v for k, v in sorted(results_count.items(), key=lambda x: (x[1], -results_mean[x[0]]), reverse=False)}

        elite_ids_sorted = [str(x) for x in results_count_sorted.keys()]
        elite_ids_order = [int(x) for x in results_count_sorted.keys()]

        min_quality = float("inf")
        best_found = 0
        pairs = [ k for k,v in results_count_sorted.items() if v==max(results_count_sorted.values())]
        for id in pairs:
            if results_mean[int(id)] <= min_quality:
                min_quality = results_mean[int(id)]
                best_found = id

        best_final = data.best_id

        # ====================================================================================
        # update x-labels for 'training' results
        x_labels = elite_ids_sorted.copy()
        if args.source not in ('test', 'testing') and check_elites:
            key_name = "-%(num)s-" % {"num": int(best_found)}
            for i, x in enumerate(elite_ids_sorted):
                if int(x) == int(best_final):
                    x = "*%(num)s*" % {"num": x}
                    if int(re.search(r'\d+', str(x)).group()) == int(best_found):
                        x = "-%(num)s-" % {"num": x}
                elif int(x) == int(best_found):
                    x = key_name
                x_labels[i] = x

            print(f"# Best configurations: (num_instances, mean)")
            print("#  (number with *: final elite configuration from crace)")
            print("#  (number with -: configuration having the minimal average value on the most instances)")
            for x in x_labels:
                int_x = int(re.search(r'\d+', x).group())
                print(f"#{x:>12}: ({results_count_sorted[int_x]:>2}, {results_mean[int_x]})", end="\n")

        # ====================================================================================
        # draw the plot
        if num == 'all':
            fig, ax = plt.subplots(figsize=(16,12))
        else:
            fig, ax = plt.subplots()  # pylint: disable=undefined-variable
        sns.boxplot(x='configuration_id', y='quality', data=new_data,
                    whis=0.5, showfliers=args.showfliers, fliersize=fliersize,
                    showmeans=args.showmeans,
                    meanprops={"marker": "x",
                                "markeredgecolor": "black",
                                "markersize": 1,
                                "linewidth": 2*fliersize},
                    width=0.4, linewidth=2*fliersize,
                    palette=palette,
                    boxprops=dict(facecolor="white"),
                    medianprops={"linewidth": 2*fliersize, "color": "black"},
                    whiskerprops={"linestyle": "--", "linewidth": 2*fliersize},
                    # flierprops={"marker": "o", "markersize": fliersize, 'markerfacecolor': 'black', 'markeredgecolor': 'black'},
                    hue='configuration_id', legend=False,
                    order=elite_ids_order,
                    # notch=True,
                    ax=ax,
                    )

        if errorbar == 'ci':
            _legend_ci(data=new_data, fliersize=fliersize, fontsize=fontsize, ax=ax, fig=fig, order=elite_ids_order)
        elif errorbar == 'rpd':
            _legend_rpd(data=new_data, fliersize=fliersize, fontsize=fontsize, ax=ax, fig=fig, order=elite_ids_order)

        if show_ori:
            sns.stripplot(x='configuration_id', y='quality', data=new_data,
                          color='green', size=4*fliersize, jitter=False,
                          order=elite_ids_order, ax=ax)

        if args.stest:
            _do_stest(data=new_data, args=args, pairs=pairs)

        # add p-value for the configurations who have the most instances
        if len(pairs) > 1:
            if (int(best_final) != best_found and 
                int(best_final) in pairs):
                pair = (int(best_found), int(best_final))
            else:
                pair = (int(elite_ids_sorted[-2]), int(elite_ids_sorted[-1]))
            pairs_results = new_data.loc[new_data['configuration_id'].isin(pair)].copy()

            # p1 = sp.posthoc_wilcoxon(pairs_results, val_col='quality', group_col='configuration_id')
            # p_values after multiple test correction
            p2 = sp.posthoc_wilcoxon(pairs_results, val_col='quality', group_col='configuration_id',
                                    p_adjust='fdr_bh')
            p2_4 = p2.round(4)

            print("#\n# Adjusted p-values of the last two elite configurations:")
            print(p2_4)

            annotator = Annotator(ax, pairs=[pair], data=new_data, order=elite_ids_order, x='configuration_id', y='quality')
            annotator.configure(test='Wilcoxon', text_format='simple', comparisons_correction='fdr_bh',
                                show_test_name=False, line_width=1)
            annotator.apply_and_annotate()

        # update labels / ticks
        ticks = ax.get_xticks()
        xticklabels = [t.get_text() for t in ax.get_xticklabels()]
        ax.set_xticks(ticks)
        if len(x_labels) > 12:
            ax.set_xticklabels(x_labels, rotation=90)
        else:
            ax.set_xticklabels(x_labels, rotation=0)
        if not args.title:
            ax.set_xlabel(None)
        elif not args.console:
            ax.set_xlabel(args.title)
        else:
            x.set_xlabel()

        if not data.options.capping.value:
            ax.set_ylabel('quality')
        else:
            ax.set_ylabel('runtime')
        plt.xticks()
        plt.yticks()

        _legend_ins(ax=ax, ticks=ticks, labels=results_count_sorted)


    else:
        # test
        num = len(new_data.slice_finished.unique())
        if num == 1:
            sns.boxplot(x=x, y=y, data=new_data,
                        hue=hue, legend=None,
                        whis=0.5, showfliers=args.showfliers, fliersize=fliersize,
                        showmeans=args.showmeans,
                        meanprops={"marker": "x",
                                "markeredgecolor": "black",
                                "markersize": 1,
                                "linewidth": 2*fliersize},
                        width=0.4, linewidth=2*fliersize,
                        palette=palette,
                        boxprops=dict(facecolor="white"),
                        medianprops={"linewidth": 2*fliersize, "color": "black"},
                        whiskerprops={"linestyle": "--", "linewidth": 2*fliersize},
                        ax=ax,
                        )

            ticks = ax.get_xticks()
            fig = ax.get_figure()
            xticklabels = [int(t.get_text()) for t in ax.get_xticklabels()]

            if errorbar == 'ci':
                _legend_ci(data=new_data, fliersize=fliersize, fontsize=fontsize, ax=ax, fig=fig, order=xticklabels, x=x, y=y, hue=hue)
            elif errorbar == 'rpd':
                _legend_rpd(data=new_data, fliersize=fliersize, fontsize=fontsize, ax=ax, fig=fig, order=xticklabels, x=x, y=y, hue=hue)

            if show_ori:
                sns.stripplot(x=x, y=y, data=new_data,
                              color='green', size=4*fliersize, jitter=False,
                              order=xticklabels, ax=ax)

            if not data.options.capping.value:
                ax.set_ylabel('quality')
            else:
                ax.set_ylabel('runtime')
            plt.xticks()
            plt.yticks()

        # training
        else:
            col_name = 'slice_elites' if args.select is None else 'group'
            col_wrap = _auto_col_wrap(num)

            p = sns.FacetGrid(data=new_data, col=col_name, col_wrap=num, legend_out=False,
                                sharex=False, sharey=True, height=3, aspect=0.7)
            p.map_dataframe(func=sns.boxplot, x=x, y=y,
                            hue=hue, legend=True,
                            whis=0.5, showfliers=args.showfliers, fliersize=fliersize,
                            showmeans=args.showmeans,
                            meanprops={"marker": "x",
                                        "markeredgecolor": "black",
                                        "markersize": 1,
                                        "linewidth": 2*fliersize},
                            width=0.4, linewidth=2*fliersize,
                            palette=palette,
                            boxprops=dict(facecolor="white"),
                            medianprops={"linewidth": 2*fliersize, "color": "black"},
                            whiskerprops={"linestyle": "--", "linewidth": 2*fliersize},
                            )

            left_axes = []
            top_axes = []
            idx = 1
            for ax, (_, subdata) in zip(p.axes.flatten(), p.facet_data()):
                print(f"#\n# The original crace results for slice {idx}:\n{subdata}\n")

                if ax.get_subplotspec().colspan.start == 0:
                    left_axes.append(ax)

                if ax.get_subplotspec().rowspan.start == 0:
                    top_axes.append(ax)

                ticks = ax.get_xticks()
                xticklabels = [int(t.get_text()) for t in ax.get_xticklabels()]

                if errorbar == "ci":
                    _legend_ci(data=subdata, fliersize=fliersize, fontsize=fontsize, ax=ax, fig=ax.figure, add_legend=False, order=xticklabels, x=x, y=y, hue=hue)

                elif errorbar == "rpd":
                    _legend_rpd(data=subdata, fliersize=fliersize, fontsize=fontsize, ax=ax, fig=ax.figure, add_legend=False, order=xticklabels, x=x, y=y, hue=hue)

                if show_ori:
                    sns.stripplot(x=x, y=y, data=subdata,
                                  color='green', size=4*fliersize, jitter=False,
                                  order=xticklabels, ax=ax)

                ax.set_xlabel("")
                ax.set_ylabel("")
                idx += 1

            fig = p.figure

            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()

            # Plot area
            axes_bboxes = [
                ax.get_position()
                for ax in p.axes.flatten()
                if ax.get_visible()
            ]

            x_min = min(b.x0 for b in axes_bboxes)
            x_max = max(b.x1 for b in axes_bboxes)
            y_min = min(b.y0 for b in axes_bboxes)


            # X label
            supx = fig.supxlabel("configuration_id")
            _, y = supx.get_position()
            supx.set_position(((x_min + x_max) / 2, y))


            # Y tick labels
            tick_bboxes = [
                label.get_window_extent(renderer=renderer)
                for ax in left_axes
                for label in ax.get_yticklabels()
                if label.get_visible() and label.get_text()
            ]

            if tick_bboxes:
                tick_bbox = Bbox.union(tick_bboxes)
                tick_bbox = tick_bbox.transformed(fig.transFigure.inverted())
                x = tick_bbox.x0 - 0.025
            else:
                x = x_min - 0.05

            y_min = min(ax.get_position().y0 for ax in left_axes)
            y_max = max(ax.get_position().y1 for ax in left_axes)

            fig.text(
                x,
                (y_min + y_max) / 2,
                'quality' if not data.options.capping.value else 'runtime',
                rotation=90,
                ha="center",
                va="center",
            )

            # add legend
            text = 'median (95% CI)' if errorbar == 'ci' else 'median ± RPD'
            _add_legend(text=text, fontsize=fontsize, glob=True, fig=fig, top=top_axes, left=left_axes)

        if args.stest:
            plog = args.file_name

            # p_values
            p1 = sp.posthoc_wilcoxon(data, val_col='quality', group_col='exp_name')
            # p_values after multiple test correction
            p2 = sp.posthoc_wilcoxon(data, val_col='quality', group_col='exp_name',
                                    p_adjust='fdr_bh')
            print("Original p_values caculated by 'Wilcoxon':\n", p1)
            print("New p_values corrected by 'fdr_bh':\n", p2)

            with open(args.out_dir + "/" + plog + '.log', 'w') as f1:
                print("Original p_values caculated by 'Wilcoxon':\n", p1, file=f1)
                print("\nNew p_values corrected by 'fdr_bh':\n", p2, file=f1)
                print("\n", file=f1)

            order = []
            pairs = []
            p_values = []
            for x in data['exp_name'].unique():
                order.append(x)
            i = 0
            for x in order[:-1]:
                i += 1
                for y in order[i:]:
                    pairs.append((x,y))
                    p_values.append(p2.loc[x, y])

            annotator = Annotator(ax, pairs=pairs, order=elite_ids_order,
                                data=data, x='exp_name', y='quality')
            annotator.configure(test='Wilcoxon', text_format='star', comparisons_correction='fdr_bh',
                                line_width=0.5)

            with open(args.out_dir + "/" + plog + '.log', 'a') as f1:
                original_stdout = sys.stdout
                sys.stdout = f1

                try:
                    annotator.apply_and_annotate()
                finally:
                    sys.stdout = original_stdout

    # plot = fig.get_figure()
    # if not _console:
    #     plot.savefig(f"{args.out_dir}/{args.file_name}.png", dpi=args.dpi)
    #     print("# {} has been saved in {}.".format(args.file_name, args.out_dir))
    plt.show()


@export
@enforce_types
def qual_scatter(
    # required parameters
    data:           CraceResults=None,
    options:        CplotOptions=None,
    select:         list=None,
    # slice:          bool=None,
    slice:          Union[Literal['budget', 'b', 'B', 'e', 'E', 'experiment', 'time', 't', 'T'
                                  ], bool, None]=None,
    out_dir:        str=None,
    file_name:      str=None,
    title:          str=None,
    num:            Literal['all', 'final', 'elites', None] = None,
    source:         Literal['training', 'test', 'testing', None] = None,
    _console:       bool=True,
    # optional parameters
    showfliers:     bool=False,
    showmeans:      bool=False,
    stest:          bool=False,
    dpi:            int=800,
    # specific parameters
    xid:           int=None,
    yid:           int=None,
    fontsize:       int=12,
    fliersize:      float=.5,
    fillna:         bool=False,
    penalty:        float=1.2,
    rpd:            bool=True,
    instance_ids:   list=None
):
    """
    Entrance to generate scatter plots for quality comparison.

    :param data: Object CraceResults that must be provided.
    :param options: Object CplotOptions that must be provided.
    :param select: Optional. A list of experiment, scenario, or method identifiers selected for plotting.
    :param slice: Optional. Specifies how the quality data are sliced before plotting. Supported values are 'budget'/'b'/'B', 'experiment'/'e'/'E', 'time'/'t'/'T', or a boolean value.
    :param out_dir: Output directory for the generated figure.
    :param file_name: File name of the generated figure.
    :param title: Optional title of the figure.
    :param num: Selects the configurations to include in the plot: 'all', 'final', or 'elites'.
    :param source: Selects the source of the results, either 'training' or 'test'/'testing'.
    :param showfliers: Whether to display outliers in the scatter plot.
    :param showmeans: Whether to display the mean value.
    :param stest: Whether to perform statistical tests between the compared groups.
    :param dpi: Resolution of the output figure in dots per inch.
    :param xid: Identifier of the quality measure plotted on the x-axis.
    :param yid: Identifier of the quality measure plotted on the y-axis.
    :param fontsize: Font size used in the figure.
    :param fliersize: Marker size used for outliers.
    :param fillna: Whether to fill missing values before plotting.
    :param penalty: Penalty factor applied to missing or invalid quality values.
    :param rpd: Whether to use relative percentage deviation for the plotted quality values.
    :param instance_ids: Optional list of instance identifiers to include in the plot.
    """
    kwargs = locals()
    plot_experiments(method='scat', **kwargs)

@enforce_types
@register_exps(['scatter', 'scat'])
def _scatter(
    # required parameters
    data:           CraceResults=None,
    options:        CplotOptions=None,
    select:         list=None,
    # slice:          bool=None,
    slice:          Union[Literal['budget', 'b', 'B', 'e', 'E', 'experiment', 'time', 't', 'T'
                                  ], bool, None]=None,
    out_dir:        str=None,
    file_name:      str=None,
    title:          str=None,
    num:            Literal['all', 'final', 'elites', None] = None,
    source:         Literal['training', 'test', 'testing', None] = None,
    _console:       bool=True,
    # optional parameters
    showfliers:     bool=False,
    showmeans:      bool=False,
    stest:          bool=False,
    dpi:            int=800,
    # specific parameters
    xid:           int=None,
    yid:           int=None,
    fontsize:       int=12,
    fliersize:      float=.5,
    fillna:         bool=False,
    penalty:        float=1.2,
    rpd:            bool=True,
    instance_ids:   list=None
):
    """drawing scatter plot"""
    if (select is None and options.selConfigurations.value is None) and (
        xid is not None and yid is not None
    ):
        select = [xid, yid]

    args = SimpleNamespace(
        data=safe_copy(data), options=safe_copy(options), num=num, select=select,
        slice=slice, out_dir=out_dir, file_name=file_name, title=title,
        source=source, console=_console,
        # optional parameters
        showfliers=showfliers, showmeans=showmeans, stest=stest, dpi=dpi,
    )

    new_data = _resolve_input(name='scat', args=args)

    # if args.console: print_args(args)
    # print(f"#\n# The original crace results:\n{new_data}\n")

    sel_ins = new_data.loc[
        new_data["configuration_id"].isin(args.select),
        "instance_id"].unique()
    
    sel_data = new_data[~(
        (new_data["configuration_id"] == 0) & 
        (~new_data["instance_id"].isin(sel_ins)))]

    pivot = sel_data.pivot(
        index="instance_id",
        columns="configuration_id",
        values="quality")

    if not fillna:
        pivot_data = pivot.dropna()
    else:
        fill_num = pivot.max().max() * penalty
        pivot_data = pivot.fillna(fill_num)
        print(f"# WARNING: fill NaN with {bold}{fill_num}{reset}, calculated by: {bold}data.max().max() * penalty({penalty}){reset}\n")

    pivot_show = pivot_data.rename(columns={0: "bests"})
    mean_row = pivot_show.mean().to_frame().T
    mean_row.index = ["mean"]
    pivot_show = pd.concat([pivot_show, mean_row])
    print(pivot_show)
    print(f"Note: {bold}bests{reset} represents an oracle configuration, constructed by selecting, "
          f"for each instance,\n\t  the configuration that achieves the best performance.\n")

    if xid is None and yid is None:
        xid, yid = args.select

    orig_instance_ids = pivot_data.index.astype(int)

    if rpd:
        pivot_data = _scatter_rpd(pivot_data)
        xlab = f"RPD (%) of configuration {xid}"
        ylab = f"RPD (%) of configuration {yid}"
    else:
        xlab = f"Cost of configuration {xid}"
        ylab = f"Cost of configuration {yid}"

    x_data = pivot_data[xid]
    y_data = pivot_data[yid]

    mask = x_data.notna() & y_data.notna()
    if not mask.any():
        raise ValueError("No instance has data for both configurations")

    x_data = x_data[mask]
    y_data = y_data[mask]
    instances = orig_instance_ids[mask]

    # find better
    best = np.full(len(x_data), "equal", dtype=object)
    best[x_data < y_data] = "conf1"
    best[x_data > y_data] = "conf2"

    # ---- instance names ----
    if instance_ids is None:
        instance_ids = instances
    elif callable(instance_ids):
        instance_ids = [instance_ids(x) for x in instances]
    else:
        if len(instance_ids) != len(pivot_data):
            raise ValueError("`instance_ids` must have same length as experiments")
        instance_ids = np.asarray(instance_ids)[mask]

    # new dataframe
    df = pd.DataFrame({
        "conf1": x_data.values,
        "conf2": y_data.values,
        "instance": instance_ids,
        "best": best,
    })

    _draw_scatter(df, xlab, ylab)

def _scatter_rpd(df, ref_id=0):
    """calculate rpd information for selected configurations on instances"""
    if ref_id in df.columns:
        best = df[ref_id]
    else:
        best = df.min(axis=1)
    return (df.sub(best, axis=0)).div(best, axis=0)

def _draw_scatter(df, xlab, ylab):
    init_plot_style()
    fig, ax = plt.subplots()

    # colors = {
    #     "conf1": "#0055CC",
    #     "conf2": "#C41700",
    #     "equal": "darkgray",
    # }
    # for key, g in df.groupby("best"):
    #     ax.scatter(
    #         g["conf1"],
    #         g["conf2"],
    #         s=40,
    #         color=colors[key],
    #         label=key,
    #         alpha=0.9,
    #     )

    import matplotlib.colors as mcolors

    norm = mcolors.Normalize(
        vmin=df["instance"].min(),
        vmax=df["instance"].max()
    )

    for key, g in df.groupby("best"):
        ax.scatter(
            g["conf1"],
            g["conf2"],
            c=g["instance"],      # 用 instance 控制颜色
            cmap="viridis",
            norm=norm,
            s=40,
            alpha=0.85,
            label=key,
            edgecolors="none"
        )

    plt.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap="viridis"),
        ax=ax,
        label="Instance ID"
    )

    # y = x
    lim = max(df["conf1"].max(), df["conf2"].max())
    ax.plot([0, lim], [0, lim], color="lightgray", linewidth=1.5)

    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)

    ax.legend().remove()

    plt.tight_layout()
    plt.show()


@export
@enforce_types
def qual_heatmap(
    # required parameters
    data:           CraceResults=None,
    options:        CplotOptions=None,
    select:         list=None,
    # slice:          bool=None,
    slice:          Union[Literal['budget', 'b', 'B', 'e', 'E', 'experiment', 'time', 't', 'T'
                                  ], bool, None]=None,
    out_dir:        str=None,
    file_name:      str=None,
    title:          str=None,
    num:            Literal['all', 'final', 'elites', None] = None,
    source:         Literal['training', 'test', 'testing', None] = None,
    _console:       bool=True,
    # optional parameters
    showfliers:     bool=False,
    showmeans:      bool=False,
    stest:          bool=False,
    dpi:            int=800,
    # specific parameters
    fontsize:       int=12,
    fliersize:      float=.5,
    colorscale:     str="Viridis",
    as_html:        bool=False,
):
    """
    Entrance to call quality heatmap in python console

    :param data: Object CraceResults that must be provided.
    :param options: Object CplotOptions that must be provided.
    :param select: A list of instance names or identifiers selected for plotting.
    :param slice: Optional. Specifies how the quality data are sliced before plotting. Supported values are 'budget'/'b'/'B', 'experiment'/'e'/'E', 'time'/'t'/'T', or a boolean value.
    :param out_dir: Output directory for saving the generated figure.
    :param file_name: File name of the generated figure.
    :param title: Title of the heatmap.
    :param num: Optional. Specifies the configurations included in the heatmap. Supported values are 'all', 'final', and 'elites'.
    :param source: Optional. Specifies the source of the quality data. Supported values are 'training' and 'test'/'testing'.
    :param showfliers: Boolean used to enable/disable showing outliers.
    :param showmeans: Boolean used to enable/disable showing mean values.
    :param stest: Boolean used to enable/disable statistical testing.
    :param dpi: Resolution of the generated figure in dots per inch.
    :param fontsize: Font size used in the heatmap.
    :param fliersize: Size of the outlier markers.
    :param colorscale: A string of palette name used for plotting.
    """
    kwargs = locals()
    plot_experiments(method='heat', **kwargs)

@enforce_types
@register_exps(['heatmap', 'heat'])
def _heatmap(
    # required parameters
    data:           CraceResults=None,
    options:        CplotOptions=None,
    select:         list=None,
    # slice:          bool=None,
    slice:          Union[Literal['budget', 'b', 'B', 'e', 'E', 'experiment', 'time', 't', 'T'
                                  ], bool, None]=None,
    out_dir:        str=None,
    file_name:      str=None,
    title:          str=None,
    num:            Literal['all', 'final', 'elites', None] = None,
    source:         Literal['training', 'test', 'testing', None] = None,
    _console:       bool=True,
    # optional parameters
    showfliers:     bool=False,
    showmeans:      bool=False,
    stest:          bool=False,
    dpi:            int=800,
    # specific parameters
    fontsize:       int=12,
    fliersize:      float=.5,
    colorscale:     str="Viridis",
    as_html:        bool=False,
):
    try:
        import plotly.graph_objects as go
    except ImportError as e:
        raise e

    """drawing scatter plot"""
    args = SimpleNamespace(
        data=safe_copy(data), options=safe_copy(options), num=num, select=select,
        slice=slice, out_dir=out_dir, file_name=file_name, title=title,
        source=source, console=_console,
        # optional parameters
        showfliers=showfliers, showmeans=showmeans, stest=stest, dpi=dpi,
    )

    new_data = _resolve_input(name='heat', args=args)

    # if args.console: print_args(args)
    # print(f"#\n# The original crace results:\n{new_data}\n")

    pivot = new_data.pivot(
        index="instance_id",
        columns="configuration_id",
        values="quality"
    )

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale=colorscale,
            colorbar=dict(title="Quality"),
            zmin=pivot.min().min(),
            zmax=pivot.max().max(),
        )
    )

    fig.update_layout(
        xaxis_title="Configuration IDs",
        yaxis_title="Instance IDs",
        template="plotly_white",
    )

    if as_html: display(fig)
    else: fig.show()

def _do_stest(data: pd.DataFrame, args, pairs):
    """add stest information for boxplot"""

    try:
        from statsmodels.formula.api import ols
        import statsmodels.api as sm
        import scikit_posthocs as sp
        import scipy.stats as stats
        import logging
    except ImportError as e:
        raise e

    l = logging.getLogger('st_log')
    filehandler = logging.FileHandler(args.out_dir + "/" + args.file_name + '.log', mode='w')
    filehandler.setLevel(0)
    streamhandler = logging.StreamHandler()
    l.setLevel(logging.DEBUG)
    l.addHandler(filehandler)
    l.addHandler(streamhandler)

    data = data.loc[data['configuration_id'].isin(pairs)].copy()

    ############################# CHECK RESULTS #############################
    #                           Shapiro-Wilk Test                           #
    #                                 LEVENE                                #
    #                                 ANOVA                                 #
    #                         Kruskal-Wallis H Test                         #
    #########################################################################

    # avg for each configuration
    data_groups = [data['quality'][data['configuration_id'] == conf] for conf in data['configuration_id'].unique()]
    print("data_groups: ", data_groups)

    # Shapiro-Wilk Test
    # H0 hypothesis: normality (normal distribution)
    shapiro_string = ''
    stat_s = p_s = []
    for conf in data['configuration_id'].unique():
        data_group = data[data['configuration_id'] == conf]['quality']
        ss, ps = stats.shapiro(data_group)
        stat_s.append(ss)
        p_s.append(ps)
        shapiro_string += 'Shapiro-Wilk Test for configuration {}, Statistic: {:.4f}, p-value: {:.4f}\n'.format(conf, ss, ps)
    l.debug(f'\nShapiro-Wilk Test - H0 hypothesis: normality (0.05)\n{shapiro_string}')

    # do levene
    # H0 hypothesis: homogeneity of variance (方差齐性)
    stat_l, p_l = stats.levene(*data_groups)
    l.debug('\nLevene’s Test - H0 hypothesis: homogeneity of variance (0.05)\n' \
            'stat_l: {:.4f}, p-value: {:.4f}\n'.format(stat_l, p_l))

    # check the results from Shapiro-Wilk Test and levene
    KW_test = ANOVA_test = False
    if p_l < 0.05 or any(x<0.05 for x in p_s):
        KW_test = True
    else:
        ANOVA_test = True

    if ANOVA_test:
        # simulate ANOVA
        # H0 hypothesis: same mean values
        model = ols('quality ~ C(configuration_id)', data=data).fit()
        anova_results = sm.stats.anova_lm(model, typ=2)  # Type 2 ANOVA DataFrame
        l.debug(f'\nANOVA_results - H0 hypothesis: all configurations have the same mean values\n{anova_results}')

    if KW_test:
        # do Kruskal-Wallis H
        # H0 hypothesis: same medians
        stat_k, p_k = stats.kruskal(*data_groups)
        l.debug('Kruskal-Wallis Test - H0 hypothesis: all configurations have the same medians (0.05)\n' \
                'Statistic: {:.4f}, p-value: {:.4f}'.format(stat_k, p_k))

        ############################# POSTHOC TEST ##############################
        #                             posthoc_dunn                              #
        #                          posthoc_mannwhitney                          #
        #########################################################################

        # # # Dunn:
        # p1 = sp.posthoc_dunn(data, val_col='quality', group_col='configuration_id')
        # # p_values after multiple test correction
        # p2 = sp.posthoc_dunn(data, val_col='quality', group_col='configuration_id',
        #                         p_adjust='fdr_bh')
        # p2_4 = p2.round(4)

        # l.debug(f"\nOriginal p_values caculated by 'dunn':\n{p1}")
        # l.debug(f"\nNew p_values corrected by 'fdr_bh':\n{p2}")
        # l.debug(f"\nNew rounded p_values:\n{p2_4}")

        # Wilcoxon rank-sum test
        p1 = sp.posthoc_mannwhitney(data, val_col='quality', group_col='configuration_id')
        # p_values after multiple test correction
        p2 = sp.posthoc_mannwhitney(data, val_col='quality', group_col='configuration_id',
                                p_adjust='fdr_bh')
        p2_4 = p2.round(4)

        l.debug(f"\nOriginal p_values caculated by 'mannwhitney (Wilcoxon rank-sum test)':\n{p1}")
        l.debug(f"\nNew p_values corrected by 'fdr_bh':\n{p2}")
        l.debug(f"\nNew rounded p_values:\n{p2_4}")

    ############################# POSTHOC TEST ##############################
    #                           posthoc_wilcoxon                            #
    #########################################################################

    # Wilcoxon signed-rank test
    p1 = sp.posthoc_wilcoxon(data, val_col='quality', group_col='configuration_id')
    # p_values after multiple test correction
    p2 = sp.posthoc_wilcoxon(data, val_col='quality', group_col='configuration_id',
                            p_adjust='fdr_bh')
    p2_4 = p2.round(4)
    l.debug(f"\n############################# Wilcoxon Signed-rank Test ##############################")
    l.debug(f"\nOriginal p_values caculated by 'Wilcoxon':\n{p1}")
    l.debug(f"\nNew p_values corrected by 'fdr_bh':\n{p2}")
    l.debug(f"\nNew rounded p_values:\n{p2_4}")

def _auto_col_wrap(n):
    """
    Given number of subplots n,
    find the closest factor pair (a, b) with a*b = n,
    and return the larger one (b) as col_wrap.
    """
    best_pair = (1, n)
    min_diff = n - 1

    for i in range(1, int(math.sqrt(n)) + 1):
        if n % i == 0:
            j = n // i
            if abs(j - i) < min_diff:
                best_pair = (i, j)
                min_diff = abs(j - i)

    return max(best_pair)

def _add_legend(text, fontsize, ax=None, fig=None, glob=False, top:list=None, left:list=None):
    legend_element = mlines.Line2D([], [], 
                           color='red', marker='_', linestyle='None', markersize=.25*fontsize,
                           label=text)

    plt.tight_layout()

    if not glob:
        offset_text = ax.yaxis.get_offset_text()
        if fig is None or not hasattr(fig, "canvas"):
            fig = ax.figure
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        bbox = offset_text.get_window_extent(renderer=renderer)

        fig_box = ax.get_position()

        y_disp = (bbox.y0 + bbox.y1) / 2
        _, offset_y = fig.transFigure.inverted().transform((0, y_disp))
        # _, offset_y = ax.transAxes.inverted().transform((0, y_disp))

        offset_y = max(0.02, min(1.0, offset_y))

        offset_x = 0.99

    else:
        supx = fig._supxlabel
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbox = supx.get_window_extent(renderer=renderer)

        x_max = max(ax.get_position().x1 for ax in top)
        y_disp = (bbox.y0 + bbox.y1)/2

        offset_x = x_max
        _, offset_y = fig.transFigure.inverted().transform((0, y_disp))

    legend = fig.legend(
        handles=[legend_element],
        loc='center right',
        bbox_to_anchor=(offset_x, offset_y),
        borderaxespad=0.0,
        frameon=False,
        prop={'size': fontsize},
    )
    legend.get_frame().set_linewidth(0.5)

def _bootstrap_ci(series, estimator=np.median, ci=95, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed)
    series = np.asarray(series)
    boot = np.array([estimator(
        resample(series, random_state=rng.integers(1e9))
        ) for _ in range(n_boot)])
    alpha = (100 - ci) / 2
    return (np.percentile(boot, alpha), np.percentile(boot, 100 - alpha))

def _legend_ci(data, fliersize, fontsize, ax, fig, order, ci=95, add_legend=True, x=None, y=None, hue=None):
    # add ci information
    x = x if x is not None else "configuration_id"
    y = y if y is not None else "quality"
    hue = hue if hue is not None else "configuration_id"
    grouped = data.groupby(x)[y]

    medians = []
    lower = []
    upper = []
    # sort based on order
    for cid in order:
        s = grouped.get_group(cid)

        m = np.median(s)
        lo, hi = _bootstrap_ci(s.to_numpy(), np.median, ci=ci)

        medians.append(m)
        lower.append(lo)
        upper.append(hi)

    medians = np.asarray(medians)
    lower = np.asarray(lower)
    upper = np.asarray(upper)

    x_positions = np.arange(len(order)) - 0.25
    ax.errorbar(
        x=x_positions,
        y=medians,
        yerr=np.vstack([medians - lower, upper - medians]),
        fmt='o',
        color='red',
        capsize=4*fliersize,
        markersize=4*fliersize,
        elinewidth=2*fliersize,
    )

    ax.set_xlabel("")
    ax.set_ylabel("")

    if not add_legend: return

    _add_legend(text='median (95% CI)', ax=ax, fig=fig, fontsize=fontsize)


def _legend_rpd(data, fliersize, fontsize, ax, fig, order, add_legend=True, x=None, y=None, hue=None):
    # add rpd information
    x = x if x is not None else "configuration_id"
    y = y if y is not None else "quality"
    hue = hue if hue is not None else "configuration_id"
    grouped = data.groupby(x)[y]

    medians = []
    lower = []
    upper = []
    # sort based on order
    for cid in order:
        s = grouped.get_group(cid)

        m = s.median()
        mad = (s - m).abs().median()

        medians.append(m)
        lower.append(m - mad)
        upper.append(m + mad)

    medians = np.asarray(medians)
    lower = np.asarray(lower)
    upper = np.asarray(upper)

    x_positions = np.arange(len(order)) - 0.25

    ax.errorbar(
        x=x_positions,
        y=medians,
        yerr=np.vstack([medians - lower, upper - medians]),
        fmt='o',
        color='red',
        capsize=4*fliersize,
        markersize=4*fliersize,
        elinewidth=2*fliersize,
    )

    ax.set_xlabel("")
    ax.set_ylabel("")

    if not add_legend: return

    _add_legend(text='median ± RPD', ax=ax, fig=fig, fontsize=fontsize)


def _legend_ins(ax, ticks, labels):
    # add instance numbers
    dx = np.diff(ticks).mean()
    plt.xlim(ticks[0] - dx, ticks[-1] + dx)

    t_top = ax.text(x=ticks[0], y=1.0, s="ins_num",
                    ha='left', va='bottom',
                    color='blue',
                    transform=ax.get_xaxis_transform())
    t_bottom = []
    for i,x in enumerate(labels.values()):
        t = ax.text(x=ticks[i], y=0.99, s=x,
                    ha='center', va='top',
                    color='blue',
                    transform=ax.get_xaxis_transform())
        t_bottom.append(t)

    _align_left_to_text(ax, t_bottom[0], t_top)

def _align_left_to_text(ax, ref_text, target_text):
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    bbox = ref_text.get_window_extent(renderer=renderer)
    x_left_disp = bbox.x0

    x_left_data = ax.transData.inverted().transform((x_left_disp, 0))[0]
    target_text.set_x(x_left_data)
import pandas as pd

# __all__ = ['bold', 'underline', 'reset', 'register', 'enforce_types', 'add_slice', 'add_ins', 'safe_copy']

def init_plot_style(size=1.0):
    import matplotlib as mpl
    import seaborn as sns

    mpl.rcdefaults()
    sns.set_theme(
        style="white",
        context="paper",
        font_scale=size,
        rc={
            # "font.size": size,
            "axes.grid": True,
            "axes.facecolor": "white",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "axes.edgecolor": "black",
            "xtick.color": "black",
            "ytick.color": "black",
        }
    )

def display(fig):
    from IPython.display import HTML, display as disp
    import plotly.io as pio

    html = pio.to_html(fig, full_html=False,
        include_plotlyjs="https://unpkg.com/plotly.js-dist-min@latest/plotly.min.js",
    )
    disp(HTML(html))

def add_elites(data: pd.DataFrame, slice: pd.DataFrame, final: list, select: list=None):
    """add slice information to selected data"""
    new = pd.DataFrame()
    tmp = []

    if select is None:
        if 'elites' not in slice.columns.values:
            print("'slice' object has no attribute 'elites'")
            return data

        for idx, row in enumerate(slice.itertuples(), start=1):
            sel = data[
                data['configuration_id'].isin(row.elites) &
                (data['end_time'] <= row.end_time)
                ].copy()
            sel['slice_elites'] = idx
            tmp.append(sel)

        last_end_time = slice.iloc[-1].end_time
        last_idx = idx + 1
        last = data[
            data['configuration_id'].isin(final) &
            (data['end_time'] > last_end_time)
            ].copy()
        last['slice_elites'] = last_idx
        tmp.append(last)

    else:
        for idx, group in enumerate(select, start=1):
            if isinstance(group, int): group = [group]
            for cid in group:
                sel = data.loc[data['configuration_id'] == cid].copy()
                sel['group'] = idx
                tmp.append(sel)

    new = pd.concat(tmp, ignore_index=True)
    return new

def add_ins(data: pd.DataFrame):
    """add ins information to selected data"""

    n_ins = data.groupby(['configuration_id']).size().reset_index(name='n_ins')
    new = data[['configuration_id']].drop_duplicates()
    new = pd.merge(new, n_ins, on=['configuration_id'], how='left')

    return new

def add_best(data: pd.DataFrame):
    """add minimal quality for each instance based on all configurations"""
    sel_data = data[['configuration_id', 'instance_id', 'quality']].dropna()
    min_qual = sel_data.groupby(['instance_id'], as_index=False).min()
    min_qual['configuration_id']=0
    new = pd.concat([sel_data, min_qual], ignore_index=True)
    
    return new

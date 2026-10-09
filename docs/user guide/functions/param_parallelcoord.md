---
jupytext:
  text_representation:
    format_name: myst
---

param_parallelcoord
===================

The plot produced by `Parcoords` from model **plotly.graph_objects** can help you to both the distribution of the parameter values of a set of configurations and the common associations between these values. 

By default, the plot colors the lines using `slice_sampled` in which slice the configuration is sampled for all configurations in the racing. You can use the `colorby` argument to choose the parameter for coloring the lines. 

To check more details for its available arguments, call:

```{code-cell} python
import craceplot as cplot

help(cplot.param_parallelcoord)
```

Take ACOTSP for example:
```{code-cell} python
import os
from pathlib import Path

cplot_home = cplot.where().path

p = Path(os.path.join(cplot_home, 'inst', 'examples', 'acotsp'))
path_to_acotsp = os.path.relpath(p, Path.cwd())

results, options = cplot.run('-l', path_to_acotsp)
```

You can do this with the `param_parallelcoord` method:

```{code-cell} python
cplot.param_parallelcoord(data=results, options=options, as_html=True)
```

You can draw more flexible parallel coord plots via providing parameters `configs`, `parameters`, `colorby`, `showscale`, `shownan`, `colorscale`. 

```{code-cell} python
cplot.param_parallelcoord(data=results, options=options, configs='final', colorby='configuration_id',
                          parameters=['algorithm', 'ants', 'beta', 'dlb', 'elitistants', 'localsearch'],
                          showscale=False, shownan=False, colorscale='YlGnBu', as_html=True)
```

Note: when `shownan = False` but there are missing values in the selected configurations, the missing values would be automatically mapped to a legal value by Parcoords.




---
<div style="display: flex; justify-content: space-between; align-items: center;">
    <button onclick="history.back()" style="padding: 6px 14px; border: 1px solid #ccc; border-radius: 5px; background-color: #f5f5f5; cursor: pointer;">
        ← Back
    </button>
    <button onclick="history.forward()" style="padding: 6px 14px; border: 1px solid #ccc; border-radius: 5px; background-color: #f5f5f5; cursor: pointer;">
        Next →
    </button>
</div>
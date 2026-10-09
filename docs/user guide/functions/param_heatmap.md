---
jupytext:
  text_representation:
    format_name: myst
---


param_heatmap
=============

The plot produced by `heatmap` from model **seaborn** can help you visualize the joint sampling frequency of two parameters. By default, this plot uses all configuration values on the selected parameters, you can also use argument `configs` to focus on the selected configurations. You can select two parameters using the `parameters` argument, or provide only one parameter to visualize its sampling frequency with `slice_sampled`, that when the configuration sampled.

You can use argument `colormap` to color the plot, and its available values could be checked using code:

```python
import matplotlib.pyplot as plt
plt.colormaps( )
```

To check more details for its available arguments, call:

```{code-cell} python
import craceplot as cplot

help(cplot.param_heatmap)
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


You can plot heatmap with the `param_heatmap` method:

```{code-cell} python
cplot.param_heatmap(data=results, options=options, parameters='algorithm')
```

You can draw more flexible heatmap plots via providing parameters `configs`, `parameters`, `colormap`,  `shownan` and `nbins`. The argument `nbins` is used to split the domain of continouos paramters. 

```{code-cell} python
cplot.param_heatmap(data=results, options=options, 
                    parameters=['q0', 'rasrank'],
                    shownan=True, colormap='YlGnBu')
```





---
<div style="display: flex; justify-content: space-between; align-items: center;">
    <button onclick="history.back()" style="padding: 6px 14px; border: 1px solid #ccc; border-radius: 5px; background-color: #f5f5f5; cursor: pointer;">
        ← Back
    </button>
    <button onclick="history.forward()" style="padding: 6px 14px; border: 1px solid #ccc; border-radius: 5px; background-color: #f5f5f5; cursor: pointer;">
        Next →
    </button>
</div>
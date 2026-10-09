---
jupytext:
  text_representation:
    format_name: myst
---

param_histplot
==============

In some cases it might be interesting to have a look at the values sampled during the racing procedure as a distribution. Such plot shows the areas in the parameter space where **crace** detected a high performance. A general overview of the distribution of sampled parameters values can be obtained with the param_histplot which generates frequency and density plots for the sampled values of selected parameters.



The plot produced by `histplot` from model **seaborn**, and by default, the plot randomly selects 6 parameters from all sampled configurations. 

In order to draw more flexible plots for the distribution of selected parameters, you can provide arguments `configs`, `parameters`, `shownan`, `stat`, `density`, `sharex` and `sharey`. `stat` is a string from provided values ['count', 'frequency', 'probability', 'percent', 'density'] for the type/shape of plots and its default value is 'percent'.

To check more details for its available arguments, call:

```{code-cell} python
import craceplot as cplot

help(cplot.param_histplot)
```

Take ACOTSP and CATS200 for example:
```{code-cell} python
import os
from pathlib import Path

cplot_home = cplot.where().path

p = Path(os.path.join(cplot_home, 'inst', 'examples', 'acotsp'))
path_to_acotsp = os.path.relpath(p, Path.cwd())

p = Path(os.path.join(cplot_home, 'inst', 'examples', 'cats200'))
path_to_cats200 = os.path.relpath(p, Path.cwd())

results1, options1 = cplot.run('-l', path_to_acotsp)
results2, options2 = cplot.run('-l', path_to_cats200)
```

You can plot with the `param_histplot` method:

```{code-cell} python
cplot.param_histplot(data=results1, options=options1)
```

```{code-cell} python
cplot.param_histplot(data=results2, options=options2,
                     configs='all',
                     parameters='sifting_algorithm',
                     slice=True,
                     stat='count',
                     density=True,)
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
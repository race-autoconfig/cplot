---
jupytext:
  text_representation:
    format_name: myst
---


param_pairplot
==============

Apart from the heatmap and joint plot, pair plot is also provided to display the pairwise relationships of provided parameters and the distribution of each parameter on the hue parameter. Similar to `param_jointplot`, by default, this plot uses all configuration values on the selected two categorical parameters, you can also use argument `configs` to focus on the selected configurations.

To draw more flexible pair plots you can call this function via providing arguments `configs`, `parameters`, `hue`, `shownan`, `palette` and `kind`. 

The argument `hue` is the parameter provided to map plot aspects to different colors for the provided at least two parameters.

The argument `kind` is the type of plot for the diagonal subplots and its avaliable values are in **['auto', 'hist', 'kde', None]**. If 'auto', choose based on whether or not `hue` is used. 

The argument `shownan` enables or disables the inclusion of NaN values for the selected parameters.
In the case of mutually exclusive parameters, setting `shownan=False` results in empty intersections.

To check more details for its available arguments, call:

```{code-cell} python
import craceplot as cplot

help(cplot.param_pairplot)
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

You must provide at least two continuous parameters using the `parameters` argument, and you can plot the pair plot by using code `param_pairplot`:

```{code-cell} python
cplot.param_pairplot(data=results, options=options, parameters=['alpha', 'beta'], hue='localsearch')
```


```{code-cell} python
cplot.param_pairplot(data=results, options=options,
                     parameters=['q0', 'rasrank', 'elitistants'],
                     hue='algorithm',
                     kind='auto',
                     shownan=False,
                     height=3)
```

As shown in the above plot, when there is no joint sub-plots, it means all selected parameters are mutually exclusive.




---
<div style="display: flex; justify-content: space-between; align-items: center;">
    <button onclick="history.back()" style="padding: 6px 14px; border: 1px solid #ccc; border-radius: 5px; background-color: #f5f5f5; cursor: pointer;">
        ← Back
    </button>
    <button onclick="history.forward()" style="padding: 6px 14px; border: 1px solid #ccc; border-radius: 5px; background-color: #f5f5f5; cursor: pointer;">
        Next →
    </button>
</div>
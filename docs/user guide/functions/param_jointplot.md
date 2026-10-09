---
jupytext:
  text_representation:
    format_name: myst
---

param_jointplot
=============

Apart from the heatmap, joint plot is also provided to display the joint sampling frequency of two parameters and the distribution of each parameter. Similar to `param_heatmap`, by default, this joint plot uses all configuration values on the two selected categorical parameters, you can also use argument `configs` to draw plot on the selected configurations.

Also, you can draw more flexible joint plots via providing parameters `hue`, `configs`, `parameters`, `palette`,  `shownan` and `kind`. 

To check more details for its available arguments, call:

```{code-cell} python
import craceplot as cplot

help(cplot.param_jointplot)
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

You must provide two continuous parameters using the `parameters` argument, and you can plot the joint plot by using code `param_jointplot`:

```{code-cell} python
cplot.param_jointplot(data=results, options=options, parameters=['alpha', 'beta'])
```

The argument `hue` is the third parameter provided for plotting the distributions of the selected two parameters on it.

The argument `kind` is type for the joint plot and its avaliable values are in **['scatter', 'kde', 'hist', 'hex', 'reg', 'resid']**.
Among these values, ['hex', 'reg', 'resid'] are not supported when argument `hue` is enabled.

```{code-cell} python
cplot.param_jointplot(data=results, options=options, parameters=['alpha', 'beta'],
                      hue='q0', 
                      kind='scatter', 
                      shownan=False)
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
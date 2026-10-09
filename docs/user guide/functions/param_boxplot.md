---
jupytext:
  text_representation:
    format_name: myst
---

param_boxplot
=============

Function `param_boxplot` can help you visualize the distribution of selected parameter(s). By default, this plot uses all configuration values on the selected parameter(s) and map all value aspects to different slices. 

For categorical and continuous parameters, this function produces different visualizations: a normalized stacked bar chart for categorical parameters and a boxplot for continuous parameters, respectively.

In order to draw more flexible plots, you can provide parameters `configs`, `parameters`, `y`,  `shownan`, `showfliers`, `showmeans`, `palette` and `monochrome`. 

To check more details for its available arguments, call:

```{code-cell} python
import craceplot as cplot

help(cplot.param_boxplot)
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

You can plot with the `param_boxplot` method:

```{code-cell} python
cplot.param_boxplot(data=results, options=options, parameters=['algorithm', 'alpha'])
```


You can also call this function with personalized arguments:

```{code-cell} python
import random
max = results.configurations.n_config
cplot.param_boxplot(data=results, options=options, parameters=['dlb', 'nnls'],
                    configs=random.sample(range(1, max), int(0.5*max)), # random selected a half of configuratioons
                    monochrome=False, shownan=False, palette='YlGnBu', 
                    showfliers=True)
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
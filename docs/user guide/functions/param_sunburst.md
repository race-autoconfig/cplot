---
jupytext:
  text_representation:
    format_name: myst
---

param_sunburst
==============

The plot produced by `Sunburst` from model **plotly.graph_objects** can create a pie plot that displays the values of all configurations sampled during the configuration process. This plot can be useful to display the tendencies in the sampling in a simple format. By default, the plot randomly selects 6 parameters for all sampled configurations. 

Here, numerical parameters domains are discretized to be shown in the plot. The size of each parameter value in the plot is dependent of the argument `textinfo`, which could be the count value (**value**) or percentage (**'percent root', 'percent entry', 'percent parent'**) of configurations having that value in the configurations.

To check more details for its available arguments, call:

```{code-cell} python
import craceplot as cplot

help(cplot.param_sunburst)
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

You can do this with the `param_sunburst` method:

```{code-cell} python
cplot.param_sunburst(data=results2, options=options2, as_html=True)
```

You can draw more flexible plots via providing parameters `configs`, `parameters`, `palette`,  `shownan`, `branchvalues`, `count`, `insidetextorientation` and `textinfo`. 

```{code-cell} python
cplot.param_sunburst(data=results1, options=options1, configs='elites',
                     parameters=['algorithm', 'q0', 'dlb', 'elitistants', 'nnls'],
                     shownan=False, palette='YlGnBu',
                     branchvalues='total', count='leaves',
                     insidetextorientation='auto',
                     textinfo='label+percent parent',
                     as_html=True)
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
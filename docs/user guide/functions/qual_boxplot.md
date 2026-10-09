---
jupytext:
  text_representation:
    format_name: myst
---

qual_boxplot
============

Function `qual_boxplot` can help you visualize the performance of selected configuration(s). 
You must provide data in `CraceResults` format, the source of data (training or testing) you select for plotting, and the number of configurations you wish to use.

Addtionally, you need to provide some plot arguments as well. To check more details for its available arguments, call:

```{code-cell} python
import craceplot as cplot

help(cplot.qual_boxplot)
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

You can plot with the `qual_boxplot` method:

```{code-cell} python
cplot.qual_boxplot(data=results, options=options, source='training', num='all')
```

In this example, data is from ACOTSP and this plot is drawn on the training process for all elite configurations selected in this phase.
Blue numbers on the top are numbers of used instance of each configuration, while black numbers on the bottom are configuration ids.




---
<div style="display: flex; justify-content: space-between; align-items: center;">
    <button onclick="history.back()" style="padding: 6px 14px; border: 1px solid #ccc; border-radius: 5px; background-color: #f5f5f5; cursor: pointer;">
        ← Back
    </button>
    <button onclick="history.forward()" style="padding: 6px 14px; border: 1px solid #ccc; border-radius: 5px; background-color: #f5f5f5; cursor: pointer;">
        Next →
    </button>
</div>
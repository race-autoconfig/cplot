# craceplot/__init__.py

_IMPORT_MAPPING = {
    'run': 'craceplot.scripts',
    'main': 'craceplot.scripts',
    'doc': 'craceplot.scripts.utils',
    'examples': 'craceplot.scripts.utils',
    'templates': 'craceplot.scripts.utils',
    'which': 'craceplot.scripts.utils',
    'where': 'craceplot.scripts.utils',
    'load_options': 'craceplot.containers.draw',
    'load_results': 'craceplot.containers.draw',
    'param_boxplot': 'craceplot.plots',
    'param_heatmap': 'craceplot.plots',
    'param_histplot': 'craceplot.plots',
    'param_jointplot': 'craceplot.plots',
    'param_pairplot': 'craceplot.plots',
    'param_parallelcoord': 'craceplot.plots',
    'param_sunburst': 'craceplot.plots',
    'qual_boxplot': 'craceplot.plots',
    'qual_heatmap': 'craceplot.plots',
    'qual_scatter': 'craceplot.plots',
}

_DESC_MAPPING = {
    '__version__': 'version',
    '__author__': 'authors',
    '__maintainers__': 'maintainers',
    '__long_description__': 'long_description',
    '__doc__': 'description'
}

__all__ = list(_IMPORT_MAPPING.keys()) + list(_DESC_MAPPING.keys())


def __getattr__(name: str):
    import importlib
    import craceplot.settings.description as csd

    if name in _DESC_MAPPING:
        return getattr(csd, _DESC_MAPPING[name])

    if name in _IMPORT_MAPPING:
        module = importlib.import_module(_IMPORT_MAPPING[name])

        if name in ('main', 'run'):
            return getattr(module, 'run')
        if name == 'doc':
            return getattr(module, 'cplot_guide')
        if name in ("examples", "templates", "which", "where"):
            func = getattr(module, 'cplot_examples')
            def wrapper():
                return func(name)
            return wrapper
        return getattr(module, name)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

def __dir__():
    return __all__

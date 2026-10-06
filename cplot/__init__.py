# cplot/__init__.py

_IMPORT_MAPPING = {
    'run': 'cplot._scripts',
    'main': 'cplot._scripts',
    'doc': 'cplot._scripts._utils',
    'examples': 'cplot._scripts._utils',
    'templates': 'cplot._scripts._utils',
    'which': 'cplot._scripts._utils',
    'where': 'cplot._scripts._utils',
    'load_options': 'cplot._containers._draw',
    'load_results': 'cplot._containers._draw',
    'param_boxplot': 'cplot._plots',
    'param_heatmap': 'cplot._plots',
    'param_histplot': 'cplot._plots',
    'param_jointplot': 'cplot._plots',
    'param_pairplot': 'cplot._plots',
    'param_parallelcoord': 'cplot._plots',
    'param_sunburst': 'cplot._plots',
    'qual_boxplot': 'cplot._plots',
    'qual_heatmap': 'cplot._plots',
    'qual_scatter': 'cplot._plots',
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
    import cplot._settings._description as _csd

    if name in _DESC_MAPPING:
        return getattr(_csd, _DESC_MAPPING[name])

    if name in _IMPORT_MAPPING:
        module = importlib.import_module(_IMPORT_MAPPING[name])

        if name in ('main', 'run'):
            return getattr(module, 'start_cplot')
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

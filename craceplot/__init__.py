# craceplot/__init__.py

_IMPORT_MAPPING = {
    'run': 'craceplot._scripts',
    'main': 'craceplot._scripts',
    'doc': 'craceplot._scripts._utils',
    'examples': 'craceplot._scripts._utils',
    'templates': 'craceplot._scripts._utils',
    'which': 'craceplot._scripts._utils',
    'where': 'craceplot._scripts._utils',
    'load_options': 'craceplot._containers._draw',
    'load_results': 'craceplot._containers._draw',
    'param_boxplot': 'craceplot._plots',
    'param_heatmap': 'craceplot._plots',
    'param_histplot': 'craceplot._plots',
    'param_jointplot': 'craceplot._plots',
    'param_pairplot': 'craceplot._plots',
    'param_parallelcoord': 'craceplot._plots',
    'param_sunburst': 'craceplot._plots',
    'qual_boxplot': 'craceplot._plots',
    'qual_heatmap': 'craceplot._plots',
    'qual_scatter': 'craceplot._plots',
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
    import craceplot._settings._description as _csd

    if name in _DESC_MAPPING:
        return getattr(_csd, _DESC_MAPPING[name])

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

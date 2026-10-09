def cplot_guide():
    import os, sys
    import pathlib
    import webbrowser
    try:
        import craceplot
        dir_cplot = pathlib.Path(craceplot.__file__).resolve().parent
    except:
        dir_cplot = pathlib.Path(__file__).resolve().parent.parent

    guide = pathlib.Path(os.path.join(dir_cplot, 'vignettes/guide.ipynb'))
    guide_online = "https://race-autoconfig.github.io/craceplot/user%20guide/index.html#"

    # not support system without GUI
    if guide.exists():
        print(guide)
        webbrowser.open(guide.as_uri())
    else:
        webbrowser.open(guide_online)
        sys.exit(1)

def cplot_examples(destname):
    import sys
    import pathlib
    import platform
    import subprocess
    from craceplot.utils.format import ConditionalReturn

    try:
        import craceplot
        dir_cplot = pathlib.Path(craceplot.__file__).resolve().parent
    except:
        dir_cplot = pathlib.Path(__file__).resolve().parent.parent

    if destname in ("which", "where"):
        destpath = pathlib.Path(dir_cplot)
        # print(destpath)
        return ConditionalReturn(path=destpath)
    else:
        destpath = pathlib.Path(dir_cplot / 'inst/' / destname)
        # print(destpath)
        return ConditionalReturn(path=destpath)

    # not support system without GUI
    system = platform.system()
    if destpath.exists():
        if system == "Darwin":  # macOS
            subprocess.run(["open", destpath])
        elif system == "Windows":
            subprocess.run(["explorer", destpath])
        else:  # Linux
            subprocess.run(["xdg-open", destpath])
    else:
        sys.exit(1)

def cplot_run():
    import sys

    from craceplot.scripts.main import start_cplot

    if len(sys.argv) > 1:

        if sys.argv[1] == "doc":
            cplot_guide()
            return

        if sys.argv[1].lower() in ("examples", "templates", "which", "where"):
            cplot_examples(sys.argv[1].lower())
            return

    start_cplot(arguments=sys.argv[1:], console=False)
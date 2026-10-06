def cplot_guide():
    import os, sys
    import pathlib
    import webbrowser
    try:
        import cplot
        dir_cplot = pathlib.Path(cplot.__file__).resolve().parent
    except:
        dir_cplot = pathlib.Path(__file__).resolve().parent.parent

    guide = pathlib.Path(os.path.join(dir_cplot, '_vignettes/guide.ipynb'))

    # not support system without GUI
    if guide.exists():
        print(guide)
        webbrowser.open(guide.as_uri())
    else:
        sys.exit(1)

def cplot_examples(destname):
    import sys
    import pathlib
    import platform
    import subprocess

    try:
        import cplot
        dir_cplot = pathlib.Path(cplot.__file__).resolve().parent
    except:
        dir_cplot = pathlib.Path(__file__).resolve().parent.parent

    if destname in ("which", "where"):
        destpath = pathlib.Path(dir_cplot)
        print(destpath)
    else:
        destpath = pathlib.Path(dir_cplot / '_inst/' / destname)
        print(destpath)

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

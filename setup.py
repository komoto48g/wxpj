#! python
# -*- coding: shift-jis -*-
"""setup file
Run the build process by entering 'python setup.py bdist_egg'.
If everything works well, you should find a subdirectory named 'dist'
"""
from setuptools import setup
from pyJeol import __version__

setup(
    name = "pj",
    version = __version__, # "2.4",
    author = "Kazuya O'moto",
    author_email = "komoto@jeol.co.jp",
    description = "wxpyJemacs library (phoenix)",
    
    ## Description of the package in the distribution
    package_dir = {
        '' : "." # root packages is `.`, i.e., mwx package is in ./
    },
    
    ## Packing all modules in mwx package
    packages = [
        "pyJeol",
        "pyJeol.em",
        "pyJeol.legacy",
        "pyJeol.coildata",
        "pyGatan",
        "pyDM3reader",
    ],
    
    ## install_requires = [
    ##     'wxPython',
    ##     'scipy',
    ##     'Pillow',
    ##     'matplotlib',
    ##     'opencv-python',
    ## ],
)

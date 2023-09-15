#! python3
# -*- coding: utf-8 -*-
"""Components of JEOL GUI Toolkit.
"""
import glob
import sys
import os

from mwx.framework import CtrlInterface, Menu, StatusBar
from mwx.controls import Param, LParam, Knob, Icon, Icon2, Clipboard
from mwx.controls import Button, ToggleButton, TextCtrl, Choice, Gauge, Indicator
from mwx.graphman import Frame, Layer, Thread, Graph


## --------------------------------
## Set paths
## --------------------------------

home = os.path.dirname(os.path.abspath(__file__))

## for debug
## sys.path.append(r"C:\usr\home\workspace\tem13\gdk-packages")

## from eggs import 3rd-modules
eggs = os.path.join(home, "nest/*-py{}.{}.egg".format(*sys.version_info))

for path in reversed(glob.glob(eggs)):
    sys.path.append(path)

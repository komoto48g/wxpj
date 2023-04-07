#! python3
# -*- coding: utf-8 -*-
"""Components of JEOL GUI Toolkit.
"""
import glob
import sys
import os

from mwx.framework import StatusBar
from mwx.graphman import Frame, Layer, Thread, Graph
from mwx.controls import Param, LParam, Knob, Icon, Clipboard
from mwx.controls import Button, ToggleButton, TextCtrl, Choice, Gauge, Indicator

## for debug
## sys.path.append(r"C:\usr\home\workspace\tem13\gdk-packages")

home = os.path.dirname(os.path.abspath(__file__))

if sys.version_info >= (3,10):
    eggs = os.path.join(home, "nest/*-py3.10.egg")
elif sys.version_info >= (3,8):
    eggs = os.path.join(home, "nest/*-py3.8.egg")
else:
    eggs = os.path.join(home, "nest/*-py3.5.egg")

for path in reversed(glob.glob(eggs)):
    sys.path.append(path)

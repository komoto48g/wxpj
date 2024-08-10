#! python3
from mwx.framework import Menu, StatusBar # noqa
from mwx.graphman import Frame, Layer, Thread, Graph # noqa
from mwx.controls import Param, LParam, Knob, Icon, Clipboard # noqa
from mwx.controls import Button, ToggleButton, TextCtrl, Choice, Gauge, Indicator # noqa

import editor as edi


def add_paths(*paths):
    import sys
    import os
    for f in paths:
        f = os.path.normpath(f)
        if f not in sys.path:
            sys.path.insert(0, f)


class Layer(Layer):
    """Layer with TEM notify interface.
    """
    su = property(lambda self: self.parent.require('startup'))
    
    illumination = property(lambda self: self.parent.notify.illumination)
    imaging = property(lambda self: self.parent.notify.imaging)
    omega = property(lambda self: self.parent.notify.omega)
    tem = property(lambda self: self.parent.notify.tem)
    eos = property(lambda self: self.parent.notify.eos)
    hts = property(lambda self: self.parent.notify.hts)
    apts = property(lambda self: self.parent.notify.apts)
    gonio = property(lambda self: self.parent.notify.gonio)
    efilter = property(lambda self: self.parent.notify.efilter)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        ## Accessing editor's functions.
        self.edi = edi
        
        ## Cross references.
        self.edi.output = self.output

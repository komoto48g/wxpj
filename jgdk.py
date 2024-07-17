#! python3
from mwx.framework import Menu, StatusBar # noqa
from mwx.graphman import Frame, Layer, Thread, Graph # noqa
from mwx.controls import Param, LParam, Knob, Icon, Clipboard # noqa
from mwx.controls import Button, ToggleButton, TextCtrl, Choice, Gauge, Indicator # noqa


class Layer(Layer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ## Accessing editor functions.
        import editor
        self.edi = editor

        ## Cross references.
        editor.output = self.output

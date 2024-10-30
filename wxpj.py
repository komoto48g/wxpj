#! python3
"""GDK utilus ver 1.0rc
"""
from mwx.graphman import Frame, Layer, Thread, Graph # noqa
from mwx.controls import Param, LParam, ControlPanel, Clipboard, Icon # noqa
from mwx.controls import Button, ToggleButton, TextCtrl, Choice, Gauge, Indicator # noqa


class Layer(Layer):
    import editor as edi

    su = property(lambda self: self.parent.require('startup'))


class TemLayer(Layer):
    """Layer with TEM notify and camera interface.
    """
    illumination = property(lambda self: self.parent.notify.illumination)
    imaging = property(lambda self: self.parent.notify.imaging)
    omega = property(lambda self: self.parent.notify.omega)
    tem = property(lambda self: self.parent.notify.tem)
    eos = property(lambda self: self.parent.notify.eos)
    hts = property(lambda self: self.parent.notify.hts)
    apts = property(lambda self: self.parent.notify.apts)
    gonio = property(lambda self: self.parent.notify.gonio)
    efilter = property(lambda self: self.parent.notify.efilter)


if __name__ == "__main__":
    from debut import main
    main(debrc=".debrc")

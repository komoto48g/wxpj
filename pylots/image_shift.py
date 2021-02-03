#! python
# -*- coding: shift-jis -*-
from mwx.graphman import Layer
from pylots.temixins import AlignInterface, TEM


class Plugin(AlignInterface, Layer):
    """Plugin of beam alignment
    Calibrate beam-shift-alignment
    """
    caption = "IS1"
    conf_key = 'imageshift'
    index = TEM.IS1
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    
    ## 照射系モード共通
    conf_arg = 0
    
    def align(self, *args, **kwargs):
        if self.mode_selection('MAG'):
            return AlignInterface.align(self, *args, **kwargs)
    
    def cal(self):
        with self.save_excursion(mmode='MAG'):
            self.spot.focus()
            return AlignInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_excursion(mmode='MAG'):
                return self.cal()

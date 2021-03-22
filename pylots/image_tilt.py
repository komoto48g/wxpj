#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import AlignInterface, TEM


class Plugin(AlignInterface, Layer):
    """Plugin of beam alignment
    Calibrate image-tilt-alignment
    """
    caption = "IS2"
    conf_key = 'imagetilt'
    index = TEM.IS2
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    
    ## 照射系モード共通
    conf_arg = 0
    
    def align(self, *args, **kwargs):
        if self.mode_selection('DIFF'):
            return AlignInterface.align(self, *args, **kwargs)
    
    def cal(self):
        with self.thread:
            with self.save_excursion(mmode='DIFF'):
                self.spot.focus()
                return AlignInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_excursion(mmode='DIFF'):
                return self.cal()

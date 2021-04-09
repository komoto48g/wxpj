#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import AlignInterface, TEM


class Plugin(AlignInterface, Layer):
    """Plugin of beam alignment
    Calibrate SPOTA-alignment [alpha]
    """
    caption = "SPA"
    conf_key = 'spa'
    index = TEM.SPOTA
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    
    def align(self, *args, **kwargs):
        if self.mode_selection('MAG'):
            return AlignInterface.align(self, *args, **kwargs)
    
    def cal(self):
        with self.thread:
            with self.save_excursion(mmode='MAG'):
                self.spot.focus()
                return AlignInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_excursion(spot=0, mmode='MAG'):
                return all(self.cal() for a in self.for_each_alpha())

#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import AlignInterface, TEM


class Plugin(AlignInterface, Layer):
    """Plugin of beam alignment
    Calibrate beam-shift-alignment [alpha]
    """
    caption = "CLA1"
    conf_key = 'beamshift'
    index = TEM.CLA1
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    
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
                return all([self.cal() for a in self.for_each_alpha()])

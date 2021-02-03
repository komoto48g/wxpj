#! python
# -*- coding: shift-jis -*-
from mwx.graphman import Layer
from pylots.temixins import AlignInterface, TEM


class Plugin(AlignInterface, Layer):
    """Plugin of beam alignment
    Calibrate beam-tilt-alignment [alpha]
    """
    caption = "CLA2"
    conf_key = 'beamtilt'
    index = TEM.CLA2
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    pla = property(lambda self: self.parent.require('align_pla'))
    
    def align(self, *args, **kwargs):
        if self.mode_selection('DIFF'):
            return AlignInterface.align(self, *args, **kwargs)
    
    def cal(self):
        with self.save_excursion(mmode='DIFF'):
            self.spot.focus()
            self.pla.align()
            return AlignInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_excursion(mmode='DIFF', mag=2000):
                return all(self.cal() for a in self.for_each_alpha())

#! python
# -*- coding: shift-jis -*-
from mwx.graphman import Layer
from pylots.temixins import AlignInterface, TEM


class Plugin(AlignInterface, Layer):
    """Plugin of beam alignment
    Calibrate GunA-alignment [spot]
    """
    caption = "Gun"
    conf_key = 'gunshift'
    index = TEM.GUNA1
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    
    ## GUNA は Alpha(=CM) ではなく Spot(=CL1) 依存性を持つ
    conf_arg = property(lambda self: self.illumination.Spot)
    
    def align(self, *args, **kwargs):
        if self.mode_selection('MAG'):
            return AlignInterface.align(self, *args, **kwargs)
    
    def cal(self):
        with self.save_excursion(mmode='MAG'):
            self.spot.focus()
            return AlignInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_excursion(alpha=-1, mmode='MAG'):
                return all(self.cal() for s in self.for_each_spot())

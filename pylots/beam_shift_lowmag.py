#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import AlignInterface, TEM


class Plugin(AlignInterface, Layer):
    """Plugin of beam alignment
    Calibrate beam-shift-alignment [alpha]
    """
    category = "Deflector Maintenance for LOWMAG"
    caption = "CLA1"
    conf_key = 'beamshift'
    index = TEM.CLA1
    
    spot = property(lambda self: self.parent.require('beam_spot_lowmag'))
    
    ## LOWMAG:Alpha(=CM) 依存性なし．単一データとする
    conf_arg = 0
    
    def align(self, *args, **kwargs):
        if self.mode_selection('LOWMAG'):
            return AlignInterface.align(self, *args, **kwargs)
    
    def cal(self):
        with self.thread:
            with self.save_excursion(mmode='LOWMAG'):
                self.spot.focus()
                return AlignInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_excursion(mmode='LOWMAG'):
                return self.cal()

#! python
# -*- coding: shift-jis -*-
from mwx.graphman import Layer
from pylots.temixins import AlignInterface, TEM


class Plugin(AlignInterface, Layer):
    """Plugin of beam alignment
    """
    caption = "PLA"
    conf_key = 'pla'
    index = TEM.PLA
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    
    ## 倍率に依存しない (PL = fixed 仮定)．CCD 面 [um/pix] 換算
    ## PL = fixval でない場合は，回転／倍率の補正が必要
    conf_arg = 0
    conf_factor = property(lambda self: self.camera.pixel_unit * 1e3)
    
    def align(self, *args, **kwargs):
        return AlignInterface.align(self, *args, **kwargs)
    
    def cal(self):
        self.index = (0x8000, 0x8000)
        self.spot.focus()
        return AlignInterface.cal(self)
    
    def execute(self):
        with self.thread:
            return self.cal()

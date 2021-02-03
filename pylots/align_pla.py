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
    
    ## �{���Ɉˑ����Ȃ� (PL = fixed ����)�DCCD �� [um/pix] ���Z
    ## PL = fixval �łȂ��ꍇ�́C��]�^�{���̕␳���K�v
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

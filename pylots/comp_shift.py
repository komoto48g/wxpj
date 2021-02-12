#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import CompInterface, TEM


class Plugin(CompInterface, Layer):
    """Plugin of compensation
    Adjust comp1-shift [alpha]
    """
    caption = "SHIFT"
    conf_key = 'compshift'
    index = TEM.SHIFT
    wobbler = TEM.CLA1
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    deflector = property(lambda self: self.parent.require('beam_tilt'))
    diffspot = property(lambda self: self.parent.require('beam_spot_diff'))
    
    def cal(self):
        with self.save_excursion(mmode='DIFF'):
            self.diffspot.focus() # DIFF-Focus をきちんと合わせること！
            self.spot.focus()
            return CompInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_excursion(mmode='DIFF'):
                return all([self.cal() for a in self.for_each_alpha()])

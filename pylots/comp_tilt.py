#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import CompInterface, TEM


class Plugin(CompInterface, Layer):
    """Plugin of compensation
    Adjust comp1-tilt [alpha]
    """
    caption = "TILT"
    conf_key = 'comptilt'
    index = TEM.TILT
    wobbler = TEM.CLA2
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    deflector = property(lambda self: self.parent.require('beam_shift'))
    
    def cal(self):
        with self.thread:
            with self.save_excursion(mmode='MAG'):
                ## self.olstd.focus() # OL-Focus をきちんと合わせること！
                self.spot.focus()
                return CompInterface.cal(self, step=0x100)
    
    def execute(self):
        with self.thread:
            with self.save_excursion(mmode='MAG'):
                return all([self.cal() for a in self.for_each_alpha()])

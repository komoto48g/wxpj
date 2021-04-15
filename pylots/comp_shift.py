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
    
    ## spot = property(lambda self: self.parent.require('beam_spot'))
    diffspot = property(lambda self: self.parent.require('beam_spot_diff'))
    para = property(lambda self: self.parent.require('beam2_para'))
    
    deflector = property(lambda self: self.parent.require('beam_tilt'))
    pla = property(lambda self: self.parent.require('align_pla'))
    saad = property(lambda self: self.parent.require('align2_saapt_diff'))
    
    def cal(self):
        with self.thread:
            with self.save_excursion(mmode='DIFF'):
                self.para.focus() # para で合わせるべし ! #20210219 Note 参照
                self.diffspot.focus() # DIFF-Focus をきちんと合わせること !
                ## self.spot.focus()
                self.pla.align()
                return CompInterface.cal(self, step=0x100)
    
    def execute(self):
        with self.thread:
            with self.save_restriction(CLA=2, SAA=0):
                with self.save_excursion(mmode='DIFF', mag=2000):
                    return all([self.cal() for a in self.for_each_alpha()])

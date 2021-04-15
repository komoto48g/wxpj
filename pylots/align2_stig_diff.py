#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import StigInterface, TEM


class Plugin(StigInterface, Layer):
    """Plugin of beam alignment
    Adjust diff-stig-alignment [alpha]
    Note: The spot focus stride (1/4) must be fixed and *DO NOT CHANGE*
    """
    caption = "ILS"
    conf_key = 'diffstig'
    index = TEM.ILS
    
    diffspot = property(lambda self: self.parent.require('beam_spot_diff'))
    para = property(lambda self: self.parent.require('beam2_para'))
    pla = property(lambda self: self.parent.require('align_pla'))
    cla = property(lambda self: self.parent.require('align2_clapt'))
    
    @property
    def conf_factor(self):
        return self.cam_unit / (self.CLA.dia /100)
    
    def align(self):
        if self.aptsel(CLA=True, SAA=0):
            if self.mode_selection('DIFF'):
                self.diffspot.focus(0.25)
                self.para.focus()
                self.pla.align()
                return StigInterface.align(self)
    
    def cal(self):
        with self.thread:
            if self.aptsel(CLA=True, SAA=0):
                with self.save_excursion(mmode='DIFF'):
                    self.diffspot.focus(0.25)
                    self.para.focus()
                    self.pla.align()
                    ## return StigInterface.cal(self)
                    retval = StigInterface.cal(self)
                    if retval is True:
                        StigInterface.align(self)
                    return retval
    
    def execute(self):
        with self.thread:
            with self.save_restriction(CL3=0xffff, CLA=2, SAA=0):
                with self.save_excursion(alpha=-1, mmode='MAG'):
                    self.cla.align()
                with self.save_excursion(mmode='DIFF', mag=2000):
                    return all(self.cal() for a in self.for_each_alpha())

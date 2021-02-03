#! python
# -*- coding: shift-jis -*-
from mwx.graphman import Layer
from pylots.temixins import StigInterface, TEM


class Plugin(StigInterface, Layer):
    """Plugin of beam alignment
    Adjust beam-stig-alignment [alpha]
    Note: The spot focus stride (1/4) must be fixed and *DO NOT CHANGE*
    """
    caption = "CLS"
    conf_key = 'beamstig'
    index = TEM.CLS
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    ## cla = property(lambda self: self.parent.require('align2_clapt'))
    
    @property
    def conf_factor(self):
        return self.mag_unit / (self.CLAPT.dia /100)
    
    def align(self):
        if self.apt_selection('CLAPT') and self.apt_selection('SAAPT', 0):
            if self.mode_selection('MAG'):
                self.spot.focus(0.25)
                self.shift.align()
                return StigInterface.align(self)
    
    def cal(self):
        if self.apt_selection('CLAPT') and self.apt_selection('SAAPT', 0):
            with self.save_excursion(mmode='MAG'):
                self.spot.focus(0.25)
                self.shift.align()
                return StigInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAAPT=0):
                with self.save_excursion(mmode='MAG'):
                    return all(self.cal() for a in self.for_each_alpha())

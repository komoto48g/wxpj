#! python
# -*- coding: shift-jis -*-
from mwx import LParam
from mwx.graphman import Layer
from pylots.temixins import AlignInterface, TEM, HTsys


class Plugin(AlignInterface, Layer):
    """Plugin of beam alignment
    Adjust beam-axis-HT-alignment [alpha]
    """
    menu = "&Test"
    category = "Deflector Test"
    
    caption = "HT-axis"
    conf_key = 'ht-beamaxis'
    index = TEM.CLA2
    wobbler = HTsys.Value
    
    default_wobstep = 100 # ht step [V]
    default_wobsec = 1.0
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    
    def Init(self):
        AlignInterface.Init(self)
        
        self.wobstep = LParam("Wobbler [V]", (10,200,10), self.default_wobstep)
        self.layout("Settings", (
            self.wobstep,
            ),
            row=1, show=1, type='vspin', tw=40,
        )
    
    def set_current_session(self, session):
        self.wobstep.value = session.get('wobstep')
    
    def get_current_session(self):
        return {
            'wobstep': self.wobstep.value,
        }
    
    @property
    def conf_factor(self):
        return (self.mag_unit / (self.CLAPT.dia /100)
                              / (self.wobstep.value / self.default_wobstep))
    
    def align(self):
        if self.apt_selection('CLAPT') and self.apt_selection('SAAPT', 0):
            if self.mode_selection('MAG'):
                try:
                    worg = self.wobbler
                    self.spot.focus(1)
                    self.shift.align()
                    self.wobbler = worg - self.wobstep.value
                    self.delay(self.default_wobsec)
                    return AlignInterface.align(self)
                finally:
                    self.wobbler = worg
    
    def cal(self):
        if self.apt_selection('CLAPT') and self.apt_selection('SAAPT', 0):
            with self.save_excursion(mmode='MAG'):
                self.spot.focus(1)
                self.shift.align()
                try:
                    worg = self.wobbler
                    self.wobbler = worg - self.wobstep.value
                    self.delay(self.default_wobsec)
                    return AlignInterface.cal(self) and AlignInterface.align(self)
                finally:
                    self.wobbler = worg
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAAPT=0):
                with self.save_excursion(mmode='MAG'):
                    return all(self.cal() for a in self.for_each_alpha())

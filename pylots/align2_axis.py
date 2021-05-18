#! python
# -*- coding: utf-8 -*-
from mwx.controls import LParam
from mwx.graphman import Layer
from pylots.temixins import AlignInterface, TEM


class Plugin(AlignInterface, Layer):
    """Plugin of beam alignment
    Adjust beam-axis-OL-alignment [alpha]
    """
    caption = "OL-axis"
    conf_key = 'beamaxis'
    index = TEM.CLA2
    wobbler = TEM.OL
    
    default_wobstep = 0x1000 # olstep = 0x1000 => OLdf=12um
    default_wobsec = 1.0
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    
    def Init(self):
        AlignInterface.Init(self)
        
        self.wobstep = LParam("Wobbler amp", (0x100,0x8000,0x100), self.default_wobstep, dtype=hex)
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
        return (self.mag_unit / (self.CLA.dia /100)
                              / (self.wobstep.value / self.default_wobstep))
    
    def align(self):
        if self.aptsel(CLA=True, SAA=0):
            if self.mode_selection('MAG'):
                self.spot.focus()
                self.shift.align()
                try:
                    worg = self.wobbler
                    self.wobbler = worg + self.wobstep.value
                    self.delay(self.default_wobsec)
                    return AlignInterface.align(self)
                finally:
                    self.wobbler = worg
    
    def cal(self):
        with self.thread:
            if self.aptsel(CLA=True, SAA=0):
                with self.save_excursion(mmode='MAG'):
                    self.spot.focus()
                    self.shift.align()
                    try:
                        worg = self.wobbler
                        self.wobbler = worg + self.wobstep.value
                        self.delay(self.default_wobsec)
                        retval = AlignInterface.cal(self)
                        if retval is True:
                            AlignInterface.align(self)
                        return retval
                    finally:
                        self.wobbler = worg
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAA=0):
                with self.save_excursion(mmode='MAG'):
                    return all(self.cal() for a in self.for_each_alpha())

#! python
# -*- coding: utf-8 -*-
from mwx import LParam
from pylots.temixins import AlignInterface, TEM, HTsys
from pylots.Autopylot2 import PylotItem


class Plugin(AlignInterface, PylotItem):
    """Plugin of beam alignment
    Adjust beam-axis-Anode-alignment [spot]
    """
    category = "*Discipline*"
    caption = "A2-axis"
    conf_key = 'a2-beamaxis'
    index = TEM.GUNA2
    ## wobbler = HTsys.A2
    
    @property
    def wobbler(self):
        return self.ht.A2
    
    @wobbler.setter
    def wobbler(self, v):
        self.ht.A2 = v
        while 1:
            self.delay(0.1)
            if self.ht.A2 == v:
                break
    
    default_wobstep = 100 # A2 voltage -100V
    default_wobsec = 0.0
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    
    ## GUNA は Alpha(=CM) ではなく Spot(=CL1) 依存性を持つ
    conf_arg = property(lambda self: self.illumination.Spot)
    
    def Init(self):
        AlignInterface.Init(self)
        PylotItem.Init(self)
        
        self.wobstep = LParam("Wobbler [V]", (10,200,10), self.default_wobstep)
        self.layout("Settings", (
            self.wobstep,
            ),
            row=1, show=1, type='vspin', tw=40,
        )
        self.ht = HTsys()
    
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
        if self.apt_selection('CLA') and self.apt_selection('SAA', 0):
            if self.mode_selection('MAG'):
                self.spot.focus()
                self.shift.align()
                try:
                    worg = self.wobbler
                    self.wobbler = (worg or 0) + self.wobstep.value
                    self.delay(self.default_wobsec)
                    return AlignInterface.align(self)
                finally:
                    self.wobbler = worg
    
    def cal(self):
        with self.thread:
            if self.apt_selection('CLA') and self.apt_selection('SAA', 0):
                with self.save_excursion(mmode='MAG'):
                    self.spot.focus()
                    self.shift.align()
                    try:
                        worg = self.wobbler
                        self.wobbler = (worg or 0) + self.wobstep.value
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
                    return all(self.cal() for a in self.for_each_spot())

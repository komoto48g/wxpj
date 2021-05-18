#! python
# -*- coding: utf-8 -*-
from mwx.controls import LParam
from pyJeol.pyJem2 import Filter
from pylots.temixins import AlignInterface, TEM
from pylots.Autopylot2 import PylotItem


class Plugin(AlignInterface, PylotItem):
    """Plugin of beam alignment
    Adjust beam-axis-HT-alignment [alpha]
    * Calibration with Magnification 100k or more is preferable
    """
    category = "*Discipline*"
    caption = "HT-axis"
    conf_key = 'ht-beamaxis'
    index = TEM.CLA2
    wobbler = Filter.EnergyShift
    
    default_wobstep = 100 # HT voltage -100V
    default_wobsec = 1.0
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    
    def Init(self):
        AlignInterface.Init(self)
        PylotItem.Init(self)
        
        self.wobstep = LParam("Wobbler [V]", (10,500,10), self.default_wobstep)
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
                    self.wobbler = (worg or 0) + self.wobstep.value
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
                        self.wobbler = (worg or 0) + self.wobstep.value
                        self.delay(self.default_wobsec)
                        return AlignInterface.cal(self)
                    finally:
                        self.wobbler = worg
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAA=0):
                with self.save_excursion(mmode='MAG'):
                    return all(self.cal() for a in self.for_each_alpha())

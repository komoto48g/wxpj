#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import AlignInterface


class Plugin(AlignInterface, Layer):
    """Plugin of alignment
    Calibrate SAA motion drive
    Note: beta (selected area size [um]) is also recorded in cal
    """
    menu = None #"Maintenance/Aperture"
    category = "Aperture Maintenance"
    caption = "SAAPT"
    conf_key = 'saapt'
    
    APT = property(lambda self: self.SAAPT)
    
    @property
    def index(self):
        return self.APT.pos
    
    @index.setter
    def index(self, v):
        self.APT.pos = v
        while 1:
            u = self.APT.pos
            if sum(abs(u - v)) < 1: # wait until pos (reached) => stopped
                break
            v = u
            self.delay(1)
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    pla = property(lambda self: self.parent.require('align_pla'))
    
    ## 照射系モード共通
    conf_arg = 0
    
    @property
    def conf_factor(self):
        return self.mag_unit
    
    def align(self):
        if self.apt_selection('SAAPT'):
            if self.mode_selection('MAG'):
                self.pla.index = (0x8000, 0x8000) # neutralize
                self.spot.focus(2)
                return AlignInterface.align(self)\
                   and AlignInterface.align(self)
    
    def cal(self):
        with self.thread:
            if self.apt_selection('SAAPT'):
                with self.save_excursion(mmode='MAG'):
                    d, p, q = self.detect_beam_diameter()
                    if d:
                        ## Reccord SAAPT size, normalizing by φ100um
                        ## >>> saadia = self.config['beta'] * (self.SAAPT.dia /100) # [um]
                        self.config['beta'] = d * self.mag_unit / (self.SAAPT.dia /100) # [um]
                    return AlignInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_restriction(CL3=0xffff, CLAPT=1, SAAPT=1):
                with self.save_excursion(spot=0, alpha=-1, mmode='MAG'):
                    self.delay(2)
                    return self.cal()

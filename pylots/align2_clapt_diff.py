#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import AlignInterface


class Plugin(AlignInterface, Layer):
    """Plugin of alignment
    Calibrate CLA motion drive in Large Area DIFF
    Note: The spot focus stride (1/4) must be fixed and *DO NOT CHANGE*
    """
    menu = None #"Maintenance/Aperture"
    category = "Aperture Maintenance"
    caption = "LADIFF"
    conf_key = 'ladiff'
    
    APT = property(lambda self: self.CLA)
    
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
    
    diffspot = property(lambda self: self.parent.require('beam_spot_diff'))
    para = property(lambda self: self.parent.require('beam2_para'))
    pla = property(lambda self: self.parent.require('align_pla'))
    
    ## 照射系 Spot には依存しないとする
    conf_arg = property(lambda self: self.illumination.Alpha)
    
    @property
    def conf_factor(self):
        ## using constant stride (1/4), be independent to mags, but depends on apt size
        return self.camera.pixel_unit * self.APT.dia /100
    
    def align(self):
        if self.aptsel(CLA=True):
            if self.mode_selection('DIFF'):
                with self.save_restriction(IL1=None):
                    self.diffspot.focus() # center pos
                    self.para.focus()
                    self.delay()
                    self.pla.align()
                    self.diffspot.focus(0.25) # Do always set quarter-open beam
                    return AlignInterface.align(self)\
                       and AlignInterface.align(self)
    
    def cal(self):
        with self.thread:
            if self.aptsel(CLA=True):
                with self.save_excursion(mmode='DIFF'):
                    with self.save_restriction(PLA=None):
                        self.diffspot.focus(0.25) # Do always set quarter-open beam
                        self.para.focus()
                        self.pla.align()
                        return AlignInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAA=0):
                with self.save_excursion(alpha=-1, mmode='DIFF', mag=2000):
                    return all(self.cal() for a in self.for_each_alpha())

#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import AlignInterface


class Plugin(AlignInterface, Layer):
    """Plugin of alignment
    Calibrate CLA motion drive
    Note: The spot focus stride (1/4) must be fixed and *DO NOT CHANGE*
    """
    menu = None #"Maintenance/Aperture"
    category = "Aperture Maintenance"
    caption = "CLA"
    conf_key = 'clapt'
    
    APT = property(lambda self: self.CLA)
    
    @property
    def index(self):
        return self.APT.pos
    
    @index.setter
    def index(self, v):
        self.APT.pos = v
        ## 目標値と最終値は一致するとは限らない▼以下のコードで待つ
        while 1:
            u = self.APT.pos
            if sum(abs(u - v)) < 1: # wait until pos (reached) => stopped
                break
            v = u
            self.delay(1)
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    pla = property(lambda self: self.parent.require('align_pla'))
    
    ## 照射系 Spot には依存しないとする
    conf_arg = property(lambda self: self.illumination.Alpha)
    
    @property
    def conf_factor(self):
        ## using constant stride (1/4), be independent to mags, but depends on apt size
        return self.camera.pixel_unit * self.APT.dia /100
    
    def align(self):
        if self.aptsel(CLA=True):
            if self.mode_selection('MAG'):
                with self.save_restriction(CL3=None, SAA=0):
                    self.pla.index = (0x8000, 0x8000) # neutralize
                    self.spot.focus(-0.25) # for histerisis loop back
                    self.delay(1)
                    self.spot.focus() # center
                    self.delay()
                    self.shift.align()
                    self.delay()
                    self.spot.focus(0.25) # Do always set quarter-open beam
                    return AlignInterface.align(self)\
                       and AlignInterface.align(self)
    
    def cal(self):
        with self.thread:
            if self.aptsel(CLA=True):
                with self.save_excursion(mmode='MAG'):
                    self.spot.focus(0.25) # Do always set quarter-open beam
                    self.shift.align()
                    return AlignInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAA=0):
                with self.save_excursion(spot=0, mmode='MAG'):
                    return all(self.cal() for a in self.for_each_alpha())

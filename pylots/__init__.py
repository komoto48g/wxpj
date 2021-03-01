#! python
# -*- coding: utf-8 -*-
"""Editor's collection of Tem algorithms of Mixin (interface) class
For the main implementaion, refer to `temixins' module

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
from .temixins import (TEM, TemInterface, SpotInterface,
                      AlignInterface, StigInterface, CompInterface,
                      DataLogger)

__version__ = "0.0"
__author__ = "Kazuya O'moto <komoto@jeol.co.jp>"


class UserInterface(TemInterface):
    """TEM Controller Interface complex
    """
    menu = "&User"
    
    lmspot = property(lambda self: self.parent.require('beam_spot_lowmag'))
    lmshift = property(lambda self: self.parent.require('beam_shift_lowmag'))
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    diffspot = property(lambda self: self.parent.require('beam_spot_diff'))
    
    para = property(lambda self: self.parent.require('beam2_para'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    tilt = property(lambda self: self.parent.require('beam_tilt'))
    
    pla = property(lambda self: self.parent.require('align_pla'))
    spa = property(lambda self: self.parent.require('align_spa'))
    gun = property(lambda self: self.parent.require('align_gun'))
    
    clapt_mag = property(lambda self: self.parent.require('align2_clapt'))
    clapt_diff = property(lambda self: self.parent.require('align2_clapt_diff'))
    saapt_mag = property(lambda self: self.parent.require('align2_saapt'))
    saapt_diff = property(lambda self: self.parent.require('align2_saapt_diff'))
    
    @property
    def clapt(self):
        if self.magp: return self.clapt_mag
        if self.diffp: return self.clapt_diff
        if self.lowmagp: return NotImplemented
    
    @property
    def saapt(self):
        if self.magp: return self.saapt_mag
        if self.diffp: return self.saapt_diff
        if self.lowmagp: return NotImplemented
    
    @property
    def selected_aperture(self):
        info = self.Aperture.Info # pmpj:Aperture.Info is always being notified
        name = info['id_name']    # get currently selected aperture plugin
        
        ## if name == 'CLA2': return self.clapt2 is NotImplemented
        if name == 'CLA': return self.clapt
        if name == 'SAA': return self.saapt
    
    axis = property(lambda self: self.parent.require('align2_axis'))
    stig = property(lambda self: self.parent.require('align2_stig'))
    diffstig = property(lambda self: self.parent.require('align2_stig_diff'))
    
    ishift = property(lambda self: self.parent.require('image_shift'))
    itilt = property(lambda self: self.parent.require('image_tilt'))
    
    comp1 = property(lambda self: self.parent.require('comp_shift'))
    comp2 = property(lambda self: self.parent.require('comp_tilt'))
    iscomp1 = property(lambda self: self.parent.require('comp_is_shift'))
    iscomp2 = property(lambda self: self.parent.require('comp_is_tilt'))
    
    alpha = property(lambda self: self.parent.require('cal_alpha'))
    stage = property(lambda self: self.parent.require('cal_focus_z'))
    ol = property(lambda self: self.parent.require('cal_focus_ol'))
    fl = property(lambda self: self.parent.require('cal_focus_fl'))

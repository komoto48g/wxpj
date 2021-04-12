#! python
# -*- coding: utf-8 -*-
import numpy as np
from mwx.graphman import Layer
from pylots.temixins import TemInterface, TEM
import wxpyJemacs as wxpj
import editor as edi


class Plugin(TemInterface, Layer):
    """Plugin of Focus calibration
    """
    menu = None #"Maintenance/&Focus"
    category = "Focus"
    caption = "Stage"
    conf_key = 'stage'
    wobbler = TEM.CLA2
    
    default_wobstep = 0x800
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    ## para = property(lambda self: self.parent.require('beam2_para'))
    ## shift = property(lambda self: self.parent.require('beam_shift'))
    cla = property(lambda self: self.parent.require('align2_clapt'))
    
    def Init(self):
        self.layout(None, (
            wxpj.Button(self, "Z-Focus", lambda v: self.thread.Start(self.focus), icon='exe'),
            ),
        )
        self.layout("Manual calibration", (
            wxpj.Button(self, "Cal", lambda v: self.thread.Start(self.cal), icon='cal'),
            wxpj.Button(self, "Save", lambda v: self.config.save(self.conf_key), icon='save'),
            wxpj.Button(self, "Load", lambda v: self.config.load(self.conf_key), icon='proc'),
            ),
            row=3, show=1,
        )
    
    def get_tilt(self, j=0):
        i = self.illumination.Alpha
        L = self.config['beamtilt'][i] # raw config table [mrad/bit]
        return L[j::2] * self.default_wobstep # [bit] -> (x,y)-tilting angles [mrad]
    
    def calc_disp(self):
        try:
            worg = self.wobbler
            self.delay(0)
            src = self.capture()
            
            self.wobbler = worg + [self.default_wobstep, 0]
            self.delay(1)
            src2 = self.capture()
            
            y = edi.eval_shift(src, src2)
            return y * self.mag_unit # [pix] -> [um]
        finally:
            self.wobbler = worg
    
    def focus(self):
        if self.mode_selection('MAG'):
            try:
                org = self.Gonio.Z
                dt = self.get_tilt()
                dy = self.calc_disp()   # [um] image displacement
                dz = min(dy / dt) * 1e3 # [um] @min eliminates inf
                
                print("$(dz) = {!r}".format((dz)))
                self.Gonio.Z += dz
                
            except Exception:
                self.Gonio.Z = org
                raise
    
    @property
    def M(self):
        """Inverse matrix [um/pix] refered to config data"""
        m = self.config[self.conf_key][0] / self.mag_unit # [pix/um] to be inversed
        return np.linalg.inv(m.reshape(2,2))
    
    def cal(self):
        with self.thread:
            if self.apt_selection('SAAPT', 0):
                with self.save_excursion(mmode='MAG'):
                    try:
                        step = 10e3 / self.imaging.Mag # CCD:10mm/Mag -> step [um]
                        
                        org_x = self.Gonio.X
                        org_y = self.Gonio.Y
                        
                        self.Gonio.X += step # get rid of backlash X+
                        self.delay(2)
                        
                        self.Gonio.Y += step # get rid of backlash Y+
                        self.delay(2)
                        
                        src = self.capture()
                        
                        self.Gonio.X += step
                        self.delay(2)
                        src2 = self.capture()
                        
                        self.Gonio.Y += step
                        self.delay(2)
                        src3 = self.capture()
                        
                        m = np.vstack((
                            edi.eval_shift(src, src2),
                            edi.eval_shift(src2, src3))).T / step # [pix/um]
                        
                        ## normalized by the expected unit length per pixel [um/pix]
                        self.config[self.conf_key][0] = m.flatten() * self.mag_unit
                        return True
                    finally:
                        self.Gonio.X = org_x
                        self.Gonio.Y = org_y
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAAPT=0):
                with self.save_excursion(spot=0, alpha=-1, mmode='MAG'):
                    #self.cla.align()
                    #self.spot.focus(2)
                    ## self.para.focus()
                    return self.cal()

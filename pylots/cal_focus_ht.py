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
    
    caption = "HT-imaxis"
    conf_key = 'ht-imageaxis'
    index = TEM.CLA2
    wobbler = HTsys.Value
    
    default_wobstep = 100 # [V]
    default_wobsec = 1.0  # [s]
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    
    def Init(self):
        AlignInterface.Init(self)
    
    @property
    def tilt(self):
        i = self.illumination.Alpha
        T = self.config['beamtilt'][i].reshape(2,2) # raw config table [mrad/bit]
        return T * self.default_wobstep # [bit] -> (x,y)-tilting angles [mrad]
    
    def calc_disp(self):
        try:
            worg = self.wobbler
            self.delay(2)
            src = self.capture()
            
            self.wobbler = worg - self.default_wobstep
            self.delay(2)
            src2 = self.capture()
            
            y = edi.eval_shift(src, src2)
            return y * self.mag_unit # [pix] -> [um]
        finally:
            self.wobbler = worg
    
    def cal(self):
        if self.apt_selection('SAAPT', 0):
            with self.save_excursion(mmode='MAG'):
                try:
                    step = 0x1000
                    org = self.index
                    dt = self.tilt[:,0]
                    
                    x1 = self.index
                    y1 = self.calc_disp()   # [um] image displacement
                    z1 = min(y1 / dt) * 1e3 # [um] @min eliminates inf
                    
                    x2 = self.index = org + step
                    y2 = self.calc_disp()
                    z2 = min(y2 / dt) * 1e3 # [um] @min eliminates inf
                    
                    zs = (z2-z1) / (x2-x1) # [um/bit] -> config
                    x0 = x1 - z1 / zs      # フォーカス推定値
                    
                    self.config[self.conf_key] = zs
                    self.index = x0
                    return True
                
                except Exception:
                    self.index = org
                    raise
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAAPT=0):
                with self.save_excursion(mmode='MAG'):
                    return all(self.cal() for a in self.for_each_alpha())

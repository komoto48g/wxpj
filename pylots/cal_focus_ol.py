#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import TemInterface, TEM
import wxpyJemacs as wxpj
import editor as edi


class Plugin(TemInterface, Layer):
    """Plugin of Focus calibration
    """
    menu = None #"&Maintenance/&Focus"
    category = "Focus"
    caption = "OL"
    conf_key = 'ol-focus'
    index = TEM.OL
    wobbler = TEM.CLA2
    
    default_wobstep = 0x800
    
    para = property(lambda self: self.parent.require('beam2_para'))
    
    def Init(self):
        TemInterface.Init(self)
        
        self.layout(None, (
            wxpj.Button(self, "OL-Focus", lambda v: self.thread.Start(self.focus), icon='exe'),
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
            self.delay(2)
            src = self.capture()
            
            self.wobbler = worg + [self.default_wobstep, 0]
            self.delay(2)
            src2 = self.capture()
            
            y = edi.eval_shift(src, src2)
            return y * self.mag_unit # [pix] -> [um]
        finally:
            self.wobbler = worg
    
    def focus(self):
        if self.mode_selection('MAG'):
            try:
                org = self.index
                dt = self.get_tilt()
                dy = self.calc_disp()   # [um] image displacement
                dz = min(dy / dt) * 1e3 # [um] @min eliminates inf
                
                print("$(dz) = {!r}".format((dz)))
                self.index -= dz / self.config[self.conf_key] # [um/bit] <- config
                
            except Exception:
                self.index = org
                raise
    
    def cal(self):
        if self.apt_selection('SAAPT', 0):
            with self.save_excursion(mmode='MAG'):
                try:
                    step = 0x1000
                    org = self.index
                    dt = self.get_tilt()
                    
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
                with self.save_excursion(spot=0, alpha=-1, mmode='MAG'):
                    self.para.focus()
                    return self.cal()

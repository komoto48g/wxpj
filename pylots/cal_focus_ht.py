#! python
# -*- coding: utf-8 -*-
## from mwx.graphman import Layer
from pylots.Autopylot2 import PylotItem as Layer
from pylots.temixins import TemInterface, TEM, Filter
import wxpyJemacs as wxpj
import editor as edi


class Plugin(TemInterface, Layer):
    """Plugin of beam alignment
    Adjust beam-axis-HT-alignment [alpha]
    """
    menu = "&Maintenance/&Test"
    category = "*Discipline*"
    caption = "HT"
    conf_key = 'ht-focus'
    index = Filter.EnergyShift
    wobbler = TEM.CLA2
    
    default_wobstep = 0x800
    
    para = property(lambda self: self.parent.require('beam2_para'))
    
    def Init(self):
        Layer.Init(self)
        
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
    
    def cal(self):
        if self.apt_selection('SAAPT', 0):
            with self.save_excursion(mmode='MAG'):
                try:
                    step = 500
                    dt = self.get_tilt()
                    
                    x1 = self.index = 0
                    y1 = self.calc_disp()   # [um] image displacement
                    z1 = min(y1 / dt) * 1e3 # [um] @min eliminates inf
                    print("$(z1) = {!r}".format((z1)))
                    
                    x2 = self.index = -step
                    y2 = self.calc_disp()
                    z2 = min(y2 / dt) * 1e3 # [um] @min eliminates inf
                    print("$(z2) = {!r}".format((z2)))
                    
                    zs = (z2-z1) / (x2-x1) # [um/V] -> config
                    
                    cc = zs * self.environ.acc_v / self.environ.cstar * 1e-3 # [mm]
                    print("$(cc) = {:g} mm".format((cc)))
                    
                    self.config[self.conf_key] = zs
                    return True
                finally:
                    self.index = None
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAAPT=0):
                with self.save_excursion(spot=0, alpha=-1, mmode='MAG'):
                    self.para.focus()
                    return self.cal()

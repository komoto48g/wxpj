#! python
# -*- coding: utf-8 -*-
import numpy as np
from numpy import cos,sin
from mwx.graphman import Layer
from pylots.temixins import TemInterface, TEM
import wxpyJemacs as wxpj


class Plugin(TemInterface, Layer):
    """Plugin of Focus calibration
    """
    menu = None #"Maintenance/&Focus"
    category = "Focus"
    caption = "FL"
    conf_key = 'fl-focus'
    index = TEM.FL
    
    def Init(self):
        self.layout(None, (
            wxpj.Button(self, "FL-Focus", lambda v: self.thread.Start(self.focus), icon='exe'),
            ),
        )
        self.layout("Manual calibration", (
            wxpj.Button(self, "Cal", lambda v: self.thread.Start(self.cal), icon='cal'),
            wxpj.Button(self, "Save", lambda v: self.config.save(self.conf_key), icon='save'),
            wxpj.Button(self, "Load", lambda v: self.config.load(self.conf_key), icon='proc'),
            ),
            row=3, show=1,
        )
    
    @property
    def conf_table(self):
        i = self.omega.Selector
        return self.config[self.conf_key][i] / self.disp_unit # [pix/bit]
    
    def focus(self):
        if self.omega.Mode == 1:
            h, w = self.camera.shape
            try:
                org = self.index
                c, p, q = self.detect_beam_center() # これがイイかどうかは要検討▲とくに試料があるとき
                if c is None:
                    return
                
                x, y = c - (w/2, h/2)    # pix.coords. from origin (the center of the screen)
                dx, dy = self.conf_table # dispersion vector ds := (dx,dy) [pix/bit]
                t = np.arctan2(dx, -dy)  # calc the nearest pos along the dispersion line
                r = x * cos(t) + y * sin(t)
                pos = (r * cos(t), r * sin(t)) # target position to be aligned
                self.index = org - min((x-pos[0])/dx, (y-pos[1])/dy) # @min eliminates inf
            
            except Exception:
                self.index = org
                raise
    
    def cal(self):
        with self.thread:
            if self.omega.Mode == 1:
                h, w = self.camera.shape
                ds = self.conf_table
                ys = np.hypot(*ds) # [pix/bit]
                step = h / ys * 0.1 # (config) 初期設定値をもとにステップを決める
                try:
                    org = self.index
                    c, p, q = self.detect_beam_center()
                    if c is None:
                        return
                    
                    for i in range(2):
                        self.index = org + step
                        u, p_, q_ = self.detect_beam_center()
                        if u is None or p_/p < 0.8:
                            step /= 2
                        else: break
                    else: return
                    
                    m = (u - c) / step # [pix/bit]
                    
                    i = self.omega.Selector
                    self.config[self.conf_key][i] = m * self.disp_unit # [eV/bit]
                    return True
                finally:
                    self.index = org
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAAPT=1):
                with self.save_excursion(mmode='MAG', kmode='Spectrum'):
                    self.delay(1)
                    return all([self.cal()
                        for d in self.for_each_disp()])

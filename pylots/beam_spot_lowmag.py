#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import SpotInterface, TEM


class Plugin(SpotInterface, Layer):
    """Plugin of focus adjustment
    Calibrate spot-beam-focus [spot/alpha] and measure the Brightness sensitivity
    """
    menu = None #"&Maintenance/&1-Focus"
    category = "1-Focus Maintenance for LOWMAG"
    caption = "LM-Spot"
    conf_key = ('cl3spot', 'cl3sens',)
    index = TEM.CL3
    
    @property
    def factor(self):
        return self.mag_unit / (self.CLAPT.dia /100)
    
    def get_spot_beam(self):
        i = (self.illumination.Spot, 0) # <spot> 列の任意の要素をとる
        j, k = self.conf_key
        xo = self.config[j][i]
        ys = self.config[k][i] / self.factor
        return xo, ys
    
    def set_spot_beam(self, v):
        i = self.illumination.Spot # <spot> 列の全ての要素を同時に書き換える
        j, k = self.conf_key
        xo, ys = v
        if xo: self.config[j][i] = int(xo)
        if ys: self.config[k][i] = abs(ys) * self.factor
    
    def cal(self):
        with self.thread:
            if self.apt_selection('CLAPT') and self.apt_selection('SAAPT', 0):
                with self.save_excursion(mmode='LOWMAG'):
                    return SpotInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAAPT=0):
                with self.save_excursion(mmode='LOWMAG'):
                    return all([None is not self.cal()
                        for s in self.for_each_spot()])
        return True

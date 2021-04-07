#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import SpotInterface, TEM


class Plugin(SpotInterface, Layer):
    """Plugin of focus adjustment
    Calibrate diff-focus [spot/alpha] and measure the DIFF-Focus sensitivity
    """
    menu = None #"Maintenance/&1-Focus"
    category = "1-Focus Maintenance"
    caption = "Diff-Spot"
    conf_key = 'diffspot'
    index = TEM.IL1
    
    para = property(lambda self: self.parent.require('beam2_para'))
    pla = property(lambda self: self.parent.require('align_pla'))
    
    @property
    def factor(self):
        ## return self.cam_unit / (self.SAAPT.dia /100)
        if self.SAAPT.sel:
            return self.cam_unit / (self.SAAPT.dia /100)
        
        dia = self.para.conf_table[1] # para:cl3dia
        beta = self.config['beta'] # saadia:100
        return self.cam_unit / (dia / beta)
    
    def get_spot_beam(self):
        i = self.imaging.Selector
        k = self.conf_key
        xo = self.config[k][i,0]
        ys = self.config[k][i,1] / self.factor
        return xo, ys
    
    def set_spot_beam(self, v):
        i = self.imaging.Selector
        xo, ys = v
        if xo: self.config[self.conf_key][i,0] = int(xo)
        if ys: self.config[self.conf_key][i,1] = abs(ys) * self.factor
    
    def cal(self):
        with self.thread:
            if self.apt_selection('SAAPT'):
                with self.save_excursion(mmode='DIFF'):
                    self.para.focus()
                    self.delay()
                    self.pla.align()
                    self.focus(0.1)
                    ret = SpotInterface.cal(self)
                    if ret is False:
                        with self.save_excursion():
                            if not self.find_beam(): # => beam lost
                                return
                        ret = SpotInterface.cal(self) # try once more, FAIL skips
                    return ret
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAAPT=1):
                with self.save_excursion(spot=0, alpha=2, mmode='DIFF', mag=2000):
                    return all([None is not self.cal()
                        for cam in self.for_each_mag()])

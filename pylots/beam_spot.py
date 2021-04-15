#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import SpotInterface, TEM


class Plugin(SpotInterface, Layer):
    """Plugin of focus adjustment
    Calibrate spot-beam-focus [spot/alpha] and measure the Brightness sensitivity
    """
    menu = None #"Maintenance/&1-Focus"
    category = "1-Focus Maintenance"
    caption = "Spot"
    conf_key = ('cl3spot', 'cl3sens',)
    index = TEM.CL3
    
    @property
    def factor(self):
        return self.mag_unit / (self.CLA.dia /100)
    
    def get_spot_beam(self):
        i = self.illumination.Selector
        j, k = self.conf_key
        xo = self.config[j][i]
        ys = self.config[k][i] / self.factor
        return xo, ys
    
    def set_spot_beam(self, v):
        i = self.illumination.Selector
        j, k = self.conf_key
        xo, ys = v
        if xo: self.config[j][i] = int(xo)
        if ys: self.config[k][i] = abs(ys) * self.factor
    
    def certify(self):
        h, w = self.camera.shape
        self.focus(0.25)
        d1,_p,_q = self.detect_beam_diameter()
        return (0.20 < d1/h < 0.30)
    
    def cal(self):
        with self.thread:
            if self.apt_selection('CLA') and self.apt_selection('SAA', 0):
                with self.save_excursion(mmode='MAG'):
                    self.focus(0.1)
                    ret = SpotInterface.cal(self)
                    if ret is False:
                        with self.save_excursion():
                            if not self.find_beam(): # => beam lost
                                return
                        ret = SpotInterface.cal(self) # try once more, FAIL skips
                    return ret and self.certify()
    
    def execute(self):
        with self.thread:
            with self.save_restriction(SAA=0):
                with self.save_excursion(mmode='MAG'):
                    return all([None is not self.cal()
                        for s in self.for_each_spot()
                        for a in self.for_each_alpha()])
        return True

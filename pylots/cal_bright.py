#! python
# -*- coding: utf-8 -*-
from mwx.graphman import Layer
from pylots.temixins import TemInterface
import wxpyJemacs as wxpj


class Plugin(TemInterface, Layer):
    """Plugin of measurement
    Calibrate brightness for each spot
    """
    menu = None #"Maintenance/&Measure"
    category = "Measurement"
    caption = "Brightness"
    conf_key = 'brightness'
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    cla = property(lambda self: self.parent.require('align2_clapt'))
    
    def Init(self):
        self.layout("Manual calibration", (
            wxpj.Button(self, "Cal", lambda v: self.thread.Start(self.cal), icon='cal'),
            wxpj.Button(self, "Save", lambda v: self.config.save(self.conf_key), icon='save'),
            wxpj.Button(self, "Load", lambda v: self.config.load(self.conf_key), icon='proc'),
            ),
            row=3, show=1,
        )
    
    def cal(self):
        with self.thread:
            if self.aptsel(CLA=True, SAA=0):
                with self.save_excursion(mmode='MAG'):
                    self.spot.focus(0.5)
                    self.delay(2)
                    el, p, q = self.detect_ellipse()
                    if el:
                        ra, rb = el[1]
                        rho = p * ra * rb / self.CLA.dia**2 # counts/s/um^2
                        j = self.illumination.Spot
                        self.config[self.conf_key][j] = rho
                        print("Spot={}, {:g} counts/s/um^2".format(j, rho))
                        return True
    
    def execute(self):
        with self.thread:
            with self.save_restriction(CLA=self.default_clapt, SAA=0): # CLA:100um
                with self.save_excursion(mmode='MAG'):
                    self.spot.focus()
                    self.shift.align()
                    self.cla.align()
                    self.delay(2)
                with self.save_excursion(mmode='MAG'):
                    return all([self.cal()
                        for s in self.for_each_spot()])

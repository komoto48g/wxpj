#! python
# -*- coding: utf-8 -*-
import numpy as np
from numpy import pi
from mwx.graphman import Layer
from pylots.temixins import TemInterface
import wxpyJemacs as wxpj


class Plugin(TemInterface, Layer):
    """Plugin of measurement
    Calibrate angle for each spot:alpha
    """
    menu = None #"Maintenance/&Measure"
    category = "Measurement"
    caption = "Alpha"
    conf_key = 'alpha'
    
    diffspot = property(lambda self: self.parent.require('beam_spot_diff'))
    spot = property(lambda self: self.parent.require('beam_spot'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    pla = property(lambda self: self.parent.require('align_pla'))
    cla = property(lambda self: self.parent.require('align2_clapt'))
    
    def Init(self):
        self.layout("Manual calibration", (
            wxpj.Button(self, "Cal", lambda v: self.thread.Start(self.cal), icon='cal'),
            wxpj.Button(self, "Save", lambda v: self.config.save(self.conf_key), icon='save'),
            wxpj.Button(self, "Load", lambda v: self.config.load(self.conf_key), icon='proc'),
            ),
            row=3, show=1,
        )
    
    @property
    def conf_table(self):
        r = self.CLA.dia /100
        i = self.illumination.Selector
        return self.config[self.conf_key][i] * r
    
    def cal(self):
        with self.thread:
            if self.aptsel(CLA=True, SAA=0):
                with self.save_excursion(mmode='DIFF'):
                    self.spot.focus()
                    self.diffspot.focus()
                    self.pla.align()
                    self.delay(2)
                    ## d, p, q = self.detect_beam_diameter()
                    el, p, q = self.detect_ellipse()
                    if el:
                        ra, rb = el[1]
                        d = np.sqrt(ra * rb)    # avr. diameter [pix]
                        r = self.CLA.dia /100   # CLA:100um-based ratio
                        i = self.illumination.Selector
                        self.config[self.conf_key][i] = d * self.cam_unit / r #= 2α[mrad]
                        
                        v = p * (pi/4 * ra * rb)    # total counts in ellipse
                        S = pi/4 * self.CLA.dia**2  # size of aperture [um^2]
                        j = self.illumination.Spot
                        self.config['brightness'][j] = v / S
                        print("Spot={}, Alpha={}, v/S = {:g} /um^2".format(j, self.illumination.Alpha, v/S))
                        
                        return True
    
    def execute(self):
        with self.thread:
            with self.save_restriction(CLA=self.default_clapt, SAA=0): # CLA:100um
                with self.save_excursion(mmode='MAG'):
                    self.spot.focus()
                    self.shift.align()
                    self.cla.align()
                with self.save_excursion(mmode='DIFF', mag=2000):
                    return all([self.cal()
                        for a in self.for_each_alpha()
                        for s in self.for_each_spot()])

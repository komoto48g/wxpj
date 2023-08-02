#! python3
# -*- coding: utf-8 -*-
import wx
import cv2
import numpy as np
from numpy import pi,exp,conj

from jgdk import Layer, Button


def _valist(params):
    return list(p.value for p in params)


def calc_dist(u, D, d):
    return complex(D, d) * u * u * conj(u)


def calc_aspect(u, r, t):
    t *= pi/180
    return ((1+r) * u + (1-r) * conj(u) * exp(2j*t)) / 2


class Plugin(Layer):
    """Adistortion.
    """
    grid = property(lambda self: self.parent.require('ld_grid'))
    
    def Init(self):
        self.dist_params = self.grid.dist_params
        self.ratio_params = self.grid.ratio_params
        
        self.layout(self.dist_params, title="Distortion", cw=0, lw=24, tw=64)
        self.layout(self.ratio_params, title="XY Aspects", cw=0, lw=24, tw=64)
        
        self.layout((
            Button(self, "Execute", self.run),
            )
        )
    
    def run(self, frame=None):
        if not frame:
            frame = self.selected_view.frame
        
        if '*remap*' in self.output:
            del self.output["*remap*"] # to avoid MemoryError
        
        self.message("remap matrices...")
        src = frame.buffer
        h, w = src.shape
        nx = np.arange(w, dtype=np.float32)
        ny = np.arange(h, dtype=np.float32)
        x, y = frame.xyfrompixel(nx, ny)
        xo, yo = np.meshgrid(x, y, copy=False)
        zo = xo + 1j * yo
        del xo
        del yo
        zi = calc_aspect(zo, *_valist(self.ratio_params))\
             + calc_dist(zo, *_valist(self.dist_params))
        del zo
        
        self.message("\b @remap...")
        map_x, map_y = frame.xytopixel(zi.real, zi.imag, cast=False)
        self.output["*remap*"] = cv2.remap(src, map_x, map_y, cv2.INTER_CUBIC)
        
        self.message("\b ok")

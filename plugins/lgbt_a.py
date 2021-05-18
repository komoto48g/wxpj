#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import numpy as np
from mwx.controls import LParam
from mwx.graphman import Layer
import editor as edi


class Plugin(Layer):
    """Gaussian Blur and Threshold --adaptive
    """
    menu = "Plugins/&Basic Tools"
    category = "Basic Tools"
    
    def Init(self):
        self.params = (
            LParam("ksize", (1,99,2), 15),
            LParam("sigma", (0,100,1), 0),
            LParam("block", (1,255*3,2), 3),
            LParam("C", (0,255,1), 0),
        )
        self.cutoff_params = (
            LParam("hi", (0, 1 ,0.001), 0.01),
            LParam("lo", (0, 1, 0.001), 0.01)
        )
        btn = wx.Button(self, label="Execute", size=(66,22))
        btn.Bind(wx.EVT_BUTTON, lambda v: self.calc())
        
        self.layout("blur-threshold", self.params, type='vspin', cw=0, lw=48, tw=48)
        self.layout("cutoff [%]", self.cutoff_params,
                    row=1, show=0, type='vspin', cw=-1, lw=16, tw=44)
        self.layout(None, [btn], row=2)
        
    def calc(self, frame=None):
        if not frame:
            frame = self.selected_view.frame
        
        k, s, block, C = np.int32(self.params)
        hi, lo = np.float32(self.cutoff_params)
        src = frame.buffer
        buf = edi.imconv(src, hi, lo)
        if k > 1:
            buf = cv2.GaussianBlur(buf, (k,k), s)
        ## self.output.load(buf, name='*Gauss*', localunit=frame.unit)
        
        dst = cv2.adaptiveThreshold(buf, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, C)
        self.output.load(dst, name='*threshold*', localunit=frame.unit)
        return dst

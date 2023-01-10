#! python3
# -*- coding: utf-8 -*-
import wx
import cv2
import numpy as np
from jgdk import Layer, LParam
import editor as edi


def _valist(params):
    return list(p.value for p in params)


class Plugin(Layer):
    """Gaussian Blur and Threshold --adaptive
    """
    menukey = "Plugins/&Basic Tools/"
    category = "Basic Tools"
    
    def Init(self):
        self.params = (
            LParam("ksize", (1,99,2), 15),
            LParam("sigma", (0,100,1), 0),
            LParam("block", (1,255*3,2), 3),
            LParam("C", (0,255,1), 0),
        )
        self.hi = LParam("hi", (0, 1, 0.005), 0)
        self.lo = LParam("lo", (0, 1, 0.005), 0)
        
        btn = wx.Button(self, label="Execute", size=(66,22))
        btn.Bind(wx.EVT_BUTTON, lambda v: self.calc())
        
        self.layout(
            self.params, title="blur-threshold",
            type='vspin', cw=0, lw=40, tw=40
        )
        self.layout(
            (self.hi, self.lo), title="cutoff [%]",
            type='vspin', cw=-1, lw=16, tw=44
        )
        self.layout((btn,))
    
    def calc(self, frame=None):
        if not frame:
            frame = self.selected_view.frame
        
        k, s, block, C = _valist(self.params)
        src = frame.buffer
        buf = edi.imconv(src, self.hi.value, self.lo.value)
        if k > 1:
            buf = cv2.GaussianBlur(buf, (k,k), s)
        self.output.load(buf, "*Gauss*", localunit=frame.unit)
        
        dst = cv2.adaptiveThreshold(buf, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, C)
        self.output.load(dst, "*threshold*", localunit=frame.unit)
        return dst

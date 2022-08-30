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
    """Gaussian Blur and Threshold
    """
    menukey = "Plugins/&Basic Tools/"
    category = "Basic Tools"
    unloadable = False
    
    def Init(self):
        self.ksize = LParam("ksize", (1,99,2), 13)
        self.sigma = LParam("sigma", (0,100,1), 0)
        self.thresh = LParam("thresh", (0,255,1), 128)
        
        self.hi = LParam("hi", (0, 1, 0.005), 0)
        self.lo = LParam("lo", (0, 1, 0.005), 0)
        
        btn = wx.Button(self, label="+Bin", size=(40,22))
        btn.Bind(wx.EVT_BUTTON, lambda v: self.calc(otsu=wx.GetKeyState(wx.WXK_SHIFT)))
        btn.SetToolTip("Test blur and threshold;\n"
                        "S-Lbutton to estimate threshold using Otsu algorithm")
        
        self.layout(
            self.params, title="blur-threshold",
            type='vspin', cw=0, lw=40, tw=40
        )
        self.layout(
            (self.hi, self.lo), title="cutoff [%]",
            visible=1, type='vspin', cw=-1, lw=16, tw=44
        )
        self.layout((btn,))
    
    params = property(lambda self: (self.ksize, self.sigma, self.thresh))
    
    def calc(self, frame=None, otsu=0, invert=0):
        """Blur by Gaussian window and binarize
        otsu : True when using Otsu's algorithm
               float number (0 < r < 1) indicates the threshold percentile
      invert : invert dst image (for dark-field image)
        """
        if not frame:
            frame = self.selected_view.frame
        
        k, s, t = _valist(self.params)
        src = frame.buffer
        buf = edi.imconv(src, self.hi.value, self.lo.value)
        if k > 1:
            buf = cv2.GaussianBlur(buf, (k,k), s)
        self.output.load(buf, "*Gauss*", localunit=frame.unit)
        
        if 0 < otsu < 1:
            t = np.percentile(buf, 100 * otsu)
            t, dst = cv2.threshold(buf, t, 255, cv2.THRESH_BINARY)
        else:
            t, dst = cv2.threshold(buf, t, 255, cv2.THRESH_OTSU if otsu else cv2.THRESH_BINARY)
        self.thresh.value = t
        if invert:
            dst = 255 - dst
        self.output.load(dst, "*threshold*", localunit=frame.unit)
        return dst

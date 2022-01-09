#! python
# -*- coding: utf-8 -*-
import wx
import cv2
import numpy as np
from mwx.controls import LParam
from mwx.graphman import Layer
import editor as edi


class Plugin(Layer):
    """Gaussian Blur and Threshold
    """
    menu = "Plugins/&Basic Tools"
    category = "Basic Tools"
    unloadable = False
    
    def Init(self):
        self.params = (
            LParam("ksize", (1,99,2), 13),
            LParam("sigma", (0,100,1), 0),
            LParam("thresh", (0,255,1), 128),
        )
        self.cutoff_params = (
            LParam("hi", (0, 1 ,0.005), 0),
            LParam("lo", (0, 1, 0.005), 0)
        )
        btn = wx.Button(self, label="+Bin", size=(40,22))
        btn.Bind(wx.EVT_BUTTON, lambda v: self.calc(otsu=wx.GetKeyState(wx.WXK_SHIFT)))
        btn.SetToolTip("Test blur and threshold;\n"
                        "S-Lbutton to estimate threshold using Otsu algorithm")
        
        self.layout(
            self.params, title="blur-threshold",
            type='vspin', cw=0, lw=40, tw=40
        )
        ## self.layout(
        ##     self.cutoff_params, title="cutoff [%]",
        ##     type='vspin', cw=-1, lw=16, tw=44
        ## )
        self.layout((btn,))
    
    ksize = property(lambda self: self.params[0])
    sigma = property(lambda self: self.params[1])
    thresh = property(lambda self: self.params[2])
    
    def init_session(self, session):
        self.ksize.value = session.get('ksize')
        self.sigma.value = session.get('sigma')
        self.thresh.value = session.get('thresh')
    
    def save_session(self, session):
        session.update({
            'ksize': self.ksize.value,
            'sigma': self.sigma.value,
           'thresh': self.thresh.value,
        })
    
    def calc(self, frame=None, otsu=0, invert=0):
        """Blur by Gaussian window and binarize
        otsu : True when using Otsu's algorithm
               float number (0 < r < 1) indicates the threshold percentile
      invert : invert dst image (for dark-field image)
        """
        if not frame:
            frame = self.selected_view.frame
        
        k, s, t = np.int32(self.params)
        hi, lo = np.float32(self.cutoff_params)
        src = frame.buffer
        buf = edi.imconv(src, hi, lo) # truncates hi & lo cutoff percentile
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

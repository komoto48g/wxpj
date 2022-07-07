#! python3
# -*- coding: utf-8 -*-
"""template

Version: 2.0
Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
import cv2
from jgdk import Layer, Button


class Plugin(Layer):
    """Plugin template ver.2
    """
    menukey = "Plugins/&Template/&template ver.2"
    category = "Test"
    caption = "temp.2"
    
    lgbt = property(lambda self: self.parent.require('template'))
    
    def Init(self):
        self.layout((
            self.lgbt.ksize, # reference of the lgbt param. (to be shared)
            
            Button(self, "1. Gaussian",
                lambda v: self.run(), icon='help',
                tip="Gaussian blurring"),
            
            Button(self, "2. blur",
                lambda v: self.run_blur(), icon='help',
                tip="Check the standard blur"),
            
            Button(self, "3. median",
                lambda v: self.run_med(), icon='help',
                tip="Also check the Median blur"),
            
            Button(self, "Execute ALL",
                lambda v: self.run_all(), icon='->',
                tip="Press to run all blurs above\n"
                    "This example shows how to give plain instruction.")
            ),
            row=1, expand=0, show=0, type='vspin', cw=12, lw=36, tw=36,
        )
    
    def run(self):
        k = self.lgbt.ksize.value
        self.output["*Gauss*"] = cv2.GaussianBlur(self.graph.buffer, (k,k), 0.)
    
    def run_blur(self):
        k = self.lgbt.ksize.value
        self.output["*blur*"] = cv2.blur(self.graph.buffer, (k,k))
    
    def run_med(self):
        k = self.lgbt.ksize.value
        self.output["*median*"] = cv2.medianBlur(self.graph.buffer, k)
    
    def run_all(self):
        self.run()
        self.run_blur()
        self.run_med()


if __name__ == "__main__":
    import wx
    from jgdk import Frame
    app = wx.App()
    frm = Frame(None)
    frm.load_plug(Plugin, show=1, dock=4)
    frm.load_buffer(r"C:\usr\home\workspace\images\sample.bmp")
    frm.Show()
    app.MainLoop()

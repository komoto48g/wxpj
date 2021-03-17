#! python
# -*- coding: utf-8 -*-
"""template

Last updated: <2021-03-17 02:17:39 +0900>
     Version: 2.0
      Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
from wxpyJemacs import Layer
import wxpyJemacs as wxpj


class Plugin(Layer):
    """Plugin template ver.2
    """
    menu = "&Plugins/&Template"
    menustr = "&template ver.2"
    category = "Test"
    caption = "temp.2"
    dockable = True
    editable = True
    reloadable = True
    unloadable = True
    
    lgbt = property(lambda self: self.parent.require('template'))
    
    def Init(self):
        Layer.Init(self)
        
        self.layout(None, (
            self.lgbt.ksize, # reference of the lgbt param. (to be shared)
            
            wxpj.Button(self, "1. Gaussian", lambda v: self.run(), icon='help',
                tip="Gaussian blurring"),
            
            wxpj.Button(self, "2. blur", lambda v: self.run_blur(), icon='help',
                tip="Check the standard blur"),
            
            wxpj.Button(self, "3. median", lambda v: self.run_med(), icon='help',
                tip="Also check the Median blur"),
            
            wxpj.Button(self, "4. ALL",
                lambda v: (self.run(), self.run_blur(), self.run_med()), icon='phoenix',
                tip="Press to run all blurs above\n"
                    "This example shows how wxpj (c) plain wizard enables instruction\n"
                    "Check it out! have fun.")
            ),
            row=1, expand=0, show=0, type='vspin', cw=12, lw=36, tw=36,
        )
    
    def Activate(self, show):
        Layer.Activate(self, show)
    
    def Destroy(self):
        return Layer.Destroy(self)
    
    def run(self):
        k = self.lgbt.ksize.value
        self.output["*Gauss*"] = cv2.GaussianBlur(self.graph.buffer, (k,k), 0.)
    
    def run_blur(self):
        k = self.lgbt.ksize.value
        self.output["*blur*"] = cv2.blur(self.graph.buffer, (k,k))
    
    def run_med(self):
        k = self.lgbt.ksize.value
        self.output["*median*"] = cv2.medianBlur(self.graph.buffer, k)


if __name__ == "__main__":
    app = wx.App()
    frm = wxpj.Frame(None)
    frm.load_plug(__file__, show=1, docking=4)
    frm.load_buffer(u"C:/usr/home/workspace/images/sample.bmp")
    frm.Show()
    app.MainLoop()

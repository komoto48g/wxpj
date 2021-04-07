#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
from mwx.graphman import Layer
import wxpyJemacs as wxpj


class Plugin(Layer):
    """To evaluate distortion of Mag-Grid pattern,
  Run the following steps;
    1. lccf.run to find contours of circles
    2. ld_grid.run to calc the aspect ratio
    """
    menu = "&Plugins/&Pragma Tools"
    category = "Pragma Tools"
    caption = "Grid"
    
    lccf = property(lambda self: self.parent.require('lccf'))
    ld = property(lambda self: self.parent.require('ld_grid'))
    
    def Init(self):
        self.chkfit = wx.CheckBox(self, label="fit")
        self.chkfit.Value = True
        
        self.chk = wx.CheckBox(self, label="inv")
        
        self.layout(None, (
            wxpj.Button(self, "Run", lambda v: self.run()),
            self.chkfit,
            self.chk,
            wxpj.Button(self, "Setting", lambda v: self.show_setting()),
            ),
            row=3
        )
    
    def show_setting(self, force=0):
        b = force or not self.ld.IsShown()
        self.ld.Show(b)
        self.lccf.Show(1)
    
    def run(self):
        self.lccf.run(otsu=1, invert=self.chk.Value)
        if self.chkfit.Value:
            self.ld.thread.Start(self.ld.run)
            self.show_setting(1)

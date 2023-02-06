#! python3
# -*- coding: utf-8 -*-
import wx
from jgdk import Layer, Button


class Plugin(Layer):
    """Evaluate distortion of Diff-Ring pattern.
    
    Run the following steps;
    1. lcrf.run to find center of rings and the radial peaks
    2. ld_ring.run to calc the aspect ratio
    """
    menukey = "Plugins/&Pragma Tools/"
    category = "Pragma Tools"
    caption = "Ring"
    
    lcrf = property(lambda self: self.parent.require('lcrf'))
    ld = property(lambda self: self.parent.require('ld_ring'))
    
    def Init(self):
        self.chkfit = wx.CheckBox(self, label="fit")
        self.chkfit.Value = True
        
        self.layout((
                Button(self, "+Run",
                    lambda v: self.run(shift=wx.GetKeyState(wx.WXK_SHIFT))),
                self.chkfit,
                (),
                Button(self, "Setting", lambda v: self.show_setting()),
            ),
            row=3,
        )
    
    def show_setting(self, force=0):
        b = force or not self.ld.IsShown()
        self.ld.Show(b)
        self.lcrf.Show(1)
    
    def run(self, shift=0):
        self.lcrf.run(shift=shift)
        if self.chkfit.Value:
            self.ld.thread.Start(self.ld.run)
            self.show_setting(1)

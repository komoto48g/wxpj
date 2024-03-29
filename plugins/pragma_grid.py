#! python3
import wx

from jgdk import Layer, Button


class Plugin(Layer):
    """Evaluate distortion of Mag-Grid pattern.
    """
    menukey = "Plugins/&Pragma Tools/"
    category = "Pragma Tools"
    caption = "Grid"
    
    lccf = property(lambda self: self.parent.require('lccf'))
    ld = property(lambda self: self.parent.require('ld_grid'))
    
    def Init(self):
        self.chkfit = wx.CheckBox(self, label="fit")
        self.chkfit.Value = True
        
        self.chk = wx.CheckBox(self, label="inv")
        
        self.layout((
                Button(self, "Run", self.run),
                self.chkfit,
                self.chk,
                Button(self, "Setting", self.show_setting),
            ),
            row=3,
        )
    
    def show_setting(self, force=0):
        """Show the settings."""
        b = force or not self.ld.IsShown()
        self.ld.Show(b)
        self.lccf.Show(1)
    
    def run(self):
        """Run scripts."""
        self.lccf.run(otsu=True, invert=self.chk.Value)
        if self.chkfit.Value:
            self.ld.thread.Start(self.ld.run)
            self.show_setting(1)

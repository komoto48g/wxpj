#! python3
import wx

from jgdk import Layer, Button


class Plugin(Layer):
    """Evaluate distortion of Diff-Ring pattern.
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
                Button(self, "Run", self.run),
                self.chkfit,
                (),
                Button(self, "Setting", self.show_setting),
            ),
            row=3,
        )
    
    def show_setting(self, force=0):
        """Show the settings."""
        b = force or not self.ld.IsShown()
        self.ld.Show(b)
        self.lcrf.Show(1)
    
    def run(self):
        """Run scripts."""
        self.lcrf.run()
        if self.chkfit.Value:
            self.ld.thread.Start(self.ld.run)
            self.show_setting(1)

#! python3
from jgdk import Layer, Button


class Plugin(Layer):
    """Evaluate distortion of Diff-Ring pattern.
    """
    menukey = "Plugins/&Pragma Tools/"
    category = "Pragma Tools"
    caption = "Ring"
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    lcrf = property(lambda self: self.parent.require('lcrf'))
    ld = property(lambda self: self.parent.require('ld_ring'))
    
    def Init(self):
        self.layout((
                Button(self, "1. Mark", self.calmark, icon='help', size=(72,-1)),
                self.lcrf.rmin,
                
                Button(self, "2. Run", self.run, icon='help', size=(72,-1)),
                Button(self, "Setting", self.show_setting),
            ),
            title="Evaluate ring pattern", row=2,
            type='vspin', cw=-1, lw=0, tw=44,
        )
        self.lgbt.ksize.value = 13 # default blur window size
    
    def show_setting(self):
        """Show the settings."""
        self.lcrf.Show()
    
    def run(self):
        """Run the fitting procedure."""
        frame = self.graph.frame
        self.ld.thread.Start(self.ld.run, frame)
        self.ld.Show()
    
    def calmark(self, frame=None):
        """Feature detection.
        
        Set parameter: Minimum radius [%] of rings to be detected.
        """
        frame = self.graph.frame
        self.lcrf.run(frame)

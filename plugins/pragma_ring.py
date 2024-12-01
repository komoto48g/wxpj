#! python3
from wxpj import Layer, Button


class Plugin(Layer):
    """Evaluate distortion of Diff-Ring pattern.
    """
    menukey = "Plugins/&Pragma Tools/"
    category = "Pragma Tools"
    caption = "Ring"
    
    lcrf = property(lambda self: self.parent.require('lcrf'))
    ld = property(lambda self: self.parent.require('ld_ring'))
    
    def Init(self):
        self.layout((
                Button(self, "1. Mark", self.calmark, icon='help', size=(72,-1)),
                Button(self, "2. Run", self.execute, icon='help', size=(72,-1)),
            ),
            title="Evaluate ring pattern", row=1,
            type='vspin', cw=-1, lw=0, tw=44,
        )
        self.layout((
                self.lcrf.rmin,
                self.lcrf.rmax,
                Button(self, "Advanced settings", self.show_setting),
            ),
            title="Selection radii", cw=0, lw=40, tw=40
        )
    
    def show_setting(self):
        """Show the settings."""
        self.lcrf.Show()
    
    def execute(self):
        """Run the fitting procedure."""
        frame = self.graph.frame
        self.ld.thread.Start(self.ld.execute, frame)
        self.ld.Show()
    
    def calmark(self, frame=None):
        """Feature detection.
        
        Set parameter: Minimum radius [%] of rings to be detected.
        """
        frame = self.graph.frame
        self.lcrf.execute(frame)

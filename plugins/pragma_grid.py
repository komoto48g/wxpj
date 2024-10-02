#! python3
from wxpj import Layer, Button


class Plugin(Layer):
    """Evaluate distortion of Mag-Grid pattern.
    """
    menukey = "Plugins/&Pragma Tools/"
    category = "Pragma Tools"
    caption = "Grid"
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    lccf = property(lambda self: self.parent.require('lccf2'))
    ld = property(lambda self: self.parent.require('ld_grid'))
    
    def Init(self):
        self.layout((
                Button(self, "1. Mark", self.calmark, icon='help', size=(72,-1)),
                self.lccf.rmin,
                
                Button(self, "2. Run", self.execute, icon='help', size=(72,-1)),
                Button(self, "Setting", self.show_setting),
            ),
            title="Evaluate grid pattern", row=2,
            type='vspin', cw=-1, lw=0, tw=44,
        )
        self.lgbt.ksize.value = 13 # default blur window size
    
    def show_setting(self, force=0):
        """Show the settings."""
        self.lccf.Show()
    
    def execute(self):
        """Run the fitting procedure."""
        frame = self.graph.frame
        self.ld.thread.Start(self.ld.execute, frame)
        self.ld.Show()
    
    def calmark(self, frame=None):
        """Feature detection.
        
        Set parameter: Minimum radius [pix] of circles to be detected.
        """
        frame = self.graph.frame
        self.lccf.execute(frame, otsu=True)

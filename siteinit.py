#! python3
"""siteinit file
"""
import sys
import os
import numpy as np


def init_mainframe(self):
    """Program settings of mainframe
    """
    self.Editor = "C:/usr/home/bin/xyzzy/xyzzy.exe"
    
    np.set_printoptions(linewidth=256)
    
    for f in [
            r"C:\usr\home\workspace\tem13\wxpj-data",
            ]:
        f = os.path.normpath(f)
        if f not in sys.path:
            sys.path.append(f)
    
    ## Film/CCD [mm/pix]
    ## 0.042 mm/pix - FLASH @JEM-3300
    ## 0.365 mm/pix - LSCR @JEM-Z300FSC/CiCLE
    u = 0.365
    self.graph.unit = u
    self.output.unit = u
    
    ## Local cutoff tolerance score percentiles.
    ## self.graph.score_percentile = 0.01
    ## self.output.score_percentile = 0.01
    
    ## Local max image size (matplotlib/WXAgg) typically < 24e6 (bytes).
    ## self.graph.nbytes_threshold = 8e6
    ## self.output.nbytes_threshold = 8e6
    
    ## window layout
    self.histogram.modeline.Show()
    
    ## --------------------------------
    ## Global keymap of the main Frame 
    ## --------------------------------
    
    self.define_key('C-x o', self.load_session)
    self.define_key('C-x s', self.save_session)
    self.define_key('C-x S-s', self.save_session_as)
    
    ## @self.define_key('M-right', dir=1, doc="focus to next window")
    ## @self.define_key('M-left', dir=-1, doc="focus to prev window")
    ## def other_window(v, dir):
    ##     """Set focus to next/prev displayed window"""
    ##     ls = [w for w in self.graphic_windows if w.IsShownOnScreen()]
    ##     for j,w in enumerate(ls):
    ##         if w.canvas.HasFocus():
    ##             next = ls[(j+dir) % len(ls)]
    ##             return next.SetFocus()
    ##     else:
    ##         self.graph.SetFocus()
    
    @self.handler.bind('frame_cached')
    def cache(frame):
        frame.attributes.update(
            illumination = dict(self.notify.illumination.Info),
                 imaging = dict(self.notify.imaging.Info),
                   omega = dict(self.notify.omega.Info),
                     eos = dict(self.notify.eos.Info),
                     hts = dict(self.notify.hts.Info),
                    apts = dict(self.notify.apts.Info),
                   gonio = dict(self.notify.gonio.Info),
                  filter = dict(self.notify.efilter.Info),
                 modestr = self.notify.modestr, # joined substr
        )
        frame.name = ("{acq_datetime:%Y_%m%d_%H%M%S}-{modestr} "
                      ## "CLA={apts[CLA]} "
                      "TX={gonio[TX]:.1f}deg "
                      "slit={filter[slit_width]}eV " # slit or None [eV]
                      "bin{binning}-{exposure:g}s"
                      .format(
                        **frame.attributes)).replace('None', '-')

    @self.graph.handler.bind('region_drawn')
    def roi_average(frame):
        self.message("\b; avr={:g}".format(np.average(frame.roi)))

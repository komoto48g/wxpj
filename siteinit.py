#! python3
# -*- coding: utf-8 -*-
"""siteinit file
"""
import sys
import numpy as np


def init_mainframe(self):
    """Program settings of mainframe
    """
    self.Editor = "C:/usr/home/bin/xyzzy/xyzzy.exe"
    sys.path.append(r"C:\usr\home\workspace\tem13\gdk-aero")
    sys.path.append(r"C:\usr\home\workspace\tem13\wxpj-data")
    
    np.set_printoptions(linewidth=256)
    
    ## Film/CCD [mm/pix]
    ## 0.042 mm/pix - FLASH @JEM-3300
    ## 0.365 mm/pix - LSCR @JEM-Z300FSC
    self.graph.unit = 0.042
    self.output.unit = 0.042
    
    ## Local cutoff tolerance score percentiles.
    ## self.graph.score_percentile = 0.01
    ## self.output.score_percentile = 0.01
    
    ## Local max image size (matplotlib/WXAgg) typically < 24e6 (bytes).
    ## self.graph.nbytes_threshold = 8e6
    ## self.output.nbytes_threshold = 8e6
    
    ## window layout
    self.histogram.modeline.Show()
    
    ## --------------------------------
    ## Plugins
    ## --------------------------------
    
    ## global reference to output buffer
    import editor as edi
    edi.out = self.output
    
    self.ed = self.require('editor')
    self.su = self.require('startup')
    self.si = sys.modules.get(__name__)
    
    from plugins import lgbt, lcrf, lccf, lccf2
    self.load_plug(lgbt)
    self.load_plug(lcrf)
    self.load_plug(lccf)
    self.load_plug(lccf2)
    
    from plugins import ld_grid, ld_ring
    self.load_plug(ld_grid)
    self.load_plug(ld_ring)
    
    from plugins import ld_cgrid, ld_cring
    self.load_plug(ld_cgrid)
    self.load_plug(ld_cring)
    
    from plugins import lineprofile, viewframe, viewfft
    self.load_plug(lineprofile)
    self.load_plug(viewframe)
    self.load_plug(viewfft)
    
    from pyJeol import legacy
    legacy.cmdl.TIMEOUT = 1
    ## legacy.set_host('localhost', offline=0)
    try:
        self.notify.start()
        ## self.notify.handler.debug = 4
    except Exception as e:
        print("$(e) = {!r}".format((e)))
    
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
        frame.update_attributes(
            illumination = dict(self.notify.illumination.Info),
                 imaging = dict(self.notify.imaging.Info),
                   omega = dict(self.notify.omega.Info),
                     eos = dict(self.notify.eos.Info),
                      ht = dict(self.notify.hts.Info),
                     apt = dict(self.notify.apts.Info),
                   gonio = dict(self.notify.gonio.Info),
                  filter = dict(self.notify.efilter.Info),
                 modestr = self.notify.modestr, # joined substr
        )
        frame.name = "{acq_datetime:%Y_%m%d_%H%M%S}-{mode},"\
                     "slit={filter[slit_width]}eV,bin{binning}-{exposure:g}s".format(
                     mode=self.notify.modestr, **frame.attributes)

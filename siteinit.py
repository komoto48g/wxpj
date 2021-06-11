#! python
# -*- coding: utf-8 -*-
"""siteinit file of wxpj

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import sys
import os


def init_frame(self):
    """Program settings of pyJemacs <Frame>
    """
    self.Editor = "C:/usr/home/bin/xyzzy/xyzzy.exe"
    
    ## Film/CCD [mm/pixel]
    ## 0.0820 mm/pixel - Jenoptik
    ## 0.0428 mm/pixel - FLASH 1181
    ## 0.435 mm/pixel - LSCR Z300FSC
    self.graph.unit = self.output.unit = 0.0428
    
    ## Cutoff tolerance of the score at a given percentile
    self.graph.score_percentile = 0.01
    self.output.score_percentile = 0.01
    
    ## matplotlib wxagg backend
    ## to restrict imshow sizes max typically < 24e6 (bytes)
    self.graph.nbytes_threshold = 20e6
    self.output.nbytes_threshold = 20e6
    
    ## window layout
    self.histogram.modeline.Show()
    
    ## --------------------------------
    ## Load plugins
    ## --------------------------------
    rootdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(os.path.join(rootdir, "gdk-aero"))
    sys.path.append(os.path.join(rootdir, "gdk-data"))
    
    self.edi = self.require("editor")
    self.su = self.require('startup')
    
    from plugins import lgbt, lccf, lcrf, lccf2
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
    
    ## from pyJeol.legacy import cmdl, cntf
    ## cmdl.HOST = cntf.HOST = 'localhost'
    ## cmdl.OFFLINE = True
    ## cmdl.open()
    self.notify.start()
    
    ## --------------------------------
    ## global keymap
    ## --------------------------------
    
    self.define_key('C-x o', self.load_session)
    self.define_key('C-x s', self.save_session)
    self.define_key('C-x S-s', self.save_session_as)
    
    @self.define_key('M-right', dir=1, doc="focus to next window")
    @self.define_key('M-left', dir=-1, doc="focus to prev window")
    def other_window(v, dir):
        """Set focus to next/prev displayed window"""
        ls = [w for w in self.graphic_windows if w.IsShownOnScreen()]
        for j,w in enumerate(ls):
            if w.canvas.HasFocus():
                next = ls[(j+dir) % len(ls)]
                return next.SetFocus()
        else:
            self.graph.SetFocus()
    
    self.define_key('pageup', lambda v: self.selected_view.OnPageUp(v), doc="previous page")
    self.define_key('pagedown', lambda v: self.selected_view.OnPageDown(v), doc="next page")
    
    self.new_buffer_name = "{acq_datetime:%Y%m%d-%H%M%S}-{annotation}"
    
    @self.handler.bind('frame_cached')
    def cache(frame):
        frame.update_attributes(
            illumination = dict(self.notify.illumination.Info),
                 imaging = dict(self.notify.imaging.Info),
                   omega = dict(self.notify.omega.Info),
                     eos = dict(self.notify.eos.Info),
                      ht = dict(self.notify.hts.Info),
                     apt = dict(self.notify.Apts.Info),
                   gonio = dict(self.notify.gonio.Info),
                  filter = dict(self.notify.efilter.Info),
                 modestr = self.notify.modestr, # joined substr
        )
        ## frame.annotation = "{0},bin{binning}-{exposure}s".format(self.notify.modestr, **frame.attributes)
        
        frame.annotation = "{0},slit={filter[slit_width]}eV,bin{binning}-{exposure}s".format(
            self.notify.modestr, **frame.attributes)
        
        frame.name = self.new_buffer_name.format(**frame.attributes)


if __name__ == '__main__':
    import wx
    import debut
    import wxpyJemacs as wxpj
    
    app = wx.App()
    frm = wxpj.Frame(None)
    init_frame(frm)
    debut.init_spec(frm.inspector.shell)
    frm.load_buffer(u"C:/usr/home/workspace/images/sample.bmp")
    frm.load_buffer(u"C:/usr/home/workspace/images/sample_circ.bmp")
    frm.load_buffer(u"C:/usr/home/workspace/images/13 TEM1-3 MAG10k FLS1=2A00,B700.dm3")
    frm.Show()
    app.MainLoop()

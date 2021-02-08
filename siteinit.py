#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import sys
import scipy as np
import editor as edi
import debut

SHELLSTARTUP = """
from __future__ import division, print_function
from __future__ import unicode_literals
from __future__ import absolute_import
import sys
import os
import wx
import mwx
import cv2
import scipy as np
from scipy import pi
from scipy import ndimage as ndi
from numpy.fft import fft,ifft,fft2,ifft2,fftshift,fftfreq
from matplotlib import pyplot as plt
import siteinit as si
import editor as edi
edit = self.edit
graph = self.graph
output = self.output
"""

def init_frame(self):
    """Program settings of pyJemacs <Frame>
    """
    self.Editor = "C:/usr/home/bin/xyzzy/xyzzy.exe"
    
    ## Note: edi can be accessed by si.edi from self
    ## Here, methods art set as self localvars temporarily
    self.imshow = edi.imshow
    self.plot = edi.plot
    self.mplot = edi.mplot
    self.splot = edi.splot
    
    ## np.set_printoptions(linewidth=256) # default 75
    
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
    self.graph.nbytes_threshold = 4e6
    self.output.nbytes_threshold = 4e6
    
    ## window layout
    self.histogram.modeline.Show()
    
    ## --------------------------------
    ## Load plugins
    ## --------------------------------
    ## sys.path.append("C:/usr/home/workspace/PyJEM/PyJEM-1.0.2.1143")
    sys.path.append(r"C:/usr/home/workspace/tem13/site-axima")
    sys.path.append(r"C:/usr/home/workspace/tem13/site-axima-factory")
    
    self.load_plug(edi)
    
    import startup as su
    self.load_plug(su)
    
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
    
    if 0:
        from pyJeol.legacy import cmdl, cntf
        cmdl.HOST = cntf.HOST = 'localhost'
        cmdl.OFFLINE = True
    
    from pyJeol import legacy
    legacy.cmdl.open() # open request port
    self.notify.start() # open notify port
    
    ## --------------------------------
    ## global keymap
    ## --------------------------------
    self.define_key('C-x o', self.load_session)
    self.define_key('C-x s', self.save_session)
    self.define_key('C-x S-s', self.save_session_as)
    
    self.define_key('M-right', lambda v: other_window(v, 1), doc="focus to next window")
    self.define_key('M-left', lambda v: other_window(v,-1), doc="focus to prev window")
    
    def other_window(v, dir):
        """Set focus to next/prev displayed window"""
        ls = [w for w in self.graphic_windows if w.IsShownOnScreen()]
        for j,w in enumerate(ls):
            if w.canvas.HasFocus():
                next = ls[(j+dir) % len(ls)]
                return next.SetFocus()
        else:
            self.graph.SetFocus()
    
    self.define_key('pageup', lambda v: self.current_graph.OnPageUp(v), doc="previous page")
    self.define_key('pagedown', lambda v: self.current_graph.OnPageDown(v), doc="next page")
    
    ## --------------------------------
    ## Shell starutp
    ## --------------------------------
    self.inspector.shell.Execute(SHELLSTARTUP)
    debut.init_spec(self.inspector)



if __name__ == '__main__':
    import wx
    import wxpyJemacs as wxpj
    
    app = wx.App()
    frm = wxpj.Frame(None)
    init_frame(frm)
    
    frm.load_buffer(u"C:/usr/home/workspace/images/sample.bmp")
    frm.load_buffer(u"C:/usr/home/workspace/images/sample_circ.bmp")
    frm.load_buffer(u"C:/usr/home/workspace/images/13 TEM1-3 MAG10k FLS1=2A00,B700.dm3")
    
    frm.Show()
    app.MainLoop()

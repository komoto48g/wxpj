#! python
# -*- coding: utf-8 -*-
"""View of FFT/iFFT

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import numpy as np
from numpy.fft import fft2,ifft2,fftshift
## from scipy.fftpack import fft,ifft,fft2,ifft2 Memory Leak? <scipy 0.16.1>
## import cv2
from mwx.controls import Param
from mwx.graphman import Layer


class Plugin(Layer):
    """FFT view
    FFT src (graph.buffer) to dst (output.buffer)
    長方形のリージョンは歪んだパターンになるので要注意
    """
    menu = "Plugins/Functions"
    menustr = "&FFT view"
    caption = "FFT view"
    
    def Init(self):
        self.vchk = wx.CheckBox(self, label="semi-live")
        self.vchk.Bind(wx.EVT_CHECKBOX, lambda v: self.setlive(v.IsChecked()))
        
        self.pchk = wx.CheckBox(self, label="logical unit")
        ## self.pchk.Value = True
        
        self.pix = Param("mask", (2,4,8,16,32,64))
        
        self.layout("normal FFT", (
            self.vchk,
            self.pchk,
            ),
            row=1, expand=1, show=1, vspacing=4
        )
        self.layout("inverse FFT", (
            self.pix,
            ),
            row=1, expand=1, show=0, type=None, style='chkbox', tw=32, h=20
        )
        self.context = {
            None: {
                  'frame_shown' : [ None, self.refft ],
                 'region_drawn' : [ None, self.newfft ],
               'region_removed' : [ None, self.newfft ],
            }
        }
        self.parent.define_key('C-f', lambda v: self.newfft(self.graph.frame), doc="fft")
        self.parent.define_key('C-S-f', lambda v: self.newfft_inv(self.output.frame), doc="ifft")
    
    def Destroy(self):
        self.setlive(False)
        self.parent.define_key('C-f', None)
        self.parent.define_key('C-S-f', None)
        return Layer.Destroy(self)
    
    def setlive(self, p):
        if p:
            self.graph.handler.append(self.context)
        else:
            self.graph.handler.remove(self.context)
    
    def newfft(self, frame):
        """New fft of frame (grahph.frame) to output.frame"""
        if frame:
            self.message("FFT execution...")
            src = frame.roi
            dst = fftshift(fft2(src))
            h, w = src.shape
            
            self.message("\b Loading image...")
            self.output.load(dst, name="*fft of {}*".format(frame.name), localunit=1/w)
            if self.pchk.Value:
                self.output.frame.unit /= frame.unit
            self.message("\b done")
    
    def refft(self, frame):
        """Show or get new fft of frame (graph.frame) to output.frame
        ディメンジョンの再設定はしない (再設定したいときは一度全部消すこと)
        """
        if frame:
            name = "*fft of {}*".format(frame.name)
            if name not in self.output:
                return self.newfft(frame)
            self.output.select(name)
    
    def newfft_inv(self, frame):
        """New inverse fft of frame (output.frame) to graph.frame"""
        if frame:
            self.message("iFFT execution...")
            src = frame.roi
            h, w = src.shape
            if self.pix.check:
                y, x = np.ogrid[-h/2:h/2, -w/2:w/2]
                mask = np.hypot(y,x) > w/self.pix.value
                ## src = cv2.bitwise_and(src, src, mask.astype(np.uint8)) !! unsupported <comlex>
                frame.roi[mask] = 0
                frame.update_buffer()
                frame.parent.draw()
            dst = ifft2(fftshift(src))
            
            self.message("\b Loading image...")
            self.graph.load(dst.real,
                name="*ifft of {}*".format(frame.name), localunit=1/w/frame.unit)
            self.message("\b done")


if __name__ == "__main__":
    import glob
    from mwx.graphman import Frame
    
    app = wx.App()
    frm = Frame(None)
    frm.load_plug(__file__, show=1, docking=4)
    for path in glob.glob(r"C:/usr/home/workspace/images/*.bmp"):
        frm.load_buffer(path)
    frm.Show()
    app.MainLoop()

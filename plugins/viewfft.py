#! python
# -*- coding: utf-8 -*-
"""View of FFT/iFFT

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
import wx
import numpy as np
from numpy.fft import fft2,ifft2,fftshift
## from scipy.fftpack import fft,ifft,fft2,ifft2 Memory Leak? <scipy 0.16.1>
## import cv2
from mwx.controls import Param
from mwx.graphman import Layer


def fftresize(src, maxsize=None):
    """Resize src image to 2**n squared ROI"""
    h, w = src.shape
    if not maxsize:
        maxsize = w
    n = pow(2, int(np.log2(min(h, w, maxsize))) - 1)
    i, j = h//2, w//2
    return src[i-n:i+n,j-n:j+n]


class Plugin(Layer):
    """FFT view
    FFT src (graph.buffer) to dst (output.buffer)
    長方形のリージョンは歪んだパターンになるので要注意
    """
    menu = "Plugins/Extensions"
    menustr = "&FFT view"
    caption = "FFT view"
    
    def Init(self):
        self.pchk = wx.CheckBox(self, label="logical unit")
        self.pchk.Value = True
        
        self.pix = Param("mask", (2,4,8,16,32,64))
        
        self.layout(
            (self.pchk,), title="normal FFT",
            row=1, expand=1, show=1, vspacing=4
        )
        self.layout(
            (self.pix,), title="inverse FFT",
            row=1, expand=1, show=1, type=None, style='chkbox', tw=32
        )
        self.parent.define_key('C-f', self.newfft)
        self.parent.define_key('C-S-f', self.newifft)
    
    def Destroy(self):
        self.parent.define_key('C-f', None)
        self.parent.define_key('C-S-f', None)
        return Layer.Destroy(self)
    
    def newfft(self, evt):
        """New FFT of graph to output"""
        frame = self.graph.frame
        if frame:
            self.message("FFT execution...")
            src = fftresize(frame.roi)
            h, w = src.shape
            
            dst = fftshift(fft2(src))
            
            self.message("\b Loading image...")
            u = 1 / w
            if self.pchk.Value:
                u /= frame.unit
            self.output.load(dst, "*fft of {}*".format(frame.name),
                             localunit=u)
            self.message("\b done")
    
    def newifft(self, evt):
        """New inverse FFT of output to graph"""
        frame = self.output.frame
        if frame:
            self.message("iFFT execution...")
            src = frame.roi
            h, w = src.shape
            if self.pix.check:
                y, x = np.ogrid[-h/2:h/2, -w/2:w/2]
                mask = np.hypot(y,x) > w/self.pix.value
                ## src = cv2.bitwise_and(src, src, mask.astype(np.uint8)) !! unsupported <complex>
                frame.roi[mask] = 0
                frame.update_buffer()
                frame.parent.draw()
            dst = ifft2(fftshift(src))
            
            self.message("\b Loading image...")
            self.graph.load(dst.real, "*ifft of {}*".format(frame.name),
                            localunit=1/w/frame.unit)
            self.message("\b done")


if __name__ == "__main__":
    import glob
    from mwx.graphman import Frame
    
    app = wx.App()
    frm = Frame(None)
    frm.load_plug(__file__, show=1, dock=4)
    for path in glob.glob(r"C:/usr/home/workspace/images/*.bmp"):
        frm.load_buffer(path)
    frm.Show()
    app.MainLoop()

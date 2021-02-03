#! python
# -*- coding: shift-jis -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import scipy as np
from scipy import pi
from scipy import ndimage as ndi
from mwx import LParam
from mwx.graphman import Layer
import wxpyJemacs as wxpj


class Plugin(Layer):
    """Image process: rotation
    This script shows how to get data from graph
    --------------------------------------------
    The graph.frame has three arts called selector, markers, and region.
    Each one posts events when they are drawing, drawn, and removed by user.
    This script also shows how to use define_key (assign up-to-two stroke key).
    """
    menu = "&Plugins/&Demo"
    
    def Init(self):
        self.btn = wxpj.Button(self, "Rotate", self.rotate,
            tip="Try [C-x r] to execute this function instead of press button.")
        
        self.rotdeg = LParam("[deg]", (-180,180, 1), 0, doc="angles to rotate:ccw")
        
        self.layout(None, (
            self.btn,
            self.rotdeg,
            ),
            row=3, expand=0, type="vspin", lw=32, cw=12, tw=60
        )
        self.parent.define_key('C-x r', self.rotate)
        self.graph.handler.bind('line_draw', self.calc_rotdeg)
    
    def Destroy(self):
        self.graph.handler.unbind('line_draw', self.calc_rotdeg)
        self.parent.define_key('C-x r', None)
        return Layer.Destroy(self)
    
    def calc_rotdeg(self, frame):
        """Calc rotation angles of selector:line and display the value:negate"""
        x, y = frame.selector
        angle = np.arctan2(y[1]-y[0], x[1]-x[0]) * 180/pi
        self.rotdeg.value = -angle
    
    def rotate(self, evt):
        """Rotate image with given angles and load to output window"""
        src = self.graph.selected_buffer
        angle = self.rotdeg.value
        ## self.output["*warp*"] = ndi.rotate(src, angle) # ndi: another method of rotation
        h, w = src.shape
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, scale=1)
        self.output["*warp*"] = cv2.warpAffine(src, M, (w, h))


if __name__ == "__main__":
    app = wx.App()
    frm = wxpj.Frame(None)
    frm.load_plug("__debug__")
    frm.load_plug(__file__, show=1)
    frm.load_buffer(u"C:/usr/home/workspace/images/sample.bmp")
    frm.Show()
    app.MainLoop()

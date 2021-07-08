#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import numpy as np
from numpy import pi
## from scipy import ndimage as ndi
from mwx.controls import LParam
from mwx.graphman import Layer, Frame
import wxpyJemacs as wxpj


class Plugin(Layer):
    """Image processing: rotation
    
    This script shows how to get data from graph,
    and how to define event-action_and the keymap.
    """
    menu = "Plugins/&Demo"
    
    def Init(self):
        self.btn = wxpj.Button(self, "Rotate", self.rotate,
            tip="Try [C-x r] to execute this function instead of press button.")
        
        self.rotdeg = LParam("[deg]", (-180,180, 1), 0, tip="angles to rotate:ccw")
        
        self.layout(None, (
            self.btn,
            self.rotdeg,
            ),
            row=3, expand=0, type="vspin", lw=32, cw=12, tw=60
        )
        
        @self.handler.bind('pane_shown')
        def activate():
            self.graph.handler.bind('line_draw', self.calc_rotdeg)
        
        @self.handler.bind('pane_closed')
        def deactivate():
            self.graph.handler.unbind('line_draw', self.calc_rotdeg)
    
    def calc_rotdeg(self, frame):
        """Calc rotation angles of selector:line and display the value
        """
        if frame:
            x, y = frame.selector
            self.rotdeg.value = np.arctan2(y[1]-y[0], x[1]-x[0]) * 180/pi
    
    def rotate(self, evt):
        """Rotate image with given angles and load to output window
        """
        src = self.graph.buffer
        angle = -self.rotdeg.value
        h, w = src.shape
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, scale=1)
        dst = cv2.warpAffine(src, M, (w, h))
        ## dst = ndi.rotate(src, angle) # ndi: another rotation
        self.output["*warp*"] = dst


if __name__ == "__main__":
    app = wx.App()
    frm = Frame(None)
    frm.load_plug("__debug__")
    frm.load_plug(__file__, show=1)
    frm.load_buffer(u"C:/usr/home/workspace/images/sample.bmp")
    frm.Show()
    app.MainLoop()

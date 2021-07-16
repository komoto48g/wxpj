#! python
# -*- coding: utf-8 -*-
"""template
Version: 0.0
Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import mwx
import cv2
import wxpyJemacs as wxpj


class Plugin(wxpj.Layer):
    """Plugin template ver.1
    """
    menu = "Plugins/&Template"
    menustr = "&template ver.1"
    category = "Test"
    caption = "temp.1"
    dockable = True
    editable = True
    reloadable = True
    unloadable = True
    
    def Init(self):
        self.ksize = wxpj.LParam("ksize", (1,99,2), 13, tip="kernel window size")
        
        self.btn = wx.Button(self, label="Run", size=(-1,22))
        self.btn.Bind(wx.EVT_BUTTON, lambda v: self.run())
        
        self.layout("Gaussian blur", # subtitle of this layout group. otherwise None if no frame
            (self.ksize, self.btn,), # the list of objects to be stacked with the following style:
            row=1, expand=0, show=1, # + style of grouping. Note `row means the horizontal stack size
            type='vspin',            # + style of Param; slider[*], [hv]spin, and choice are available
            cw=-1, lw=36, tw=30      # + and *w indicates width of Param; [c]ontrol, [l]abel, [t]ext
        )
    
    def set_current_session(self, session):
        self.ksize.value = session.get('ksize')
    
    def get_current_session(self):
        return {
            'ksize': self.ksize.value,
        }
    
    def run(self):
        k = self.ksize.value
        src = self.graph.buffer
        dst = cv2.GaussianBlur(src, (k,k), 0.)
        self.output.load(dst, name='*gauss*')


if __name__ == "__main__":
    app = wx.App()
    frm = wxpj.Frame(None)
    frm.load_plug(__file__, show=1, docking=4)
    frm.load_buffer(u"C:/usr/home/workspace/images/sample.bmp")
    frm.Show()
    app.MainLoop()

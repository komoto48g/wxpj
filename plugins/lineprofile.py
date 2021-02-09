#! python
# -*- coding: utf-8 -*-
"""Line profile

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
from mwx import LineProfile
from mwx.graphman import Layer


class Plugin(Layer):
    """Line profile of the currently selected buffers
    """
    menu = "&File/&Extensions"
    menustr = "&Line profile\tAlt+l"
    caption = "Line profile"
    dockable = False
    unloadable = False
    
    def Init(self):
        self.plot = LineProfile(self, log=self.message, size=(300,200))
        self.layout(None, [self.plot], expand=2, border=0)
        self.Draw(1)
    
    def Destroy(self):
        self.plot.Destroy()
        return Layer.Destroy(self)
    
    def Draw(self, show=True):
        if show:
            for win in self.parent.graphic_windows:
                self.plot.attach(win)
            self.plot.linplot(self.parent.current_graph.frame)
        else:
            for win in self.parent.graphic_windows:
                self.plot.detach(win)
        return Layer.Draw(self, show)


if __name__ == "__main__":
    import wx
    import glob
    import wxpyJemacs as wxpj
    
    app = wx.App()
    frm = wxpj.Frame(None)
    frm.load_plug(__file__, show=1)
    for path in glob.glob(r"C:/usr/home/workspace/images/*.bmp"):
        frm.load_buffer(path)
    frm.Show()
    app.MainLoop()

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
        
        @self.handler.bind('pane_shown')
        def attach(*v):
            self.plot.attach(*self.parent.graphic_windows)
            self.plot.linplot(self.parent.selected_view.frame)
        
        @self.handler.bind('pane_removed')
        @self.handler.bind('pane_closed')
        @self.handler.bind('pane_hidden')
        def detach(*v):
            self.plot.detach(*self.parent.graphic_windows)


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

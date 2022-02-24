#! python
# -*- coding: utf-8 -*-
"""Line profile

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from mwx.graphman import Layer
from mwx.matplot2lg import LineProfile


class Plugin(Layer):
    """Line profile of the currently selected buffers
    """
    menu = "Plugins/Extensions"
    menustr = "&Line profile\tCtrl+l"
    caption = "Line profile"
    dockable = False
    unloadable = False
    
    def Init(self):
        self.plot = LineProfile(self, log=self.message, size=(300,200))
        
        self.layout((self.plot,), expand=2, border=0)
        
        @self.handler.bind('pane_shown')
        def activate(*v):
            self.plot.attach(*self.parent.graphic_windows)
            self.plot.linplot(self.parent.selected_view.frame)
        
        @self.handler.bind('pane_closed')
        def deactivate(*v):
            self.plot.detach(*self.parent.graphic_windows)


if __name__ == "__main__":
    import glob
    import wx
    from mwx.graphman import Frame
    
    app = wx.App()
    frm = Frame(None)
    frm.load_plug(__file__, show=1)
    for path in glob.glob(r"C:/usr/home/workspace/images/*.bmp"):
        frm.load_buffer(path)
    frm.Show()
    app.MainLoop()

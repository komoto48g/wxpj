#! python3
# -*- coding: utf-8 -*-
"""Startup utility.

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
import numpy as np 
import wx
from jgdk import Layer, Param, LParam, Button, Icon
from pyJeol.temisc import Environ


class Plugin(Layer):
    """Plugins of startup settings.
    """
    menukey = "File/Options/&Startup"
    category = "Option"
    unloadable = False
    
    em = property(lambda self: self.__em)
    em_std = property(lambda self: self.__em_std)
    
    def Init(self):
        self.accv_param = Param("Acc.Voltage", (100e3, 200e3, 300e3), 300e3,
                handler=self.set_htv,
                fmt='{:,g}'.format,
                tip="Acceleration voltage [V].")
        
        self.accv_param.reset() # -> call set_htv
        
        self.unit_param = LParam("unit/pix", (0,1,1e-4), self.graph.unit,
                handler=None,
                updater=self.set_unit,
                tip="Set/unset localunit to the selected frame.")
        
        self.layout((
                self.accv_param,
                self.unit_param,
            ),
            type='vspin', style='button', cw=-1, lw=66, tw=60,
        )
        self.layout((
            Button(self, "Apply ALL",
                lambda v: self.setup_all(), icon=Icon('v'),
                tip="Set globalunit to all frames."),
            ),
            row=2,
        )
        self.context = {
            None : {
                  "frame_shown" : [ None, self.on_unit_notify ],
                "frame_updated" : [ None, self.on_unit_notify ],
               "frame_selected" : [ None, self.on_unit_notify ],
            },
        }
        
        @self.handler.bind('page_shown')
        def activate(*v):
            for win in self.parent.graphic_windows:
                win.handler.append(self.context)
        
        @self.handler.bind('page_closed')
        def deactivate(*v):
            for win in self.parent.graphic_windows:
                win.handler.remove(self.context)
    
    def on_unit_notify(self, frame):
        if frame:
            self.unit_param.value = frame.unit
            self.unit_param.std_value = frame.parent.unit
    
    def set_htv(self, p):
        self.__em = Environ(p.value)
        self.__em_std = Environ(p.std_value)
    
    def set_unit(self, p):
        target = self.selected_view
        if target.frame:
            u = p.value
            if target.unit == u:
                del target.frame.unit # unset localunit
            elif target.frame.unit != u:
                target.frame.unit = u # set localunit
            target.draw()
    
    def setup_all(self):
        u = self.unit_param.value
        target = self.selected_view
        target.unit = self.unit_param.std_value = u
        target.draw()


if __name__ == "__main__":
    from jgdk import Frame
    
    app = wx.App()
    frm = Frame(None)
    frm.load_plug(__file__, show=1, dock=4)
    frm.load_buffer(u"C:/usr/home/workspace/images/sample_grid.tif")
    frm.load_buffer(u"C:/usr/home/workspace/images/sample_diff.tif")
    frm.Show()
    app.MainLoop()

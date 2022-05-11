#! python3
# -*- coding: utf-8 -*-
"""startup utility

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
import numpy as np 
import wx
from mwx.controls import Param, LParam, Button
from mwx.graphman import Layer, Frame
from pyJeol.temisc import Environ


class Plugin(Layer):
    """Plugins of startup settings
    """
    menu = "File/Options"
    menustr = "&startup"
    category = "Option"
    unloadable = False
    
    em = property(lambda self: self.__em)
    em_std = property(lambda self: self.__em_std)
    
    def Init(self):
        self.accv_param = Param("Acc.Voltage", (100e3, 200e3, 300e3), 300e3,
                handler=self.set_htv,
                fmt='{:,g}'.format,
                tip="Acceleration voltage [V]")
        
        self.accv_param.reset() # -> call set_htv
        
        self.unit_param = LParam("unit/pixel", (0,1,1e-4), self.graph.unit,
                updater=self.set_localunit,
                tip="Set localunit to the selected frame")
        
        self.cuts_param = LParam("cutoff [%]", (0,1,1e-2), self.graph.score_percentile,
                updater=self.set_cutoff,
                tip="Set cutoff score percentiles of the current frame\n"
                    "to cut the upper/lower limits given by the tolerances[%]")
        
        self.layout((
                self.accv_param,
                self.unit_param,
                self.cuts_param,
            ),
            type='vspin', style='button', lw=66, tw=60, cw=-1
        )
        self.layout((
            Button(self, "Apply ALL",
                lambda v: self.setup_all(), icon='v',
                tip="Set globalunit and cutoff conditions to all frames"),
            
            Button(self, "Remove",
                lambda v: self.del_localunit(), icon='x',
                tip="Remove localunit"),
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
        
        @self.handler.bind('pane_shown')
        def activate(*v):
            for win in self.parent.graphic_windows:
                win.handler.append(self.context)
        
        @self.handler.bind('pane_closed')
        def deactivate(*v):
            for win in self.parent.graphic_windows:
                win.handler.remove(self.context)
        
        wx.CallAfter(self.setup_all)
    
    def on_unit_notify(self, frame):
        if frame:
            self.unit_param.value = frame.unit
            self.unit_param.std_value = frame.parent.unit
    
    def set_htv(self, p):
        self.__em = Environ(p.value)
        self.__em_std = Environ(p.std_value)
    
    def set_localunit(self, p):
        target = self.selected_view
        if target.frame:
            target.frame.unit = self.unit_param.value
            target.draw()
    
    def del_localunit(self):
        target = self.selected_view
        if target.frame:
            target.frame.unit = None
    
    def set_cutoff(self, p):
        target = self.selected_view
        target.score_percentile = self.cuts_param.value
        if target.frame:
            target.frame.update_buffer()
            target.draw()
    
    def setup_all(self):
        cuts = self.cuts_param.value
        unit = self.unit_param.value
        self.unit_param.std_value = unit
        
        target = self.selected_view
        target.score_percentile = cuts
        if unit is not np.nan:
            target.unit = unit # reset globalunit (localunits remain, however)
        for frame in target.all_frames:
            if unit is np.nan:
                frame.unit = None # remove localunits if none
            frame.update_buffer() # update buffer cuts of floor/ceiling
        target.draw()


if __name__ == '__main__':
    app = wx.App()
    frm = Frame(None)
    frm.load_plug(__file__, show=1, dock=4)
    frm.load_buffer(u"C:/usr/home/workspace/images/sample_grid.tif")
    frm.load_buffer(u"C:/usr/home/workspace/images/sample_diff.tif")
    frm.Show()
    app.MainLoop()

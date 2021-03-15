#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import numpy as np 
import wx
from mwx import Param
from mwx import LParam
from mwx.graphman import Layer
import wxpyJemacs as wxpj


class Plugin(Layer):
    """Plugins of startup settings
    """
    menu = "&File/&Options"
    menustr = "&startup\tAlt+s"
    category = "Option"
    
    def Init(self):
        self.accv_param = Param("Acc.Voltage", (100e3, 200e3, 300e3), 300e3, dtype=int,
            handler=self.set_htv,
                doc="Acceleration voltage [V]")
        
        self.unit_param = LParam("unit/pixel", (0,1,1e-4), self.graph.unit,
            updater=self.set_localunit,
                doc="Set localunit to the selected frame")
        
        self.cuts_param = LParam("cutoff [%]", (0,1,1e-2), self.graph.score_percentile,
            updater=self.set_cutoff,
                doc="Set cutoff score percentiles of the current frame\n"
                    "to cut the upper/lower limits given by the tolerances[%]")
        
        self.layout(None, (
            self.accv_param,
            self.unit_param,
            self.cuts_param,
            (),
            wxpj.Button(self, "Apply ALL",
                lambda v: self.setup_all(), icon='v',
                    tip="Set globalunit and cutoff conditions to all frames"),
            ),
            row=1, expand=0, type='vspin', style='btn', lw=66, tw=60, cw=-1
        )
        
        for win in self.parent.graphic_windows:
            win.handler.bind("frame_shown", self.on_unit_notify)
            win.handler.bind("canvas_focus_set", self.on_unit_notify)
    
    def Destroy(self):
        for win in self.parent.graphic_windows:
            win.handler.unbind("frame_shown", self.on_unit_notify)
            win.handler.unbind("canvas_focus_set", self.on_unit_notify)
        return Layer.Destroy(self)
    
    def set_current_session(self, session):
        self.accv_param.value = session.get('accv')
        self.unit_param.std_value = session.get('unit')
        self.cuts_param.value = session.get('cuts')
        self.setup_all()
        self.set_htv(self.accv_param)
    
    def get_current_session(self):
        return {
            'accv': self.accv_param.value,
            'unit': self.unit_param.std_value,
            'cuts': self.cuts_param.value,
        }
    
    def on_unit_notify(self, frame):
        if frame:
            self.unit_param.value = frame.unit
            self.unit_param.std_value = frame.parent.unit
    
    def set_htv(self, p):
        self.parent.env.__init__(p.value)
    
    def set_localunit(self, p):
        target = self.selected_view
        if target.frame:
            target.frame.unit = self.unit_param.value
            target.draw()
    
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
        
        for target in self.parent.graphic_windows:
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
    frm = wxpj.Frame(None)
    frm.load_plug(__file__, show=1, docking=4)
    frm.load_buffer(u"C:/usr/home/workspace/images/sample_grid.tif")
    frm.load_buffer(u"C:/usr/home/workspace/images/sample_diff.tif")
    frm.Show()
    app.MainLoop()

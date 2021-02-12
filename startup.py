#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
from mwx import Param
from mwx import LParam
from wxpyJemacs import Layer
import wxpyJemacs as wxpj


class Plugin(Layer):
    """Plugins of startup settings
    """
    menu = "&File/&Options"
    menustr = "&startup\tAlt+s"
    category = "Option"
    
    def Init(self):
        self.accv_param = Param("Acc.Voltage", (100e3, 200e3, 300e3), 300e3,
            handler=self.set_htv,
                doc="Acceleration voltage [V]")
        
        self.unit_param = LParam("unit/pixel", (0,1,1e-4), self.graph.unit,
            updater=self.setup_unit,
                doc="Set cutoff score percentiles of the current frame\n"
                    "to cut the upper/lower limits given by the tolerances[%]")
        
        self.cuts_param = LParam("cutoff [%]", (0,1,1e-2), self.graph.score_percentile,
            updater=self.setup_cutoff,
                doc="Set cutoff score percentiles of the current frame\n"
                    "to cut the upper/lower limits given by the tolerances[%]")
        
        self.layout(None, (
            self.accv_param,
            self.unit_param,
            self.cuts_param,
            (),
            wxpj.Button(self, "Apply",
                lambda v: self.setup_all(), icon='v',
                    tip="Apply conditions to all stack frames"
                        "\n except for those who have localunit and localcuts"),
            ),
            row=1, expand=0, type='vspin', style='btn', lw=66, tw=60, cw=-1
        )
        self.graph.handler.bind("frame_shown", self.on_unit_notify)
        ## self.graph.handler.bind("frame_updated", self.on_unit_notify)
    
    def Destroy(self):
        self.graph.handler.unbind("frame_shown", self.on_unit_notify)
        ## self.graph.handler.unbind("frame_updated", self.on_unit_notify)
        return Layer.Destroy(self)
    
    def set_current_session(self, session):
        self.reset_params((
            session.get('accv'),
            session.get('unit'),
            session.get('cuts'),
        ))
        self.setup_all()
    
    def get_current_session(self):
        return {
            'accv': self.accv_param.value,
            'unit': self.unit_param.value,
            'cuts': self.cuts_param.value,
        }
    
    def on_unit_notify(self, frame):
        self.unit_param.value = frame.unit
        self.unit_param.std_value = frame.parent.unit
    
    def setup_unit(self, p):
        for target in (self.graph, self.output):
            frame = target.frame
            if frame:
                frame.unit = self.unit_param.value # make localunit
                target.draw()
                self.unit_param.value = frame.unit
    
    def setup_cutoff(self, p):
        for target in (self.graph, self.output):
            target.score_percentile = self.cuts_param.value # make localvar
            frame = target.frame
            if frame:
                frame.update_buffer()
                target.draw()
    
    def setup_all(self):
        for target in (self.graph, self.output):
            target.score_percentile = self.cuts_param.value # make localvar
            target.unit = self.unit_param.value # reset globalunit (localunits will ramain)
            for frame in target.all_frames:
                frame.update_buffer() # update buffer cuts of floor/ceiling
            target.draw()
    
    def set_htv(self, p):
        self.parent.environ.__init__(p.value)


if __name__ == '__main__':
    app = wx.App()
    frm = wxpj.Frame(None)
    frm.load_plug(__file__, show=1, docking=4)
    frm.load_buffer(u"C:/usr/home/workspace/images/sample_grid.tif")
    frm.load_buffer(u"C:/usr/home/workspace/images/sample_diff.tif")
    frm.Show()
    app.MainLoop()

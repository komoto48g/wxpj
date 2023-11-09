#! python3
"""Startup utility.

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
import numpy as np

from jgdk import Layer, Graph, Param, LParam, Button, Icon
from pyJeol.temisc import Environ


class Plugin(Layer):
    """Plugins of startup settings.
    """
    menukey = "File/Options/&Startup\tAlt-s"
    category = "Option"
    unloadable = False
    
    em = property(lambda self: self.__em)
    em_std = property(lambda self: self.__em_std)
    
    def Init(self):
        self.accv_param = Param("Acc.Voltage", (10e3, 100e3, 200e3, 300e3), 300e3,
                handler=self.set_htv)
        
        ## self.accv_param.reset() # -> call set_htv
        self.set_htv(self.accv_param)
        
        self.unit_param = LParam("unit/pix", (0,1,1e-4), self.graph.unit,
                updater=self.set_unit)
        
        self.cuts_param = LParam("cutoff [%]", (0,1,1e-2), Graph.score_percentile,
                handler=self.set_cutoff)
        
        self.threshold_param = LParam("image [Mb]", (1,24,1), Graph.nbytes_threshold/1e6,
                handler=self.set_nbytes)
        
        self.layout((
                self.accv_param,
                self.unit_param,
                self.cuts_param,
                self.threshold_param,
            ),
            type='vspin', style='button', cw=-1, lw=66, tw=60,
        )
        self.layout((
            Button(self, "Apply ALL",
                   self.setup_all, icon=Icon('v')),
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
        """Acceleration voltage [V]."""
        self.__em = Environ(p.value)
        self.__em_std = Environ(p.std_value)
    
    def set_unit(self, p):
        """Set the localunit to the selected frame."""
        view = self.selected_view
        if view.frame:
            u = p.value
            if view.unit == u:
                view.frame.unit = None  # del localunit
            elif view.frame.unit != u:
                view.frame.unit = u     # set localunit
    
    def set_cutoff(self, p):
        """Set cutoff score percentiles of a frame.
        Upper/lower limits given by the tolerances[%].
        Press [f5] to update_buffer.
        """
        Graph.score_percentile = self.cuts_param.value
    
    def set_nbytes(self, p):
        """Set the max bytes for the image in a frame.
        Press [f5] to update_buffer.
        """
        Graph.nbytes_threshold = self.threshold_param.value * 1e6
    
    def setup_all(self):
        """Set globalunit to all frames."""
        u = self.unit_param.value
        view = self.selected_view
        view.unit = self.unit_param.std_value = u

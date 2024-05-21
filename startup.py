#! python3
"""Startup utility.
"""
from jgdk import Layer, Param, LParam
from pyJeol import Environ


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
        
        self.gu_param = LParam("global unit/pix", (0,1,1e-4), self.graph.unit,
                                updater=self.set_unit)
        
        self.lu_param = LParam("local unit/pix", (0,1,1e-4),
                                updater=self.set_unit)
        
        self.layout((
                self.accv_param,
                self.gu_param,
                self.lu_param,
            ),
            type='vspin', style='button', cw=-1, lw=80, tw=60,
        )
        self.context = {
            None : {
                  "frame_shown" : [ None, self.on_unit_notify ],
                "frame_updated" : [ None, self.on_unit_notify ],
               "frame_selected" : [ None, self.on_unit_notify ],
            },
        }
        for win in self.parent.graphic_windows:
            win.handler.append(self.context)
    
    def Destroy(self):
        for win in self.parent.graphic_windows:
            win.handler.remove(self.context)
        return Layer.Destroy(self)
    
    def load_session(self, session):
        self.accv_param.value = session['accv']
        self.gu_param.value = session['unit']
        self.graph.unit = session['unit']
    
    def save_session(self, session):
        session['accv'] = self.accv_param.value
        session['unit'] = self.gu_param.value
    
    def on_unit_notify(self, frame):
        if frame:
            self.gu_param.value = frame.parent.unit
            self.lu_param.value = frame.localunit
    
    def set_htv(self, p):
        """Acceleration voltage [V]."""
        self.__em = Environ(p.value)
        self.__em_std = Environ(p.std_value)
    
    def set_unit(self, p):
        """Set global/local unit to the selected frame."""
        if p is self.gu_param:
            self.selected_view.unit = p.value
        else:
            frame = self.selected_view.frame
            if frame:
                frame.unit = p.value

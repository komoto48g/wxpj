#! python
# -*- coding: shift-jis -*-
"""Editor's collection of TEM

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
from pylots import TemInterface
from wxpyJemacs import LParam
from wxpyJemacs import Layer
import wxpyJemacs as wxpj


class Plugin(TemInterface, Layer):
    """TEM Controller Interface complex
    """
    menu = "&File/&Options"
    menustr = "&TEM MAG Control"
    category = "Option"
    caption = "TEM"
    
    def Init(self):
        TemInterface.Init(self)
        
        def setf(**kwargs):
            ## Note: [setf = self.tem.__dict__.update] gives no effect on property.
            for k,v in kwargs.items():
                setattr(self.tem, k, v)
        
        self.cl_focus_param = LParam("Brightness", (0, 0xffff, 1), dtype=hex,
            handler=lambda p: setf(CL3=p.value))
        
        self.ol_focus_param = LParam("OL-Focus", (0, self.pj.OLHex.maxval, 1), dtype=hex,
            handler=lambda p: setf(OL=p.value),
            updater=lambda p: setf(OL=p.std_value),
                doc="Reset to the standard focus value (MAG mode only)")
        
        self.om_focus_param = LParam("OM-Focus", (0, 0xffff, 1), dtype=hex,
            handler=lambda p: setf(OM=p.value),
            updater=lambda p: setf(OM=p.std_value),
                doc="Reset to the standard focus value (LOWMAG mode only)")
        
        self.fl_focus_param = LParam("FL-Focus", (0, self.pj.FLHex.maxval, 1), dtype=hex,
            handler=lambda p: setf(FL=p.value),
            updater=lambda p: setf(FL=p.std_value),
                doc="Reset to the standard focus value")
        
        self.SetToolTip("Set the current value as the standard focus."
                        "\n To neutralize (return to the std-value),"
                        " press M[iddle]button on label or textctrl.")
        
        self.layout(None, (
            self.cl_focus_param,
            self.ol_focus_param,
            self.om_focus_param,
            self.fl_focus_param,
            ),
            row=1, type='spin', style='btn', lw=60, tw=50,
        )
        self.layout("Standard Focus", (
            wxpj.Button(self, "Brightness", size=(70,-1)),
            self.tem.foci['CL3'],
            (),
            wxpj.Button(self, "OL:Std/F", self.on_olstdf_update, size=(70,-1)),
            self.tem.foci['OLC'],
            self.tem.foci['OLF'],
            
            wxpj.Button(self, "OM:Std/F", self.on_olstdf_update, size=(70,-1)),
            self.tem.foci['OM1'],
            self.tem.foci['OM2'],
            
            wxpj.Button(self, "FL:Std/F", self.on_flstdf_update, size=(70,-1)),
            self.tem.foci['FLC'],
            self.tem.foci['FLF'],
            ),
            row=3, show=0, type=None, editable=0, lw=0, tw=40,
        )
        for name in "CL3 OLC OLF OM1 FLC FLF".split():
            self.tem.foci[name].bind(self.tem.foci.write) # bind -> WR:Enabled
        
        self.parent.notify.handler.bind("lens_notify", self.on_lens_notify)
        self.parent.notify.handler.bind("imaging_info", self.on_imaging_notify)
    
    def Destroy(self):
        for name in "CL3 OLC OLF OM1 FLC FLF".split():
            self.tem.foci[name].unbind(self.tem.foci.write)
        
        self.parent.notify.handler.unbind("lens_notify", self.on_lens_notify)
        self.parent.notify.handler.unbind("imaging_info", self.on_imaging_notify)
        return Layer.Destroy(self)
    
    def set_current_session(self, session):
        self.ol_focus_param.std_value = session.get('ol')
        self.fl_focus_param.std_value = session.get('fl')
    
    def get_current_session(self):
        return {
            'ol' : self.ol_focus_param.std_value,
            'fl' : self.fl_focus_param.std_value,
        }
    
    def on_olstdf_update(self, evt):
        self.ol_focus_param.std_value = self.tem.OL # save current value as std/f
    
    def on_flstdf_update(self, evt):
        self.fl_focus_param.std_value = self.tem.FL # save current value as std/f
    
    def on_lens_notify(self, argv):
        self.cl_focus_param.value = self.tem.CL3
        self.ol_focus_param.value = self.tem.OL
        self.fl_focus_param.value = self.tem.FL
    
    def on_imaging_notify(self, argv):
        lowmagp = argv['mode'] == 2
        for x in self.ol_focus_param.knobs:
            x.Enable(not lowmagp)
        for x in self.om_focus_param.knobs:
            x.Enable(lowmagp)

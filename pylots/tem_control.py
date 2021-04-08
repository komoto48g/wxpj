#! python
# -*- coding: utf-8 -*-
"""Editor's collection of TEM

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
from mwx import LParam
from mwx.graphman import Layer
from pylots.temixins import TemInterface
import wxpyJemacs as wxpj


class Plugin(TemInterface, Layer):
    """TEM Controller Interface complex
    """
    menu = "File/Options"
    menustr = "&TEM MAG Control"
    category = "Option"
    caption = "TEM"
    
    def Init(self):
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
                        "press Mbutton on label or textctrl.")
        
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
            wxpj.Button(self, "OL:Std/F", self.on_update_olstdf, size=(70,-1),
                tip="Set the current value as the standard focus of MAG mode"),
            self.tem.foci['OLC'],
            self.tem.foci['OLF'],
            
            wxpj.Button(self, "OM:Std/F", self.on_update_omstdf, size=(70,-1),
                tip="Set the current value as the standard focus of LOWMAG mode"),
            self.tem.foci['OM1'],
            self.tem.foci['OM2'],
            
            wxpj.Button(self, "FL:Std/F", self.on_update_flstdf, size=(70,-1)),
            self.tem.foci['FLC'],
            self.tem.foci['FLF'],
            ),
            row=3, show=0, type=None, editable=0, lw=0, tw=40,
        )
        self.context = {
            None : {
                  "lens_notify" : [ None, self.on_lens_notify ],
                 "imaging_info" : [ None, self.on_imaging_notify ],
            },
        }
    
    def Activate(self, show):
        foci = self.tem.foci
        if show:
            for name in "CL3 OLC OLF OM1 FLC FLF".split():
                ## foci[name].bind(foci.write) # WR:Enabled
                foci[name].flag = 1
            self.parent.notify.handler.append(self.context)
            try:
                self.on_lens_notify(self.tem.foci)
                self.on_imaging_notify(self.imaging.Info)
            except Exception as e:
                print("- tem controler failed to get TEM info; {}.".format(e))
        else:
            for name in "CL3 OLC OLF OM1 FLC FLF".split():
                ## foci[name].unbind(foci.write) # WR:Disabled
                foci[name].flag = 0
            self.parent.notify.handler.remove(self.context)
    
    def set_current_session(self, session):
        self.ol_focus_param.std_value = session.get('ol')
        self.om_focus_param.std_value = session.get('om')
        self.fl_focus_param.std_value = session.get('fl')
    
    def get_current_session(self):
        return {
            'ol' : self.ol_focus_param.std_value,
            'om' : self.om_focus_param.std_value,
            'fl' : self.fl_focus_param.std_value,
        }
    
    ## --------------------------------
    ## Standard Focus setting
    ## --------------------------------
    
    def on_update_olstdf(self, evt):
        if not self.lowmagp:
            self.ol_focus_param.std_value = self.tem.OL # save current value as std/f
    
    def on_update_omstdf(self, evt):
        if self.lowmagp:
            self.om_focus_param.std_value = self.tem.OM # save current value as std/f
    
    def on_update_flstdf(self, evt):
        self.fl_focus_param.std_value = self.tem.FL # save current value as std/f
    
    def on_lens_notify(self, argv):
        self.cl_focus_param.value = self.tem.CL3
        self.ol_focus_param.value = self.tem.OL
        self.om_focus_param.value = self.tem.OM
        self.fl_focus_param.value = self.tem.FL
    
    def on_imaging_notify(self, argv):
        lowmagp = (argv['mode'] == 2)
        for x in self.ol_focus_param.knobs:
            x.Enable(not lowmagp)
        for x in self.om_focus_param.knobs:
            x.Enable(lowmagp)

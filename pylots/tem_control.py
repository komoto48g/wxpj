#! python
# -*- coding: utf-8 -*-
"""Editor's collection of TEM

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
from mwx.controls import LParam
from mwx.graphman import Layer
from pyJeol import FLHex, OLHex
from pylots.temixins import TemInterface, TEM
import wxpyJemacs as wxpj


class Plugin(TemInterface, Layer):
    """TEM Controller Interface complex
    """
    menu = "Maintenance/Options"
    menustr = "&TEM MAG Control"
    category = "Option"
    caption = "TEM"
    
    def Init(self):
        def setf(**kwargs):
            for k,v in kwargs.items():
                ## setattr(self.tem, k, v)
                self.tem[k] = v
        
        self.cl_focus_param = LParam("Brightness", (0, 0xffff, 1), dtype=hex,
            handler=lambda p: setf(CL3=p.value))
        
        self.ol_focus_param = LParam("OL-Focus", (0, OLHex.maxval, 1), dtype=hex,
            handler=lambda p: setf(OL=p.value),
            updater=lambda p: setf(OL=p.std_value),
                doc="Reset to the standard focus value (MAG mode only)")
        
        self.om_focus_param = LParam("OM-Focus", (0, 0xffff, 1), dtype=hex,
            handler=lambda p: setf(OM=p.value),
            updater=lambda p: setf(OM=p.std_value),
                doc="Reset to the standard focus value (LOWMAG mode only)")
        
        self.fl_focus_param = LParam("FL-Focus", (0, FLHex.maxval, 1), dtype=hex,
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
        foci = TEM.foci
        self.layout("Standard Focus", (
            wxpj.Button(self, "Brightness", size=(70,-1)),
            foci['CL3'],
            (),
            wxpj.Button(self, "OL:Std/F", self.on_update_olstdf, size=(70,-1),
                tip="Set the current value as the standard focus of MAG mode"),
            foci['OLC'],
            foci['OLF'],
            
            wxpj.Button(self, "OM:Std/F", self.on_update_omstdf, size=(70,-1),
                tip="Set the current value as the standard focus of LOWMAG mode"),
            foci['OM1'],
            foci['OM2'],
            
            wxpj.Button(self, "FL:Std/F", self.on_update_flstdf, size=(70,-1)),
            foci['FLC'],
            foci['FLF'],
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
        foci = TEM.foci
        if show:
            for name in "CL3 OLC OLF OM1 FLC FLF".split():
                ## foci[name].bind(foci.write) # WR:Enabled
                foci[name].flag = 1
            self.parent.notify.handler.append(self.context)
            try:
                self.on_lens_notify(foci)
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
        foci = TEM.foci # ref only, no reading
        self.cl_focus_param.value = foci['CL3'].value
        self.om_focus_param.value = foci['OM1'].value
        self.ol_focus_param.value = OLHex(foci['OLC'].value, foci['OLF'].value).value
        self.fl_focus_param.value = FLHex(foci['FLC'].value, foci['FLF'].value).value
        
    
    def on_imaging_notify(self, argv):
        lowmagp = (argv['mode'] == 2)
        for x in self.ol_focus_param.knobs:
            x.Enable(not lowmagp)
        for x in self.om_focus_param.knobs:
            x.Enable(lowmagp)

#! python
# -*- coding: shift-jis -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import mwx
import scipy as np
from pprint import pprint
from mwx import Param, LParam
from mwx.graphman import Layer
import wxpyJemacs as wxpj


class Plugin(Layer):
    """catalogue of wxpj
    This script shows wxpj icons/widgets
    """
    menu = "&Plugins/&Demo"
    
    def Init(self):
        self.layout('Provided art images',
            (wxpj.Button(self, k, icon=k, size=(80,-1)) for k in sorted(wxpj.Icon.provided_arts)),
            row=6, show=0
        )
        self.layout('Custom images',
            (wxpj.Button(self, k, icon=k, size=(80,-1)) for k in sorted(wxpj.Icon.custom_images)),
            row=6, show=0
        )
        self.layout('Custom controls', (
            wxpj.Button(self, label="button",
                handler=lambda v: self.statusline(v.String, "pressed"),
                    tip="this is a button",
                    icon='v',
                    size=(100,-1)),
            
            wxpj.ToggleButton(self, label="toggle-button",
                handler=lambda v: self.statusline(v.IsChecked(), "checked"),
                    tip="this is a toggle-button",
                    icon=None,
                    size=(100,-1)),
            
            wx.StaticLine(self, size=(200,-1)), #----
            (),
            wxpj.TextCtrl(self, label="ctrl label",
                handler=lambda v: self.statusline(v.String, "enter"),
                updater=lambda v: self.statusline(v.value, "update"),
                    tip="this is a textctrl",
                    icon=wx.ART_NEW,
                    size=(200,-1)),
            (),
            wxpj.Choice(self, label="ctrl label",
                handler=lambda v: self.statusline(v.String, "selected"),
                updater=lambda v: self.statusline(v.value, "update"),
                choices=['1','2','3'],
                selection=1,
                    tip="this is a choice",
                    readonly=0,
                    icon=wx.ART_NEW,
                    size=(200,-1)),
            ),
            row=2, expand=0,
        )
        self.LP =  LParam('L', (-1,1,0.01), 0, handler=print,
            doc="Linear param"
                "\n In addition to direct key input to the textctrl,"
                "\n [up][down][wheelup][wheeldown] keys can be used,"
                "\n   with modifiers S- 2x, C- 4x, and M- 16x steps."
                "\n [Mbutton] resets to the std. value if it exists.")
        
        self.P = Param('U', (1,2,3, np.inf), handler=print)
        
        self.layout('Custom param controls', (
            self.LP,
            self.P,
            ),
            row=1, expand=1, show=1, 
            type='slider', lw=20, tw=40, cw=100, h=22,
        )
        self.statusline = mwx.StatusBar(self, style=wx.STB_DEFAULT_STYLE)
        self.layout(None, (
            wxpj.TextCtrl(self, '',
                handler=lambda v: self.statusline(v.String, "enter"),
                updater=lambda v: self.statusline(v.value, "update"),
                value = wxpj.TextCtrl.__doc__,
                    tip="this is a textctrl",
                    icon='v',
                    size=(210,100),
                    style=wx.TE_MULTILINE),
            
            self.statusline,
            ),
            row=1, expand=2, border=0,
        )
        self.text = self.groups[2][2] # How params in layout groups can be accessed
        self.choice = self.groups[2][3]


if __name__ == "__main__":
    app = wx.App()
    frm = wxpj.Frame(None)
    frm.load_plug("__debug__")
    frm.load_plug(__file__, show=1)
    frm.Show()
    app.MainLoop()

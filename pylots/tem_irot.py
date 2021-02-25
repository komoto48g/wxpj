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
    """Imaging rotation angles in Tem.IL_LENSES
    """
    menu = "&File/&Options"
    menustr = "&TEM ROT option"
    category = "Option"
    caption = "ROT"
    conf_key = "rotation"
    
    def Init(self):
        ## config: ctor 時点ではまだ未確定
        
        self.rot_mag = wxpj.TextCtrl(self, "MAG",
            updater=lambda v: self.update_stdrot(),
            ## value="{:8.2f}".format(self.config_tem_mag.data.get(self.conf_key)),
            size=(120,-1), readonly=1)
        
        self.rot_lowmag = wxpj.TextCtrl(self, "LMAG",
            updater=lambda v: self.update_stdrot(),
            ## value="{:8.2f}".format(self.config_tem_lowmag.data.get(self.conf_key)),
            size=(120,-1), readonly=1)
        
        self.layout("Standard Rotations", (
            self.rot_mag,
            self.rot_lowmag,
            ),
            row=1, show=1, type=None, editable=0, lw=0, tw=40,
        )
        self.layout("Manual calibration", (
            wxpj.Button(self, "Save", lambda v: self.config.save(self.conf_key), icon='save'),
            wxpj.Button(self, "Load", lambda v: self.config.load(self.conf_key), icon='proc'),
            ),
            row=3, show=1,
        )
    
    def calc_rot(self, tags):
        NI = 0
        for s in tags:
            lp = self.tem.foci[s]
            NI += lp.value / lp.max * self.Tem.LENS_NIMAX[s]
        return self.environ.j2deg * NI
    
    def update_stdrot(self):
        v = self.calc_rot(self.Tem.IL_LENSES)
        self.config[self.conf_key] = v
        
        if self.lowmagp:
            self.rot_lowmag.value = "{:8.2f}".format(v)
        else:
            self.rot_mag.value = "{:8.2f}".format(v)

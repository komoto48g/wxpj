#! python
# -*- coding: utf-8 -*-
"""Editor's collection of TEM

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import os
import wx
from mwx import LParam
from mwx.graphman import Layer
from pylots.temixins import TemInterface
import wxpyJemacs as wxpj
## import logging
## 
## logging ?? なぜか debshell のほうにパイプされるので使わない
## logging.basicConfig(
##     level = logging.WARNING,
##    format = '%(filename)s:%(lineno)d: [%(threadName)s] %(message)s: %(asctime)s',
## )

## setq = TemInterface.__dict__.update !! 'mappingproxy' object has no attribute 'update'
def setq(**kwargs):
    for k,v in kwargs.items():
        setattr(TemInterface, k, v)
    return v


class Plugin(TemInterface, Layer):
    """Plugins of optional TEM settings
    """
    menu = "&File/&Options"
    menustr = "&TEM Option"
    category = "Option"
    caption = "SYS"
    
    def Init(self):
        self.noise_param = LParam("noise_level/s", (0, 1e3, 5), self.noise_level,
            handler=lambda p: setq(noise_level=p.value),
                doc="Signal/Noize threshold [counts/pixel/s]"
                    "\n typ.value is 20/s (1/0.05s)")
        
        self.delay_param = LParam("delay time", (0, 1, 0.1), self.default_delay,
            handler=lambda p: setq(default_delay=p.value),
                doc="Delay time [s] before exposing till afterglow vanishes"
                    "\n typ.value is 0.5s")
        
        self.camera_selector = wxpj.Choice(self, "Camera",
            updater=lambda p: setq(camerasys=p.value),
            readonly=1, size=(162,-1), value=self.camerasys,
            choices=[
                'JeolCamera',
                'RigakuCamera'
            ],
            tip="Update camera system used by pylot modules.")
        
        self.config_selector = wxpj.TextCtrl(self, "Config",
            updater=lambda v: self.set_config(),
            value=os.path.basename(self.config.path) if self.config else '',
            readonly=1, size=(162,-1), icon='file')
        
        self.layout(None, (
            self.parent.su.accv_param,
            self.noise_param,
            self.delay_param,
            self.camera_selector,
            self.config_selector,
            ),
            row=1, show=1, type='vspin', style='btn', lw=80, tw=50, cw=-1
        )
    
    def set_current_session(self, session):
        noise = session.get('noise') or self.noise_level
        delay = session.get('delay') or self.default_delay
        camera = session.get('camera') or ''
        config = session.get('config') or ''
        
        TemInterface.noise_level = self.noise_param.value = noise
        TemInterface.default_delay = self.delay_param.value = delay
        TemInterface.camerasys = self.camera_selector.value = camera
        self.set_config(config)
    
    def get_current_session(self):
        return {
            'noise': self.noise_param.value,
            'delay': self.delay_param.value,
            'camera': self.camera_selector.value,
            'config': self.config.path if self.config else ''
       }
    
    def set_camerasys(self, v):
        if self.thread.is_active:
            self.pause("Please stop thread [C-g] before changing camearasys.")
            return
        TemInterface.camerasys = v.String
    
    wildcards = [
        "CONFIG (*.config)|*.config",
         "INI file (*.ini)|*.ini",
          "ALL files (*.*)|*.*",
    ]
    
    def set_config(self, path=None):
        if self.thread.is_active:
            self.pause("Please stop thread [C-g] before changing configuration.")
            return
        if path is None:
            with wx.FileDialog(self, wildcard='|'.join(self.wildcards)) as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                path = dlg.Path
        if not os.path.exists(path):
            wx.MessageBox("- No such file: {!r}".format(path),
                caption=self.__module__, style=wx.ICON_WARNING)
            return
        
        TemInterface.configure(path)
        if self.config:
            self.config_selector.Value = os.path.basename(self.config.path)
            self.config_selector.btn.SetToolTip(self.config.path)
            self.parent.su.accv_param.std_value = self.Tem.ACC_V  # 回転角 U* 補正のベース
            self.parent.su.accv_param.reset(self.config['acc_v']) # ターゲット加速電圧


if __name__ == "__main__":
    from plugins import JeolCamera, RigakuCamera
    
    app = wx.App()
    frm = wxpj.Frame(None)
    frm.load_plug(__file__, show=1)
    frm.load_plug(JeolCamera, show=0)
    frm.load_plug(RigakuCamera, show=0)
    frm.Show()
    app.MainLoop()

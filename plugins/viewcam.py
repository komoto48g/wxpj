#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
## import time
import wx
import cv2
import numpy as np
from mwx import Param, LParam
from mwx.graphman import Layer
import wxpyJemacs as wxpj
import editor as edi


class Plugin(Layer):
    """Plugins of camera viewer
    """
    menu = "&Camera"
    menustr = "Camera &viewer"
    
    camerasys = property(lambda self: self.camera_selector.value)
    cameraman = property(lambda self: self.parent.require(self.camerasys))
    
    def Init(self):
        self.viewer = Layer.Thread(self)
        
        self.button = wxpj.ToggleButton(self, "View camera", icon='cam',
            handler=lambda v: self.viewer.Start(self.run) if v.IsChecked() else self.viewer.Stop())
        
        self.rate_param = LParam('rate', (100,500,100), 500, doc="refresh speed [ms] (>= 100ms)")
        self.size_param = Param('size', (128,256,512,1024), 512, doc="resizing view window (<= 1k)")
        
        self.camera_selector = wxpj.Choice(self,
                choices=['JeolCamera', 'RigakuCamera'], readonly=1)
        
        self.layout(None, (
            self.button,
            ),
        )
        self.layout("Setting", (
            self.rate_param,
            self.size_param,
            self.camera_selector,
            ),
            row=1, show=0, type='vspin', lw=40, tw=40, cw=-1
        )
    
    def set_current_session(self, session):
        self.rate_param.value = session.get('rate')
        self.size_param.value = session.get('size')
        self.camera_selector.value = session.get('camera')
    
    def get_current_session(self):
        return {
            'rate': self.rate_param.value,
            'size': self.size_param.value,
          'camera': self.camera_selector.value,
        }
    
    def Destroy(self):
        if self.viewer.is_active:
            self.viewer.Stop()
        return Layer.Destroy(self)
    
    def run(self):
        try:
            title = self.__module__
            
            while self.viewer.is_active:
                src = edi.imconv(self.cameraman.capture())
                h, w = src.shape
                H = self.size_param.value
                W = H * w // h
                dst = cv2.resize(src, (W, H), interpolation=cv2.INTER_AREA)
                ## dst = cv2.cvtColor(dst, cv2.COLOR_GRAY2BGR)
                
                ## lines and circles with color:cyan #00c0c0
                ## c = (192,192,0)
                c = 255
                cx, cy = W//2, H//2
                
                buf = np.resize(0, (H, W)).astype(dst.dtype)
                cv2.line(buf, (0, cy), (W, cy), c, 1)
                cv2.line(buf, (cx, 0), (cx, H), c, 1)
                cv2.circle(buf, (cx, cy), cx//2, c, 1)
                cv2.circle(buf, (cx, cy), cx//4, c, 1)
                dst = cv2.bitwise_xor(buf, dst)
                
                cv2.imshow(title, dst)
                cv2.waitKey(self.rate_param.value)
                
                if cv2.getWindowProperty(title, 0) < 0:
                    self.button.Value = False
                    self.viewer.Stop()
                    break
        finally:
            cv2.destroyAllWindows()


if __name__ == '__main__':
    from plugins import JeolCamera, RigakuCamera
    app = wx.App()
    frm = wxpj.Frame(None)
    frm.load_plug(__file__, show=1)
    frm.load_plug(JeolCamera, show=0)
    frm.load_plug(RigakuCamera, show=0)
    frm.Show()
    app.MainLoop()

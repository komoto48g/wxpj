#! python3
# -*- coding: utf-8 -*-
import wx
import cv2
import numpy as np
from jgdk import Layer, Thread, Param, LParam, ToggleButton, Choice
import editor as edi


class Plugin(Layer):
    """Plugins of camera viewer
    """
    menukey = "Cameras/Camera &viewer"
    
    @property
    def cameraman(self):
        camerasys = self.camera_selector.value
        if not camerasys:
            print(self.message("- camera is not selected."))
            return None
        return self.parent.require(camerasys)
    
    def Init(self):
        self.viewer = Thread(self)
        
        self.button = ToggleButton(self, "View camera", icon='cam',
            handler=lambda v: self.viewer.Start(self.run)
                        if v.IsChecked() else self.viewer.Stop())
        
        self.sight_chk = wx.CheckBox(self, label="sight+") # 照準器
        self.sight_chk.Value = 1
        
        self.detect_chk = wx.CheckBox(self, label="detect")
        
        self.hi = LParam("hi", (0, 10, 0.01), 0.1)
        self.lo = LParam("lo", (0, 10, 0.01), 0.0)
        
        self.rate_param = LParam('rate', (100,500,100), 500, tip="refresh speed [ms] (>= 100ms)")
        self.size_param = Param('size', (128,256,512,1024), 512, tip="resizing view window (<= 1k)")
        
        self.camera_selector = Choice(self,
                choices=['JeolCamera', 'RigakuCamera'], readonly=1)
        
        self.layout((
                self.button, None,
                self.sight_chk,
                self.detect_chk,
            ),
            row=2, cw=0, lw=16, tw=40
        )
        self.layout((
                self.camera_selector,
                self.rate_param,
                self.size_param,
                self.hi,
                self.lo,
            ),
            title="Setting",
            show=0, type='vspin', lw=40, tw=40, cw=-1
        )
    
    def Destroy(self):
        if self.viewer.active:
            self.viewer.Stop()
        return Layer.Destroy(self)
    
    def run(self):
        try:
            title = self.__module__
            
            while self.viewer.active:
                buf = self.cameraman.capture()
                src = edi.imconv(buf, self.hi.value, self.lo.value)
                h, w = src.shape
                H = self.size_param.value
                W = H * w // h
                dst = cv2.resize(src, (W, H), interpolation=cv2.INTER_AREA)
                
                ## 照準サークルを xor で足し合わせる
                if self.sight_chk.Value:
                    c = 255 # white (xor) line 
                    cx, cy = W//2, H//2
                    buf = np.zeros((H, W), dtype=dst.dtype)
                    cv2.line(buf, (0, cy), (W, cy), c, 1)
                    cv2.line(buf, (cx, 0), (cx, H), c, 1)
                    cv2.circle(buf, (cx, cy), cx//2, c, 1)
                    cv2.circle(buf, (cx, cy), cx//4, c, 1)
                    dst = cv2.bitwise_xor(buf, dst)
                
                ## TEST for ellipses detection
                if self.detect_chk.Value:
                    ellipses = edi.find_ellipses(src, ksize=3, sortby='size')
                    if ellipses:
                        el = ellipses[0]
                        R, n, s = edi.calc_ellipse(src, el)
                        p = R * n/s
                        q = R * (1-n)/(1-s)
                        print("$(p, q) = {:g}, {:g}".format(p, q))
                        ratio = H/h # dst/src 縮小率
                        cc, rc, angle = el
                        cc = np.int32(np.array(cc) * ratio)
                        rc = np.int32(np.array(rc) * ratio / 2)
                        dst = cv2.cvtColor(dst, cv2.COLOR_GRAY2BGR)
                        cv2.ellipse(dst, cc, rc, angle, 0, 360, (192,192,0), 2) # cyan:"#00c0c0"
                
                cv2.imshow(title, dst)
                cv2.waitKey(self.rate_param.value)
                
                if cv2.getWindowProperty(title, 0) < 0:
                    self.button.Value = False
                    self.viewer.Stop()
                    break
        except AttributeError:
            wx.MessageBox("The camera is not specified.\n\n",
                          "Select a camera system from Setting",
                          style=wx.ICON_ERROR)
        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    from plugins import JeolCamera, RigakuCamera
    from jgdk import Frame
    
    app = wx.App()
    frm = Frame(None)
    frm.load_plug(__file__, show=1)
    frm.load_plug(JeolCamera, show=0)
    frm.load_plug(RigakuCamera, show=0)
    frm.Show()
    app.MainLoop()

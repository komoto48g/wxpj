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
    menukey = "Cameras/"
    
    @property
    def cameraman(self):
        camerasys = self.camera_selector.value
        if not camerasys:
            print(self.message("- camera is not selected."))
            return None
        return self.parent.require(camerasys)
    
    def Init(self):
        self.viewer = Thread(self)
        
        def view(v):
            if v.IsChecked():
                self.viewer.Start(self.run)
            else:
                self.viewer.Stop()
        
        self.button = ToggleButton(self, "View camera", icon='camera', handler=view)
        self.detect_chk = wx.CheckBox(self, label="detect")
        
        self.hi = LParam("hi", (0, 10, 0.01), 0.1)
        self.lo = LParam("lo", (0, 10, 0.01), 0.0)
        
        self.rate_param = LParam('rate', (100,500,100), 500, tip="refresh speed [ms] (>= 100ms)")
        self.size_param = Param('size', (128,256,512,1024), 512, tip="resizing view window (<= 1k)")
        
        self.camera_selector = Choice(self,
                choices=['JeolCamera', 'RigakuCamera'], readonly=1)
        
        self.layout((
                self.button,
                4,
                self.detect_chk,
            ),
            row=3,
        )
        self.layout((
                self.camera_selector, None,
                self.rate_param, self.hi,
                self.size_param, self.lo,
            ),
            title="Detection settings",
            row=2, show=0, type='vspin', lw=-1, tw=40
        )
    
    def Destroy(self):
        try:
            if self.viewer.active:
                self.viewer.Stop()
        finally:
            return Layer.Destroy(self)
    
    def run(self):
        try:
            title = self.__module__
            
            while self.viewer.active:
                buf = self.cameraman.capture()
                
                ## 画像サイズの縮小
                src = edi.imconv(buf, self.hi.value, self.lo.value)
                h, w = src.shape
                H = self.size_param.value
                W = H * w // h
                dst = cv2.resize(src, (W, H), interpolation=cv2.INTER_AREA)
                
                ratio = H / h # dst/src 縮小率
                
                ## 照準器サークルを xor で足し合わせる
                if 1:
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
                        cc, rc, angle = el
                        cc = np.int32(np.array(cc) * ratio)
                        rc = np.int32(np.array(rc) * ratio / 2)
                        dst = cv2.cvtColor(dst, cv2.COLOR_GRAY2BGR)
                        cv2.ellipse(dst, cc, rc, angle, 0, 360, (192,192,0), 2) # cyan:"#00c0c0"
                
                cv2.imshow(title, dst)
                cv2.waitKey(self.rate_param.value)
                
                if cv2.getWindowProperty(title, 0) < 0:
                    self.button.Value = False
                    break
        except Exception as e:
            print(e)
        finally:
            self.viewer.Stop()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    from plugins import JeolCamera
    from jgdk import Frame
    
    app = wx.App()
    frm = Frame(None)
    frm.load_plug(__file__, show=1)
    frm.load_plug(JeolCamera, show=0)
    frm.Show()
    app.MainLoop()

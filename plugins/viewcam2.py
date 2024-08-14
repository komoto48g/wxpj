#! python3
import wx
import cv2
import numpy as np

from jgdk import Layer, Thread, Param, LParam, Choice
import editor as edi


class Plugin(Layer):
    """Plugins of camera viewer.
    """
    menukey = "Cameras/"
    
    def Init(self):
        self.viewer = Thread(self)
        
        self.camera_selector = Choice(self,
                                updater=self.viewer.wraps(self.run),
                                choices=['JeolCamera', 'RigakuCamera'],
                                icon='camera', size=(114,-1), readonly=1)
        
        self.detect_chk = wx.CheckBox(self, label="Ellipse detection")
        
        self.rate_param = LParam('rate', (0,500,50), 500)
        self.size_param = Param('size', (128,256,512,1024), 512)
        
        self.layout((
                self.camera_selector, None, (4,-1),
                self.detect_chk,
            ),
            row=2,
        )
        self.layout((
                self.rate_param,
                self.size_param,
            ),
            title="Live view setting", row=1, show=0,
            type='vspin', cw=-1, lw=36, tw=44,
        )
    
    def update_brightness(self, argv):
        el, p, q = argv
        self.message("{}/pix (S/N {:g})".format(int(p), p/q))
    
    def run(self):
        """Live view using the specified camera manager."""
        title = self.camera_selector.value
        if not title:
            self.message("- No camera specified.")
            return
        cameraman = self.parent.require(title)
        _prev = None
        try:
            ## cv2.startWindowThread()
            cv2.namedWindow(title)
            cv2.setMouseCallback(title, self.on_mouse_button)
            while self.viewer.active:
                buf = cameraman.capture()
                if buf is not _prev:
                    dst = self.display(buf)
                    cv2.imshow(title, dst)
                _prev = buf
                cv2.waitKey(self.rate_param.value + 1)
                if cv2.getWindowProperty(title, 0) < 0:
                    break
        except cv2.error:
            pass
        except Exception:
            ## cv2.destroyAllWindows()
            cv2.destroyWindow(title)
    
    def display(self, buf):
        ## 画像サイズの縮小
        src = edi.imconv(buf, hi=0.1)
        h, w = src.shape
        H = self.size_param.value
        W = H * w // h
        dst = cv2.resize(src, (W, H), interpolation=cv2.INTER_AREA)
        
        ratio = H / h # dst/src 縮小率
        self._ratio = ratio
        
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
                R, n, s = edi.calc_ellipse(src, el)
                p = R * n/s
                q = R * (1-n)/(1-s)
                self.update_brightness((el, p, q))
                cc, rc, angle = el
                cc = np.int32(np.array(cc) * ratio)
                rc = np.int32(np.array(rc) * ratio / 2)
                dst = cv2.cvtColor(dst, cv2.COLOR_GRAY2BGR)
                cv2.ellipse(dst, cc, rc, angle, 0, 360, (192,192,0), 2) # cyan:"#00c0c0"
        return dst
    
    def on_mouse_button(self, event, x, y, flags, param):
        """Cv2 mouse callback method.
        Triggers [det/mod-key] (x, y) notify events.
        """
        if event == 0: key = 'motion'
        elif event in (1,4,7): key = 'Lbutton'
        elif event in (2,5,8): key = 'Rbutton'
        elif event in (3,6,9): key = 'Mbutton'
        ## elif event == 10:
        ##     key = 'wheel' + ('up' if flags > 0 else 'down')
        ## elif event == 11:
        ##     key = 'wheel' + ('right' if flags > 0 else 'left')
        else:
            return
        
        if event > 0:
            if event < 4: key += ' pressed'
            elif event < 7: key += ' released'
            elif event < 10: key += ' dblclick'
        
        mod = ''
        if flags & cv2.EVENT_FLAG_CTRLKEY:  mod += "C-"
        if flags & cv2.EVENT_FLAG_ALTKEY:   mod += "M-"
        if flags & cv2.EVENT_FLAG_SHIFTKEY: mod += "S-"
        
        try:
            ## title = self.__module__
            ## x, y, w, h = print(cv2.getWindowImageRect(title))
            r = self._ratio
            self.parent.notify.handler(f"det/{mod}{key}", x/r, y/r)
        except Exception:
            pass

#! python3
import wx
import cv2
import numpy as np

from wxpj import Layer, LParam, Button
import editor as edi


class Plugin(Layer):
    """Gaussian Blur and Threshold.
    """
    menukey = "Plugins/&Basic Tools/"
    category = "Basic Tools"
    
    def Init(self):
        self.ksize = LParam("ksize", (1,99,2), 13)
        self.sigma = LParam("sigma", (0,100,1), 0)
        self.thresh = LParam("thresh", (0,255,1), 128)
        
        btn = Button(self, label="+Execute",
                     handler=lambda v: self.execute(otsu=wx.GetKeyState(wx.WXK_SHIFT)))
        
        self.layout(
            self.params, title="blur-threshold",
            type='vspin', cw=0, lw=40, tw=40
        )
        self.layout((btn,))
    
    params = property(lambda self: (self.ksize, self.sigma, self.thresh))
    
    def execute(self, frame=None, otsu=True):
        """GaussianBlur and binarize using threshold.
        
        [S-Lbutton] Estimate the threshold using Otsu's algorithm.
        
        Args:
            otsu    : float number (0 < r < 1) indicating threshold percentile
                      Set True (1) to use Otsu's algorithm.
                      Set False (0) to use the specified threshold value.
        
        Returns:
            blurred and binarized dst image <uint8>
        """
        if not frame:
            frame = self.selected_view.frame
        
        k, s, t = [p.value for p in self.params]
        src = frame.buffer
        if k > 1:
            src = edi.imcv(src)
            src = cv2.GaussianBlur(src, (k, k), s)
        buf = edi.imconv(src)
        self.output.load(buf, "*Gauss*", localunit=frame.unit)
        
        if 0 < otsu < 1:
            t = np.percentile(buf, 100 * otsu)
            t, dst = cv2.threshold(buf, t, 255, cv2.THRESH_BINARY)
        else:
            t, dst = cv2.threshold(buf, t, 255, cv2.THRESH_OTSU if otsu else cv2.THRESH_BINARY)
        self.thresh.value = t
        self.output.load(dst, "*threshold*", localunit=frame.unit)
        return dst

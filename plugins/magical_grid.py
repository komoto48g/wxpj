#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import numpy as np
from numpy import pi,nan
from numpy.fft import fft2,fftshift
from mwx.controls import LParam
from mwx.graphman import Layer
import wxpyJemacs as wxpj
import editor as edi


class Plugin(Layer):
    """Plugin for magcal
    """
    menu = "Plugins/&Pragma Tools"
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    lccf = property(lambda self: self.parent.require('lccf2'))
    ldc = property(lambda self: self.parent.require('ld_cgrid'))
    
    def Init(self):
        self.page = LParam("page", (-1,1000,1), -1)
        self.page.bind(lambda lp: self.selected_view.select(lp.value))
        
        self.choice = wxpj.Choice(self, size=(60,-1),
            choices=['FFT',
                     'FFT+',
                     'Cor',
                     ],
            readonly=1,
        )
        self.choice.Selection = 0
        
        self.score = LParam("score", (0.01, 10, 0.01), 0.1)
        
        self.grid = wxpj.Choice(self, label="grid [mm]", size=(140,-1),
            handler=lambda v: self.calc_mag(),
            choices=['1/2000', # Standard grating(Ted Pera)
                     '1/2160', # Standard Gatan grating
                     '2.04e-7' # Au single 100
                     ],
            tip="Set grid length [mm/grid] to calculate Mag.")
        self.grid.Selection = 0
        
        self.text = wxpj.TextCtrl(self, size=(140,40), style=wx.TE_READONLY|wx.TE_MULTILINE)
        
        size = (72,-1)
        
        self.layout("Evaluate step by step", (
            wxpj.Button(self, "1. Show",
                lambda v: self.selected_view.select(self.selected_frame), icon='help', size=size,
                tip="Select frame buffer.\n"
                    "(page -1 means the last frame)"),
            self.page,
            
            wxpj.Button(self, "2. Eval",
                lambda v: self.testrun(), icon='help', size=size,
                tip="Select evaluation method\n"
                    "  :FFT evaluates using FFT method. Use when grid is small\n"
                    "  :FFT+ in addition to FFT method, corss-cut the center (十文字きりちょんぱ)\n"
                    "  :Cor evaluates using Cor (pattern matching) method. Use when grid is large"),
            self.choice,
            
            wxpj.Button(self, "3. Mark",
                lambda v: self.calc_mark(), icon='help', size=size,
                tip="Set paramter of socre at percentile (:COR only).\n"
                    "score is the ratio [%] to maximum count for extracting spots"),
            self.score,
            
            wxpj.Button(self, "4. Go",
                lambda v: self.run(), icon='help', size=size,
                tip="Run the fitting procedure.\n"),
            None,
            ),
            row=2, show=1, type='vspin', tw=40, lw=0,
        )
        self.layout(None, (
            wxpj.Button(self, "check unit",
                lambda v: self.parent.su.Show(), icon='v',
                tip="Check unit length [mm/pixel]\n"
                    "See the startup option where globalunit can be set to calc mags."),
            
            wxpj.Button(self, "Run",
                lambda v: self.run_all(), icon='->',
                tip="Run above (1-2-3) step by step.\n"
                    "Before calculating Mags, check unit length [mm/pixel]"),
            ),
            row=2,
        )
        self.layout("log/output", (
            self.grid,
            self.text,
            ),
            row=1, show=1, tw=50, vspacing=4,
        )
        self.lgbt.ksize.value = 5 # default blur window size
    
    @property
    def result_frame(self):
        if self.choice.Selection < 2:
            name = "*result of fft*"
        else:
            name = "*result of matching*"
        return self.selected_view.find_frame(name)
    
    @property
    def selected_frame(self):
        self.page.range = (-1, len(self.selected_view))
        ## if self.page.value is nan:
        ##     return self.selected_view.frame
        return self.selected_view.find_frame(self.page.value)
    
    def testrun(self, frame=None):
        """Evaluation using selected method (ref: choice.Selection)"""
        if not frame:
            frame = self.selected_frame
        
        if not self.result_frame and self.page.value >= 0:
            ## A new frame (*result*) is to be loaded ahead of stacks
            ## so we need to put forward the page counter (no problem when -1)
            self.page.value += 1
        
        if self.choice.Selection < 2:
            return self.test_fft(frame, crossline=self.choice.Selection==1)
        else:
            return self.test_cor(frame)
    
    def run(self, frame=None):
        if not frame:
            frame = self.selected_frame
        self.message("\b @ldc...")
        self.ldc.reset_params(backcall=None)
        self.ldc.thread.Start(self.calc_fit, frame)
    
    def run_all(self, frame=None):
        result = self.testrun(frame)
        frame = self.calc_mark(result)
        ## if self.choice.Selection == 2:
        ##     frame = self.selected_view.select(self.selected_frame)
        ##     self.show_page()
        self.run(frame)
    
    ## --------------------------------
    ## calc functions
    ## --------------------------------
    
    def calc_mark(self, frame=None):
        if not frame:
            frame = self.result_frame
            if not frame:
                print(self.message("- No *result* frame"))
                return
        self.message("\b @lccf...")
        if self.score.value is nan:
            self.lccf.run(frame, otsu=1)
        else:
            self.lgbt.thresh.value = np.percentile(frame.buffer, 100-self.score.value)
            self.lccf.run(frame, otsu=0)
        return frame
    
    def calc_fit(self, frame=None):
        self.ldc.run(frame)
        self.ldc.run(frame) # 計算 x2 回目
        self.ldc.Show()
        self.calc_mag()
        if frame:
            frame.update_attributes(
                parameters = self.parameters[:-1], # except the last text
                annotation = ', '.join(self.text.Value.splitlines()),
            )
    
    def calc_mag(self):
        g = self.ldc.grid_params[0].value
        g0 = eval(self.grid.Value)
        if self.choice.Selection < 2: # FFT
            res = ("Mag = {:6,.0f} [fft]".format(1/g/g0),
                         "grid = {:g} mm".format(1/g))
        else:
            res = ("Mag = {:6,.0f} [cor]".format(g/g0),
                         "grid = {:g} mm".format(g))
        self.text.Value = '\n'.join(res)
    
    ## --------------------------------
    ## test functions
    ## --------------------------------
    
    ## def test_corr(self, frame):
    ##     src = frame.buffer
    ##     h, w = src.shape
    ##     
    ##     self.message("processing corr...")
    ##     buf = edi.Corr(src, src) # リソースめっちゃ食われる
    ##     tmp = cv2.GaussianBlur(src, (111,111), 0)
    ##     bkg = edi.Corr(tmp, tmp)
    ##     dst = edi.imconv(buf - bkg)
    ##     return frame.parent.load(dst, name="*result of corr*", pos=0, localunit=frame.unit)
    
    def test_cor(self, frame):
        src = frame.buffer
        h, w = src.shape
        
        d = h//8            # 特徴点を選んで ROI をとりたいところだが，
        i, j = h//2, w//2   # ld_cgrid を使うので，画像の中心であることが必須．
        temp = src[i-d:i+d, j-d:j+d] # とりあえずの真ん中らへんをテキトーに ROI る
        
        self.message("processing pattern matching...")
        src = edi.imconv(src)
        temp = edi.imconv(temp)
        dst, (l,t) = edi.match_pattern(src, temp)
        
        ## <float32> to <uint8>
        dst = edi.imconv(dst, hi=0)
        return frame.parent.load(dst, name="*result of matching*", pos=0, localunit=frame.unit)
    
    def test_fft(self, frame, crossline=0):
        src = frame.roi
        h, w = src.shape
        
        ## resize to 2**N squared ROI
        n = pow(2, int(np.log2(min(h,w)))-1)
        i, j = h//2, w//2
        src = src[i-n:i+n,j-n:j+n]
        
        h, w = src.shape
        i, j = h//2, w//2
        
        self.message("processing fft... @log")
        src = fftshift(fft2(src))
        buf = np.log(1 + abs(src)) # log intensity
        
        ## background subst.
        if 1:
            self.message("\b @subst")
            rmax = w/2
            buf = cv2.linearPolar(buf, (w/2, h/2), rmax, cv2.WARP_FILL_OUTLIERS)
            buf -= sum(buf) / h # バックグラウンド(ぽい)強度を引いてみる (中央も 0 になるので注意)
            
            self.message("\b @remap")
            ## X, Y = np.meshgrid(
            ##     np.arange(-w/2, w/2, dtype=np.float32),
            ##     np.arange(-h/2, h/2, dtype=np.float32),
            ## )
            ## map_r = w/rmax * np.hypot(Y, X)
            ## map_t = ((pi + np.arctan2(Y, X)) * h/2/pi)
            ## buf = cv2.remap(buf.astype(np.float32), map_r, map_t,
            ##                 cv2.INTER_CUBIC, cv2.WARP_FILL_OUTLIERS)
            ## 
            buf = cv2.linearPolar(buf, (w/2, h/2), rmax, cv2.WARP_INVERSE_MAP)
            
            ## 確認
            ## self.output.load(buf, name="*remap*", localunit=1/w)
            
        dst = np.exp(buf) - 1 # log --> exp で戻す
        
        ## 十紋形切ちょんぱマスク (option)
        if crossline:
            d = int(h * 0.001)
            i, j = h//2, w//2
            dst[:,j-d:j+d+1] = 0
            dst[i-d:i+d+1,:] = 0
            
        ## force the central spot be white (default)
        ## if 0:
        ##     d = 2
        ##     i, j = h//2, w//2
        ##     y, x = np.ogrid[-d:d+1,-d:d+1]     # index arrays
        ##     m = np.where(np.hypot(y,x) <= d)   # mask submatrix
        ##     dst[m[0]+i-d,m[1]+j-d] = dst.max() # apply to the center +-d
        
        ## <uint8> 逆空間 論理スケール [ru/pixel] に変換する
        ## do not cuts hi/lo: 強度重心を正しくとるためには飽和しないようにする
        ## dst = edi.imconv(dst, hi=0)
        return frame.parent.load(dst, name="*result of fft*", pos=0, localunit=1/w/frame.unit)


if __name__ == "__main__":
    import glob
    
    app = wx.App()
    frm = wxpj.Frame(None)
    frm.load_plug(__file__, show=1, docking=4)
    for path in glob.glob(r"C:/usr/home/workspace/images/*.bmp"):
        frm.load_buffer(path)
    frm.Show()
    app.MainLoop()

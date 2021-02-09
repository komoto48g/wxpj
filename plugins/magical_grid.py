#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import scipy as np
from scipy import pi
from numpy.fft import fft2,fftshift
from mwx import LParam
from mwx.graphman import Layer
import wxpyJemacs as wxpj
import editor as edi


class Plugin(Layer):
    """Plugin for magcal
    """
    menu = "&Plugins/&Pragmas"
    
    def Init(self):
        self.index = LParam("page", (-1,1024,1), -1)
        self.index.bind(lambda lp: self.graph.select(lp.value))
        
        self.choice = wxpj.Choice(self, size=(60,-1),
            choices=['FFT',
                     'FFT+',
                     'Cor'
                     ],
            readonly=1,
        )
        self.choice.Select(0)
        
        self.score = LParam("spot", (0.01, 5, 0.01), 0.50)
        
        self.grid = wxpj.Choice(self, label="grid [mm]", size=(140,-1),
            handler=lambda v: self.calc_mag(),
            choices=['1/2000', # Standard grating(Ted Pera)
                     '1/2160', # Standard Gatan grating
                     '2.04e-7' # Au single 100
                     ],
            tip="Set grid length [mm/grid] to calculate Mag.")
        self.grid.Select(0)
        
        self.text = wxpj.TextCtrl(self, size=(140,40), style=wx.TE_READONLY|wx.TE_MULTILINE)
        
        size = (72,-1)
        
        self.layout("Evaluate step by step", (
            wxpj.Button(self, "1. Show",
                lambda v: self.graph.select(self.index.value), icon='help', size=size,
                tip="Select frame buffer.\n"
                    "(index -1 means the last frame)"),
            self.index,
            
            wxpj.Button(self, "2. Test",
                lambda v: self.testrun(), icon='help', size=size,
                tip="Select evaluation method\n"
                    "  :FFT evaluates using FFT method. Use when grid is small\n"
                    "  :FFT+ in addition to FFT method, corss-cut the center (十文字きりちょんぱ)\n"
                    "  :Cor evaluates using Cor (pattern matching) method. Use when grid is large"),
            self.choice,
            
            wxpj.Button(self, "3. Find",
                lambda v: self.run(), icon='help', size=size,
                tip="Set paramter of socre at percentile.\n"
                    "This also runs the fitting procedure using `lccf2` algorithm.\n"
                    "  :score is the ratio [%] to maximum count for extracting white spots"),
            self.score,
            ),
            row=2, show=1, type='vspin', tw=40, lw=0,
        )
        self.layout(None, (
            wxpj.Button(self, "Run ALL",
                lambda v: (self.testrun(), self.run()), icon='help', size=size,
                tip="Run above (1-2-3) step by step.\n"
                    "Before calculating Mags, check unit length [mm/pixel]"),
                    
            wxpj.Button(self, "check unit",
                lambda v: self.parent.require('startup').Show(), icon='v',
                tip="Check unit length [mm/pixel]\n"
                    "See the startup option where globalunit can be set to calc mags."),
            ),
            row=2,
        )
        self.layout("log/output", (
            self.grid,
            self.text,
            ),
            row=1, show=1, tw=50, vspacing=4,
        )
        ## self.lgbt.ksize.value = 13
        ## self.lgbt.sigma.value = 0
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    lccf = property(lambda self: self.parent.require('lccf2'))
    ldc = property(lambda self: self.parent.require('ld_cgrid'))
    ## ld = property(lambda self: self.parent.require('ld_grid'))
    
    def testrun(self, frame=None):
        if not frame:
            frame = self.graph.all_frames[self.index.value]
        
        if self.choice.Selection < 2:
            nop = "*result of fft*" not in frame.parent
            result = self.test_fft(frame, crossline=self.choice.Selection==1)
        else:
            nop = "*result of matching*" not in frame.parent
            result = self.test_cor(frame)
        
        if nop and self.index.value != -1:
            self.index.value += 1
        return result
    
    def run(self, frame=None):
        if not frame:
            if self.choice.Selection < 2:
                name = "*result of fft*"
            else:
                name = "*result of matching*"
            if name not in self.graph:
                self.message("- No results found: testrun may have not been run yet.")
                return
            frame = self.graph.find_frame(name)
            
        elif not frame.name.startswith("*result of"):
            self.message("- The frame must be the result of *fft* or *cor*")
            return
        
        del frame.markers
        self.lccf.Draw(0)
        self.ldc.Draw(0)
        
        self.message("\b @lccf...")
        self.lgbt.thresh.value = np.percentile(frame.buffer, 100-self.score.value)
        self.lccf.run(frame)
        
        self.message("\b @ldc...")
        self.ldc.reset_params(backcall=None)
        self.ldc.thread.Start(self.ldc.run, frame) # ここから子スレッド IN
        self.ldc.Show()
        
        ## ldc のスレッドが終わるまで待たなければ，途中結果を参照してしまう．
        ## しかし，メインプロセス＝親が待ち続ける (ビジー状態) と子スレッドは怠けてしまう．
        ## self.ldc.thread.join(1) ... なのでこれではダメ．メインスレッドで待機する必要がある．
        ## ここでは thread_end <sentinel> を待機して最終結果を出力する．
        self.ldc.handler.hook('thread_end', lambda v: self.calc_mag())
    
    def calc_mag(self):
        g = self.ldc.grid_params[0].value
        g0 = eval(self.grid.Value)
        if self.choice.Selection < 2:
            res = ("grid = {:g} mm".format(1/g),
                   "Mag = {:,.0f} [fft]".format(1/g/g0))
        else:
            res = ("grid = {:g} mm".format(g),
                   "Mag = {:,.0f} [cor]".format(g/g0))
        self.text.Value = '\n'.join(res)
        print(*res)
    
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
        
        d = h//10           # 特徴点を選んで ROI をとりたいところだが，
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
        
        ## 2**n - squared ROI
        if 1:
            ## nn = (1,2,4,8,16,32,64,128,256,512,1024,2048,4096,8192)
            ## k = np.searchsorted(nn, min(h,w), 'right')
            ## n = nn[k-1]//2
            n = pow(2, int(np.logn(2, min(h,w)))-1)
            i, j = h//2, w//2
            src = src[i-n:i+n,j-n:j+n]
            h, w = src.shape
        
        self.message("processing fft... @log")
        src = fftshift(fft2(src))
        buf = np.log(1 + abs(src)) # log intensity
        
        ## background subt. processing (default)
        if 1:
            self.message("\b @polar-transform")
            rmax = w/2
            buf = cv2.linearPolar(buf, (w/2, h/2), rmax, cv2.WARP_FILL_OUTLIERS)
            buf -= sum(buf) / h # バックグラウンド(ぽい)強度を引いてみる
            
            self.message("\b @remap")
            X, Y = np.meshgrid(
                np.arange(-w/2, w/2, dtype=np.float32),
                np.arange(-h/2, h/2, dtype=np.float32),
            )
            map_r = w/rmax * np.hypot(Y, X)
            map_t = ((pi + np.arctan2(Y, X)) * h/2/pi)
            buf = cv2.remap(buf.astype(np.float32), map_r, map_t,
                            cv2.INTER_CUBIC, cv2.WARP_FILL_OUTLIERS)
            
        dst = np.exp(buf) - 1 # log --> exp で戻す
        
        ## 十紋形切ちょんぱマスク (to be option)
        if crossline:
            d = int(h * 0.001)
            i, j = h//2, w//2
            dst[:,j-d:j+d+1] = 0
            dst[i-d:i+d+1,:] = 0
            
        ## force the central spot be white (default)
        if 1:
            d = 4
            i, j = h//2, w//2
            y, x = np.ogrid[-d:d+1,-d:d+1]     # index arrays
            m = np.where(np.hypot(y,x) <= d)   # mask submatrix
            dst[m[0]+i-d,m[1]+j-d] = dst.max() # apply to the center +-d
        
        ## <uint8> 逆空間 論理スケール [ru/pixel] に変換する
        ## do not cuts hi/lo: 強度重心を正しくとるためには飽和しないようにする
        dst = edi.imconv(dst, hi=0.0)
        return frame.parent.load(dst, name="*result of fft*", pos=0, localunit=1/w/frame.unit)


if __name__ == "__main__":
    app = wx.App()
    frm = wxpj.Frame(None)
    frm.load_plug(__file__, show=1, docking=4)
    frm.Show()
    app.MainLoop()

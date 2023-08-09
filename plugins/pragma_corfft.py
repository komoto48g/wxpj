#! python3
# -*- coding: utf-8 -*-
import wx
import cv2
import numpy as np
from numpy import nan
from numpy.fft import fft2,fftshift

from jgdk import Layer, LParam, Button, TextCtrl, Choice
import editor as edi


FFT_FRAME_NAME = "*result of fft*"
COR_FRAME_NAME = "*result of cor*"


class Plugin(Layer):
    """Plugin for magcal.
    """
    menukey = "Plugins/&Pragma Tools/"
    
    su = property(lambda self: self.parent.require('startup'))
    lgbt = property(lambda self: self.parent.require('lgbt'))
    lccf = property(lambda self: self.parent.require('lccf2'))
    ldc = property(lambda self: self.parent.require('ld_cgrid'))
    
    def Init(self):
        self.choice = Choice(self, size=(60,-1),
                             choices=['FFT', 'FFT+', 'Cor'],
                             readonly=1)
        self.choice.Selection = 0
        
        self.score = LParam("score", (0.01, 10, 0.01), 0.1)
        
        self.grid = Choice(self, label="grid [mm]", size=(140,-1),
            handler=lambda p: self.calc_mag(),
            updater=lambda p: self.calc_ru(),
            choices=[
                '1/2000', # Standard grating(Ted Pera)
                '1/2160', # Standard Gatan grating
                '2.356e-7', # Au single 111
                '2.040e-7', # Au single 200
                ],
            tip="Set grid length [mm/grid] to calculate Mag."
        )
        self.grid.Selection = 0
        
        self.text = wx.TextCtrl(self, size=(140,40),
                             style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.layout((
                Button(self, "1. Eval", self.evaluate, icon='help', size=(72,-1)),
                self.choice,
                
                Button(self, "2. Mark", self.calc_mark, icon='help', size=(72,-1)),
                self.score,
                
                Button(self, "3. Run", self.run, icon='help', size=(72,-1)),
                
                Button(self, "Settings", self.show_settings),
            ),
            title="Evaluate step by step", row=2,
            type='vspin', cw=-1, lw=0, tw=44,
        )
        self.layout((
                self.grid,
                self.text,
            ),
            title="Output", row=0, show=1, vspacing=2,
        )
        self.lgbt.ksize.value = 5 # default blur window size
    
    @property
    def result_frame(self):
        if self.choice.Selection < 2: # FFT/FFT+ mode
            name = FFT_FRAME_NAME
        else:
            name = COR_FRAME_NAME
        return self.output.find_frame(name)
    
    target_view = None          # given at evaluation time
    output_view = Layer.output  # property
    
    ## --------------------------------
    ## calc/marking functions
    ## --------------------------------
    ## Run the following procs (1-2-3) step by step.
    ## Before calculating Mags, check unit length [mm/pixel]
    
    def show_settings(self):
        """Show settings to check.
        
        - lccf radii [rmin:rmax] for marking spots
        - unit length [mm/pixel] for calculating mags
        """
        self.su.Show()
        self.lccf.Show()
    
    def run(self):
        """Run the fitting procedure."""
        try:
            busy = wx.BusyCursor()
            self.ldc.reset_params()
            self.ldc.thread.Start(self.calc_fit)
        finally:
            del busy
    
    def evaluate(self, frame=None):
        """Evaluation using the selected method.
        
        Select evaluation method:
        
        - :FFT evaluates using FFT method. Use when grid is small
        - :FFT+ in addition to FFT method, corss-cut the center (十文字きりちょんぱ)
        - :Cor evaluates using Cor (pattern matching) method. Use when grid is large
        """
        if not frame:
            frame = self.graph.frame
        self.target_view = frame.parent # update target view <graph>
        
        if self.choice.Selection < 2: # FFT/FFT+ mode
            self.test_fft(frame, crossline=(self.choice.Selection==1))
        else:
            self.test_cor(frame)
    
    def calc_mark(self):
        """Set parameter of socre at percentile.
        
        Ratio [%] to maximum count for extracting spots.
        """
        frame = self.result_frame
        if not frame:
            print(self.message("- No *result*"))
            return
        self.message("\b @lccf...")
        if self.score.value is nan:
            self.lccf.run(frame, otsu=True)
        else:
            self.lccf.run(frame, otsu=1-self.score.value/100)
    
    def calc_fit(self):
        frame = self.result_frame
        if not frame:
            print(self.message("- No *result*"))
            return
        self.message("\b @ldc...")
        self.ldc.run(frame)
        self.ldc.run(frame) # 計算 x2 回目
        self.ldc.Show()
        self.calc_mag()
        frame.parent.select(frame)
    
    def calc_mag(self):
        """Calculate Mags from the grid length [mm/grid].
        """
        frame = self.result_frame
        if not frame:
            print(self.message("- No *result*"))
            return
        u = frame.unit                    # [u/pix]
        g = self.ldc.grid_params[0].value # [u/grid] image or 1/g :FFT
        g0 = eval(self.grid.Value)        # [u/grid] org
        if self.choice.Selection < 2: # FFT
            h, w = frame.buffer.shape
            method = 'fft'
            M = 1/g/g0
            u = 1/w/u
        else:
            method = 'cor'
            M = g/g0
        self.text.Value = '\n'.join((
            "Mag = {:,.0f} [{}]".format(M, method),
            "({:g} A/pix)".format(u/M * 1e7)
        ))
        self.target_view.frame.update_attributes(
            parameters = self.parameters[:-1], # except the last text
            annotation = ', '.join(self.text.Value.splitlines())\
                       + '; \n' + frame.annotation,
        )
    
    def calc_ru(self):
        """Estimate [u/pix] on specimen from two spots.
        
        1. Select the *result* frame
        2. Draw line from origin to the nearest spot
        3. Press to estimate the unit length [u/pix]
        """
        frame = self.result_frame
        if not frame:
            print(self.message("- No *result*"))
            return
        x, y = frame.selector
        if len(x) < 2:
            wx.MessageBox("Select two nearest spots.\n\n"
                          "{}".format(self.calc_ru.__doc__))
            return
        
        u = frame.unit                      # [u/pix] or [u-1/pix] :FFT
        g = np.hypot(y[1]-y[0], x[1]-x[0])  # [u/grid] or [u-1/grid] :FFT
        g0 = eval(self.grid.Value)          # [u/grid] org
        if self.choice.Selection < 2: # FFT
            h, w = frame.buffer.shape
            method = 'fft'
            M = 1/g/g0
            u = 1/w/u
        else:
            method = 'cor'
            M = g/g0
        self.text.Value = "({:g} A/pix) {}".format(u/M * 1e7, method)
    
    ## --------------------------------
    ## test/eval functions
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
    ##     return frame.parent.load(dst, COR_FRAME_NAME, pos=0, localunit=frame.unit)
    
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
        return self.output.load(dst, COR_FRAME_NAME, localunit=frame.unit)
    
    def test_fft(self, frame, crossline=0):
        src = frame.roi
        h, w = src.shape
        
        n = pow(2, int(np.log2(min(h, w)))-1) # resize to 2**N squared ROI (N=2n)
        i, j = h//2, w//2
        src = src[i-n:i+n,j-n:j+n]
        
        self.message("processing fft... @log")
        src = fftshift(fft2(src))
        
        buf = np.log(1 + abs(src)) # log intensity
        h, w = buf.shape           # shape:(2n,2n)
        
        ## background subst.
        if 1:
            self.message("\b @subst")
            rmax = n * 0.75
            buf = cv2.linearPolar(buf, (w/2, h/2), rmax, cv2.WARP_FILL_OUTLIERS)
            buf -= sum(buf) / h # バックグラウンド(ぽい)強度を引いてみる
            
            self.message("\b @remap")
            buf = cv2.linearPolar(buf, (w/2, h/2), rmax, cv2.WARP_INVERSE_MAP)
            
            ## ## 逆変換
            ## N = np.arange(-n, n, dtype=np.float32),
            ## X, Y = np.meshgrid(N, N)
            ## map_r = w/rmax * np.hypot(Y, X)
            ## map_t = (pi + np.arctan2(Y, X)) * h/2 /pi
            ## buf = cv2.remap(buf.astype(np.float32), map_r, map_t,
            ##                 cv2.INTER_CUBIC, cv2.WARP_FILL_OUTLIERS)
            ## ## 確認
            ## self.output.load(buf, "*remap*", localunit=1/w)
            
        dst = np.exp(buf) - 1 # log --> exp で戻す
        
        ## 十紋形切ちょんぱマスク (option)
        d = max(int(n * 0.002), 2)
        
        if crossline:
            dst[:,n-d:n+d+1] = 0
            dst[n-d:n+d+1,:] = 0
        
        ## force the central spot white (option)
        if 1:
            y, x = np.ogrid[-d:d+1,-d:d+1]     # index arrays
            m = np.where(np.hypot(y,x) <= d)   # mask submatrix
            dst[m[0]+n-d,m[1]+n-d] = dst.max() # apply to the center +-d
        
        ## 逆空間：論理スケール [ru/pixel] に変換する
        ## Don't cut hi/lo: 強度重心を正しくとるため，飽和させないこと
        ## dst = edi.imconv(dst, hi=0, lo=0)
        return self.output.load(dst, FFT_FRAME_NAME, localunit=1/w/frame.unit)


if __name__ == "__main__":
    import glob
    from jgdk import Frame

    app = wx.App()
    frm = Frame(None)
    frm.load_plug(__file__, show=1, dock=4)
    frm.load_frame(glob.glob(r"C:/usr/home/workspace/images/*.bmp"))
    frm.Show()
    app.MainLoop()

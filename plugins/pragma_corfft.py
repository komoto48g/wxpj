#! python3
import wx
import numpy as np

from wxpj import Layer, LParam, Button, Choice
import editor as edi


FFT_FRAME_NAME = "*result of fft*"
COR_FRAME_NAME = "*result of cor*"


class Plugin(Layer):
    """Pragma suite for distortion analysis using COR/FFT methods.
    """
    menukey = "Plugins/&Pragma Tools/"
    
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
            handler=self.calc_mag,
            updater=self.calc_ru,
            choices=[
                '1/2000', # Standard grating(Ted Pera)
                '1/2160', # Standard Gatan grating
                '2.356e-7', # Au single 111
                '2.040e-7', # Au single 200
                ],
        )
        self.grid.Selection = 0
        
        self.text = wx.TextCtrl(self, size=(140,40),
                                style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.layout((
                Button(self, "1. Eval", self.evaluate, icon='help', size=(72,-1)),
                self.choice,
                
                Button(self, "2. Mark", self.calc_mark, icon='help', size=(72,-1)),
                self.score,
                
                Button(self, "3. Run", self.execute, icon='help', size=(72,-1)),
                
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
        self.lgbt.ksize.value = 13 # default blur window size
    
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
        self.lccf.Show()
    
    def execute(self):
        """Run the fitting procedure."""
        self.ldc.reset_params()
        self.ldc.thread.Start(self.calc_fit)
    
    def evaluate(self, frame=None):
        """Evaluation using the selected method.
        
        Select evaluation method:
        
        - :FFT evaluates using FFT method. Use when grid is small
        - :FFT+ in addition to FFT method, cross-cut the center (十文字きりちょんぱ)
        - :Cor evaluates using COR (pattern matching). Use when grid is large
        """
        if not frame:
            frame = self.graph.frame
        self.target_view = frame.parent # update target view <graph>
        
        if self.choice.Selection < 2: # FFT/FFT+ mode
            self.test_fft(frame, crossline=(self.choice.Selection==1))
        else:
            self.test_cor(frame)
    
    def calc_mark(self):
        """Feature detection.
        
        Set parameter: Ratio [%] of upper counts to extract spots.
        """
        frame = self.result_frame
        if not frame:
            self.message("- No *result*")
            return
        self.message("\b @lccf...")
        if np.isnan(self.score.value):
            self.lccf.execute(frame, otsu=True)
        else:
            self.lccf.execute(frame, otsu=1-self.score.value/100)
    
    def calc_fit(self):
        frame = self.result_frame
        if not frame:
            self.message("- No *result*")
            return
        self.message("\b @ldc...")
        self.ldc.execute(frame)
        self.ldc.execute(frame) # 計算 x2 回目
        self.ldc.Show()
        self.calc_mag()
        frame.parent.select(frame)
    
    def calc_mag(self):
        """Calculate Mags from the grid length [mm/grid].
        """
        frame = self.result_frame
        if not frame:
            self.message("- No *result*")
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
        self.target_view.frame.annotation = (
            ', '.join(self.text.Value.splitlines()) + '; \n' + frame.annotation)
    
    def calc_ru(self):
        """Estimate [u/pix] on specimen from two spots.
        
        1. Select the *result* frame
        2. Draw line from origin to the nearest spot
        3. Press to estimate the unit length [u/pix]
        """
        frame = self.result_frame
        if not frame:
            self.message("- No *result*")
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
    
    def test_cor(self, frame):
        src = frame.buffer
        h, w = src.shape
        
        n = h//8            # 特徴点を選んで ROI をとりたいところだが，
        i, j = h//2, w//2   # ld_cgrid を使うので，画像の中心であることが必須．
        tmp = src[i-n:i+n, j-n:j+n]
        
        self.message("Processing pattern matching...")
        dst, (x, y) = edi.match_pattern(src, tmp)
        
        ## self.message("Processing corr...")
        ## dst, (x, y) = edi.eval_corr_shift(src, tmp)
        
        return self.output.load(dst, COR_FRAME_NAME, localunit=frame.unit)
    
    def test_fft(self, frame, crossline=0):
        src = edi.fftcrop(frame.roi)
        
        self.message("Processing enhanced FFT...")
        dst = edi.enhanced_fft(src, 0.75)
        
        n = src.shape[0] // 2
        d = max(int(n * 0.002), 2)
        
        ## 十紋形切ちょんぱマスク (option)
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
        
        return self.output.load(dst, FFT_FRAME_NAME, localunit=1/2/n/frame.unit)

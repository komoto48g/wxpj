#! python3
import wx
import numpy as np
from numpy import pi
from numpy.fft import fft,ifft,fft2,ifft2,fftshift,fftfreq
from scipy import optimize

from jgdk import Layer, LParam, Button
import editor as edi


def _make_indices(i, j, N):
    """Indices list descentding order[i..j] and ascending order[j..k].
    """
    lhs = np.arange(i, np.floor(j), -1)
    n = N - len(lhs)
    j = np.ceil(j)
    rhs = np.arange(j, j+n)
    return np.append(lhs, rhs)


def make_indices_matrix(n):
    return np.array([_make_indices(0, -j, n)
                     for j in np.arange(0, n-0.5, 0.5)], dtype=int)


class Plugin(Layer):
    """Plugin test of CTF ver.2
    """
    menukey = "CTF/"
    
    debug = 0
    
    lctf = property(lambda self: self.parent.require('lctf'))
    su = property(lambda self: self.parent.require('startup'))
    em = property(lambda self: self.su.em)
    
    def Init(self):
        self.cmax = LParam("limit", (2, 50), 10,
                           updater=self.calc_optvar,
                           tip="Set maximum index for fitting")
        
        self.ru = LParam("A/pix", (0, 2, 0.001), 0.5, fmt="{:5.3f}".format,
                         tip="Angstrom per pixel")
        
        self.cs = LParam("Cs", (0, 5, 0.01), 1.0, fmt="{:5.2f}".format,
                         updater=self.calc_sherzer,
                         tip="Design value of Cs")
        
        self.layout((
            self.lctf.rmin,
            self.lctf.tol,
            ),
            title="CTF step by step",
            type='vspin', style='button', cw=-1, lw=28, tw=50,
        )
        self.layout((
            self.ru,
            self.cs,
            ),
            title="TEM/Image Cond.", show=0,
            type='vspin', style='button', cw=-1, lw=28, tw=50,
        )
        self.layout((
            self.cmax,
            None,
            Button(self, "CTF", self.run, icon='->'),
            Button(self, "clf", edi.clear, icon='-'),
            ),
            row=2,
            type='vspin', style='button', cw=-1, lw=32, tw=50,
        )
    
    def calc_sherzer(self):
        """Sherzer focus [m] defined as sin(2*pi/3) = 0.866
        """
        el = self.em.elambda
        cs = self.cs.value * 1e-3
        df = np.sqrt(4/3 * cs * el)
        ds = (3/16 * cs * el**3) ** 0.25
        
        print("Sherzer conditions:",
              "Acc_v = {:,g} V".format(self.em.acc_v),
              "    K = {:g} A-1".format(1/el * 1e-10),
              "  df* = {:g} nm".format(df * 1e9),
              "  ds* = {:g} nm".format(ds * 1e9),
              sep='\n')
    
    def calc_optvar(self, show=True):
        """Calc optical variables.
        """
        xx = self.lctf.lpoints[0] # selected peak points of x:ref
        ## yy = np.arange(len(xx)) # selected peak indices # ▲昇順のみを仮定している
        
        u = self.ru.value * 1e-10 # [m/pix]
        K = 1 / self.em.elambda   # [1/m] wave vector
        
        cs = self.cs.value * 1e-3
        A = cs * K/2 / (K * u)**4 # expected cs value
        
        ## --------------------------------
        ## The first trial of optimization 
        ## --------------------------------
        ## index オフセットの最適値を探索する (Cs 設計値を用いる)
        def residual1(params, x, y):
            b, = params
            return (A*x**2 + b*x - y)**2
        
        def optimize_index(x, y):
            result = optimize.leastsq(residual1, [0], args=(x, y))
            res = sum(residual1(result[0], x, y))
            b, = result[0]
            ya = np.round(A*x**2 + b*x).astype(int)
            if np.all(ya == y): # 整数列パターンが合致するときだけ解を返す
                if self.debug:
                    df = b / K * (K * u)**2
                    print("  {}, {:.1f} mm, res: {:g}".format(ya, df*1e9, res))
                return res
        
        n = min(self.cmax.value, len(xx))
        lres = []
        lyy = []
        while n > 1:
            yy = np.arange(0, n)
            for i in range(n, 0, -1): # over-focus
                x = xx[:n]
                y = yy + i
                res = optimize_index(x, y)
                if res:
                    lres.append(res)
                    lyy.append(y)
            yy = make_indices_matrix(n)
            for i in range(0, n): # under-focus
                x = xx[:n]
                for y in (yy - i):
                    res = optimize_index(x, y)
                    if res:
                        lres.append(res)
                        lyy.append(y)
            if lres:
                break
            n -= 1
        else:
            print("- No solution. Fitting failed.")
            return False
        
        print("+ {} peaks are used for fitting.".format(n))
        k = np.argmin(lres)
        yy = lyy[k]
        n = len(yy)
        print("The first trial indices({}) are {}".format(len(xx[:n]), yy))
        
        ## --------------------------------
        ## The second trial of fitting
        ## --------------------------------
        ## Cs 設計値に近い条件を探す (残差の最小値では曖昧さが残る)
        def residual(params, x, y):
            a, b = params
            return (a*x**2 + b*x - y)**2
        
        ## インデクスオフセットの最適値は最初のトライアルで決定されている
        x = xx[:n]
        y = yy[:n]
        result = optimize.leastsq(residual, [A, 0], args=(x, y))
        a, b = result[0]
        
        if show:
            edi.plot(self.lctf.axis**2, self.lctf.data, '--', lw=0.5) # original
            edi.plot(self.lctf.newaxis, self.lctf.newdata, '-') # interpolated
            edi.plot(*self.lctf.lpoints, 'o') # filtered peaks
            
            ## x = np.linspace(0, 0.1, 1000)
            x = np.arange(0, xx[n-1] * 2, 1e-4)
            edi.plot(x, a*x**2 + b*x, '-')
            edi.plot(xx[:n], yy[:n], 'o')
        
        ## --------------------------------
        ## Evaluation of optical consts
        ## --------------------------------
        ## cs の見積もりは誤差が大きいので参考のみ
        cs = a * 2/K * (K * u)**4
        
        ## デフォーカス (-under, +over)
        df = b / K * (K * u)**2
        
        ## CTFFIND の結果は 1/4 定義 ?(楕円の正規化 1/2, 非点の定義 1/2)
        A = self.lctf.stig * df * (K * u)
        
        print("The fitting results are as follows:",
              "Acc_v = {:,g} V".format(self.em.acc_v),
              "  u = {:g} A/pix".format(u * 1e10),
              "df* = {:g} nm".format(df * 1e9),
              "Ast = {:g} nm".format(np.abs(A) * 1e9),
              "phi = {:g} deg".format(np.angle(A) * 180/pi),
              "cs* = {:g} mm".format(cs * 1e3),
              sep='\n  ')
        self.graph.frame.annotation = ','.join((
              "df* = {:g} nm".format(df * 1e9),
              "cs* = {:g} mm".format(cs * 1e3),
        ))
    
    def run(self):
        """Execute all processes.
        
        1. Calc log-polar of ring pattern.
        2. Calc min/max peak detection.
        3. Calc optical variables.
        """
        print('-' * 32)
        print('>', self.graph.frame.name)
        self.lctf.calc_ring(show=0)
        self.lctf.calc_peak(show=0)
        self.calc_optvar(show=1)


if __name__ == "__main__":
    import glob
    from jgdk import Frame

    app = wx.App()
    frm = Frame(None)
    frm.load_plug(__file__, show=1)
    frm.load_frame(glob.glob(r"C:/usr/home/workspace/images/*.bmp"))
    frm.Show()
    app.MainLoop()

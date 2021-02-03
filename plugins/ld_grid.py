#! python
# -*- coding: shift-jis -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
from itertools import chain
import wx
import scipy as np
from scipy import optimize
from scipy import pi,exp,sin,cos
from mwx import LParam
from mwx.graphman import Layer


def calc_dist(u, D, d):
    return complex(D, d) * u * u * np.conj(u)


def calc_aspect(u, r, t):
    t *= pi/180
    ## return ((1+r) * u + (1-r) * np.conj(u) * exp(2j*t)) / 2
    return u + (1-r) * np.conj(u) * exp(2j*t)


class Model(object):
    """�O���b�h�p�^�[�����f�� [mm]
     grid : length per grid [mm/gr]
     tilt : rotation angles of pattern
    xc,yc : position of center
    """
    nGrid = 30 # number of grid (in x,y) --> (N+1) �{�̃O���b�h��������
    
    def __init__(self, parent):
        self.owner = parent
    
    def basegrid(self, params):
        """�`��͈͂̊�O���b�h (���f���z��̑g) ��Ԃ�
        ���b�V�����ƕ������͓����ł���K�v�͂Ȃ����C�����ł͓����D
        """
        grid, tilt, xc, yc = np.float32(params)
        u = grid * exp(1j * tilt * pi/180)
        N = self.nGrid
        lu = u * N * np.linspace(-0.5, 0.5, N+1) # 1/(N)grid
        X = xc + lu
        Y = yc + lu
        return [(X + 1j * y) for y in Y]\
             + [(x + 1j * Y) for x in X]
        
        ## ���b�V�����ƕ������͓����̏ꍇ�C����łn�j
        ## X, Y = np.meshgrid(lu, lu)
        ## return (xc + 1j * yc) + np.vstack((X + 1j * Y, Y + 1j * X))
    
    def residual(self, fitting_params, x, y):
        """�ŏ�����@�̏�]����"""
        grid, tilt, xc, yc, ratio, phi, D, d = fitting_params
        z = x + 1j*y
        
        ## �Ӓ��ߎ��̕␳
        if not -90 < phi < 90:
            ## print("  warning! phi is over limit ({:g})".format(phi))
            if phi < -90: phi += 180
            elif phi > 90: phi -= 180
            fitting_params[5] = phi
        
        if not self.owner.thread.is_active:
            print("... Iteration stopped")
            raise StopIteration
        
        ## �����͈́i�`��͈͂ł͂Ȃ��j�̊�O���b�h (-N:N �\���L���ݒ肷��)
        N = int(max(np.hypot(x,y)) / grid) + 1
        u = grid * exp(1j * tilt * pi/180)
        lu = u * np.arange(-N, N+1)
        X, Y = np.meshgrid(lu, lu)
        net = (xc + 1j * yc + X + 1j * Y).ravel()
        gr = calc_aspect(net, ratio, phi) + calc_dist(net, D, d)
        
        ## �ċߐڃO���b�h�_����̃Y����]������ (�T���͈͂̃��~�b�g��݂���)
        lim = N * grid
        res = [ min(abs(gr - p))**2 for p in z if abs(p.real) < lim and abs(p.imag) < lim ]
        
        print("\b"*72 + "point({}): residual {:g}".format(len(res), sum(res)), end='')
        return res


class Plugin(Layer):
    """Distortion fitting of grid
    """
    menu = "&Plugins/Measure &Distortion"
    
    Fitting_model = Model
    fitting_params = property(
        lambda self: self.grid_params + self.ratio_params + self.dist_params)
    
    def Init(self):
        self.thread = Layer.Thread()
        
        x = 5e-3
        self.dist_params = (
            LParam("D", (-x, x, x/1e5), 0.0, '{:.3G}'.format),
            LParam("d", (-x, x, x/1e5), 0.0, '{:.3G}'.format),
        )
        self.ratio_params = (
            LParam("��", (0.5, 1.5, 0.001), 1.0),
            LParam("��", (-90, 90, 0.1), 0.0),
        )
        self.grid_params = (
            LParam("grid", (0, 5e4, 0.1), 1.0),
            LParam("tilt", (-90, 90, 0.1), 0.0),
            LParam("xc", (-200, 200, 0.1), 0.0),
            LParam("yc", (-200, 200, 0.1), 0.0),
        )
        for lp in chain(self.dist_params, self.ratio_params, self.grid_params):
            lp.bind(lambda v: self.calc())
        
        self.btn = wx.Button(self, label="+Execute", size=(80,22))
        self.btn.Bind(wx.EVT_BUTTON,
            lambda v: self.thread.Start(self.run, skip=wx.GetKeyState(wx.WXK_SHIFT)))
            
        self.btn.SetToolTip("S-Lbutton to skip estimating grid params")
        
        self.order = LParam("order", (0,6,1), 3)
        
        self.text = wx.TextCtrl(self, size=(160,60), style=wx.TE_READONLY|wx.TE_MULTILINE)
        
        self.layout("Distortion", self.dist_params, cw=64, lw=20, tw=64, show=0)
        self.layout("XY Aspects", self.ratio_params, cw=64, lw=20, tw=64)
        self.layout("Grid paramter", self.grid_params, cw=56, lw=28, tw=64)
        self.layout(None, [self.btn, self.order], row=2, type='choice', cw=40, lw=36)
        self.layout(None, [self.text], expand=2)
        
        self.model = self.Fitting_model(self)
        self.init_grid(self.graph.axes)
    
    def init_grid(self, axes):
        grid = self.model.basegrid(self.grid_params)
        self.Arts = [axes.plot([], [], 'k--', lw=0.5, alpha=0.75)[0] for z in grid]\
                  + [axes.plot([], [], 'r-',  lw=0.5, alpha=0.75)[0] for z in grid]
    
    def calc(self):
        """�A�X�y�N�g��F R1=Y/X, R2=Y2/X2 ���v�Z����
        �A�X�y�N�g�䂸��{�R���c�����l�������O���b�h�f�[�^�ɕϊ����ĕ`�悷��
        """
        r, t = np.float32(self.ratio_params)
        D, d = np.float32(self.dist_params)
        
        grid0 = list(self.model.basegrid(self.grid_params))
        grid1 = list(calc_aspect(z,r,t) + calc_dist(z,D,d) for z in grid0)
        grids = grid0 + grid1 # ���X�g�a
        
        for art,z in zip(self.Arts, grids): # �O���b�h�̐ݒ�
            art.set_data(z.real, z.imag)
        self.Draw()
        
        ## e = (1-r) / (1+r)
        e = (1 - r)
        t *= pi/180
        R1 = (1 - e * cos(2*t)) / (1 + e * cos(2*t))
        R2 = (1 - e * sin(2*t)) / (1 + e * sin(2*t))
        
        ## R50 �̘c���w�W�F�A�X�y�N�g�䂸��(Y/X)�{�R���c��
        ## R = 50
        ## d = abs(complex(*self.dist_params)) * (R ** 2)
        
        self.text.SetValue("\n".join((
            "Y/X = {:.3f}".format(R1),
            "Y2/X2 = {:.3f}".format(R2),
            "Aspect �� = {:.2%}".format((r-1)*2),
            ## "Total(R50) = {:.2%}".format(d + (r-1)*2),
        )))
        return R1, R2
    
    def run(self, frame=None, skip=0):
        if not frame:
            frame = self.graph.frame
        
        x, y = frame.markers
        if not x.any():
            print(self.message("- abort: No markers found in the frame."))
            return
        
        ## re-init grid which is to be bound to the frame
        self.init_grid(frame.axes)
        
        with self.thread:
            ## �����O���b�h�p�����[�^�̌��ς���
            if not skip:
                print("estimating initial grid paramtres... order(0)")
                self.find_near_grid(x, y)
            
            ## �œK�O���b�h�p�����[�^�̌��ς���
            order = self.order.value
            if order > 0:
                result = optimize.leastsq(self.model.residual,
                    np.float32(self.fitting_params), args=(x,y), ftol=10**-order)
                
                for lp,v in zip(self.fitting_params, result[0]):
                    lp.value = v
            
            ## check final result
            res = self.model.residual(np.float32(self.fitting_params), x, y)
            
            print("... refined with order({})".format(order),
                  ":res {:g}".format(np.sqrt(np.average(res)) / frame.unit))
            self.calc()
    
    def find_near_grid(self, x, y):
        j = np.hypot(x,y).argmin() # nearest point to the center
        dx = x - x[j]
        dy = y - y[j]
        dx[j] = dy[j] = 1e3 # dummy to escape argmin
        dd = np.hypot(dx,dy)
        k = dd.argmin() # ���S�ɍł��߂��_����C���ɋ߂��_
        grid = dd[k]
        tilt = np.arctan(dy[k]/dx[k]) * 180/pi
        for lp,v in zip(self.grid_params, (grid,tilt,x[j],y[j])): # set parameters
            lp.value = v


if __name__ == "__main__":
    model = Model(None)
    params = 100, 0, 0, 0
    print(*enumerate(model.basegrid(params)), sep='\n')

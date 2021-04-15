#! python
# -*- coding: utf-8 -*-
"""Editor's collection of Tem algorithms of Mixins (interfaces) class

Author: Kazuya O'moto <komoto@jeol.co.jp>
Contributer: Hirohumi IIjima <hiiijima@jeol.co.jp>,
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
from collections import OrderedDict
import threading
import time
import os
import wx
import numpy as np
from numpy import pi,cos,sin
from mwx import LParam
from mwx.graphman import Thread
from pyJeol import pyJem2 as pj # pmpj: Poor man's pyJem package (not a PyJEM)
from pyJeol.pyJem2 import TEM, EOsys, HTsys, Filter, Stage # to be referred from pylots
from pyJeol.temisc import Environ
from misc import ConfigData
import wxpyJemacs as wxpj
import editor as edi


class TemInterface(object):
    """Camera/TEM interface Mixin
    
    This class provides common TEM objects, configs, and functions
    This class is supposed to be mixied-in the Plugin.
    Otherwise, the `parent should be given explicitly.
    """
    camerasys = 'JeolCamera'
    ## camerasys = 'RigakuCamera'
    
    cameraman = property(lambda self: self.parent.require(self.camerasys))
    
    @property
    def camera(self):
        if not self.cameraman:
            print("- No camera system installed {!r}".format(self.camerasys))
            return
        cam = self.cameraman.camera
        if not cam:
            print("trying to connect to the camera of {}".format(self.cameraman))
            cam = self.cameraman.connect()
        return cam
    
    thread = Thread() # Common workerthread instance shared by pylot modules
    
    env = property(lambda self: self.parent.env)
    
    default_saapt = property(lambda self: self.config.get('default_saapt', 1))
    default_clapt = property(lambda self: self.config.get('default_clapt', 1))
    default_acc_v = property(lambda self: self.config['acc_v'])
    
    ustar_sqrt = 1
    config_tem_mag = None
    config_tem_lowmag = None
    
    @property
    def config(self):
        """configuration (mode-specific)"""
        ## if self.lowmagp:
        ##     return self.config_tem_lowmag
        ## return self.config_tem_mag
        try:
            if self.lowmagp: # cmdl:stream must be open
                return self.config_tem_lowmag
        except Exception:
            pass
        return self.config_tem_mag
    
    @staticmethod
    def configure(path):
        Tem = None
        Aperture = pj.Aperture
        
        if os.path.exists(path):
            print("$(config path) = {!r}".format((path)))
            
            TemInterface.config_tem_mag = ConfigData(path, section='TEM')
            TemInterface.config_tem_lowmag = ConfigData(path, section='TEM-LOWMAG')
            
            ## Extract Tem info from default section like,
            ## >>> from pyJeol.em import JEM_P1181 as Tem
            config = TemInterface.config_tem_mag
            try:
                Tem = __import__(config['tem'])
            except ImportError:
                Tem = __import__("pyJeol.em.{}".format(config['tem']), fromlist=["pyJeol.em"])
            
            if config['apt_extype']:
                Aperture = pj.ApertureEx
        
        ## Extracted Tem info are inherited to `pj` globals
        if Tem:
            Aperture.APERTURES.update(Tem.APERTURES) # ID が関係するので上書きではなく更新
            pj.Illumination.MODES = OrderedDict(Tem.ILLUMINATION_MODES) # 他のはオーバーライド
            pj.Imaging.MODES = OrderedDict(Tem.IMAGING_MODES)
            pj.Omega.MODES = OrderedDict(Tem.OMEGA_MODES)
            
            ## U* - corrected quantity e.g. j2deg
            basenv = Environ(Tem.ACC_V)
            env = Environ(config['acc_v']) # cf. self.parent.env (see tem_option)
            TemInterface.ustar_sqrt = np.sqrt(env.ustar / basenv.ustar)
        
        TemInterface.pj = pj # just for debug, include pj in self namespace
        TemInterface.Tem = Tem
        TemInterface.Aperture = Aperture
        
        TemInterface.illumination = pj.Illumination()
        TemInterface.imaging = pj.Imaging()
        TemInterface.omega = pj.Omega()
        TemInterface.tem = pj.TEM()
        
        TemInterface.CLA = Aperture('CLA')
        TemInterface.SAA = Aperture('SAA')
        TemInterface.OLA = Aperture('OLA')
        TemInterface.Gonio = pj.Stage()
        TemInterface.OmegaFilter = pj.Filter()
    
    def calc_imrot(self, tags):
        NI = 0
        for s in tags:
            lp = self.tem.foci[s]
            NI += lp.value / lp.max * self.Tem.LENS_NIMAX[s]
        return self.env.j2deg * NI * self.ustar_sqrt
    
    @property
    def mag_unit(self):
        """Conversion of camera unit length to specimen space [um/pix] for MAG mode.
        Note: In DIFF mode, this leads reciprocal value [mrad/pix]
        """
        mag = self.imaging.Mag or 1e3
        return self.camera.pixel_unit / mag * 1e3 # [um/pix] on specimen
    
    @property
    def cam_unit(self):
        """Conversion of camera unit to length specimen reciprocal space [mrad/pix] for DIFF mode.
        Note: The result is the same as 'mag_unit', though,
              this function should better be used for clarity of the mode context.
        """
        cam = self.imaging.Mag or 1e3
        return self.camera.pixel_unit / cam * 1e3 # [mrad/pix] on specimen
    
    @property
    def disp_unit(self):
        """Conversion of camera unit length [mm/pix] to dispersion space [eV/pix] for Spectrum mode.
        Note: in imaging mode, the result is indefinite (may zero return)
        """
        disp = self.omega.Dispersion or 1e3
        return self.camera.pixel_unit / disp * 1e3 # [eV/pix] on spectrum
    
    ## --------------------------------
    ## Functions for calibration 
    ## --------------------------------
    magp = property(lambda self: self.imaging.Mode in (0,1,3)) # MAG,MAG2,SAMAG
    diffp = property(lambda self: self.imaging.Mode == 4)      # DIFF
    lowmagp = property(lambda self: self.imaging.Mode == 2)    # LOWMAG
    
    ## @staticmethod
    ## def aptsel_restriction(func):
    ##     def _f(self, *args, **kwargs):
    ##         if not self.APT.sel:
    ##             if not self.pause("Please select one of {}.".format(self.APT.name)):
    ##                 return
    ##             return _f(self, *args, **kwargs) # recursive call
    ##         return func(self, *args, **kwargs)
    ##     return _f
    
    def aptsel(self, **kwargs):
        return all(self.apt_selection(k,v) for k,v in kwargs.items())
    
    def apt_selection(self, k, v=True):
        apt = getattr(self, k)
        if v and not apt.sel:
            if self.pause("Please set one of {}.".format(apt.name)):
                return self.apt_selection(k, v)
            raise Exception("cancelled by user")
        if not v and apt.sel:
            if self.pause("Please get rid of {}.".format(apt.name)):
                return self.apt_selection(k, v)
            raise Exception("cancelled by user")
        return True
    
    def mode_selection(self, mmode, verbose=True):
        """Check mag mode.
        verbose: show message and let user select mode and continue or cancel.
        if not verbose, this is just equiv to mode-p (mag-p, diff-p, lowmag-p)
        """
        p = (self.imaging.Name in mmode)
        if p or not verbose:
            return p
        if self.pause("The current mode is not in {} mode.".format(mmode)):
            self.imaging.Mode = mmode
            self.delay(1)
            return True
    
    def save_excursion(self, **kwargs):
        """Save optical mode settings :set_state temporarily"""
        return Excursion(self, **kwargs)
    
    def save_restriction(self, **kwargs):
        """Save lens/def paramtres :set_param temporarily"""
        return Restriction(self, **kwargs)
    
    def get_state(self):
        return {
           "imode" : self.illumination.Mode,
            "spot" : self.illumination.Spot,
           "alpha" : self.illumination.Alpha,
           "mmode" : self.imaging.Mode,
             "mag" : self.imaging.Mag,
           "kmode" : self.omega.Mode,
            "disp" : self.omega.Dispersion,
        }
    
    def set_state(self, imode=None, spot=None, alpha=None, mmode=None, mag=None, kmode=None, disp=None):
        ns, na = self.illumination.Range
        if spot is not None: spot %= ns
        if alpha is not None: alpha %= na
        
        self.illumination.Mode = imode
        self.illumination.Spot = spot
        self.illumination.Alpha = alpha
        self.imaging.Mode = mmode
        self.imaging.Mag = mag
        self.omega.Mode = kmode
        self.omega.Dispersion = disp
    
    def set_param(self, **kwargs):
        saved = {}
        for k,v in kwargs.items():
            if k in self.Aperture.APERTURES:
                apt = getattr(self, k)
                if apt.sel != v:
                    saved[k] = apt.sel
                    apt.sel = v
                    busy = wx.BusyInfo("Relax one moment please. Aperture drive is moving...")
                    try:
                        self.wait('aptsel end')
                        self.delay(1)
                    except Exception:
                        self.delay(5)
            elif k == 'SLIT':
                self.OmegaFilter.Slit = v
            elif k == 'ES':
                self.OmegaFilter.EnergyShift = v
            else:
                saved[k] = self.tem[k]
                self.tem[k] = v
        return saved
    
    def for_each_spot(self):
        """Generates for each spot number [0:N]"""
        ns, na = self.illumination.Range
        a = self.illumination.Alpha
        for s in range(ns):
            self.message("spot={}, alpha={}".format(s, a))
            self.illumination.Spot = s
            self.delay(1)
            self.thread.check()
            yield s
    
    def for_each_alpha(self):
        """Generates for each alpha number [0:N]"""
        ns, na = self.illumination.Range
        s = self.illumination.Spot
        for a in range(na):
            self.message("spot={}, alpha={}".format(s, a))
            self.illumination.Alpha = a
            self.delay(1)
            self.thread.check()
            yield a
    
    def for_each_mag(self):
        """Generates for each mag/cam (index, value)"""
        for j, v in enumerate(self.imaging.Range):
            self.message("mag/cam: [{}] {:,d}".format(j, v))
            self.imaging.Mag = v
            self.delay(1)
            self.thread.check()
            yield (j, v)
    
    def for_each_disp(self):
        """Generates for each dispersion (index, value)"""
        for j, v in enumerate(self.omega.Range):
            self.message("dispersion: [{}] {:,d}".format(j, v))
            self.omega.Dispersion = v
            self.delay(1)
            self.thread.check()
            yield (j, v)
    
    def pause(self, msg=""):
        """Pause the process where called"""
        return self.thread.pause(msg)
    
    def wait(self, sentinel, timeout=5):
        """Halt the thread and wait the notify `sentinel"""
        with self.thread:
            hook = self.parent.notify.handler.hook(sentinel,
                                lambda v: self.thread.flag.set())
            try:
                self.thread.flag.clear() # halt the thread
                self.thread.flag.wait(timeout) # wait the sentinel
            finally:
                self.thread.flag.set() # let the thread go
                self.parent.notify.handler.unbind(sentinel, hook) # unhook in timeout
    
    ## --------------------------------
    ## Functions for detecting beam
    ## --------------------------------
    default_delay = 0.50 # delay time before exposing (till afterglow vanishes)
    signal_level = 100 # [counts/pixel/s] > 10/0.1s
    noise_level = 20 # [counts/pixel/s] < 1/0.05s
    borderline = 2 # threshold border p/q
    
    def is_signal(self, p, q):
        r = abs(p/q) # S/N ratio as inside/outside the boundary
        return (r > self.borderline * 5
            or (r > self.borderline and p > self.noise_level))
    
    def delay(self, sec=None):
        if sec is None:
            sec = self.default_delay
        time.sleep(sec) # [sec] wait for afterglow goes off
    
    def capture(self):
        try:
            return self.cameraman.capture().astype(np.float32)
        except Exception as e: # bad connection ? try once
            print(e)
        self.delay(1)
        return self.cameraman.capture().astype(np.float32)
    
    def detect_ellipse(self, ksize=13, delays=None, cache=True):
        """Detect ellipse pattern in captured `src image
        ksize : size of blur window
       delays : delay [s] till afterglow vanishes
        cache : previously cached buffer to integrate
                if true value, get integration recursively until over the singnal level
                if false value, no integration
      retval -> args
         el : the largest ellipse (center, rect, anle), otherwise None if not found
        p/t : density inside the area of mask per exposure time
        q/t : density outside
        """
        t = self.camera.exposure
        self.delay(t) # before capturing, delay cam to clear the cache
        self.delay(delays) # plus default delay till afterglow vanishes
        
        src = self.capture()
        if isinstance(cache, np.ndarray): # integrate the cached buffer
            src += cache
            cache = True
        
        ellipses = edi.find_ellipses(src, ksize=ksize, sortby='size')
        if ellipses:
            el = ellipses[0]
            p, q = edi.calc_ellipse(src, el) # S/N count density p:inside, q:outside,
            args = (el, p/t, q/t)
            if p/t < self.noise_level:
                self.cameraman.handler('detect-nobeam', args)
            elif abs(p/q) < self.borderline:
                self.cameraman.handler('detect-noborder', args)
            else:
                if p/t < self.signal_level and cache:
                    return self.detect_ellipse(ksize, delays=None, cache=src)
                self.cameraman.handler('detect-beam', args)
        else:
            p = q = src.sum() / src.size # averaged count
            args = (None, p/t, q/t)
            if p/t < self.noise_level:
                self.cameraman.handler('detect-nosignal', args)
            else:
                self.cameraman.handler('detect-noellipse', args)
        return args
    
    def detect_beam_center(self, border=None, **kwargs):
        """ビームの楕円中心 (重心ではない)
        border : 検出範囲の境界のしきい値
        """
        el, p, q = self.detect_ellipse(**kwargs)
        if el and self.is_signal(p, q):
            if border is None:
                return np.array(el[0]), p, q
            
            h, w = self.camera.shape
            cx, cy = el[0]
            r = border
            if r < cx/w < 1-r and r < cy/h < 1-r:
                return np.array(el[0]), p, q
        return None, p, q
    
    ## def detect_beam_centroid(self, **kwargs):
    ##     """ビームの検出域内の重心 (楕円中心ではない)
    ##     """
    
    def detect_beam_diameter(self, **kwargs):
        """Averaged diameter of beam contour ellipse
        A square root of product (ra:minor, rb:major)
        """
        el, p, q = self.detect_ellipse(**kwargs)
        if el and self.is_signal(p, q):
            ra, rb = el[1]
            return np.sqrt(ra * rb), p, q
        return None, p, q


TemInterface.configure("config.ini")


## --------------------------------
## Tools for alignment functions
## --------------------------------

class Excursion(object):
    def __init__(self, target, **kwargs):
        self.target = target
        self.params = kwargs
    
    def __enter__(self):
        self.saved = self.target.get_state()
        ## self.saved = dict((k,v) for k,v in self.saved.items() if k in self.params)
        self.target.set_state(**self.params) # load
    
    def __exit__(self, t, v, tb):
        self.target.set_state(**self.saved) # restore all


class Restriction(object):
    def __init__(self, target, **kwargs):
        self.target = target
        self.params = kwargs
    
    def __enter__(self):
        self.saved = self.target.set_param(**self.params) # load
    
    def __exit__(self, t, v, tb):
        self.target.set_param(**self.saved) # restore


class DataLogger(object):
    def __init__(self):
        self.clear_data()
    
    def clear_data(self):
        self.data = [],[]
    
    def update_data(self, lx, ly):
        x, y = self.data
        if not hasattr(lx, '__iter__'):
            lx, ly = [lx], [ly]
        lk = np.searchsorted(x, lx)
        for k, xo, yo in zip(lk, lx, ly):
            if xo in x:
                y[k] = yo
            else:
                x.insert(k, xo)
                y.insert(k, yo)
    
    def plot_data(self):
        x, y = self.data
        if len(x) > 1: # 線形近似グラフの追加
            a, b = np.polyfit(x, y, 1)
            f = np.poly1d((a, b))
            edi.plot(x, f(x), '--')
        edi.plot(x, y, 'o-')
    
    def save_data(self, path=None):
        if not path:
            with wx.FileDialog(None, "Save as", wildcard="text file (*.txt)|*.txt",
                style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT) as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                path = dlg.Path
        buf = np.array(self.data).T
        np.savetxt(path, buf, fmt='%.8e', delimiter='\t')


## --------------------------------
## Focus/Alignment interfaces
## --------------------------------

class SpotInterface(TemInterface):
    """Spot Finder Algorithm/Interface
    
    The inherited class must have the following attributes:
    index : target lens
 conf_key : config key
    """
    menu = None #"Maintenance/&1-Focus"
    category = "Focus Maintenance"
    
    default_threshold = 0.05 # spot size ratio to the shape of image
    
    def Init(self):
        self.threshold = LParam("Threshold", (0.005, 0.1, 0.005), self.default_threshold)
        
        self.layout(None, (
            wxpj.Button(self, "Spot", lambda v: self.focus(), icon='exe'),
            wxpj.Button(self, "Wide/4", lambda v: self.focus(1/4), icon='exe'),
            ),
            row=3,
        )
        self.layout("Manual calibration", (
            wxpj.Button(self, ":Spot beam", self.set_spot_beam_manually, icon='+'),
            wxpj.Button(self, ":Wide beam", self.set_wide_beam_manually, icon='+'),
            (),
            wxpj.Button(self, "Cal", lambda v: self.thread.Start(self.cal), icon='cal'),
            wxpj.Button(self, "Save", lambda v: self.config.save(self.conf_key), icon='save'),
            wxpj.Button(self, "Load", lambda v: self.config.load(self.conf_key), icon='proc'),
            
            self.threshold,
            ),
            row=3, show=1, type='vspin', cw=-1, lw=-1, tw=40,
        )
        self.layout("Function test", (
            wxpj.Button(self, ":Find", lambda v: self.thread.Start(self.find_beam)),
            wxpj.Button(self, ":Spot", lambda v: self.thread.Start(self.find_spot_beam)),
            wxpj.Button(self, ":plot", lambda v: self.logger.plot_data()),
            wxpj.Button(self, ":clear", lambda v: self.logger.clear_data()),
            ),
            row=4, show=0, visible=1,
        )
        self.logger = DataLogger()
    
    def set_current_session(self, session):
        self.threshold.value = session.get('threshold')
    
    def get_current_session(self):
        return {
            'threshold': self.threshold.value,
        }
    
    ## (cl3spot, cl3sens) for MAG,LOWMAG
    ## (il1spot, il1sens) for DIFF
    
    ## virtual property: get_spot_beam --> (xo, ys)
    ## virtual function: set_spot_beam <-- (xo, ys)
    
    conf_table = property(
        lambda self: self.get_spot_beam(),
        lambda self,v: self.set_spot_beam(v))
    
    def set_spot_beam_manually(self, evt=None):
        """Set the current index value to the spot beam manually"""
        xo = self.index
        self.set_spot_beam((xo, None))
    
    def set_wide_beam_manually(self, evt=None):
        """Calculate sensitivity using the current beam condition manually
        Note: the index value of :Spot beam must be set in advance.
        """
        xo, ys = self.conf_table
        x = self.index
        y,_p,_q = self.detect_beam_diameter() # y=None: 輪郭がありません
        ys = 2 * xo * y / (x**2 - xo**2)
        self.set_spot_beam((xo, ys))
    
    def focus(self, stride=0):
        h, w = self.camera.shape
        xo, ys = self.conf_table
        self.index = xo + stride * h / ys
    
    def cal(self, step=None, maxiter=3):
        self.logger.clear_data()
        try:
            h, w = self.camera.shape
            xo, ys = self.conf_table # [pix/bit]
            step = step or h / ys * 0.1 # (config) 初期設定値をもとにステップを決める
            if step > 0x800: step = 0x800
            elif step < 0x80: step = 0x80
            
            threshold = self.threshold.value
            temp = [xo, h]
            org = self.index
            for i in range(maxiter):
                if not self.thread.is_active: # quit the thread
                    self.index = org
                    return -1
                
                ret = self.find_spot_beam(step)
                if not ret:
                    return False
                
                xo, yo, yso = ret
                if yo < temp[1]:
                    temp = [xo, yo] # update data of which yo is minimum
                
                if abs(yso) > abs(ys):
                    ys = yso            # update data of which |ys| is maximum
                    step = h / ys * 0.1 # update amplitude for next iteration
                
                r = yo / h
                print(" "*i, "[{}] {:g}".format(i, r), r<threshold, "$(ys)={:g}".format((ys)))
                if r < threshold:
                    self.update_config(temp)
                    return True
            
            ## ループ範囲内では，よい条件が見つからなかった
            xo, yo = temp
            print("- Result (={:g}) exceeds threshold (> {})".format(yo/h, threshold),
                  "at illumination mode {}".format(self.illumination.Selector))
            
            ## テスト範囲内での最良値をとりあえず入れておく
            self.update_config(temp)
            return False
        
        except Exception:
            self.index = org
            raise
    
    def update_config(self, vo):
        xo, yo = vo
        q, y = self.logger.data # 最大位置 (x,y) と最小位置 (xo,yo) から計算する
        k = np.argmax(y)
        ys = 2 * xo * y[k] / (q[k] - xo**2)
        self.set_spot_beam((xo, ys))
    
    ## --------------------------------
    ## Beam finder methods
    ## --------------------------------
    ## `logger は共通なので，それぞれのルーチンを使用する前にあらかじめクリアする
    ## `logger being a common object, :clear must be called every time before used.
    
    def find_beam(self, step=0x400):
        """Beam finder ver.2 現在位置から強度のピーク位置を推定する
        ▲dark 補正していない強度では正しく見積もることはできない
        x = 1/f ∝ J**2
        y = 1/√p ∝ R  (カウント総数 N がわからないので R-比例係数は未定)
        """
        self.logger.clear_data()
        xj = self.index
        if not 0 <= xj + step <= 0xffff:
            step = -step
        for i in range(3):
            el, p, q = self.detect_ellipse()
            self.logger.update_data(xj**2, 1/np.sqrt(p))
            xj += step
            self.index = xj
        
        x, y = self.logger.data
        ## a, b = np.polyfit(x, y, 1) # y = a*x + b # ２点補間で探す
        ## self.index = np.sqrt(-b/a) # クロスオーバーを挟むと NG ↓以下に変更
        ## ▼
        yss = np.diff(y) / np.diff(x)
        k = np.argmax(abs(yss))
        xq = x[k] - y[k] / yss[k] # 傾きが最大となる方から線形補外する
        if xq > 0:
            xo = np.sqrt(xq)
            self.index = xo
            el, p, q = self.detect_ellipse()
            return el and self.is_signal(p, q)
    
    def find_spot_beam(self, step=0x80):
        """Spot finder 3点計測法
        x = 1/f ∝ J**2
        y = d: Diameter of the spot (Total counts N := p * (pi/4 * d*d))
        """
        xj = self.index
        if not 0 <= xj + 2*step <= 0xffff:
            step = -step
        for i in range(3):
            yo,_p,_q = self.detect_beam_diameter()
            if yo is None:
                return
            self.logger.update_data(xj**2, yo)
            xj += step
            self.index = xj
        
        x, y = self.logger.data
        dx = np.diff(x)
        dy = np.diff(y)
        yss = dy/dx
        k = np.argmax(abs(yss))
        xq = x[k] - y[k] / yss[k] # 傾きが最大となる方から線形補外する
        if xq > 0:
            xo = np.sqrt(xq)
            self.index = xo
            yo,_p,_q = self.detect_beam_diameter()
            self.logger.update_data(xq, yo)
            ## ys = dy[k] / step
            ys = 2 * xo * yss[k]
            return xo, yo, ys


class AlignInterface(TemInterface):
    """Alignment Algorithm/Interface
    
    The inherited class must have the following attributes:
    index : target alignment coil
 conf_key : config key
    * The inherited class can also have optionals to customize config accesser:
    * conf_arg : index (int or tuple) to withdraw value from conf_table matrix
    * conf_factor : factor [um/pix][mrad/pix] mul-commit and div-checkout
    """
    menu = None #"Maintenance/&Deflector"
    category = "Deflector Maintenance"
    
    def Init(self):
        self.layout(None, (
            wxpj.Button(self, "{}".format(self.caption),
                lambda v: self.thread.Start(self.align), icon='exe'),
            ),
        )
        self.layout("Manual calibration", (
            wxpj.Button(self, "Cal", lambda v: self.thread.Start(self.cal), icon='cal'),
            wxpj.Button(self, "Save", lambda v: self.config.save(self.conf_key), icon='save'),
            wxpj.Button(self, "Load", lambda v: self.config.load(self.conf_key), icon='proc'),
            ),
            row=4, show=1,
        )
    
    conf_table = property(
        lambda self: self.get_conf_array(),
        lambda self,v: self.set_conf_array(v))
    
    ## デフォルトは 照射系 Spot に依存しない系とする
    conf_arg = property(lambda self: self.illumination.Alpha)
    
    ## 通常は mag_unit(cam_unit と同じ) に依存する
    conf_factor = property(lambda self: self.mag_unit)
    
    def get_conf_array(self):
        """Get config table [pix/bit]"""
        ## i = self.illumination.Alpha
        return self.config[self.conf_key][self.conf_arg] / self.conf_factor
    
    def set_conf_array(self, v):
        """Set config table [pix/bit] --> [um/bit]"""
        ## i = self.illumination.Alpha
        self.config[self.conf_key][self.conf_arg] = v * self.conf_factor
    
    @property
    def M(self):
        """Inverse matrix [bit/pix]"""
        m = self.conf_table.reshape(2,2)
        ## try:
        ##     a0 = self.config['rotation'] # std rotation angles of IL
        ##     a = self.calc_imrot(self.Tem.IL_LENSES) # get present rotation
        ##     t = (a - a0) * pi/180
        ##     c = cos(t)
        ##     s = sin(t)
        ##     R = np.array(((c, -s), (s, c)))
        ##     Ri = np.array(((c, s), (-s, c)))
        ##     m = np.dot(R, np.dot(m, Ri))
        ## except KeyError:
        ##     pass
        return np.linalg.inv(m)
    
    def align(self, pos=None, power=1):
        if pos is None:
            h, w = self.camera.shape
            pos = (w/2, h/2) # target position be the center of the screen
        try:
            org = self.index
            c, p, q = self.detect_beam_center()
            if c is None:
                return False
            self.index = org - np.dot(self.M, c-pos) * power
            return True
        except Exception:
            self.index = org
            raise
    
    def cal(self, step=None, maxiter=3):
        ## try:
        ##     self.config['rotation'] = self.calc_imrot(self.Tem.IL_LENSES) # set std rotation angles of IL
        ## except KeyError as e:
        ##     print("$(e) = {!r}".format((e)))
        ##     pass
        
        h, w = self.camera.shape
        m = self.conf_table
        ys = np.hypot(m[0], m[2])   # [pix/bit]
        step = step or h / ys * 0.1 # (config) 初期設定値をもとにステップを決める
        if step < 0x10:
            step = 0x10 # set minimum step
        ## elif step > 0x2000:
        ##     step = 0x2000 # set maximum step
        try:
            org = self.index
            xo, yo = org
            c, p, q = self.detect_beam_center()
            if c is None:
                return
            
            for i in range(maxiter):
                if not self.thread.is_active: # quit the thread
                    return -1
                self.index = (xo+step, yo)
                u, p_, q_ = self.detect_beam_center()
                if u is None or p_/p < 0.5:
                    step /= 2 # try again with smaller step
                else: break
            else: return
            
            for i in range(maxiter):
                if not self.thread.is_active: # quit the thread
                    return -1
                self.index = (xo, yo+step)
                v, p_, q_ = self.detect_beam_center()
                if u is None or p_/p < 0.5:
                    step /= 2 # try again with smaller step
                else: break
            else: return
            
            m = np.vstack((u-c, v-c)).T / step
            self.set_conf_array(m.flatten())
            return True
        
        finally:
            self.index = org


class StigInterface(AlignInterface):
    """Stigmator Algorithm/Interface
    Note: The spot focus stride (1/4) must be fixed and *DO NOT CHANGE*
    
    The inherited class must have the following attributes:
    index : target stigmator coil
 conf_key : config key
    """
    menu = None #"Maintenance/&Stigmator"
    category = "Stigmator Maintenance"
    
    threshold = 0.005 # to be less than 0.5% aspect ratio
    
    def align(self):
        ## self.spot.focus(0.25)
        maxiter = 5
        for i in range(maxiter):
            xo, yo = self.index
            c = self.eval_beam_roundness()
            if c is None:
                return
            val = np.all(abs(c-1) < self.threshold)
            print(" "*i, "[{}] Roundness =".format(i), c, val, end='') # check the roundness in the criteria
            if val:
                print(" < {:g}".format(np.hypot(*(c-1))))
                return True
            print()
            self.index = (xo, yo) - np.dot(self.M, c-1)
        return False
    
    def cal(self, step=None):
        ## self.spot.focus(0.25)
        step = step or 0x800
        try:
            org = self.index
            xo, yo = (0x8000, 0x8000) # 中点から始める
            self.index = (xo, yo)
            c = self.eval_beam_roundness()
            if c is None:
                return
            
            self.index = (xo+step, yo)
            u = self.eval_beam_roundness()
            
            self.index = (xo, yo+step)
            v = self.eval_beam_roundness()
            
            m = np.vstack((u-c, v-c)).T / step
            self.set_conf_array(m.flatten())
            self.index = (xo, yo) - np.dot(np.linalg.inv(m), c-1) # adjust once,
            return True
        
        except Exception:
            self.index = org
            raise
    
    def eval_beam_roundness(self):
        """Roundness R1 := Y1/X1, R2 := Y2/X2
        """
        el, p, q = self.detect_ellipse()
        if el and self.is_signal(p, q):
            c, (ra,rb), angle = el
            ## e = np.sqrt(rb / ra) - 1
            x = rb / ra
            e = (x-1) / (x+1)
            t = (90-angle) * pi/90
            R1 = (1 - e * cos(t)) / (1 + e * cos(t))
            R2 = (1 - e * sin(t)) / (1 + e * sin(t))
            return np.array((R1, R2))


class CompInterface(TemInterface):
    """Compensation Algorithm/Interface
    
    The inherited class must have the following attributes:
    index : target compensator coil
  wobbler : wobbler coil property
 conf_key : config key
deflector : deflector to offset beam (shift or tilt)
    """
    menu = None #"Maintenance/&Compensator"
    category = "Compensation Maintenance"
    
    default_threshold = 0.005 # wobbler 変更に対するビーム位置の変化(率
    default_wobstep = 0x800
    default_wobsec = 0.5
    
    def Init(self):
        self.threshold = LParam("Threshold", (0.005, 0.05, 0.005), self.default_threshold)
        self.wobstep = LParam("Wobbler amp", (0x100,0x1000,0x100), self.default_wobstep, dtype=hex)
        self.wobsec = LParam("Wobbler sec", (0, 1, 0.1), self.default_wobsec)
        
        self.layout(None, (
            wxpj.Button(self, "{}".format(self.caption),
                lambda v: self.thread.Start(self.cal), icon='exe'),
            ),
        )
        self.layout("Manual calibration", (
            wxpj.Button(self, "Save", lambda v: self.config.save(self.conf_key), icon='save'),
            wxpj.Button(self, "Load", lambda v: self.config.load(self.conf_key), icon='proc'),
            
            self.threshold, (),
            self.wobstep, (),
            self.wobsec, (),
            ),
            row=2, show=1, type='vspin', cw=-1, lw=-1, tw=40,
        )
    
    def set_current_session(self, session):
        self.threshold.value = session.get('threshold')
        self.wobstep.value = session.get('wobstep')
        self.wobsec.value = session.get('wobsec')
    
    def get_current_session(self):
        return {
            'threshold': self.threshold.value,
            'wobstep': self.wobstep.value,
            'wobsec': self.wobsec.value,
        }
    
    @property
    def conf_table(self):
        i = self.illumination.Alpha
        return self.config[self.conf_key][i]
    
    def cal(self, step=None):
        """Adjust X-comp-ratio and Y-comp-ratio"""
        step = step or 0x100
        return all([self.cal_comp(0, step),
                    self.cal_comp(1, step),])
    
    def cal_comp(self, k, step=0x80, maxiter=5):
        ## self.spot.focus()
        self.deflector.align()
        if k == 0:
            step = [step, 0]
            wstep = [self.wobstep.value, 0]
        else:
            step = [0, step]
            wstep = [0, self.wobstep.value]
        try:
            h, w = self.camera.shape
            org = xj = self.index
            worg = self.wobbler
            threshold = self.threshold.value
            temp = [xj, 1.]
            for i in range(maxiter):
                if not self.thread.is_active: # quit the thread
                    self.index = org
                    return -1
                
                X1 = xj
                self.index = X1
                self.deflector.align()
                O1,_p,_q = self.detect_beam_center() # [o,r1] := [wobbler, index]
                if O1 is None:
                    return
                
                self.wobbler = worg + wstep
                self.delay(self.wobsec.value)
                P1,_p,_q = self.detect_beam_center() # [w,r1]
                if P1 is None:
                    print("- wobbler step out of range; {:#x}".format(wstep))
                    wstep[k] //= 2 # lost beam center; halve the amplitude
                    self.wobstep.value //= 2 # update original value
                    continue
                
                X2 = xj + step
                self.index = X2
                P2,_p,_q = self.detect_beam_center() # [w,r2]
                
                self.wobbler = worg
                self.delay(self.wobsec.value)
                O2,_p,_q = self.detect_beam_center() # [o,r2]
                
                if O2 is None or P2 is None:
                    step[k] //= 2 # lost beam center; halve the amplitude
                    print("- index step out of range; conitnue with step={}".format(step))
                    continue
                
                x1 = X1[k]
                x2 = X2[k]
                y1 = P1 - O1
                y2 = P2 - O2
                d1 = np.linalg.norm(y1)
                d2 = np.linalg.norm(y2)
                rd = min(d1, d2) / h
                if rd < temp[1]:
                    temp = [X1 if d1 < d2 else X2, rd]
                
                print(" "*i, "[{}] {:g}".format(i, rd), rd < threshold)
                if rd < threshold:
                    xj = X1 if d1 < d2 else X2
                    self.index = xj
                    self.deflector.align()
                    self.conf_table[:] = xj # overwrite config raw-table
                    return True
                
                ## 方位 (符号) を含めて推定値 x0 (原点に一番近いところ) を求める．
                ## Y1, Y2 は平面空間上の点だが，基本的にはおなじみの N-R 法．
                ys = (y2-y1) / (x2-x1)
                u1, v1 = y1
                u2, v2 = y2
                t = np.arctan2(u1-u2, v2-v1)
                r = u1 * cos(t) + v1 * sin(t)
                y0 = (r * cos(t), r * sin(t))
                x0 = x1 - min((y1-y0) / ys) # @min eliminates inf
                ## x0 = x1 - min(np.divide(y1-y0, ys)) # (y1-y0)/ys @min eliminates inf
                
                ## comp-ratio を推定値 x0 に変更し仮想シフト量をキャンセルする
                a = (O2-O1) / (x2-x1)
                p = O1 - a * (x1 - x0)
                self.deflector.align((w,h) - p) # q = o + (o-p)
                xj[k] = int(x0)
                
            ## ループ回数範囲内では，よい条件が見つからなかった
            ## テスト範囲内での最良値をとりあえず入れておく
            xj, rd = temp
            self.index = xj
            print("- Result (={:g}) exceeds threshold (> {})".format(rd, threshold),
                  "at mode {!r}".format(self.illumination.Selector))
            return False
        
        except Exception:
            self.index = org
            raise
        finally:
            self.wobbler = worg

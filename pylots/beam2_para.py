#! python
# -*- coding: utf-8 -*-
from mwx import LParam
from mwx.graphman import Layer
from pylots.temixins import TemInterface, TEM
import wxpyJemacs as wxpj


class Plugin(TemInterface, Layer):
    """Plugin of focus adjustment
    Adjust para-beam-focus [spot/alpha] using OL
    so that the beam diameter fluctuation gets minimum.
    """
    menu = None #"&Maintenance/&1-Focus"
    category = "1-Focus Maintenance"
    caption = "Para"
    conf_key = ('cl3para', 'cl3dia')
    index = TEM.CL3
    wobbler = TEM.OL
    
    default_threshold = 0.005 # wobbler 変更に対するビーム径の変化(率
    default_wobstep = 0x1000 # olstep = 0x1000 => OLdf=12um
    default_wobsec = 1.0
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    shift = property(lambda self: self.parent.require('beam_shift'))
    
    def Init(self):
        self.threshold = LParam("Threshold", (0.005, 0.05, 0.005), self.default_threshold)
        self.wobstep = LParam("Wobbler amp", (0x100,0x10000,0x100), self.default_wobstep, dtype=hex)
        
        self.layout(None, (
            wxpj.Button(self, "Parallel focus", lambda v: self.focus(), icon='exe'),
            ),
        )
        self.layout("Manual calibration", (
            wxpj.Button(self, ":Paralell beam", self.set_para_beam_manually, icon='+'),
            (),
            (),
            wxpj.Button(self, "Cal", lambda v: self.thread.Start(self.cal), icon='cal'),
            wxpj.Button(self, "Save", lambda v: self.config.save(self.conf_key), icon='save'),
            wxpj.Button(self, "Load", lambda v: self.config.load(self.conf_key), icon='proc'),
            
            self.threshold, (), (),
            self.wobstep,
            ),
            row=3, show=1, type='vspin', tw=40,
        )
    
    def set_current_session(self, session):
        self.threshold.value = session.get('threshold')
        self.wobstep.value = session.get('wobstep')
    
    def get_current_session(self):
        return {
            'threshold': self.threshold.value,
            'wobstep': self.wobstep.value,
        }
    
    conf_table = property(
        lambda self: self.get_para_beam(),
        lambda self,v: self.set_para_beam(v))
    
    def get_para_beam(self):
        r = self.CLAPT.dia /100
        i = self.illumination.Selector
        j, k = self.conf_key
        xp = self.config[j][i]
        yp = self.config[k][i] * r
        return xp, yp
    
    def set_para_beam(self, v):
        r = self.CLAPT.dia /100
        i = self.illumination.Selector
        j, k = self.conf_key
        xp, yp = v
        self.config[j][i] = int(xp)
        self.config[k][i] = abs(yp) * self.mag_unit / r #= dia[um]
    
    def set_para_beam_manually(self, evt=None):
        """Set the current index value to the Parallel beam manually"""
        xp = self.index
        yp = self.eval_diameter() # yp=None: 輪郭がありません
        self.set_para_beam((xp, yp))
    
    def eval_diameter(self):
        d, p, q = self.detect_beam_diameter()
        return d
    
    def focus(self):
        i = self.illumination.Selector
        j = self.conf_key[0]
        self.index = self.config[j][i]
    
    def cal(self):
        maxiter = 3
        with self.save_excursion(mmode='MAG'):
            try:
                h, w = self.camera.shape
                xo, ys = self.spot.conf_table
                step = h / ys * 0.05
                
                org = xj = self.index
                if xj < xo:
                    xj = xo + step * 2 # reset index when lower than expected xo point
                    if xj > 0xffff:
                        xj = 0xffff
                        step = -step # negate step, index starting from 0xffff
                
                worg = self.wobbler
                wstep = self.wobstep.value
                threshold = self.threshold.value
                temp = [xj, 1.]
                for i in range(maxiter):
                    if not self.thread.is_active:
                        return -1
                    
                    if not 0 <= xj + step <= 0xffff:
                        step = -step
                    
                    x1 = xj
                    self.index = x1
                    self.shift.align()
                    o1 = self.eval_diameter() # [o,x1] := [wobbler, index]
                    if o1 is None:
                        return
                    
                    self.wobbler = worg + wstep
                    self.delay(self.default_wobsec)
                    p1 = self.eval_diameter() # [w,x1]
                    if p1 is None:
                        print("- wobbler step is out of range; {}".format(wstep))
                        wstep /= 2 # lost beam center; halve the amplitude
                        continue
                    
                    x2 = xj + step
                    self.index = x2
                    p2 = self.eval_diameter() # [w,x2]
                    
                    self.wobbler = worg
                    self.delay(self.default_wobsec)
                    o2 = self.eval_diameter() # [o,x2]
                    
                    if o2 is None or p2 is None:
                        ## CLAPT が大きすぎるか，倍率が高すぎるため，検出不能
                        self.imaging.Mag /= 2
                        continue
                    
                    y1 = p1 - o1
                    y2 = p2 - o2
                    d1 = abs(y1)
                    d2 = abs(y2)
                    rd = min(d1, d2) / h
                    if rd < temp[1]:
                        temp = [x1 if d1 < d2 else x2, rd]
                    
                    print(" "*i + "[{}] {:g}".format(i, rd), rd < threshold)
                    if rd < threshold:
                        xp, yp = (x1, o1) if d1 < d2 else (x2, o2)
                        self.index = xp
                        self.set_para_beam((xp, yp))
                        return True
                    
                    ys = (y2-y1) / (x2-x1)
                    xj = x1 - y1/ys # 推定値 (index)
                    
                    if xj > 0xffff:
                        xj = 0xffff
                        print("- Abort: the index reached the maximum.")
                        temp[0] = xj
                        break
                    elif xj < 0:
                        return None # bad result
                    
                    a = (o2-o1) / (x2-x1)
                    p = o1 - a * (x1 - xj) # 推定ビームサイズ
                    
                    ## self.imaging.Mag *= h /p /1.41421356 ▲
                
                ## ループ範囲内では，よい条件が見つからなかった
                xj, rd = temp
                print("- Result (={:g}) exceeds threshold (> {:g})".format(rd, threshold),
                      "at illumination mode {}".format(self.illumination.Selector))
                
                ## テスト範囲内での最良値をとりあえず入れておく
                self.index = xj
                p = self.eval_diameter()
                self.set_para_beam((xj, p))
                return False
            
            except Exception:
                self.index = org
                raise
            finally:
                self.wobbler = worg
    
    def execute(self):
        ## alpha-specific mags given apriori▲
        mags_apriori = [50e3, 30e3, 20e3, 12e3, 10e3, 8e3, 8e3, 8e3,]
        ret = True
        with self.thread:
            with self.save_excursion(mmode='MAG'):
                with self.save_restriction(CLAPT=3, SAAPT=0):
                    for a in self.for_each_alpha():
                        self.imaging.Mag = mags_apriori[a]
                        self.spot.focus(0.5)
                        ret &= all([self.cal() for s in self.for_each_spot()])
        return ret

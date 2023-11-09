#! python3
"""PyJEM facade of the Poor man's PyJEM

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from collections import OrderedDict
import time
import numpy as np
from numpy import inf
try:
    from temisc import mrange
    from temisc import FLHex, OLHex
    from legacy import info, cmdl, cntf 
    from legacy import LensSystem, DeflSystem, FocusSystem
except ImportError:
    from .temisc import mrange
    from .temisc import FLHex, OLHex
    from .legacy import info, cmdl, cntf 
    from .legacy import LensSystem, DeflSystem, FocusSystem

Command = cmdl.Command
NotifyCommand = cntf.NotifyCommand

ioget = Command("X900", "!I", "!H", doc="Get I/O data")
ioset = Command("X901", "!IH", None, doc="Set I/O data")


## --------------------------------
## PMPJ GLOBAL NAME AND THE CLASSE 
## --------------------------------
## MAJOR_MODE = 'TEM', 'STEM'
## USER_MODE  = 'MAINT', 'USER', 'STDBASE'

def uhex(v, vmax=0xffff):
    if v < 0: return 0
    elif v > vmax: return vmax
    else: return int(v)

def staticproperty(name):
    def fget(self):
        TEM.fsys.read()
        return TEM.fsys[name].value
    def fset(self, v):
        TEM.fsys.Write(name, uhex(v))
    return property(fget, fset)

def static2property(xname, yname):
    def fget(self):
        TEM.dsys.read()
        return np.array((TEM.dsys[xname].value,
                         TEM.dsys[yname].value))
    def fset(self, v):
        TEM.dsys.Write(xname, uhex(v[0]))
        TEM.dsys.Write(yname, uhex(v[1]))
    return property(fget, fset)


class TEM(object):
    """TEM Lens/Defl system
    
    通常は，このクラスを基底クラスとしてプロパティを継承／使用するが，
    self に依存しないので静的プロパティ (static property) としてアクセス可．
    
    Normally, properties are inherited/used with this class as the base class,
    but since they do not depend on self, they can be accessed as static properties.
    
    [Lens/Defl]
    LensParam は，アクセスされるたびに値を読み取るように動作しますが，
    一つのコイルにアクセスすると，システムクラスの全コイルが更新されます．
    オーバーヘッドを避けるため，いったん，コイルの値にアクセスしたら，
    その後はシステムクラスから値を取得できます．
    
    LensParam works to read the value each time it is accessed,
    but accessing one coil updates the entire system class coils.
    To avoid overhead, once the value of a coil is accessed,
    the value can be retrieved from the system class.
    
    [fsys/lsys/dsys]
    通常 system によって 0.5s 以内に通知が行われます．
    読み出し速度が重要でないい場合は，これらのオブジェクトを参照してください．
    
    Normally, the system will notify them within 0.5s.
    If read speed is not important, refer to these objects.
    """
    ## _set_br_defocus = Command("E151", "!h", None) # Brightness:link 相対値
    ## _set_ol_defocus = Command("E154", "!h", None) # OBJ  Focus:link 相対値
    ## _set_df_defocus = Command("E157", "!h", None) # DIFF Focus:link 相対値
    _set_il_focus = Command("E159", "!h", None) # IL Focus
    _set_pl_focus = Command("E162", "!h", None) # PL Focus
    _set_fl_focus = Command("E165", "!h", None) # FL Focus
    
    lsys = LensSystem()  # Lens Free Control System
    dsys = DeflSystem()  # Deflector system
    fsys = FocusSystem() # Focus system
    
    foci = fsys  #: for backward compatibility
    
    def __getitem__(self, name):
        return getattr(self, name)
    
    def __setitem__(self, name, v):
        return setattr(self, name, v)
    
    GUNA1 = static2property('GUNA1X', 'GUNA1Y')
    GUNA2 = static2property('GUNA2X', 'GUNA2Y')
    SPOTA = static2property('SPOTAX', 'SPOTAY')
    CLA1 = static2property('CLA1X', 'CLA1Y')
    CLA2 = static2property('CLA2X', 'CLA2Y')
    SHIFT = static2property('SHIFTX', 'SHIFTY')
    TILT = static2property('TILTX', 'TILTY')
    ANGLE = static2property('ANGLEX', 'ANGLEY')
    CLS = static2property('CLSX', 'CLSY')
    OLS = static2property('OLSX', 'OLSY')
    ILS = static2property('ILSX', 'ILSY')
    IS1 = static2property('IS1X', 'IS1Y')
    IS2 = static2property('IS2X', 'IS2Y')
    PLA = static2property('PLAX', 'PLAY')
    FLA1 = static2property('FLA1X', 'FLA1Y')
    FLA2 = static2property('FLA2X', 'FLA2Y')
    FLS1 = static2property('FLS1X', 'FLS1Y')
    FLS2 = static2property('FLS2X', 'FLS2Y')
    
    SCAN1 = static2property('SCAN1X', 'SCAN1Y') # No getter
    SCAN2 = static2property('SCAN2X', 'SCAN2Y') # No getter
    STEMIS = static2property('STEMISX', 'STEMISY')
    MagAdjust = static2property('MagAdjust_H', 'MagAdjust_V') # No setter
    Correction = static2property('Correction_H', 'Correction_V') # No setter
    Rotation = static2property('Rotation_H', 'Rotation_V') # No setter
    Offset = static2property('Offset_H', 'Offset_V') # No setter
    
    CL1 = staticproperty('CL1')
    CL2 = staticproperty('CL2')
    CL3 = staticproperty('CL3')
    CM  = staticproperty('CM' )
    OLC = staticproperty('OLC')
    OLF = staticproperty('OLF')
    OM  = staticproperty('OM1')
    IL1 = staticproperty('IL1')
    IL2 = staticproperty('IL2')
    IL3 = staticproperty('IL3')
    IL4 = staticproperty('IL4')
    PL1 = staticproperty('PL1')
    PL2 = staticproperty('PL2')
    PL3 = staticproperty('PL3')
    FLC = staticproperty('FLC')
    FLF = staticproperty('FLF')
    FLCOMP1 = staticproperty('FLCOMP1')
    FLCOMP2 = staticproperty('FLCOMP2')
    
    @property
    def FL(self):
        TEM.fsys.read()
        return FLHex(TEM.fsys['FLC'].value,
                     TEM.fsys['FLF'].value).value
    
    @FL.setter
    def FL(self, v):
        u = FLHex(0, uhex(v, FLHex.maxval))
        TEM.fsys.Write('FLC', u.coarse)
        TEM.fsys.Write('FLF', u.fine)
    
    @property
    def OL(self):
        TEM.fsys.read()
        return OLHex(TEM.fsys['OLC'].value,
                     TEM.fsys['OLF'].value).value
    
    @OL.setter
    def OL(self, v):
        u = OLHex(0, uhex(v, OLHex.maxval))
        TEM.fsys.Write('OLC', u.coarse)
        TEM.fsys.Write('OLF', u.fine)
    
    Brightness = CL3
    DiffFocus = IL1
    ObjFocus = OL
    ILFocus = NotImplemented
    PLFocus = PL1
    FLFocus = FL


class Optics(object):
    """Optics mode base(mixin) class
    
    The inherited class must have MODES and Info which is to be notified.
    The request command complementary to the notify must be defined as _get_info.
    The Mode.setter can only function if the class has a request command _set_mode.
    The Selector.setter can only function if the class has a request command _set_index.
    """
    @classmethod
    def request(self, key=None):
        i = self.Info(self._get_info())
        return i[key] if key else i
    
    ## @classmethod
    ## def refer(self, key=None):
    ##     i = self.Info
    ##     return i[key] if key else i
    
    @property
    def Name(self):
        """mode-specific name"""
        j = self.Mode
        if j is not None:
            return list(self.MODES)[j]
    
    @property
    def Mode(self):
        """mode-specific index"""
        return self.request('mode')
    
    @Mode.setter
    def Mode(self, v):
        if isinstance(v, str):
            v = list(self.MODES).index(v)
        j = int(v)
        if 0 <= j < len(self.MODES):
            if j != self.Mode:
                self._set_mode(j)
        else:
            raise IndexError("Mode index out of range")
    
    @property
    def Selector(self):
        """submode-specifc index e.g., spot/alpha, mag, cam, and disp"""
        return self.request('index')
    
    @Selector.setter
    def Selector(self, v):
        if isinstance(v, (list, tuple)):
            self._set_index(v)
        elif v >= 0:
            self._set_index(int(v))
    
    @property
    def Range(self):
        """mode-specific range"""
        j = self.Mode
        if j is not None:
            return list(self.MODES.values())[j]


class Illumination(Optics):
    """Illumination system
    """
    MODES = OrderedDict(( # number of (spot, alpha)
        ('TEM',     (8, 8)),
        ('Koehler', (8, 2)),
    ))
    
    Info = info.Illumination_info()
    
    _get_info = Command("E055", None, "!H10sHH10s")
    _set_mode = Command("E050", "!H", "!H")
    _set_spot = Command("E054", "!H", "!H")
    _set_alpha = Command("E052", "!H", "!H")
    
    def _set_index(self, v):
        self.Spot, self.Alpha = v
    
    @property
    def Spot(self):
        return self.request('spot')
    
    @Spot.setter
    def Spot(self, v):
        if 0 <= v != self.Spot:
            self._set_spot(int(v))
    
    @property
    def Alpha(self):
        return self.request('alpha')
    
    @Alpha.setter
    def Alpha(self, v):
        if 0 <= v != self.Alpha:
            self._set_alpha(int(v))


class Imaging(Optics):
    """Imaging system
    """
    MODES = OrderedDict((
        ('MAG',    mrange(1000, 1.2e6)),
        ('MAG2',   mrange(1000, 1.2e6)),
        ('LOWMAG', mrange(  50,  50e3)),
        ('SAMAG',  mrange(1000, 500e3)),
        ('DIFF',   mrange( 300,  5000)),
    ))
    
    Info = info.Imaging_info()
    
    _get_info = Command("E015", None, "!H10sHI10s10s")
    _set_mode = Command("E010", "!H", "!H")
    _set_index = Command("E012", "!H", "!H")
    
    @property
    def Mag(self):
        return self.request('value')
    
    @Mag.setter
    def Mag(self, v):
        if v != self.Mag:
            lm = self.Range
            k = np.searchsorted(lm, v)
            if k < len(lm):
                self._set_index(int(k))
            else:
                raise IndexError("Mag index is out of range: {}".format(v))


class Omega(Optics):
    """Omega/Projection system
    """
    MODES = OrderedDict((
        ('Imaging', (0,)),
        ('Spectrum', mrange(100, 250)), # um/eV
    ))
    
    Info = info.Omega_info()
    
    _get_info = Command("E016", None, "!HH10sHI10s10s")
    _set_mode = Command("E620", "!H", "!2H2I2H2IH5dH")
    _set_index = Command("E614", "!H", "!H")
    
    @staticmethod
    def isEnabled():
        return 'Spectrum' in Omega.MODES
    
    @property
    def Dispersion(self):
        return self.request('value')
    
    @Dispersion.setter
    def Dispersion(self, v):
        if v != self.Dispersion:
            lm = self.Range
            k = np.searchsorted(lm, v)
            if k < len(lm):
                self._set_index(int(k))
            else:
                raise IndexError("Dispersion index is out of range: {}".format(v))


## --------------------------------
## PMPJ GLOBAL INSTRUMENTAL CLASSE 
## --------------------------------

class Device(object):
    """Device base class mixin
    """
    @classmethod
    def request(self, key=None):
        i = self.Info(self._get_info())
        return i[key] if key else i
    
    ## @classmethod
    ## def refer(self, key=None):
    ##     i = self.Info
    ##     return i[key] if key else i


class EOsys(Device):
    """EM device system
    """
    Info = info.Eos_info()
    
    _get_info = Command("E090", None, "!16HIH")
    
    _set_mode = Command("E000", "!H", "!H", device='ASID') # {0:TEM, 1:ASID}
    _get_mode = Command("E001", None, "!H", device='ASID') # => Info['major_mode']
    
    ## _get_v1_status = Command("F818", None, "!5I", device='VAC') # (V1,_,_,_,_,_)
    ## _get_v1_ready = staticmethod(lambda: EOsys._get_v1_status()[0] & 0b1011 == 0) # V1 all clear
    
    _set_v1_state = Command("F811", "!H", None, device='VAC') # {0:close, 1:open}
    _get_v1_state = Command("F817", None, "!H", device='VAC')
    
    _set_fscr = Command("C321", "!H", "!H", device='PHOTO') # ? FSCR {0:out, 1:in}
    _set_lscr = Command("C320", "!H", "!H", device='PHOTO') # o LSCR {0:0, 2:90} deg
    _get_scr = Command("C325", None, "!2H", device='PHOTO') # o LSCR {0:0, 2:90} deg, FSCR {0:out, 1:in}.
    
    _set_det = Command("D170", "!25H", None, device='ASID') # x ▼not supported
    _get_det = Command("D171", None, "!25H", device='ASID') # x ▼not supported
    
    ## for FEG only
    ## for LAB6-2100, V1open/close toggles emission
    V1 = property(
        lambda self: EOsys._get_v1_state()[0],
        lambda self,v: EOsys._set_v1_state(1 if v else 0),
        doc="Status of V1 valve.")
    
    LSCR = property(
        lambda self: EOsys._get_scr()[0],
        lambda self,v: EOsys._set_lscr(v if v else 0),
        doc="Status of LSCR {0:0, 1:7, 2:90} degs.")
    
    FSCR = property(
        lambda self: EOsys._get_scr()[1],
        lambda self,v: EOsys._set_fscr(1 if v else 0),
        doc="Status of FSCR {0:out, 1:in}.")
    
    @property
    def Screen(self):
        """Status of default screen."""
        lscr, fscr = EOsys._get_scr()
        return fscr==1 or lscr==0
    
    @Screen.setter
    def Screen(self, v):
        ## EOsys._set_fscr(0 if v else 1) # deprecated ?
        EOsys._set_lscr(0 if v else 2)


class HTsys(Device):
    """HT system
    """
    Info = info.HT_info()
    
    _get_info = Command("F902", None, "!19hi5h", device='HT')
    _set_htv = Command("F502", "!I", None, device='HT', cmdtype='ACK') # [0:130000:10V]
    
    _set_ems_state = Command("F200", "!H", "!H", device='HT') # {0:off, 1:on}
    _get_ems_state = staticmethod(lambda: HTsys.request("ems_state"))
    
    _set_a1 = Command("F220", "!h", "!h", device='HT')      # x [0:1000:10V] ▼not supported
    _set_a2 = Command("F221", "!h", "!h", device='HT')      # o [0:1000:10V]
    _set_a1_rel = Command("F210", "!h", "!h", device='HT')  # x [-1:1:10V] ▼not supported
    _set_a2_rel = Command("F211", "!h", "!h", device='HT')  # o [-1:1:10V]
    
    ## _start_cfeg_emission = Command("F204", "!H", "!H", device='HT')
    
    ht_value = property(
        lambda self: HTsys.request('ht_value'),
        lambda self,v: HTsys._set_htv(int(v/10)))
    
    A1 = property(
        lambda self: HTsys.request('A1'))
    
    A2 = property(
        lambda self: HTsys.request('A2'),
        lambda self,v: HTsys._set_a2(int(v / 10)))


class Aperture(Device):
    """Aperture system: Normal type (extype=0)
    """
    APERTURES = OrderedDict((
        ('NULL', ( inf, 150, 100, 50, 20)),
        ( 'CLA', ( inf, 150, 100, 50, 20)),
        ( 'OLA', ( inf,  60,  40, 30,  5)),
        ( 'HCA', ( inf, 120,  60, 20,  5)),
        ( 'SAA', ( inf, 100,  50, 20, 10)),
        ('ENTA', ( inf, 120,  60, 40, 20)),
        ( 'HXA', ( inf, 200,   0,  0,  0)),
    ))
    
    Info = info.Aperture_info()
    
    _get_info = Command("E405", None ,"!3H798s", device='APT') # extype=0
    _select_apt = Command("E400", "!H", "!H", device='APT')
    _set_sel = Command("E401", "!H", "!H", device='APT')
    _get_sel = Command("E406", "!H", "!H", device='APT')
    _get_pos = Command("E407", None, "!2H", device='APT')
    _set_pos = Command("E402", "!2H", "!2H", device='APT')
    
    @staticmethod
    def stop():
        for x in range(0,8,2):
            ioset(0xffff01c4 + x, 1)
            ioset(0xffff01c4 + x, 0)
    
    @classmethod
    def select_apt_name(self, name):
        return self._select_apt(list(self.APERTURES).index(name))
    
    def __init__(self, name):
        if name not in self.APERTURES:
            raise KeyError(name)
        self.name = name
        self.Id = list(self.APERTURES).index(name)
    
    def select(self):
        self._select_apt(self.Id)
        return True
    
    def select_hole(self, v):
        return self._select_apt(self.Id) and self._set_sel(int(v))
    
    @property
    def holes(self):
        return self.APERTURES[self.name]
    
    @property
    def pos(self):
        """selected hole position [2:int]"""
        if self.select():
            return np.array(self._get_pos())
    
    @pos.setter
    def pos(self, v):
        if self.select():
            self._set_pos(0, int(v[0]))
            self._set_pos(1, int(v[1]))
            
            ## 目標値と最終値は一致するとは限らない▼停止まで待つ
            for t in range(5): # timeout
                u = self.pos
                if sum(abs(u - v)) <= 1: # wait until stopped
                    break
                v = u
                time.sleep(1)
            ## else:
            ##     self.stop() #▲非常停止
    
    @property
    def sel(self):
        """selected hole number index"""
        return self.request(self.name)
    
    @sel.setter
    def sel(self, v):
        self.select_hole(int(v))
    
    @property
    def dia(self):
        """selected hole diameter value"""
        if self.sel is not None:
            return self.holes[self.sel]
    
    @dia.setter
    def dia(self, v):
        self.select_hole(self.holes.index(v))


class ApertureEx(Aperture):
    """Aperture system: Extended type (extype=1)
    """
    APERTURES = OrderedDict((
        ( 'CLA', ( inf, 150, 100, 50, 20)),
        ('CLA2', ( inf,  40,  30, 20, 10)),
        ( 'OLA', ( inf,  60,  40, 30,  5)),
        ( 'HCA', ( inf, 120,  60, 20,  5)),
        ( 'SAA', ( inf, 100,  50, 20, 10)),
        ('ENTA', ( inf, 120,  60, 40, 20)),
        ( 'HXA', ( inf, 200,   0,  0,  0)),
    ))
    
    Info = info.ApertureEx_info()
    
    _get_info = Command("E423", None, "!15H", device='APT') # extype=1
    _select_apt = Command("E421", "!H", "!H", device='APT')
    ## _select_hole2 = Command("E422", "!2H", "!2H", device='APT') # x ▼not supported
    
    @staticmethod
    def stop():
        ## 拡張絞りタイプ
        ioset(0xffff084e, 0) # x
        ioset(0xffff085e, 0) # y


class Stage(Device):
    """Stage (Gonio) system
    
    X,Y,Z unit [um] and TX,TY [deg]
    """
    Info = info.Gonio_info()
    
    _get_info = Command("G921", None, "!7d", device='GONIO')
    _get_status = Command("G920", None ,"!11H", device='GONIO') # (X,Y,Z,TX,TY,M/P,X+,Y+,Z+,TX+,TY+)
    
    ## _set_gonio = Command("G630", "!H5d", None, device='GONIO') # (0b11111,X,Y,Z,TX,TY) ▼not supported
    _set_xpos = Command("G631", "!d", None, device='GONIO')
    _set_ypos = Command("G632", "!d", None, device='GONIO')
    _set_zpos = Command("G633", "!d", None, device='GONIO')
    _set_xtilt = Command("G634", "!d", None, device='GONIO')
    _set_ytilt = Command("G635", "!d", None, device='GONIO')
    
    ## _set_gonio_rel = Command("G680", "!H5d", None, device='GONIO') # (0b11111,X,Y,Z,TX,TY) ▼not supported
    _set_xpos_rel = Command("G681", "!d", None, device='GONIO')
    _set_ypos_rel = Command("G682", "!d", None, device='GONIO')
    _set_zpos_rel = Command("G683", "!d", None, device='GONIO')
    _set_xtilt_rel = Command("G684", "!d", None, device='GONIO')
    _set_ytilt_rel = Command("G685", "!d", None, device='GONIO')
    
    X = property(
        lambda self: Stage.request('X') / 1e3,
        lambda self,v: Stage._set_xpos(v * 1e3))
    
    Y = property(
        lambda self: Stage.request('Y') / 1e3,
        lambda self,v: Stage._set_ypos(v * 1e3))
    
    Z = property(
        lambda self: Stage.request('Z') / 1e3,
        lambda self,v: Stage._set_zpos(v * 1e3))
    
    TX = property(
        lambda self: Stage.request('TX'),
        lambda self,v: Stage._set_xtilt(float(v)))
    
    TY = property(
        lambda self: Stage.request('TY'),
        lambda self,v: Stage._set_ytilt(float(v)))
    
    dX = property(
        lambda self: None,
        lambda self,v: Stage._set_xpos_rel(v * 1e3))
    
    dY = property(
        lambda self: None,
        lambda self,v: Stage._set_ypos_rel(v * 1e3))
    
    dZ = property(
        lambda self: None,
        lambda self,v: Stage._set_zpos_rel(v * 1e3))
    
    dTX = property(
        lambda self: None,
        lambda self,v: Stage._set_xtilt_rel(float(v)))
    
    dTY = property(
        lambda self: None,
        lambda self,v: Stage._set_ytilt_rel(float(v)))


class Filter(Device):
    """Filter system
    """
    Info = info.Filter_info()
    
    _get_info = Command("E630", None, "!2H2I2H2IH5dH")
    _set_slit = Command("E621", "!H", "!2H2I2H2IH5dH")
    _set_slitw = Command("E623", "!I", "!2H2I2H2IH5dH") # slit width [0.01eV]
    _set_slitp = Command("E624", "!H", "!2H2I2H2IH5dH") # slit position (rel)
    
    _set_es = Command("F520", "!H", None, device='HT') # energy shift off/on
   #_set_esv = Command("F522", "!h", "!h", device='HT') # energy shift [-15000:15000:0.2V]
    _set_esv = Command("F524", "!d", "!2H2I2H2IH5dH", device='HT') # energy shift [-3000:3000:1V]
    
    @property
    def slit_state(self):
        return Filter.request('slit_state')
    
    @slit_state.setter
    def slit_state(self, v):
        Filter._set_slit(bool(v))
    
    @property
    def slit_width(self):
        return Filter.request('slit_width')
    
    @slit_width.setter
    def slit_width(self, v):
        Filter._set_slitw(int(v * 100))
    
    @property
    def energy_shift(self):
        return Filter.request('energy_shift')
    
    @energy_shift.setter
    def energy_shift(self, v):
        if v is not None:
            Filter._set_esv(v)
        else:
            Filter._set_es(0) # energy shift off


if __name__ == "__main__":
    ## cmdl.HOST = cntf.HOST = '172.17.41.201'
    ## cmdl.HOST = cntf.HOST = 'localhost'
    cmdl.open()
    cntf.open()
    
    extype = bool(ApertureEx._get_info())
    print("extype =", extype)
    if extype:
        Aperture = ApertureEx
    
    eos = EOsys()
    tem = TEM()
    ca = Aperture('CLA')
    sa = Aperture('SAA')
    oa = Aperture('OLA')
    i = Illumination()
    j = Imaging()
    k = Omega()
    g = Stage()
    fl = Filter()
    ht = HTsys()

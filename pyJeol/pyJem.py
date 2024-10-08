#! python3
"""PyJEM - 'はじめてのぱいじえむ'

Wx Import Warning:
    Please ``import PyJEM`` *before* the wx.App is created and enters mainloop.
    Wx accepts TEM3 module only if it already loaded in process.
    Do *NOT* import PyJEM after the wx.App mainloop started,
    or else you can never expect it works correctly.
"""
import sys
import numpy as np
from numpy import inf

from .temisc import mrange
from .temisc import FLHex, OLHex

try:
    if 'PyJEM.offline' in sys.modules:
        from PyJEM.offline import TEM3
        print('Loaded TEM3:offline module.')
        OFFLINE = True
    else:
        from PyJEM import TEM3  # TEMExternal is required.
        print('Loaded TEM3:online module.')
        OFFLINE = False
except ImportError as e:
    print(e)
    print("Current version is {}".format(sys.version))
    OFFLINE = None
    TEM3 = None
else:
    APT  = TEM3.Apt3()
    LENS = TEM3.Lens3()
    DEFL = TEM3.Def3()
    EOS  = TEM3.EOS3()
    HT   = TEM3.HT3()
    FEG  = TEM3.FEG3() # We won't use these (use notify).
    GUN  = TEM3.GUN3() # ditto
    VAC  = TEM3.VACUUM3() # ditto
    ## CAM  = TEM.Camera3() # obsolete
    DET  = TEM3.Detector3()
    STAGE = TEM3.Stage3()
    FILTER = TEM3.Filter3()


## --------------------------------
## PYJEM GLOBAL NAME AND THE CLASSE
## --------------------------------
## MAJOR_MODE = 'TEM', 'STEM'
## USER_MODE  = 'MAINT', 'USER', 'STDBASE'

def _uhex(v, vmax=0xffff):
    if v < 0:
        return 0
    elif v > vmax:
        return vmax
    else:
        return int(v) # needs cast to int (! PyJEM.TEM3 cannot eat np.int)


def staticproperty(_get, _set=None):
    def fget(self):
        f = getattr(LENS, _get)
        return f()
    def fset(self, v):
        f = getattr(LENS, _set)
        return f(_uhex(v))
    return property(fget, fset if _set else None)


def static2property(_get, _set):
    def fget(self):
        f = getattr(DEFL, _get)
        return np.array(f())
    def fset(self, v):
        f = getattr(DEFL, _set)
        return f(_uhex(v[0]), _uhex(v[1]))
    return property(fget, fset)


class TEM(object):
    """TEM Lens/Defl system.
    
    通常は，このクラスを基底クラスとしてプロパティを継承／使用するが，
    self に依存しないので静的プロパティ (static property) としてアクセス可．
    
    Normally, properties are inherited/used with this class as the base class,
    but since they do not depend on self, they can be accessed as static properties.
    """
    def __getitem__(self, name):
        return getattr(self, name)
    
    def __setitem__(self, name, v):
        return setattr(self, name, v)
    
    GUNA1 = static2property('GetGunA1', 'SetGunA1')
    GUNA2 = static2property('GetGunA2', 'SetGunA2')
    SPOTA = static2property('GetSpotA', 'SetSpotA') # オフライン版は SetSpotA が抜けている▲
    CLA1 = static2property('GetCLA1', 'SetCLA1')
    CLA2 = static2property('GetCLA2', 'SetCLA2')
    SHIFT = static2property('GetShifBal', 'SetShifBal')
    TILT = static2property('GetTiltBal', 'SetTiltBal')
    ANGLE = static2property('GetAngBal', 'SetAngBal')
    CLS = static2property('GetCLs', 'SetCLs')
    OLS = static2property('GetOLs', 'SetOLs')
    ILS = static2property('GetILs', 'SetILs')
    IS1 = static2property('GetIS1', 'SetIS1')
    IS2 = static2property('GetIS2', 'SetIS2')
    PLA = static2property('GetPLA', 'SetPLA')
    FLA1 = static2property('GetFLA1', 'SetFLA1')
    FLA2 = static2property('GetFLA2', 'SetFLA2')
    FLS1 = static2property('GetFLs1', 'SetFLs1')
    FLS2 = static2property('GetFLs2', 'SetFLs2')
    
    SCAN1 = static2property('GetScan1', 'SetScan1')
    SCAN2 = static2property('GetScan2', 'SetScan2')
    STEMIS = static2property('GetStemIS', 'SetStemIS')
    MagAdjust = static2property('GetMagAdjust', 'SetMagAdjust') # Setter は存在しない▲
    Correction = static2property('GetCorrection', 'SetCorrection') # (ditto)
    Rotation = static2property('GetRotation', 'SetRotation') # (ditto)
    Offset = static2property('GetOffset', 'SetOffset') # (ditto)
    
    CL1 = staticproperty('GetCL1')
    CL2 = staticproperty('GetCL2')
    CL3 = staticproperty('GetCL3', 'SetCL3')
    CM  = staticproperty('GetCM')
    OLC = staticproperty('GetOLc', 'SetOLc')
    OLF = staticproperty('GetOLf', 'SetOLf')
    OM  = staticproperty('GetOM')
    IL1 = staticproperty('GetIL1')
    IL2 = staticproperty('GetIL2')
    IL3 = staticproperty('GetIL3')
    IL4 = staticproperty('GetIL4')
    PL1 = staticproperty('GetPL1')
    PL2 = staticproperty('GetPL2')
    PL3 = staticproperty('GetPL3')
    FLC = staticproperty('GetFLc', 'SetFLc') # 12bit max
    FLF = staticproperty('GetFLf', 'SetFLf') # 12bit max
    FLCOMP1 = staticproperty('GetFLcomp1')
    FLCOMP2 = staticproperty('GetFLcomp2')
    
    @property
    def FL(self):
        c, f = LENS.GetFLc(), LENS.GetFLf()
        return FLHex(c, f).value
    
    @FL.setter
    def FL(self, v):
        u = FLHex(0, _uhex(v, FLHex.maxval))
        LENS.SetFLc(u.coarse)
        LENS.SetFLf(u.fine)
    
    @property
    def OL(self):
        c, f = LENS.GetOLc(), LENS.GetOLf()
        return OLHex(c, f).value
    
    @OL.setter
    def OL(self, v):
        u = OLHex(0, _uhex(v, OLHex.maxval))
        LENS.SetOLc(u.coarse)
        LENS.SetOLf(u.fine)
    
    Brightness = CL3
    DiffFocus = IL1
    ObjFocus = OL
    ILFocus = NotImplemented
    PLFocus = PL1
    FLFocus = FL


class Optics(object):
    """Optics mode base(mixin) class.
    
    The inherited class must have MODES.
    The Mode can only function if the class has commands _set_mode and _get_mode.
    The Selector can only function if the class has commands _set_index and _get_index.
    """
    @classmethod
    def init(self, alist):
        self.MODES = dict(alist)
    
    def _get_mode_name(self, j):
        if j is not None:
            return list(self.MODES)[j]
    
    def _get_mode_range(self, j):
        if j is not None:
            return list(self.MODES.values())[j]
    
    @property
    def Name(self):
        """Mode-specific name."""
        return self._get_mode_name(self.Mode)
    
    @property
    def Mode(self):
        """Mode-specific index."""
        ret = self._get_mode()
        if isinstance(ret, (list, tuple)):
            return ret[0]
        return ret
    
    @Mode.setter
    def Mode(self, v):
        if isinstance(v, str):
            v = list(self.MODES).index(v)
        if 0 <= v < len(self.MODES):
            if v != self.Mode:
                self._set_mode(int(v))
        else:
            raise IndexError("Mode index is out of range: {}".format(v))
    
    @property
    def Selector(self):
        """Submode-specifc index e.g., (spot, alpha), mag, cam, and disp."""
        return self._get_index()
    
    @Selector.setter
    def Selector(self, v):
        if isinstance(v, (list, tuple)):
            self._set_index(v)
        elif v >= 0:
            self._set_index(int(v))
    
    @property
    def Range(self):
        """Mode-specific range."""
        return self._get_mode_range(self.Mode)


class Illumination(Optics):
    """Illumination system.
    """
    MODES = dict(( # number of (spot, alpha)
        ('TEM',     (8, 8)),
        ('Koehler', (8, 8)),
    ))
    _get_mode = EOS.GetProbeMode   # --> [0,'TEM']
    _set_mode = EOS.SelectProbMode # --> オフライン版でこれをやると▲(ﾟДﾟ)
    
    def _get_index(self):
        return (self.Spot, self.Alpha)
    
    def _set_index(self, v):
        self.Spot, self.Alpha = v
    
    @property
    def Spot(self):
        return EOS.GetSpotSize()
    
    @Spot.setter
    def Spot(self, v):
        if 0 <= v != self.Spot:
            EOS.SelectSpotSize(int(v))
    
    @property
    def Alpha(self):
        return EOS.GetAlpha()
    
    @Alpha.setter
    def Alpha(self, v):
        if 0 <= v != self.Alpha:
            EOS.SetAlphaSelector(int(v))


class Imaging(Optics):
    """Imaging system.
    """
    MODES = dict((
        ('MAG',    mrange(1000, 1.2e6)),
        ('MAG2',   mrange(1000, 1.2e6)),
        ('LOWMAG', mrange(  50,  50e3)),
        ('SAMAG',  mrange(1000, 500e3)),
        ('DIFF',   mrange( 300,  5000)),
    ))
    _get_mode = EOS.GetFunctionMode    # --> [0,'MAG']
    _set_mode = EOS.SelectFunctionMode # 
    
    _get_index = EOS.GetCurrentMagSelectorID
    _set_index = EOS.SetSelector
    
    @property
    def Mag(self):
        return EOS.GetMagValue()[0] # --> [200,'X','X200'][0] ▲オフライン板は 400k 抜け
    
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
    """Omega/Projection system.
    """
    MODES = dict((
        ('Imaging', (0,)),
        ('Spectrum', mrange(100, 250)), # um/eV
    ))
    _get_mode = EOS.GetSpctrMode
    _set_mode = EOS.SetSpctrMode
    
    _get_index = lambda self: np.searchsorted(self.Range, self.Dispersion)
    _set_index = EOS.SetSpctrSelector # --> オフライン版でこれをやると▲(ﾟДﾟ)
    
    @staticmethod
    def isEnabled():
        return 'Spectrum' in Omega.MODES
    
    @property
    def Dispersion(self):
        return EOS.GetSpctrValue()[0] # --> [200,('um/eV'),('200um/eV')]
    
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
## PYJEM GLOBAL INSTRUMENTAL CLASSE
## --------------------------------

class EOsys(object):
    """EM device system.
    """
    get_v1_ready = FEG.GetV1Ready
    get_v1_state = FEG.GetBeamValve
    set_v1_state = FEG.SetBeamValve
    
    ## for FEG only
    ## for LAB6-2100, 動作未確認▲
    V1 = property(
        lambda self: FEG.GetBeamValve(),
        lambda self,v: FEG.SetBeamValve(1 if v else 0),
        doc="Status of V1 valve.")
    
    Screen = property(
        lambda self: DET.GetScreen(),
        lambda self,v: DET.SetScreen(v),
        doc="Status of default screen.")


class HTsys(object):
    """HT system.
    """
    ht_value = property(
        lambda self: HT.GetHtValue(),
        lambda self,v: HT.SetHtValue(v))


class Aperture(object):
    """Aperture system: Normal type (extype=0).
    """
    APERTURES = dict((
        ('NULL', (inf,  40,  30, 20, 10)), # CLA2 for extype=1
        ('CLA',  (inf, 150, 100, 50, 20)),
        ('OLA',  (inf,  60,  40, 30,  5)),
        ('HCA',  (inf, 120,  60, 20,  5)),
        ('SAA',  (inf, 100,  50, 20, 10)),
        ('ENTA', (inf, 120,  60, 40, 20)),
        ('EDS',  (inf, 200,   0,  0,  0)),
    ))
    select_apt = APT.SelectKind # extype=0
    get_pos = APT.GetPosition
    set_pos = APT.SetPosition
    get_sel = APT.GetSize
    set_sel = APT.SetSize
    get_id = APT.GetKind
    
    @classmethod
    def init(self, alist):
        self.APERTURES.update(alist) # ID が関係するので上書きではなく更新
    
    @classmethod
    def select_apt_name(self, name):
        return self.select_apt(list(self.APERTURES).index(name))
    
    def __init__(self, name):
        if name not in self.APERTURES:
            raise KeyError(name)
        self.name = name
        self.Id = list(self.APERTURES).index(name)
    
    def select(self):
        self.select_apt(self.Id)
        return True
    
    def select_hole(self, v):
        return self.select_apt(self.Id) and self.set_sel(int(v))
    
    @property
    def holes(self):
        return self.APERTURES[self.name]
    
    @property
    def pos(self):
        """Selected hole position [2:int]."""
        if self.select():
            return np.array(self.get_pos())
    
    @pos.setter
    def pos(self, v):
        if self.select():
            self.set_pos(int(v[0]), int(v[1]))
    
    @property
    def sel(self):
        """Selected hole number index."""
        return self.get_sel(self.Id)
    
    @sel.setter
    def sel(self, v):
        self.select_hole(int(v))
    
    @property
    def dia(self):
        """Selected hole diameter value."""
        if self.sel is not None:
            return self.holes[self.sel]
    
    @dia.setter
    def dia(self, v):
        self.select_hole(self.holes.index(v))


class ApertureEx(Aperture):
    """Aperture system: Extended type (extype=1).
    """
    APERTURES = dict((
        ('CLA',  (inf, 150, 100, 50, 20)),
        ('CLA2', (inf,  40,  30, 20, 10)),
        ('OLA',  (inf,  60,  40, 30,  5)),
        ('HCA',  (inf, 120,  60, 20,  5)),
        ('SAA',  (inf, 100,  50, 20, 10)),
        ('ENTA', (inf, 120,  60, 40, 20)),
        ('HXA',  (inf, 200,   0,  0,  0)),
    ))
    ## オフライン版には Exp 系のコマンドがない▲
    if 1:
        select_apt = APT.SelectExpKind # extype=1
        get_sel = APT.GetExpSize
        set_sel = APT.SetExpSize
        get_id = APT.GetExpKind


class Stage(object):
    """Stage (Gonio) system.
    
    X, Y, Z [um] and TX, TY [deg].
    """
    X = property(
        lambda self: STAGE.GetPos()[0] / 1e3,
        lambda self,v: STAGE.SetX(v * 1e3))
    
    Y = property(
        lambda self: STAGE.GetPos()[1] / 1e3,
        lambda self,v: STAGE.SetY(v * 1e3))
    
    Z = property(
        lambda self: STAGE.GetPos()[2] / 1e3,
        lambda self,v: STAGE.SetZ(v * 1e3))
    
    TX = property(
        lambda self: STAGE.GetPos()[3],
        lambda self,v: STAGE.SetTiltXAngle(v))
    
    TY = property(
        lambda self: STAGE.GetPos()[4],
        lambda self,v: STAGE.SetTiltYAngle(v))
    
    dX = property(
        lambda self: None,
        lambda self,v: STAGE.SetXRel(v * 1e3))
    
    dY = property(
        lambda self: None,
        lambda self,v: STAGE.SetYRel(v * 1e3))
    
    dZ = property(
        lambda self: None,
        lambda self,v: STAGE.SetZRel(v * 1e3))
    
    dTX = property(
        lambda self: None,
        lambda self,v: STAGE.SetTXRel(v))
    
    dTY = property(
        lambda self: None,
        lambda self,v: STAGE.SetTYRel(v))


class Filter(object):
    """Energy filter system.
    """
    @property
    def slit_state(self):
        return FILTER.GetSlitPosition() # 0=OUT, 1=IN
    
    @slit_state.setter
    def slit_state(self, v):
        FILTER.SetSlitPosition(v)
    
    @property
    def slit_width(self):
        return FILTER.GetSlitWidth()
    
    @slit_width.setter
    def slit_width(self, v):
        FILTER.SetSlitWidth(v)
    
    @property
    def energy_shift(self):
        if FILTER.GetEnergyShiftSw():
            return FILTER.GetEnergyShift()
    
    @energy_shift.setter
    def energy_shift(self, v):
        if v is not None:
            FILTER.SetEnergyShift(v)
        else:
            FILTER.SetEnergyShiftSw(0)

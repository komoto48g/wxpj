#! python3
"""tem13 information class
Class for notify optics state and hardware status

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from collections import OrderedDict
import struct


def getargs(x):
    if isinstance(x, bytes):
        return x.split(b'\0')[0].decode()
    return x


class Infodict(OrderedDict):
    """Mode info base class.
    
    Show how the inherited class builds keys from the docstring.
    (heads of colon-separted words after the first line are used as keywords)
    
    1. 1 行目は無視．2 行目からヘッダを解析する
    2. コロン(:) の左側の文字列をキーとする (comma-seperated words ok)
    3. コロン(:) の右側の文字列はコメントとして無視される
    4. 空行は無視される
    """
    def __init__(self):
        keys = []
        lines = self.__doc__.split('\n')
        for ln in lines[1:]:
            ln = ln.split(':', 1)[0].strip()
            if ln:
                keys += [w.strip() for w in ln.split(',')] # suppose comma-seperated words
        keys = [k for k in keys if k]
        OrderedDict.__init__(self, zip(keys, [None] * len(keys)))
    
    def __call__(self, argv, decode=True):
        if argv:
            if decode:
                argv = [getargs(x) for x in argv]
            self.update(zip(self.keys(), argv))
        return self


class Illumination_info(Infodict): #[N105] - [E055]
    """Illumination (CL) system
    
    mode        : illumination mode {0:TEM, 1:EDS, 2:NBD, 3:CBD}
    mode_name   : illumination name
    alpha       : alpha index
    spot        : spot index
    probe       : [um]
    index       : illumination index +++ 付加情報 (コマンドには含まれない)
    """
    def __call__(self, argv):
        Infodict.__call__(self, argv)
        try:
            self['index'] = (self['spot'], self['alpha'])
        finally:
            return self


class Imaging_info(Infodict): #[N101] - [E015]
    """Imaging (IL) system
    
    mode        : imaging mode {0:MAG1, 1:MAG2, 2:LOWMAG, 3:SAMAG, 4:DIFF}
    mode_name   : imaging name ditto
    index       : mag/cam index
    value       : mag/cam value
    submodestr  : mag/cam submode string
    unit        : mag/cam unit string [x][cm]
    """
    def __call__(self, argv):
        Infodict.__call__(self, argv)
        try:
            self['mode_name'] = self['mode_name'].upper() # LowMAG 対応
            if self['mode_name'] == 'MAG1':
                self['mode_name'] = 'MAG'
            
            self['submodestr'] = self['submodestr'].replace('X','x')
            self['unit'] = self['unit'].lower()
        finally:
            return self


class Omega_info(Infodict): #[N102] - [E016]
    """Projection (Omega, PL) system
    
    mode        : spectrum mode off/on {0:Imaging, 1:Spectrum}
    mmode       : imaging mode {0:MAG1, 1:MAG2, 2:LOWMAG, 3:SAMAG, 4:DIFF}
    mmode_name  : imaging name ditto
    index       : dispersion index ▲BUG: 1181 では論理番号 1 or 2 から始まる
    value       : dispersion value
    submodestr  : dispersion submode string
    unit        : dispersion unit string [um/eV]
    mode_name   : spectrum mode +++ 付加情報 (コマンドには含まれない)
    """
    def __call__(self, argv):
        Infodict.__call__(self, argv)
        try:
            if self['mode'] == 0:
                self.update(
                    submodestr = 'x',
                    mode_name = 'Imaging',
                    unit = 'x',
                )
            else:
                self.update(
                    submodestr = '{}um/eV'.format(self['value']),
                    mode_name = 'Spectrum',
                    unit = 'um/eV',
                )
            self['mmode_name'] = self['mmode_name'].upper() # LowMAG 対応
            if self['mmode_name'] == 'MAG1':
                self['mmode_name'] = 'MAG'
        finally:
            return self


class Eos_info(Infodict): #[N109] - [E090]
    """EO system
    
    dark        : dark level {0:bright, 1:dark}
    dark_index  : dark level number
    bright_zoom : zoom switch off/on
    stigma_index: stigma level number
    major_mode  : operation mode {0:TEM, 1:ASID}
    ht_index    : HT level number
    maint_mode  : alignment mode {0:User, 1:Maint} (▲ドキュメントは user_mode : {0:Maint, 1:User, 2:Stdbase} になっているが機種依存 ?)
    mmode       : imaging system mode {0:MAG1, 1:MAG2, 2:LOWMAG, 3:SAMAG, 4:DIFF}
    mag         : mag/cam index
    mag2        : default MAG2 mag index
    kmode       : spectrum mode off/on
    imode       : illumination mode {0:TEM, 1:EDS, 2:NBD, 3:CBD}
    spot        : spot index
    alpha       : alpha index
    slit        : {0:out, 1:in}
    defknob     : deflector knob
    defocus     : defofcus depth [0.1nm]
    ht_suspend  : HT suspended state {0:normal, 1:suspend}
    """
    def __call__(self, argv):
        Infodict.__call__(self, argv)


class Aperture_info(Infodict): #[N140] - [E405]
    """Aperture system extype=0
    
    speed       : {0:fine, 1:coarse}
    csid        : currently selected aperture id (0--6): None,CLA,OLA,HCA,SAA,ENTA,HXA
    adj_mode    : {0:User, 1:Maint}
    _info       : info bytes (7*114=798bytes) --- 除外される
    NULL,CLA,OLA,HCA,SAA,ENTA,HXA: hole indices (7) +++ 付加情報 (コマンドには含まれない)
    selected_name: currently selected aperture name +++
    """
    def __call__(self, argv):
        Infodict.__call__(self, argv, decode=0)
        try:
            def chop(i):
                info = self['_info']
                _cor,_cx,_cy,_t,_bx,_by, sel, psel = struct.unpack("!100s7H", info[i:i+114])
                return sel
            
            ls = "NULL,CLA,OLA,HCA,SAA,ENTA,HXA".split(',')
            for i,name in enumerate(ls):
                self[name] = chop(i * 114)
            self['_info'] = None # clear big-bytes after chopping and extracting data
            self['selected_name'] = ls[self['csid']]
        finally:
            return self


class ApertureEx_info(Infodict): #[N153] - [E423]
    """Aperture system extype=1 (1601 or later)
    
    csid        : currently selected aperture id (0--11): CLA,CLA2,OLA,HCA,SAA,ENTA,HXA,BFA,...
    speed       : {0:fine, 1:coarse}
    adj_mode    : {0:User, 1:Maint}
    CLA,CLA2,OLA,HCA,SAA,ENTA,HXA,BFA,BS,Aux2,Aux3,Aux4: hole indices (!12H)
    selected_name: currently selected aperture name +++ 付加情報 (コマンドには含まれない)
    """
    def __call__(self, argv):
        Infodict.__call__(self, argv)
        try:
            ls = "CLA,CLA2,OLA,HCA,SAA,ENTA,HXA,BFA,BS,Aux2,Aux3,Aux4".split(',')
            self['selected_name'] = ls[self['csid']]
        finally:
            return self


class Filter_info(Infodict): #[N162] - [E630]
    """Energy Filter system
    
    spectrum_mode: off/on
    slit_state  : Slit state {0:out, 1:in}
    slit_width  : Slit width                [0.01eV] --> [eV]
    slit_zero   : Slit width zero position  [ 〃   ] --> [eV]
    slit_adj    : Slit adjustment mode
    status      : Device status {0:normal,1:on(deGauss)}
    slit_max    : Maximum slit width        [0.01eV] --> [eV]
    slit_step   : Minimum slit step value   [ 〃   ] --> [eV]
    es_state    : Energy shift off/on
    es_value    : Energy shift value            [eV]
    es_max      : Energy shift maximum value    [〃]
    es_step     : Energy shift min Step Value   [〃]
    es_coef_tem : Energy shift correction factor for TEM mode
    es_coef_stem: Energy shift correction factor for STEM mode
    illum_corr  : Illumination system correction off/on
    energy_shift: Energy sfhit value (None:off) +++ 付加情報 (コマンドには含まれない)
    """
    def __call__(self, argv):
        Infodict.__call__(self, argv)
        try:
            if not self['slit_state']:
                self['slit_width'] = None
            else:
                self['slit_width'] *= 0.01
            self['slit_zero'] *= 0.01
            self['slit_max'] *= 0.01
            self['slit_step'] *= 0.01
            self['energy_shift'] = self['es_value'] if self['es_state'] else None
        finally:
            return self


class Gonio_info(Infodict): #[N533] - [G921]
    """Gonio ゴニオ座標情報
    
    X,Y,Z       : motor position [nm]
    TX,TY       : Tilt X [deg] and Tilt Y [deg] (or rotatoin angles)
    X_piezo     : piezo X position [nm]
    Y_piezo     : piezo Y 
    """
    def __call__(self, argv):
        Infodict.__call__(self, argv)
        return self


class HT_info(Infodict): #[F900] - [F902]
    """HT 高圧モード／電子銃／アノード情報
    
    Dark        : Dark current value       [0.1uA] --> [uA]
    Emission    : Emission current value   [0.1uA] --> [uA]
    A1,A2       : A1/A2 current value      [10V] --> [V]
    Bias        : Bias current value       [V]
    Filament    : Filament current value   [mA] --> [A]
    htsub_status: Operating status of HT subsystem
    condbar_status: Operating status of conditioning shortbar {0:ope, (1,2):med, 3:cond}
    QES         : quick emission setting (0--5)
    ht_status   : Operating state of HT {0:stable, 1:ascending, 2:descending}
    ht_ready    : High pressure can be applied
    ems_ready   : Emission can be applied (FEG ready and Beam ready)
    wob_status  : Wobbler status
    ht_state    : HT off/on
    ems_state   : Emission off/on
    ems_status  : Operating state of Emission {0:stable, 1:ascending, 2:descending}
    es_state    : Energy shift off/on
    es_value    : Energy shift current value [0.2eV] --> [eV]
    htsub_state : Setting of HT subsystem
    ht_value    : HT current value         [V]
    a1,a2       : A1/A2 target value       [10V] --> [V]
    bias        : Bias target value        [V]
    filament    : Filament target value    [mA] --> [A]
    energy_shift: Omega superimposed value [0.2eV] --> [eV]
    """
    def __call__(self, argv):
        Infodict.__call__(self, argv)
        try:
            self['Dark'] *= 0.1
            self['Emission'] *= 0.1
            self['A1'] *= 10
            self['A2'] *= 10
            self['Filament'] *= 1e-3
            self['es_value'] *= 0.2
            self['a1'] *= 10
            self['a2'] *= 10
            self['filament'] *= 1e-3
            self['energy_shift'] *= 0.2
        finally:
            return self


class HTsub_info(Infodict): #[F901] - ?
    """HT 高圧モード／エミッション情報
    
    htsub_status: Operating status of HT subsystem
    condbar_status: Operating status of conditioning shortbar {0:ope, (1,2):med, 3:cond}
    QES         : quick emission setting (0--5)
    ht_status   : Operating state of HT {0:stable, 1:ascending, 2:descending}
    ht_ready    : High pressure can be applied
    ems_ready   : Emission can be applied (FEG ready and Beam ready)
    wob_status  : Wobbler status
    ht_state    : HT off/on
    ems_state   : Emission off/on
    ems_status  : Operating state of Emission {0:stable, 1:ascending, 2:descending}
    es_state    : Energy shift off/on
    es_value    : Energy shift current value [0.2eV] --> [eV]
    htsub_state : Setting of HT subsystem
    """
    def __call__(self, argv):
        Infodict.__call__(self, argv)
        try:
            self['es_value'] *= 0.2
        finally:
            return self


class HTsub2_info(Infodict): #[N309] - ?
    """HT 高圧モード／エミッション情報
    
    ht_value    : HT current value         [V]
    a1,a2       : A1/A2 target value       [10V] --> [V]
    bias        : Bias target value        [V]
    filament    : Filament target value    [mA] --> [A]
    energy_shift: Omega superimposed value [0.2eV] --> [eV]
    """
    def __call__(self, argv):
        Infodict.__call__(self, argv)
        try:
            self['a1'] *= 10
            self['a2'] *= 10
            self['filament'] *= 1e-3
            self['energy_shift'] *= 0.2
        finally:
            return self


class Current_info(Infodict): #[N404] - ?
    """Current density 照射電流密度
    
    value   : Current density    [0.01pA/cm2]
    exp     : Auto exposure time [0.1sec]
    """


class Screen_info(Infodict): #[N401] - [C320,C321][C325] ! WHITE-TEMCENTER only
    """Screen status スクリーン情報
    
    pose    : {0:0+, 1:7+, 2:90+} degs
    state   : out/in
    """


class Detector_info(Infodict): #[N627] - [D170][D171]
    """Detector status (!25H)
    N, SEI, EDS, BIPRISM, UDFI, TVCAM_U, SSCAM_U, FARADAY, BS, HRD : (10)
    DFI_U, FI_U, CR_F, SCR_L, DFI_B, BFI_B, SSCAM_B, TVCAM_B, EELS : (9)
    TVCAM_GIF, SSCAM_GIF, BEI_TOPO, BEI_COMPO, SEI_TOPO, SEI_COMPO : (6) BEI/SEI
    """


if __name__ == "__main__":
    from pprint import pprint
    
    i = Illumination_info()
    j = Imaging_info()
    k = Omega_info()
    eos = Eos_info()
    pprint(i)
    pprint(j)
    pprint(k)
    pprint(eos)

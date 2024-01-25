#! python3
"""Jeol Lens/Deflector system types
"""
from mwx.controls import LParam
from . import _cmdl as cmdl

Command = cmdl.Command


class LensParam(LParam):
    """Lens/Deflector coil hex param.
    """
    flag = LParam.check


def _iter_pair(ls, n=2):
    return (ls[i:i+n] for i in range(0,len(ls),n))


class Systembase(object):
    """Base class of Lens/Deflector system.
    """
    def __call__(self, argv):
        for lp, v in zip(self.Lenses, argv):
            lp.value = v # change offset
        return self
    
    def __getitem__(self, j):
        if isinstance(j, str):
            j = self.TAGS.index(j)
        return self.Lenses.__getitem__(j)
    
    def __setitem__(self, j, v):
        if isinstance(j, str):
            j = self.TAGS.index(j)
        if isinstance(j, int) and not isinstance(v, LensParam):
            raise TypeError("setting value must be a LensParam, not {}.".format(type(v).__name__))
        self.Lenses.__setitem__(j, v)
    
    def __len__(self):
        return len(self.Lenses)
    
    def __str__(self):
        f = "{0.name:12s} {0.value:04X}({0.offset:+5X}) [{0.flag:d}]".format
        return '\n'.join("{}\t{}".format(f(x), f(y)) for x, y in _iter_pair(self.Lenses))


class LensSystem(Systembase):
    """Lens (Free Control) System.
    """
    TAGS = (
             'CL1', #  0 : CL1                
             'CL2', #  1 : CL2                
             'CL3', #  2 : CL3                
              'CM', #  3 : CM                 
     'Preserved_0', #  4 : 照射系予備1        
     'Preserved_1', #  5 : 照射系予備2        
             'OLC', #  6 : OL Coarse          
             'OLF', #  7 : OL Fine            
             'OM1', #  8 : OM1                
             'OM2', #  9 : 操作不可(OM2)      
             'IL1', # 10 : IL1                
             'IL2', # 11 : IL2                
             'IL3', # 12 : IL3                
             'IL4', # 13 : IL4                
             'PL1', # 14 : PL1                
             'PL2', # 15 : PL2                
             'PL3', # 16 : PL3                
     'Preserved_2', # 17 : 結像系予備1        
     'Preserved_3', # 18 : 結像系予備2        
             'FLC', # 19 : FL Coarse          
             'FLF', # 20 : FL Fine            
            'FL2R', # 21 : FL Ratio           
         'FLCOMP1', # 22 : 操作不可(FL1 Comp) * no record in FLC
         'FLCOMP2', # 23 : 操作不可(FL2 Comp) * no record in FLC
     'Preserved_4', # 24 : 分光系予備1        
     'Preserved_5', # 25 : 分光系予備2        
              'U*', # 26 : U*補正             * OM2R (reverse) in FLC
    )
    Lenses = property(lambda self: self.__Lenses)
    
    flc = Command("E269", "!HH", None, doc="FLCモード (個別設定)")
    flcn = Command("E270", "!H", None, doc="FLCモード (同時設定)")
    flc1set = Command("E268", "!HH", None, doc="FLCデータ設定")
    flc2get = Command("E262", None, "!49H", doc="FLCデータ取得")
    flc2set = Command("E263", "!49H", "!49H", doc="FLCデータ設定")
    
    def __init__(self):
        self.__Lenses = [LensParam(name, (0, 0xffff), fmt=hex,
                                   handler=self.write,
                                   updater=self.setflag) for name in self.TAGS[:24]]
        self["FLC"].range = (0, 0xfff)
        self["FLF"].range = (0, 0xfff)
        self["FLCOMP1"].range = (0, 0xfff)
        self["FLCOMP2"].range = (0, 0xfff)
    
    def read(self, stdbase=False):
        data = self.flc2get() # --> get (49 = 24*2+1) record
        if not data:
            raise IOError("Failed to read online data {}".format(type(self)))
        
        flags = data[0:48:2]  # 0--46
        values = data[1:48:2] # 1--47
        for lp, v, f in zip(self.Lenses, values, flags):
            if stdbase:
                lp.std_value = v
            lp.value = v
            lp.flag = f
        return values
    
    def write(self, lens=None):
        if lens is None:
            data = [0] * 49 # <-- set (49 = 24*2+1) record
            flags = [lp.flag for lp in self.Lenses]
            values = [lp.value for lp in self.Lenses]
            data[0:48:2] = flags
            data[1:48:2] = values
            self.flc2set(*data)
        elif lens.flag:
            self.Write(lens.name, lens.value)
    
    def Write(self, name, value):
        self.flc1set(self.TAGS.index(name), int(value))
    
    def setflag(self, lens):
        if lens.flag:
            self.write(lens)
        else:
            self.flc(self.TAGS.index(lens.name), False)


class FocusSystem(LensSystem):
    """Lens (Focus :variable) System.
    
    [Brightness,OBJ,DIFF,IL,PL,FL] に割り当てられたレンズのみ変更可能
    """
    ldget = Command("E261", None, "!27H", doc="レンズ情報取得")
    ldset = Command("E271", "!HH", None, doc="レンズデータ出力値 絶対値設定")
    ldclr = Command("E236", "!H", None, doc="レンズデータ可変値クリア")
    
    def read(self, stdbase=False):
        data = self.ldget() # --> get (27) lenses record
        if not data:
            raise IOError("Failed to read online data {}".format(type(self)))
        
        for lp, v in zip(self, data):
            if stdbase:
                lp.std_value = v
            lp.value = v
        return data
    
    def write(self, lens=None):
        if lens is None:
            for j,lp in enumerate(self.Lenses):
                if lp.flag:
                    self.ldset(j, lp.value)
        elif lens.flag:
            self.Write(lens.name, lens.value)
    
    def Write(self, name, value):
        self.ldset(self.TAGS.index(name), int(value))


class DeflSystem(Systembase):
    """Deflector (Maint/User) System.
    """
    TAGS = (
          'GUNA1X',       'GUNA1Y', #  0 : GunA1 X             1 : GunA1 Y            
          'GUNA2X',       'GUNA2Y', #  2 : GunA2 X             3 : GunA2 Y            
           'CLA1X',        'CLA1Y', #  4 : CLA1 X              5 : CLA1 Y             
           'CLA2X',        'CLA2Y', #  6 : CLA2 X              7 : CLA2 Y             
          'SHIFTX',       'SHIFTY', #  8 : Shift Balance X     9 : Shift Balance Y    
           'TILTX',        'TILTY', # 10 : Tilt Balance X     11 : Tilt Balance Y     
          'ANGLEX',       'ANGLEY', # 12 : Angle Balance X    13 : Angle Balance Y    
            'CLSX',         'CLSY', # 14 : CL Stig X          15 : CL Stig Y          
          'SPOTAX',       'SPOTAY', # 16 : SPOTA X            17 : SPOTA Y            
    'Preserved_0X', 'Preserved_0Y', # 18 : 照射系データ予備1  19 : 照射系データ予備2  
    'Preserved_1X', 'Preserved_1Y', # 20 : 照射系データ予備3  21 : 照射系データ予備4  
            'OLSX',         'OLSY', # 22 : OL Stig X          23 : OL Stig Y          
            'ILSX',         'ILSY', # 24 : IL Stig X          25 : IL Stig Y          
            'IS1X',         'IS1Y', # 26 : ISC1 X             27 : ISC1 Y             
            'IS2X',         'IS2Y', # 28 : ISC2 X             29 : ISC2 Y             
            'PLAX',         'PLAY', # 30 : PLA X              31 : PLA Y              
    'Preserved_2X', 'Preserved_2Y', # 32 : 結像系データ予備1  33 : 結像系データ予備2  
    'Preserved_3X', 'Preserved_3Y', # 34 : 結像系データ予備3  35 : 結像系データ予備4  
           'FLA1X',        'FLA1Y', # 36 : FLA1 X             37 : FLA1 Y             
           'FLA2X',        'FLA2Y', # 38 : FLA2 X             39 : FLA2 Y             
           'FLS1X',        'FLS1Y', # 40 : FL Stig1 X         41 : FL Stig1 Y         
           'FLS2X',        'FLS2Y', # 42 : FL Stig2 X         43 : FL Stig2 Y         
    'Preserved_4X', 'Preserved_4Y', # 44 : 分光系データ予備1  45 : 分光系データ予備2  
    'Preserved_5X', 'Preserved_5Y', # 46 : 分光系データ予備3  47 : 分光系データ予備4  
                                    # 
              'U*',          'U*' , # 48 : Def U* 補正        49 : Def U* 補正        
        'CLA_Comp',     'CLA_Comp', # 50 : CLA Comp           51 : CLA Comp           
     'MagAdjust_H',  'MagAdjust_V', # 52 : MAG Adjust H       53 : MAG Adjust V       
    'Correction_H', 'Correction_V', # 54 : Correction H       55 : Correction V       
      'Rotation_H',   'Rotation_V', # 56 : Rotation H         57 : Rotation V         
        'Offset_H',     'Offset_V', # 58 : Offset H           59 : Offset V           
         'STEMISX',      'STEMISY', # 60 : ASID Image Shift X 61 : ASID Image Shift Y 
    )
    Lenses = property(lambda self: self.__Lenses)
    
    algn2get = Command("E341", None, "!62H", doc="偏向系データ取得")
    algn2set = Command("E342", "!72H", None, doc="偏向系データ設定")
    _algn1set = Command("E321", "!HH", "!H", doc="偏向系データ個別設定")
    
    def __init__(self):
        self.__Lenses = [LensParam(name, (0, 0xffff), fmt=hex,
                                   handler=self.write) for name in self.TAGS[:62]]
    
    def read(self, stdbase=False):
        data = self.algn2get() # --> get (62) deflectors record
        if not data:
            raise IOError("Failed to read online data {}".format(type(self)))
        
        for lp, v in zip(self.Lenses, data):
            if stdbase:
                lp.std_value = v
            lp.value = v
        return data
    
    def write(self, lens=None):
        if lens is None:
            data = [0] * 72 # <-- set (72 = 24*3) deflectors record
            flags = [x.flag or y.flag for x, y in _iter_pair(self.Lenses)]
            values = [x.value for x in self.Lenses]
            data[0::3] = flags[0:24]
            data[1::3] = values[0:48:2]
            data[2::3] = values[1:48:2]
            self.algn2set(*data)
        elif lens.flag:
            self.Write(lens.name, lens.value)
    
    def Write(self, name, value):
        Tags = (
             'GUNA1X',       'GUNA1Y',
             'GUNA2X',       'GUNA2Y',
              'CLA1X',        'CLA1Y',
              'CLA2X',        'CLA2Y',
             'SHIFTX',       'SHIFTY',
              'TILTX',        'TILTY',
             'ANGLEX',       'ANGLEY',
               'CLSX',         'CLSY',
               'IS1X',         'IS1Y',
               'IS2X',         'IS2Y',
             'SPOTAX',       'SPOTAY',
               'PLAX',         'PLAY',
               'OLSX',         'OLSY',
               'ILSX',         'ILSY',
              'FLS1X',        'FLS1Y',
              'FLS2X',        'FLS2Y',
              'FLA1X',        'FLA1Y',
              'FLA2X',        'FLA2Y',
              'DETAX',        'DETAY',
                   '',             '',
             'SCAN1X',       'SCAN1Y',
             'SCAN2X',       'SCAN2Y',
            'STEMISX',      'STEMISY',
               'CMSX',         'CMSY', # [46--65] adds to JEM-1300NEF
              'ISC3X',        'ISC3Y',
              'ILA1X',        'ILA1Y',
              'ILA2X',        'ILA2Y',
              'ILA3X',        'ILA3Y',
              'FLDQX',        'FLDQY',
              'FLDHX',        'FLDHY',
              'FLDDX',        'FLDDY',
              'CLA3X',        'CLA3Y',
              'CLA4X',        'CLA4Y',
          'CLA1FINEX',    'CLA1FINEY', # [66--93] adds to JEM-1000KRS
          'CLA2FINEX',    'CLA2FINEY',
              'CMS2X',        'CMS2Y',
          'GUNSHIFTX',    'GUNSHIFTY',
           'GUNTILTX',     'GUNTILTY',
          'GUNANGLEX',    'GUNANGLEY',
          'IS1SHIFTX',    'IS1SHIFTY',
           'IS1TILTX',     'IS1TILTY',
          'IS1ANGLEX',    'IS1ANGLEY',
          'IS2SHIFTX',    'IS2SHIFTY',
           'IS2TILTX',     'IS2TILTY',
          'IS2ANGLEX',     'IS2TILTY',
              'OMA1X',        'OMA1Y',
              'OMA2X',        'OMA2Y',
        )
        self._algn1set(Tags.index(name), int(value))

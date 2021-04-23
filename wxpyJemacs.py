#! python
# -*- coding: utf-8 -*-
"""The frontend of Graph and Plug manager

  Phase 1: Legacy (2015--2017) TEM control
  Phase 2: Phoenix (2018--2020) Integrated system for image analysis
  Phase 3: Analysis center phoenix (2020--)
"""
from __future__ import division, print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from collections import OrderedDict
from pprint import pprint
import traceback
import datetime # imported but unused :necessary to eval
import getopt
import sys
import os
import re
import wx
import cv2
import numpy as np
import scipy
import matplotlib
from PIL import Image
from PIL import TiffImagePlugin # tiff extension for py2exe
if 'mwx' not in sys.modules:
    ## Add eggs in the nest to the path
    home = os.path.dirname(os.path.abspath(__file__))
    sys.path += [
        os.path.join(home, "nest/pj-2.5-py3.5.egg"),
        os.path.join(home, "nest/mwxlib-0.40-py3.5.egg"),
    ]
import mwx
from mwx import Param, LParam
from mwx.graphman import Icon
from mwx.graphman import Layer
from mwx.graphman import Graph
from mwx.graphman import Frame as Framebase
from pyJeol.plugman import NotifyFront
from pyJeol.temisc import Environ
from pyDM3reader import DM3lib
import wx.lib.mixins.listctrl # for py2exe
import wx.lib.platebtn as pb

__version__ = "3.0"
__author__ = "Kazuya O'moto <komoto@jeol.co.jp>"
__copyright__ = "Copyright (c) 2018-2021"

def version():
    return '\n  '.join((
      "<Python {}>".format(sys.version),
      "wx.version(selected) {}".format(wx.version()),
      "scipy/numpy version {}/{}".format(scipy.__version__, np.__version__),
      "matplotlib verison {}".format(matplotlib.__version__),
      "Image verison {}".format(Image.__version__),
      "cv2 verison {}".format(cv2.__version__),
      "mwx {}".format(mwx.__version__),
      ))


class pyJemacs(Framebase):
    """the Frontend of Graph and Plug manager
    """
    su = property(lambda self: self.require('startup'))
    
    env = Environ(300e3) # default 300kV HT constants (to be reset by user)
    
    def About(self):
        try:
            from wx.adv import AboutDialogInfo, AboutBox #! phoenix
        except Exception:
            from wx import AboutDialogInfo, AboutBox #? obsolete
        
        info = AboutDialogInfo()
        info.Name = self.__class__.__name__
        info.Version = __version__
        info.Copyright = __copyright__ +' '+ __author__
        info.Description = '\n'.join((__doc__, version()))
        info.License = '\n'.join((mwx.__doc__ , ))
        info.Developers = []
        info.Artists = []
        AboutBox(info)
    
    def __init__(self, *args, **kwargs):
        Framebase.__init__(self, *args, **kwargs)
        
        HOME = sys.path[0]
        
        if HOME[-4:] == '.exe': # ~/dist/*.exe (py2exe)
            HOME = os.path.dirname(os.path.dirname(HOME))
            if HOME not in sys.path:
                sys.path += [ HOME ] # adds root for loading plugins
        
        icon = os.path.join(HOME, "Jun.ico")
        if os.path.exists(icon):
            self.SetIcon(wx.Icon(icon, wx.BITMAP_TYPE_ICO))
        
        self.nfront = NotifyFront(self)
        self.notify = self.nfront.notify
        ## self.notify.start() # do not start here; do after setting 'host:port:online'
        
        self.menubar["File"][-4:-4] = [
            (100, "&Notifyee\tF11", "Notify logger", wx.ITEM_CHECK,
                lambda v: self.nfront.Show(v.IsChecked()),
                lambda v: v.Check(self.nfront.IsShown())),
        ]
        ## self.menubar["File"][9:9] = [ # insert menus for extenstion, option, etc.
        self.menubar["Plugins"] += [ # insert menus for extenstion, option, etc.
            ("Extensions", []),
            ("Functions", []),
            ("Options", []),
            ("Cameras", []),
            (),
        ]
        self.menubar.reset()
    
    def Destroy(self):
        self.nfront.Destroy()
        return Framebase.Destroy(self)
    
    ## --------------------------------
    ## read/write buffers
    ## --------------------------------
    wildcards = [
              "TIF file (*.tif)|*.tif",
              "BMP file (*.bmp)|*.bmp",
        "Gatan DM3 file (*.dm3)|*.dm3", # Gatan DM extension (read-only)
       "Rigaku IMG file (*.img)|*.img", # Rigaku image file extension (read-only)
               "All files (*.*)|*.*",
    ]
    
    @staticmethod
    def read_buffer(path):
        """Read a buffer from path file (override) +.dm3 extension"""
        if path[-4:] == '.dm3':
            dmf = DM3lib.DM3(path)
            ## return dmf.image # PIL Image file
            return dmf.imagedata, {'header':dmf.info}
        
        if path[-4:] == '.img':
            with open(path, 'rb') as i:
                head = i.read(4096).decode()
                head = head[1:head.find('}')] # get header in '{...}'
                head = re.sub(r"(\w+)=\s(.*?);\n", r"\1='\2',", head)
                info = eval("dict({})".format(head))
                w = int(info['SIZE1'])
                h = int(info['SIZE2'])
                type = info['Data_type']
                if type == 'unsigned short int':
                    dtype = np.uint16
                elif type == 'unsigned long int':
                    dtype = np.uint32
                else:
                    raise Exception("unexpected data type {!r}".format(type))
                buf = np.frombuffer(i.read(), dtype)
                buf.resize(h, w)
                return buf, {'header':info}
        
        return Framebase.read_buffer(path)
    
    @staticmethod
    def write_buffer(path, buf):
        """Write a buffer to path file (override) +.dm3 extension"""
        if path[-4:] == '.dm3':
            raise NotImplementedError("Saving as DM3 type is not supported")
        if path[-4:] == '.img':
            raise NotImplementedError("Saving as IMG type is not supported")
        return Framebase.write_buffer(path, buf)

Frame = pyJemacs


class Button(pb.PlateButton):
    """Flat button
    """
    def __init__(self, parent, label='', handler=None, icon=None, tip=None, **kwargs):
        pb.PlateButton.__init__(self, parent, -1, label,
            style=pb.PB_STYLE_DEFAULT|pb.PB_STYLE_SQUARE, **kwargs)
        if handler:
            self.Bind(wx.EVT_BUTTON, handler)
            tip = tip or handler.__doc__
        tip = (tip or '').strip()
        self.SetToolTip(tip)
        try:
            if icon:
                self.SetBitmap(Icon(icon))
        except Exception:
            ## self.SetBitmap(wx.Bitmap(0,0)) # for pb no wx.NullBitmap?
            pass


class ToggleButton(wx.ToggleButton):
    """Togglable button
    check `Value property to get the status
    """
    def __init__(self, parent, label='', handler=None, icon=None, tip=None, **kwargs):
        wx.ToggleButton.__init__(self, parent, -1, label, **kwargs)
        if handler:
            self.Bind(wx.EVT_TOGGLEBUTTON, handler)
            tip = tip or handler.__doc__
        tip = (tip or '').strip()
        self.SetToolTip(tip)
        self.SetBitmap(Icon(icon))


## class TextLabel(wx.Panel):
##     """Label (widget complex of bitmap and label) readonly.
##     """
##     def __init__(self, parent, label, icon=None, tip=None, **kwargs):
##         wx.Panel.__init__(self, parent, **kwargs)
##         txt = wx.StaticText(self, label=label)
##         bmp = wx.StaticBitmap(self, bitmap=Icon(icon)) if icon else (0,0)
##         self.SetSizer(
##             mwx.pack(self,
##                 (bmp, 0, wx.ALIGN_CENTER|wx.ALL, 0),
##                 (txt, 0, wx.ALIGN_CENTER|wx.ALL, 0),
##                 orient=wx.HORIZONTAL,
##             )
##         )
##         txt.SetToolTip(tip)


class TextCtrl(wx.Panel):
    """Text control panel
    widget complex of bitmap, label, and textctrl
    """
    Value = property(
        lambda self: self.ctrl.GetValue(),
        lambda self,v: self.ctrl.SetValue(v))
    value = Value
    
    def reset(self, v=''):
        self.value = v
    
    def __init__(self, parent, label='',
        handler=None, updater=None, icon=None, tip=None, readonly=0, **kwargs):
        wx.Panel.__init__(self, parent, size=kwargs.get('size') or (-1,-1))
        
        self.btn = Button(self, label, icon=icon, tip=tip,
                                size=(-1,-1) if label or icon else (0,0))
        
        kwargs['style'] = kwargs.get('style', 0)
        kwargs['style'] |= wx.TE_PROCESS_ENTER|(wx.TE_READONLY if readonly else 0)
        self.ctrl = wx.TextCtrl(self, **kwargs)
        ## self.ctrl.SetFont(
        ##     wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'MS Gothic'))
        
        self.SetSizer(
            mwx.pack(self,
                (self.btn, 0, wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT, 0),
                (self.ctrl, 1, wx.EXPAND|wx.RIGHT, 0),
                orient=wx.HORIZONTAL,
            )
        )
        if handler:
            self.ctrl.Bind(wx.EVT_TEXT_ENTER, handler) # use style=wx.TE_PROCESS_ENTER
        if updater:
            self.btn.Bind(wx.EVT_BUTTON, lambda v: updater(self))


class Choice(wx.Panel):
    """Editable Choice (ComboBox) control panel
    If input item is not found, appends to `choices (only if `readonly=0)
    """
    Value = property(
        lambda self: self.ctrl.GetValue(),
        lambda self,v: self.ctrl.SetValue(v))
    value = Value
    
    Selection = property(
        lambda self: self.ctrl.GetSelection(),
        lambda self,v: self.ctrl.SetSelection(v))
    index = Selection
    
    def reset(self, v=None):
        if v is not None:
            self.value = v
    
    def __getattr__(self, attr): #! to be deprecated (Note: Panel interface is prior)
        return getattr(self.ctrl, attr)
    
    def __init__(self, parent, label='',
        handler=None, updater=None, icon=None, tip=None, readonly=0, selection=None, **kwargs):
        wx.Panel.__init__(self, parent, size=kwargs.get('size') or (-1,-1))
        
        self.btn = Button(self, label, icon=icon, tip=tip,
                                size=(-1,-1) if label or icon else (0,0))
        
        kwargs['style'] = kwargs.get('style', 0)
        kwargs['style'] |= wx.TE_PROCESS_ENTER|(wx.CB_READONLY if readonly else 0)
        self.ctrl = wx.ComboBox(self, **kwargs)
        
        self.SetSizer(
            mwx.pack(self,
                (self.btn, 0, wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT, 0),
                (self.ctrl, 1, wx.EXPAND|wx.RIGHT, 0),
                orient=wx.HORIZONTAL,
            )
        )
        if handler:
            self.ctrl.Bind(wx.EVT_COMBOBOX, handler)
            self.ctrl.Bind(wx.EVT_TEXT_ENTER, handler) # use style=wx.TE_PROCESS_ENTER
        self.ctrl.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        if updater:
            self.btn.Bind(wx.EVT_BUTTON, lambda v: updater(self))
        if selection is not None:
            self.index = selection
    
    def OnEnter(self, evt):
        s = evt.String.strip()
        if not s:
            self.ctrl.SetSelection(-1)
        elif s not in self.ctrl.Items:
            self.ctrl.Append(s)
            self.ctrl.SetStringSelection(s)
        evt.Skip()



if __name__ == '__main__':
    print(version())
    
    session = None
    online = None
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "s:", ["pyjem="])
        for k,v in opts:
            if k == "-s":
                session = v if v.endswith(".jssn") else v + '.jssn'
            if k == "--pyjem":
                online = eval(v)
    except Exception as e:
        print("  Exception occurs in getopt;", e)
        sys.exit(1)
    
    ## --------------------------------
    ## Do import TEM3 before the wx.App
    ##   or else you never do it hereafter.
    ## --------------------------------
    ## switch --pyjem: 0(=offline), 1(=online), 2(=online+TEM3)
    try:
        if online:
            try:
                print("Loading PyJEM.detector...")
                from PyJEM import detector
                
                if online > 1:
                    print("Loading PyJEM.TEM3 module...")
                    from PyJEM import TEM3
            
            except Exception as e:
                print("  {}... pass".format(e))
                print("  Switching to offline mode.")
                online = 0
        
        if online == 0:
            print("Loading PyJEM.offline...")
            from PyJEM.offline import detector
            from PyJEM.offline import TEM3
    
    except Exception as e:
        print("  {}... pass".format(e))
        print("  PyJEM is supported under Python 3.5... sorry")
    
    ## --------------------------------
    ## Start main process
    ## Execute startup file and session
    ## --------------------------------
    app = wx.App()
    frm = pyJemacs(None)
    try:
        sys.path.insert(0, '')
        si = __import__('siteinit')
        print("Executing {!r}".format(si.__file__))
        si.init_frame(frm)
        
        debut = __import__('debut')
        print("Executing {!r}".format(debut.__file__))
        debut.init_spec(frm.inspector.shell)
        
        ## frm.inspector.shell._Nautilus__startup = debut.init_spec
        frm.inspector.shell.handler.bind('shell_cloned', debut.init_spec)
        
    except Exception:
        traceback.print_exc()
        pass
    
    if session:
        print("Starting session {!r}".format(session))
        frm.load_session(session, flush=False)
    
    frm.Show()
    app.MainLoop()

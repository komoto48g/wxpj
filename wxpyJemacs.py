#! python3
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
import glob
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
    ## Add eggs in the nest to the path (new PyJEM for PY38)
    home = os.path.dirname(os.path.abspath(__file__))
    if sys.version_info >= (3,8):
        eggs = os.path.join(home, "nest/*-py3.8.egg")
    else:
        eggs = os.path.join(home, "nest/*-py3.5.egg")
    for path in reversed(glob.glob(eggs)):
        sys.path.append(path)
import mwx
from mwx.controls import Icon, Button, ToggleButton, TextCtrl, Choice, Gauge, Indicator
from mwx.controls import Param, LParam, ControlPanel
from mwx.graphman import Layer, Thread, Graph
from mwx.graphman import Frame as Framebase
from pyJeol.temsys import NotifyFront
from pyJeol.temisc import Environ
import pyDM3reader as DM3lib

## import wx.lib.mixins.listctrl # for py2exe
## import wx.lib.platebtn as pb

__version__ = "0.34rc"
__author__ = "Kazuya O'moto <komoto@jeol.co.jp>"
__copyright__ = "Copyright (c) 2018-2021"

def version():
    return '\n  '.join((
      "<Python {}>".format(sys.version),
      "wx.version {}".format(wx.version()),
      "scipy/numpy version {}/{}".format(scipy.__version__, np.__version__),
      "matplotlib version {}".format(matplotlib.__version__),
      "Image version {}".format(Image.__version__),
      "cv2 version {}".format(cv2.__version__),
      "mwx {}".format(mwx.__version__),
      ))


class pyJemacs(Framebase):
    """the Frontend of Graph and Plug manager
    """
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
        
        ## HOME = sys.path[0]
        ## if HOME[-4:] == '.exe': # ~/dist/*.exe (py2exe)
        ##     HOME = os.path.dirname(os.path.dirname(HOME))
        ##     if HOME not in sys.path:
        ##         sys.path += [ HOME ] # adds root for loading plugins
        
        home = os.path.dirname(os.path.abspath(__file__))
        icon = os.path.join(home, "Jun.ico")
        if os.path.exists(icon):
            self.SetIcon(wx.Icon(icon, wx.BITMAP_TYPE_ICO))
        
        ## Settings with default acc [V]
        ## Note: referenced thru su.
        self.em = Environ(300e3)
        
        ## Notify process
        self.nfront = NotifyFront(self)
        self.notify = self.nfront.notify
        ## self.notify.start() # do not start here; do after setting 'host:port:online'
        
        self.menubar["File"][-4:-4] = [
            (100, "&Notifyee\tF11", "Notify logger", wx.ITEM_CHECK,
                lambda v: self.nfront.Show(v.IsChecked()),
                lambda v: v.Check(self.nfront.IsShown())),
        ]
        ## self.menubar["File"][9:9] = [ # insert menus for extension, option, etc.
        self.menubar["Plugins"] += [ # insert menus for extension, option, etc.
            ("Extensions", []),
            ("Functions", []),
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
        "Gatan DM3 file (*.dm3)|*.dm3", # Gatan DM3 extension (read-only)
        "Gatan DM4 file (*.dm4)|*.dm3", # Gatan DM4 extension (read-only)
       "Rigaku IMG file (*.img)|*.img", # Rigaku image file extension (read-only)
               "All files (*.*)|*.*",
    ]
    
    @staticmethod
    def read_buffer(path):
        """Read a buffer from path file (override) +.dm3 extension"""
        if path[-4:] in ('.dm3', '.dm4'):
            dmf = DM3lib.DM3(path)
            ## return dmf.image # PIL Image file
            return dmf.imagedata, {'header':dmf.info}
        
        ## if path[-4:] == '.dm4':
        ##     dmf = DM4lib.DM4File.open(path)
        ##     tags = dmf.read_directory()
        ##     data = tags.named_subdirs['ImageList'].unnamed_subdirs[1].named_subdirs['ImageData']
        ##     w = dmf.read_tag_data(data.named_subdirs['Dimensions'].unnamed_tags[0])
        ##     h = dmf.read_tag_data(data.named_subdirs['Dimensions'].unnamed_tags[1])
        ##     buf = dmf.read_tag_data(data.named_tags['Data'])
        ##     return np.asarray(buf, dtype=np.uint16).reshape(h,w), {'header':None}
        
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
        ext = path[-4:]
        if ext in ('.dm3', '.dm4', '.img'):
            raise NotImplementedError(
                "Saving as {} type is not supported".format(ext))
        return Framebase.write_buffer(path, buf)

Frame = pyJemacs


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
    if online is not None:
        try:
            if online > 1:
                print("Loading PyJEM.TEM3 module...")
                from PyJEM import TEM3
            elif online:
                print("Loading PyJEM...")
                import PyJEM
            else:
                print("Loading PyJEM.offline...")
                import PyJEM.offline
        except ImportError as e:
            print("  {}... pass".format(e))
            print("  PyJEM is supported under Python 3.5... sorry")
    
    ## --------------------------------
    ## Start main process with siteinit
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
        debut.init_spec(frm.inspector.rootshell)
        frm.inspector.rootshell.handler.bind('shell_cloned', debut.init_spec)
    except Exception:
        ## traceback.print_exc()
        raise
    
    if session:
        try:
            print("Starting session {!r}".format(session))
            frm.load_session(session, flush=False)
        except FileNotFoundError:
            print("- No such session file {!r}".format(session))
            pass
    
    frm.Show()
    app.MainLoop()

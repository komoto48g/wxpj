#! python3
# -*- coding: utf-8 -*-
"""The frontend of Graph and Plug manager.

Development phase::

    Phase 1. Legacy (2015--2017) TEM control.
    Phase 2. Phoenix (2018--2020) Integrated system for image analysis.
    Phase 3. Analysis center phoenix (2020--2021).
    Phase 4. Automation center phoenix (2022--2023).
"""
__version__ = "0.50rc"
__author__ = "Kazuya O'moto <komoto@jeol.co.jp>"
__copyright__ = "Copyright (c) 2018-2022"
__license__ = """\
This program is under MIT license
see https://opensource.org/licenses/MIT
"""
import getopt
import sys
import os
import re
import wx
import wx.adv
import numpy as np

from jgdk import Frame
from pyJeol.temsys import NotifyFront
import pyDM3reader as DM3lib


class MainFrame(Frame):
    """Frontend of Graph and Plug manager.
    """
    Name = "pyJemacs"
    
    def About(self):
        info = wx.adv.AboutDialogInfo()
        info.Name = self.Name
        info.Version = __version__
        info.Copyright = __copyright__ +' '+ __author__
        info.License = __license__
        info.Description = __doc__
        info.Developers = []
        info.DocWriters = []
        info.Artists = []
        info.SetWebSite("https://github.com/komoto48g")
        wx.adv.AboutBox(info)
    
    def __init__(self, *args, **kwargs):
        Frame.__init__(self, *args, **kwargs)
        
        ## Notify process
        self.nfront = NotifyFront(self)
        self.notify = self.nfront.notify
        
        wx.CallAfter(self.notify.start)
        
        self.menubar["File"][-4:-4] = [
            (wx.ID_NETWORK, "&Notify", "Notify logger", wx.ITEM_CHECK,
                lambda v: self.nfront.Show(v.IsChecked()),
                lambda v: v.Check(self.nfront.IsShown())),
        ]
        self.menubar["Plugins"] += [ # insert menus for extension, option, etc.
            ("Extensions", []),
            ("Functions", []),
            (),
        ]
        self.menubar.reset()
        
        home = os.path.dirname(__file__)
        
        icon = os.path.join(home, "Jun.ico")
        if os.path.exists(icon):
            self.SetIcon(wx.Icon(icon, wx.BITMAP_TYPE_ICO))
        
        if home not in sys.path: # Add home (to import Frame)
            sys.path.insert(0, home)
        
        sys.path.insert(0, os.path.join(home, 'plugins'))
        sys.path.insert(0, '') # Add local . to import si:local first
        try:
            si = __import__('siteinit')
        except ImportError:
            print("- No siteinit file.")
        else:
            print(f"Executing {si.__file__!r}")
            si.init_mainframe(self)
    
    def Destroy(self):
        self.nfront.Destroy()
        return Frame.Destroy(self)
    
    ## --------------------------------
    ## read/write buffers
    ## --------------------------------
    wildcards = [
              "TIF file (*.tif)|*.tif",
              "BMP file (*.bmp)|*.bmp",
        "Gatan DM3 file (*.dm3)|*.dm3", # Gatan DM3 extension (read-only)
        "Gatan DM4 file (*.dm4)|*.dm4", # Gatan DM4 extension (read-only)
       "Rigaku IMG file (*.img)|*.img", # Rigaku image file extension (read-only)
               "All files (*.*)|*.*",
    ]
    
    @staticmethod
    def read_buffer(path):
        """Read a buffer from path file (override) +.dm3 extension.
        """
        if path[-4:] in ('.dm3', '.dm4'):
            dmf = DM3lib.DM3(path)
            ## return dmf.image # PIL Image file
            return dmf.imagedata, {'header': dmf.info}
        
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
                return buf, {'header': info}
        
        return Frame.read_buffer(path)
    
    @staticmethod
    def write_buffer(path, buf):
        """Write a buffer to path file (override) +.dm3 extension.
        """
        ext = path[-4:]
        if ext in ('.dm3', '.dm4', '.img'):
            raise NotImplementedError(
                "Saving as {} type is not supported".format(ext))
        return Frame.write_buffer(path, buf)


if __name__ == "__main__":
    session = None
    online = None
    opts, args = getopt.gnu_getopt(sys.argv[1:], "s:", ["pyjem="])
    ## opts, args = getopt.gnu_getopt(sys.argv[1:], "s:")
    for k, v in opts:
        if k == "-s":
            if not v.endswith(".jssn"):
                v += ".jssn"
            session = v
        if k == "--pyjem":
            online = eval(v)

    ## Please import TEM3 before the wx.App, or else you never do it hereafter.
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
            print(e)
            ## print("  PyJEM is supported under Python 3.8... sorry")

    app = wx.App()
    frm = MainFrame(None)
    if session:
        try:
            print(f"Starting session {session!r}")
            frm.load_session(session, flush=False)
        except FileNotFoundError:
            print(f"- No such file {session!r}")
    try:
        from wxpyNautilus import debut
        debut.main(frm.shellframe)
    except ImportError:
        pass
    frm.Show()
    app.MainLoop()

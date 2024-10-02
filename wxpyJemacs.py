#! python3
"""The frontend of Graph and Plug manager.
"""
__version__ = "0.67"
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

from wxpj import Frame
from wxpj import stylus


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
        from pyJeol.temsys import NotifyFront
        
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
            (),
        ]
        self.menubar.reset()
        
        HOME = os.path.dirname(__file__)
        self.SetIcon(wx.Icon(os.path.join(HOME, "Jun.ico"), wx.BITMAP_TYPE_ICO))
        
        for f in [
                HOME,   # Add ~/ to import si:home
                '',     # Add ./ to import si:local first
                ]:
            if f not in sys.path:
                sys.path.insert(0, f)
        try:
            si = __import__('siteinit')
        except ImportError:
            print("- No siteinit file.")
        else:
            print(f"Executing {si.__file__!r}")
            si.init_mainframe(self)
        stylus(self.shellframe)
    
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
        _, ext = os.path.splitext(path)
        
        if ext in ('.dm3', '.dm4'):
            from pyDM3reader import DM3
            
            dmf = DM3(path)
            buf = dmf.imagedata # cf. dmf.image <PIL Image file>
            info = dmf.info
            return buf, {'header': info}
        
        if ext == '.img':
            with open(path, 'rb') as i:
                head = i.read(4096).decode()
                head = head[1:head.find('}')] # get header in '{...}'
                head = re.sub(r"(\w+)=\s(.*?);\n", r"\1=r'\2',", head)
                info = eval(f"dict({head})")
                w = int(info['SIZE1'])
                h = int(info['SIZE2'])
                type = info['Data_type']
                if type == 'unsigned short int':
                    dtype = np.uint16
                elif type == 'unsigned long int':
                    dtype = np.uint32
                else:
                    raise Exception(f"unexpected data type {type!r}")
                buf = np.frombuffer(i.read(), dtype)
                buf.resize(h, w)
            return buf, {'header': info}
        
        return Frame.read_buffer(path)
    
    @staticmethod
    def write_buffer(path, buf):
        """Write a buffer to path file (override) +.dm3 extension.
        """
        _, ext = os.path.splitext(path)
        if ext in ('.dm3', '.dm4', '.img'):
            raise NotImplementedError(f"Saving as {ext} type is not supported")
        
        return Frame.write_buffer(path, buf)


if __name__ == "__main__":
    session = None
    opts, args = getopt.gnu_getopt(sys.argv[1:], "s:")
    for k, v in opts:
        if k == "-s":
            if not v.endswith(".jssn"):
                v += ".jssn"
            session = v
    
    app = wx.App()
    frm = MainFrame(None)
    if session:
        try:
            print(f"Starting session {session!r}")
            frm.load_session(session, flush=False)
        except FileNotFoundError:
            print(f"- No such file {session!r}")
    frm.Show()
    app.MainLoop()

#! python
# -*- coding: utf-8 -*-
"""Rigaku camera module

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
from datetime import datetime
import socket
import time
import os
import re
import wx
import numpy as np
from PIL import Image
from mwx.controls import Param, LParam
from mwx.graphman import Layer
import wxpyJemacs as wxpj

hostnames = [
    'localhost',
    '172.17.41.50',
]

typenames_info = { # [mm/pix], h, w, (bins,
    "HyPix" : (0.100, 385, 775),
}


class HyPix(object):
    def __init__(self, host, port, timeout=4):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.stream = None
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, t, v, tb):
        self.close()
    
    def open(self):
        if not self.stream:
            print("Initializing port {}:{}... ".format(self.host, self.port), end='')
            self.stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.stream.settimeout(self.timeout or None)
            errno = self.stream.connect_ex((self.host, self.port))
            if errno:
                print("failed to open ({}): ".format(errno), end='')
                self.stream = None
            print(errno == 0)
            return (errno == 0)
        self.close()
        return self.open()
    
    def close(self):
        if self.stream:
            self.stream.close()
            self.stream = None
            print("port {}:{} is closed.".format(self.host, self.port))
    
    def send(self, name, *argv):
        try:
            args = ''.join("/{}".format(x) for x in argv or ())
            cmd = "\2{}{}\r\n".format(name, args)
            nbytes = self.stream.send(cmd.encode())
            buf = self.flush()
            m = re.match("\2C\r{}(.*)\r\n".format(name), buf.decode())
            if m:
                data = m.group(1)
                if data.startswith('/'):
                    data = data[1:]
                return data.split('/') # ret: list of string
        except socket.timeout as e:
            print(e)
    
    def flush(self):
        bufsize = 8192
        buf = b""
        while 1:
            s = self.stream.recv(bufsize)
            buf += s
            if len(s) < bufsize:
                break
        return buf


## if __name__ == "__main__":
##     import mwx
##     host = '172.17.41.50'
##     
##     with HyPix(host, 60000) as cont:
##         with HyPix(host, 60001) as conn:
##             ## print(cont.send("GetState"))
##             print(cont.send("GetImage", 1,1,0,0))
##             data = conn.flush()
##             data += conn.flush()
##             print("data =", data)
##             print(len(data))
##             mwx.deb()


class Camera(object):
    """Rigaku camera (proxy of Detector)
    """
    busy = 0
    
    def __init__(self, host):
        self.name = "HyPix"
        self.cont = HyPix(host, 60000)
        self.conn = HyPix(host, 60001)
        self.dtype = np.uint16
        self.cached_time = 0
        self.cached_image = None
    
    def start(self):
        """Begin with camera settings"""
        if self.cont.open() and self.conn.open():
            self.cont.send("ExpTime", 100)
            self.cont.send("NumFrame", 1)
            self.cont.send("ImgMode", 0) # type={0:uint16, 1:uint32,}
            self.cont.send("AcqMode", 0)
            self.cont.send("OutputMode", 0)
            self.cont.send("ZeroDeadTimeState", 0,0)
            self.cont.send("ExpInterval", 0)
            self.cont.send("ExpDelay", 0)
            self.cont.send("ActiveOut", 0)
            self.cont.send("ExtTrgEnable", 0)
            self.cont.send("Calibration", 2,1,1,1,1)
            self.cont.send("Monitor")
            print(self.cont.send("GetDataInfo"))
            print(self.cont.send("GetDetectorConfig"))
            
            ret = self.cont.send("GetImage", 1,1,0,0) # psuh a sentinel.
            if ret:
                time.sleep(1)
                try:
                    data = self.conn.flush() # receive all bytes
                    h, w = (385, 775)
                    ndt = int((len(data) - 4096) /h /w)
                    print("  {:,d} bytes data (type:{}u) received".format(len(data), ndt))
                except Exception as e:
                    print(e)
            return True
    
    def stop(self):
        """End acquisition and connection"""
        self.camera.cont.send("StopAcq")
        self.cont.close()
        self.conn.close()
    
    def cache(self):
        """Cache of the current image <uint16|uint32>"""
        try:
            while Camera.busy:
                time.sleep(0.01) # ここで通信待機
            Camera.busy += 1
            if time.time() - self.cached_time < self.exposure:
                if self.cached_image is not None:
                    return self.cached_image
            
            h, w = (385, 775)
            if self.dtype == np.uint16:
                nbytes = 4096 + w * h * 2 # 600,846 bytes - unsigned short int
            elif self.dtype == np.uint32:
                nbytes = 4096 + w * h * 4  # 1,197,596 bytes - unsigned long int
            else:
                raise Exception("unsupported data type (>1)")
            ret = self.cont.send("GetImage", 1,1,0,0)
            if ret:
                time.sleep(self.exposure)
                data = self.conn.stream.recv(nbytes)
                if len(data) < nbytes:
                    print("- failed to read:"
                          " {} bytes read (expected {} bytes)".format(len(data), nbytes))
                    return
                buf = np.frombuffer(data, self.dtype, offset=4096)
            buf.resize(h, w)
            self.cached_image = buf
            self.cached_time = time.time()
            return buf
        finally:
            Camera.busy -= 1
    
    ## pixel size [mm/pixel] without binning modification
    pixel_size = 0.1
    pixel_unit = 0.1
    binning = 1
    
    @property
    def shape(self):
        h, w = (385, 775)
        return h, w
    
    @property
    def exposure(self):
        """Exposure time [s] 0.0125us(1/80MHz) -- 4,294,967,295ms (2^32-1)"""
        ret, = self.cont.send("ExpTime")
        return float(ret)/1000
    
    @exposure.setter
    def exposure(self, sec):
        self.cont.send("ExpTime", sec*1000)


class Plugin(Layer):
    """Rigaku camera manager
    """
    menu = "Plugins/Cameras"
    menustr = "&Rigaku camera ver.2"
    
    def Init(self):
        self.binning_selector = Param("bin", (1,), handler=self.set_binning)
        self.exposure_selector = LParam("exp", (0.05, 5, 0.05), handler=self.set_exposure)
        
        self.dark_chk = wx.CheckBox(self, label="dark")
        self.dark_chk.Enable(0)
        
        self.name_selector = wxpj.Choice(self,
            choices=list(typenames_info), size=(100,22), readonly=1)
        
        self.host_selector = wxpj.Choice(self,
            choices=hostnames, size=(100,22))
        
        self.unit_selector = LParam("mm/pix", (0,1,1e-4), 0.1)
        
        self.layout("Acquire setting", (
            self.binning_selector,
            self.exposure_selector,
            ),
            type='vspin', lw=32, cw=-1, tw=40
        )
        self.layout(None, (
            wxpj.Button(self, "Capture", self.capture_ex, icon='cam'),
            self.dark_chk,
            ),
            row=2,
        )
        self.layout("Setup", (
            self.name_selector,
            self.host_selector,
            self.unit_selector,
            wxpj.Button(self, "Connect", self.connect, size=(-1,20)),
            wxpj.Button(self, "Prepare/dark", self.prepare_dark, size=(-1,20)),
            ),
            row=1, show=0, type=None, lw=-1, tw=50, editable=0,
        )
    
    def set_current_session(self, session):
        self.name_selector.value = session.get('name')
        self.host_selector.value = session.get('host')
        self.unit_selector.value = session.get('unit')
        self.preset_dark()
    
    def get_current_session(self):
        return {
            'name': self.name_selector.value,
            'host': self.host_selector.value,
            'unit': self.unit_selector.value,
        }
    
    ## --------------------------------
    ## Camera Attribtues
    ## --------------------------------
    camera = None
    
    def set_exposure(self, p):
        if self.camera:
            self.camera.exposure = p.value
    
    def set_binning(self, p):
        if self.camera:
            ## self.camera.binning = p.value # *no binning (=1 const.)
            self.preset_dark()
    
    def connect(self, evt=None):
        name = self.name_selector.value
        host = self.host_selector.value
        if not name:
            print(self.message("- Camera name is not specified."))
            return
        try:
            self.camera = Camera(host)
            
            if not self.camera.start():
                raise OSError("- Failed to start camera")
            
            self.message("Connected to {!r}".format(self.camera))
            
            ## <--- set camera parameter
            self.camera.binning = self.binning_selector.value
            self.camera.exposure = self.exposure_selector.value
            self.preset_dark()
            return self.camera
        
        except Exception as e:
            print(self.message("- Connection failed; {!r}".format(e)))
            self.camera = None
    
    ## --------------------------------
    ## Camera Interface
    ## --------------------------------
    dark_image = None
    
    @property
    def dark_filename(self):
        if self.camera:
            name = self.camera.name
            binning = self.camera.binning
        else:
            name = self.name_selector.value
            binning = self.binning_selector.value
            
        return "{}-dark-bin{}.tif".format(name, binning)
    
    @property
    def attributes(self):
        return {
                'camera' : self.camera.name,
                 'pixel' : self.camera.pixel_size,
               'binning' : self.camera.binning,
              'exposure' : self.camera.exposure,
          'acq_datetime' : datetime.now(), # acquired datetime stamp
        }
    
    def acquire(self):
        """Acquire image with no dark subtraction"""
        try:
            if self.camera is None:
                self.connect()
            try:
                return self.camera.cache()
            except Exception:
                self.camera.start()
                return self.camera.cache()
        except Exception as e:
            print(self.message("- Failed to acquire image: {!r}".format(e)))
    
    def capture(self):
        """Capture image
        If `dark subtraction' is checked, the image is dark-subtracted,
        and the result image is dtype:float32, otherwise uint16.
        """
        buf = self.acquire()
        if buf is not None:
            if self.dark_chk.Value and self.dark_image is not None:
                return buf - self.dark_image
        return buf
    
    def capture_ex(self, evt=None):
        """Capture image and load to the target window
        """
        self.message("Capturing image...")
        buf = self.capture()
        if buf is not None:
            frame = self.graph.load(buf,
                localunit=self.camera.pixel_unit, **self.attributes)
            self.parent.handler('frame_cached', frame)
    
    def preset_dark(self, evt=None): # internal use only
        f = self.dark_filename
        if os.path.exists(f):
            self.dark_image = np.asarray(Image.open(f)) # cf. read_buffer
            self.dark_chk.Enable(1)
            self.dark_chk.SetToolTip("Subtract dark: {!r}".format(f))
        else:
            ## self.message("- No such file: {!r}".format(f))
            self.dark_chk.Enable(0)
    
    def prepare_dark(self, evt=None, verbose=True):
        """Prepare dark reference
        Before execution, blank the beam manually.
        Please close the curtain to prevent light leakage.
        """
        if not self.camera:
            wx.MessageBox("The camera is not ready", self.__module__,
                style=wx.ICON_WARNING)
            return
        
        if verbose:
            if wx.MessageBox("Proceeding new dark reference.", self.__module__,
                style=wx.OK|wx.CANCEL|wx.ICON_INFORMATION) != wx.OK:
                    return
        
        f = self.dark_filename
        
        self.dark_image = self.acquire().astype(np.float32) # for underflow in subtraction
        self.dark_chk.Value = True
        self.dark_chk.Enable(1)
        self.dark_chk.SetToolTip("Subtract dark: {!r}".format(f))
        
        Image.fromarray(self.dark_image).save(f) # cf. write_buffer
        
        frame = self.output.load(self.dark_image, name=f,
            localunit=self.camera.pixel_unit, pathname=f, **self.attributes)
        
        self.parent.handler('frame_cached', frame)
        self.message("dark ref saved to {!r}".format(f))

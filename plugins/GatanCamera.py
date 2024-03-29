#! python3
"""Gatan Camera module.
"""
from datetime import datetime
import time
import os
import wx
import numpy as np
from PIL import Image

from jgdk import Layer, Param, LParam, Button, Choice
from pyGatan import gatan


hostnames = [
    'localhost',
    '172.17.41.3',
    '172.17.41.13',
]

typenames_info = { # [mm/pix], h, w, (bins,
    "USC1000" : (0.0140, 2048, 2048),
      "SC200" : (0.0074, 2048, 2048),
         "K2" : (0.0050, 3710, 3838),
         "K3" : (0.0050, 4092, 5760),
    "OneView" : (0.0150, 4096, 4096),
}


class Camera(gatan.GatanSocket):
    """Gatan camera (proxy of Detector).
    """
    busy = 0
    
    pixel_unit = property(lambda self: self.pixel_size * self.binning)
    
    def __init__(self, name, host):
        gatan.GatanSocket.__init__(self, host)
        
        self.name = name
        self.info = typenames_info[name]
        self.pixel_size = self.info[0]
        self.shape = self.info[1:3]
        self.binning = 1
        self.exposure = 0.1
        if name == 'K3':
            # [K2] 0:Linear, 1:Counting, 2:S/Res
            # [K3] 3:linear, 4:S/Res
            self.mode = 4
        else:
            self.mode = 0
        self.SetK2Parameters(
                readMode = self.mode,
                 scaling = 1.0,
            hardwareProc = 4,
                doseFrac = 0,
               frameTime = 0.1,
             alignFrames = 0,
              saveFrames = 0,
        )
    
    def cache(self):
        """Cache of the current image."""
        try:
            while Camera.busy:
                time.sleep(0.01) # ここで通信待機
            Camera.busy += 1
            
            h, w = H, W = self.shape
            bin = self.binning
            if self.mode == 4:
                ## [K3] Defaults to 4 (S/Res mode).
                H *= 2
                W *= 2
                bin *= 2
            buf = self.GetImage(
              processing = 'gain normalized',
                  height = H//bin,
                   width = W//bin,
                 binning = bin,
                     top = 0,
                    left = 0,
                  bottom = h//bin,
                   right = w//bin,
                exposure = self.exposure,
            shutterDelay = 0,
            )
            return buf
        finally:
            Camera.busy -= 1


class Plugin(Layer):
    """Gatan camera manager.
    """
    menukey = "Cameras/&Gatan camera ver.2"
    
    def Init(self):
        self.binning_selector = Param("bin", (1,2,4), 1, handler=self.set_binning)
        self.exposure_selector = LParam("exp", (0, 5, 0.05), 0.05, handler=self.set_exposure)
        
        self.dark_chk = wx.CheckBox(self, label="dark")
        self.dark_chk.Enable(0)
        
        self.name_selector = Choice(self,
            choices=list(typenames_info), size=(100,22), readonly=1,
            handler=lambda p: self.unit_selector.reset(typenames_info[p.Value][0]))
        
        self.host_selector = Choice(self,
            choices=hostnames, size=(100,22))
        
        self.unit_selector = LParam("mm/pix", (0,1,1e-4))
        
        self.layout((
                self.binning_selector,
                self.exposure_selector,
            ),
            title="Acquire setting",
            type='vspin', cw=-1, lw=32, tw=40
        )
        self.layout((
                Button(self, "Capture", self.capture_ex, icon='camera'),
                self.dark_chk,
            ),
            row=2,
        )
        self.layout((
                self.name_selector,
                self.host_selector,
                self.unit_selector,
                
                Button(self, "Connect", self.connect, size=(-1,20)),
                Button(self, "Prepare/dark", self.prepare_dark, size=(-1,20)),
                Button(self, "Insert camera", self.insert, size=(-1,20)),
            ),
            title="Setup", show=0,
            type=None, lw=-1, tw=50, editable=0,
        )
        self.__camera = None
    
    ## --------------------------------
    ## Camera Attributes
    ## --------------------------------
    @property
    def camera(self):
        return self.__camera
    
    def set_exposure(self, p):
        if p.value < 0.01:
            p.value = 0.01
        if self.camera:
            self.camera.exposure = p.value
    
    def set_binning(self, p):
        if self.camera:
            self.camera.binning = p.value
            self.preset_dark()
    
    def connect(self, evt=None):
        name = self.name_selector.value
        host = self.host_selector.value
        if not name:
            print(self.message("- Camera name is not specified."))
            return
        try:
            self.__camera = Camera(name, host)
            
            self.message("Connected to {!r}".format(self.camera))
            self.message("\b GMS ver.{}".format(self.camera.GetDMVersion()))
            
            ## <--- set camera parameter
            self.camera.binning = self.binning_selector.value
            self.camera.exposure = self.exposure_selector.value
            
            ## ---> get camera info from system
            self.unit_selector.value = self.camera.pixel_size
            self.preset_dark()
            return self.camera
        
        except Exception as e:
            print(self.message("- Connection failed; {!r}".format(e)))
            self.__camera = None
    
    def insert(self, evt=None, ins=True):
        if self.camera:
            if ins and not self.camera.IsCameraInserted(0):
                self.camera.InsertCamera(0, True)
                time.sleep(5)
            else:
                self.camera.InsertCamera(0, False)
    
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
        """Acquire image with no dark subtraction."""
        try:
            if self.camera is None:
                self.connect()
            return self.camera.cache().copy()
        except Exception as e:
            print(self.message("- Failed to acquire image: {!r}".format(e)))
    
    def capture(self):
        """Capture image.
        
        If 'dark subtraction' is checked, the image is dark-subtracted,
        and the result image is dtype:float32, otherwise uint16.
        """
        buf = self.acquire()
        if buf is not None:
            if self.dark_chk.Value and self.dark_image is not None:
                return buf - self.dark_image
        return buf
    
    def capture_ex(self, evt=None):
        """Capture image and load to the target window.
        """
        self.message("Capturing image...")
        buf = self.capture()
        if buf is not None:
            frame = self.graph.load(buf,
                localunit=self.camera.pixel_unit, **self.attributes)
            self.parent.handler('frame_cached', frame)
            return frame
    
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
        """Prepare dark reference.
        
        Before execution, blank the beam manually.
        Please close the curtain to prevent light leakage.
        """
        if not self.camera:
            wx.MessageBox(
                "The camera is not ready",
                self.__module__,
                style=wx.ICON_WARNING)
            return
        
        if verbose:
            if wx.MessageBox(
                    "Proceeding new dark reference.",
                    self.__module__,
                    style=wx.ICON_INFORMATION) != wx.OK:
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

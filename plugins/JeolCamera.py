#! python3
"""Jeol Camera module.
"""
from datetime import datetime
import time
import os
import wx
import numpy as np
from PIL import Image

from jgdk import Layer, Param, LParam, Button, Choice
from pyJeol.detector import Detector


hostnames = [
    'localhost',
    '172.17.41.1',  # TEM server
]

typenames_info = { # 0:maxcnt, (pixel_size, bins, gains,
    "camera"      : (65535, ), # dummy for offline
    "TVCAM_U"     : (65535, ), # Flash cam
    "TVCAM_SCR_L" : ( 4095, ), # Large screen
    "TVCAM_SCR_F" : ( 4095, ), # Focus screen
}


class Camera(object):
    """Jeol camera (proxy of Detector).
    
    Args:
        name : name of selected camera
        host : localhost if offline (default) otherwise 172.17.41.1
    
    Camera property::
    
        cont        : camera controller
        pixel_size  : raw pixel size [u/pix]
        pixel_unit  : pixel (with binning) size [u/pix]
        exposure    : exposure time [s]
        binning     : binning number (typ. 1,2,4) in bins <list>
        gain        : gain number (1 -- 10) in gains <list>
        shape       : (h,w) height and width of image
        max_count   : the maximum count (used to check if saturated)
    """
    busy = 0
    bins = (1,2,4)
    gains = np.arange(1, 10.1, 0.5)
    
    def __init__(self, name, host):
        self.name = name
        self.host = host
        self.cont = Detector(name, host)
        self.pixel_size = 0.05
        self.cached_time = 0
        self.cached_image = None
        self.max_count = typenames_info[self.name][0]
        try:
            self.cont.StartCache() # setup cache
        except Exception:
            pass
    
    def __del__(self):
        try:
            self.cont.StopCache()  # close cache
        except Exception:
            pass
    
    def start(self):
        self.cont.LiveStart()
    
    def stop(self):
        self.cont.LiveStop()
    
    def cache(self):
        """Cache of the current image <uint16>."""
        try:
            while Camera.busy:
                time.sleep(0.01) # ここで通信待機
            Camera.busy += 1
            if time.time() - self.cached_time < self.exposure:
                if self.cached_image is not None:
                    return self.cached_image
            
            data = self.cont.Cache()
            buf = np.frombuffer(data, dtype=np.uint16)
            buf.resize(self.shape)
            self.cached_image = buf
            self.cached_time = time.time()
            return buf
        finally:
            Camera.busy -= 1
    
    @property
    def cached_saturation(self):
        buf = self.cached_image
        if buf is not None:
            return buf.max() == self.max_count
    
    ## pixel size [mm/pix] without binning modification
    pixel_size = 0.05
    pixel_unit = property(lambda self: self.pixel_size * self.binning)
    
    @property
    def shape(self):
        info = self.cont['OutputImageInformation']['ImageSize']
        h = info['Height']
        w = info['Width']
        return h, w
    
    @property
    def exposure(self):
        return self.cont['ExposureTimeValue'] / 1e3
    
    @exposure.setter
    def exposure(self, sec):
        if abs(self.exposure - sec) > 1e-6:
            self.cont['ExposureTimeValue'] = sec * 1e3
        
    @property
    def binning(self):
        try:
            return self.bins[self.cont['BinningIndex']]
        except KeyError:
            pass
    
    @binning.setter
    def binning(self, v):
        if 0 < v <= self.bins[-1]:
            j = np.searchsorted(self.bins, v) #<np.int64> crashes online▲
            self.cont['BinningIndex'] = int(j)
    
    @property
    def gain(self):
        try:
            return self.gains[self.cont['GainIndex']]
        except KeyError:
            pass
    
    @gain.setter
    def gain(self, v):
        if 0 < v <= self.gains[-1]:
            j = np.searchsorted(self.gains, v) #<np.int64> crashes online▲
            self.cont['GainIndex'] = int(j)


class DummyCamera(object):
    """Dummy camera (proxy of Detector).
    """
    def __init__(self, parent):
        self.parent = parent
        self.name = 'camera'
        self.host = 'localhost'
        self.gain = 1
        self.binning = 1
        self.exposure = 0.05
        self.cached_time = 0
        self.cached_image = None
        self.max_count = typenames_info[self.name][0]
    
    def cache(self):
        ## n = 2048 // self.binning
        ## buf = np.uint16(np.random.randn(n, n) * self.max_count)
        buf = self.parent.graph.buffer
        self.cached_image = buf
        self.cached_time = time.time()
        return buf
    
    @property
    def cached_saturation(self):
        buf = self.cached_image
        if buf is not None:
            return buf.max() == self.max_count
    
    pixel_size = 0.05
    pixel_unit = property(lambda self: self.pixel_size * self.binning)
    
    @property
    def shape(self):
        return self.parent.graph.buffer.shape


class Plugin(Layer):
    """Jeol camera manager.
    """
    menukey = "Cameras/&Jeol camera ver.2"
    
    def Init(self):
        self.binning_selector = Param("bin", (1,2,4), 1, handler=self.set_binning)
        self.exposure_selector = LParam("exp", (0, 5, 0.05), 0.05, handler=self.set_exposure)
        self.gain_selector = LParam("gain", (1, 10, 0.5), 5, handler=self.set_gain)
        
        self.dark_chk = wx.CheckBox(self, label="dark")
        self.dark_chk.Enable(0)
        
        self.name_selector = Choice(self,
            choices=list(typenames_info), size=(100,22), readonly=1)
        
        self.host_selector = Choice(self,
            choices=hostnames, size=(100,22))
        
        self.unit_selector = LParam("mm/pix", (0,1,1e-4), self.graph.unit,
            handler=self.set_pixsize)
        
        self.layout((
                self.binning_selector,
                self.exposure_selector,
                self.gain_selector,
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
            ),
            title="Setup", show=0,
            type=None, lw=-1, tw=50,
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
    
    def set_gain(self, p):
        if self.camera:
            self.camera.gain = p.value
    
    def set_pixsize(self, p):
        if self.camera:
            self.camera.pixel_size = p.value
    
    def connect(self, evt=None):
        name = self.name_selector.value
        host = self.host_selector.value
        if not name:
            print(self.message("- Camera name is not specified."))
            return
        try:
            if name != 'camera':
                self.__camera = Camera(name, host)
                self.camera.start()
            else:
                self.__camera = DummyCamera(self)
            
            self.message("Connected to {!r}".format(self.camera))
            
            ## <--- set camera parameter
            self.camera.pixel_size = self.unit_selector.value
            
            ## ---> get camera info from system
            self.gain_selector.value = self.camera.gain
            self.binning_selector.value = self.camera.binning
            self.exposure_selector.value = self.camera.exposure
            self.preset_dark()
            return self.camera
        
        except Exception as e:
            print(self.message("- Connection failed; {!r}".format(e)))
            self.__camera = None
    
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

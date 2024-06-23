#! python3
"""Jeol Camera module.
"""
from datetime import datetime
import time
import threading
import traceback
import numpy as np

from jgdk import Layer, Param, LParam, Button, Choice
from pyJeol.detector import Detector


hostnames = [
    'localhost',
    '172.17.41.1',  # TEM server
]

typenames_info = { # maxcnt,
    "camera"      : (65535, ), # dummy camera
    "TVCAM_U"     : (65535, ), # Flash camera
    "TVCAM_SCR_L" : ( 4095, ), # Large screen
    "TVCAM_SCR_F" : ( 4095, ), # Focus screen
}


class Camera:
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
    """
    bins = (1, 2, 4)
    gains = np.arange(1, 10.1, 0.5)
    
    def __init__(self, name, host):
        self.name = name
        self.host = host
        self.cont = Detector(name, host)
        self.pixel_size = 0.05
        self._cached_time = 0
        self._cached_image = None
        self._cached_exposure = 0.1
        self._lock = threading.RLock()
    
    def __del__(self):
        try:
            self.cont.StopCache()  # close cache
        except Exception:
            pass
    
    def start(self):
        """Start live and cache."""
        self.cont.LiveStart()
        self.cont.StartCache()
        self._cached_exposure = self.exposure
    
    def stop(self):
        """Stop live and cache."""
        self.cont.LiveStop()
        self.cont.StopCache()
    
    def cache(self):
        """Cache of the current image <uint16>."""
        if time.perf_counter() - self._cached_time < self._cached_exposure:
            if self._cached_image is not None:
                return self._cached_image
        with self._lock:
            data = self.cont.Cache()
            buf = np.frombuffer(data, dtype=np.uint16)
            buf.resize(self.shape)
            self._cached_image = buf
            self._cached_time = time.perf_counter()
            return buf
    
    @property
    def pixel_unit(self):
        return self.pixel_size * self.binning
    
    @property
    def shape(self):
        with self._lock:
            info = self.cont['OutputImageInformation']['ImageSize']
            h = info['Height']
            w = info['Width']
            return h, w
    
    @property
    def exposure(self):
        with self._lock:
            return self.cont['ExposureTimeValue'] / 1e3
    
    @exposure.setter
    def exposure(self, sec):
        with self._lock:
            if abs(self.exposure - sec) > 1e-6:
                self.cont['ExposureTimeValue'] = sec * 1e3
                self._cached_exposure = sec
    
    @property
    def binning(self):
        with self._lock:
            try:
                return self.bins[self.cont['BinningIndex']]
            except KeyError:
                pass
    
    @binning.setter
    def binning(self, v):
        with self._lock:
            if 0 < v <= self.bins[-1]:
                j = np.searchsorted(self.bins, v) #<np.int64> crashes online▲
                self.cont['BinningIndex'] = int(j)
    
    @property
    def gain(self):
        with self._lock:
            try:
                return self.gains[self.cont['GainIndex']]
            except KeyError:
                pass
    
    @gain.setter
    def gain(self, v):
        with self._lock:
            if 0 < v <= self.gains[-1]:
                j = np.searchsorted(self.gains, v) #<np.int64> crashes online▲
                self.cont['GainIndex'] = int(j)


class DummyCamera:
    """Dummy camera (proxy of Detector).
    """
    def __init__(self, name, host):
        self.name = name
        self.host = host
        self.gain = 1
        self.binning = 1
        self.exposure = 0.1
        self.pixel_size = 0.05
        self.max_size = 1024
    
    def start(self):
        pass
    
    def stop(self):
        pass
    
    def cache(self):
        n = self.max_size // self.binning
        buf = np.uint16((0.5 + 0.1 * np.random.randn(n, n)) * 0xffff)
        return buf
    
    @property
    def pixel_unit(self):
        return self.pixel_size * self.binning
    
    @property
    def shape(self):
        w = h = self.max_size // self.binning
        return w, h


class Plugin(Layer):
    """Jeol camera manager.
    """
    menukey = "Cameras/&Jeol camera ver.2"
    
    def Init(self):
        self.binning_selector = Param("bin", (1,2,4), 1, handler=self.set_binning)
        self.exposure_selector = LParam("exp", (0, 5, 0.05), 0.05, handler=self.set_exposure)
        self.gain_selector = LParam("gain", (1, 10, 0.5), 5, handler=self.set_gain)
        
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
            ),
            row=2,
        )
        self.layout((
                self.name_selector,
                self.host_selector,
                self.unit_selector,
                Button(self, "Connect", self.connect, size=(-1,20)),
            ),
            title="Setup", show=0,
            type=None, lw=-1, tw=50,
        )
        self.camera = None
    
    ## --------------------------------
    ## Camera Attributes
    ## --------------------------------
    
    def set_exposure(self, p):
        if p.value < 0.01:
            p.value = 0.01
        if self.camera:
            self.camera.exposure = p.value
    
    def set_binning(self, p):
        if self.camera:
            self.camera.binning = p.value
    
    def set_gain(self, p):
        if self.camera:
            self.camera.gain = p.value
    
    def set_pixsize(self, p):
        if self.camera:
            self.camera.pixel_size = p.value
    
    def connect(self):
        name = self.name_selector.value
        host = self.host_selector.value
        if not name:
            self.message("- Camera name is not specified.")
            return
        try:
            self.message(f"Connecting to {name}...")
            if name == 'camera':
                self.camera = DummyCamera(name, host)
            else:
                self.camera = Camera(name, host)
            self.camera.start()
            
            self.message("Connected to", self.camera)
            
            ## <--- set camera parameter
            self.camera.pixel_size = self.unit_selector.value
            
            ## ---> get camera info from system
            self.gain_selector.value = self.camera.gain
            self.binning_selector.value = self.camera.binning
            self.exposure_selector.value = self.camera.exposure
            return self.camera
        
        except Exception as e:
            self.message("- Connection failed:", e)
            self.camera = None
    
    def capture(self, view=False, **kwargs):
        """Capture image.
        
        Args:
            view    : If True, the buffer will be loaded into the graph view.
            **kwargs: Additional attributes of the buffer frame.
                      Used only if view is True.
        """
        try:
            if self.camera is None:
                self.connect()
            buf = self.camera.cache()
        except Exception:
            traceback.print_exc()
            buf = None
        else:
            if view and buf is not None:
                attributes = {
                    'localunit' : self.camera.pixel_unit,
                       'camera' : self.camera.name,
                        'pixel' : self.camera.pixel_size,
                      'binning' : self.camera.binning,
                     'exposure' : self.camera.exposure,
                 'acq_datetime' : datetime.now(),
                }
                frame = self.graph.load(buf, **attributes, **kwargs)
                self.parent.handler('frame_cached', frame)
        return buf
    
    def capture_ex(self):
        """Capture image and load into the graph view."""
        return self.capture(True)

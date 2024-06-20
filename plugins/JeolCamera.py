#! python3
"""Jeol Camera module.
"""
from datetime import datetime
import time
import traceback
import numpy as np

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
        max_count   : the maximum count (used to check if saturated)
    """
    busy = 0
    bins = (1, 2, 4)
    gains = np.arange(1, 10.1, 0.5)
    
    def __init__(self, name, host):
        self.name = name
        self.host = host
        self.cont = Detector(name, host)
        self.pixel_size = 0.05
        self._cached_time = 0
        self._cached_image = None
        self.max_count = typenames_info[self.name][0]
        ## try:
        ##     self.cont.StartCache() # setup cache
        ## except Exception:
        ##     pass
    
    def __del__(self):
        try:
            self.cont.StopCache()  # close cache
        except Exception:
            pass
    
    def start(self):
        self.cont.LiveStart()
        self.cont.StartCache() # setup cache
    
    def stop(self):
        self.cont.StopCache()  # close cache
        self.cont.LiveStop()
    
    def cache(self):
        """Cache of the current image <uint16>."""
        try:
            while Camera.busy:
                time.sleep(0.01) # ここで通信待機
            Camera.busy += 1
            if time.perf_counter() - self._cached_time < self.exposure:
                if self._cached_image is not None:
                    return self._cached_image
            
            data = self.cont.Cache()
            buf = np.frombuffer(data, dtype=np.uint16)
            buf.resize(self.shape)
            self._cached_image = buf
            self._cached_time = time.perf_counter()
            return buf
        finally:
            Camera.busy -= 1
    
    @property
    def cached_saturation(self):
        buf = self._cached_image
        if buf is not None:
            return buf.max() == self.max_count
    
    @property
    def pixel_unit(self):
        return self.pixel_size * self.binning
    
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


class DummyCamera:
    """Dummy camera (proxy of Detector).
    """
    def __init__(self, parent):
        self.parent = parent
        self.name = 'camera'
        self.host = 'localhost'
        self.gain = 1
        self.binning = 1
        self.exposure = 0.05
        self.pixel_size = 0.05
        self._cached_time = 0
        self._cached_image = None
        self.max_count = typenames_info[self.name][0]
    
    def cache(self):
        ## n = 2048 // self.binning
        ## buf = np.uint16(np.random.randn(n, n) * self.max_count)
        buf = self.parent.graph.buffer
        self._cached_image = buf
        self._cached_time = time.perf_counter()
        return buf
    
    @property
    def cached_saturation(self):
        buf = self._cached_image
        if buf is not None:
            return buf.max() == self.max_count
    
    @property
    def pixel_unit(self):
        return self.pixel_size * self.binning
    
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
    
    @property
    def attributes(self):
        return {
                'camera' : self.camera.name,
                 'pixel' : self.camera.pixel_size,
               'binning' : self.camera.binning,
              'exposure' : self.camera.exposure,
          'acq_datetime' : datetime.now(), # acquired datetime stamp
        }
    
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
            if name != 'camera':
                self.camera = Camera(name, host)
                self.camera.start()
            else:
                self.camera = DummyCamera(self)
            
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
    
    def capture(self, blit=False):
        """Capture image.
        If blit is True, it will be loaded into the graph view.
        """
        try:
            self.message("Capturing image...")
            if self.camera is None:
                self.connect()
            buf = self.camera.cache()
        except Exception as e:
            self.message("- Failed to acquire image:", e)
            traceback.print_exc()
            buf = None
        else:
            if blit and buf is not None:
                frame = self.graph.load(buf,
                    localunit=self.camera.pixel_unit, **self.attributes)
                self.parent.handler('frame_cached', frame)
        return buf
    
    def capture_ex(self):
        """Capture image and load into the graph view."""
        return self.capture(blit=True)

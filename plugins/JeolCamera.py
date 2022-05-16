#! python3
# -*- coding: utf-8 -*-
"""Jeol Camera module

Author: Kazuya O'moto <komoto@jeol.co.jp>
Contributions by Hiroyuki Satoh @JEOL.JP
"""
from datetime import datetime
import time
import sys
import os
import wx
import httplib2
import numpy as np
from PIL import Image
from jgdk import Layer, Param, LParam, Button, Choice

try:
    Offline = None
    from PyJEM import detector

except ImportError:
    Offline = 1
    try:
        if 'PyJEM.offline' in sys.modules:
            print('Loading PyJEM:offline module has already loaded.')
            from PyJEM.offline import detector
            Offline = True
        
        elif 'PyJEM' in sys.modules:
            print('Loading PyJEM:online module has already loaded.')
            from PyJEM import detector
            Offline = False
        
        else: # the case when this modulue is tested in standalone
            if Offline:
                from PyJEM.offline import detector
            else:
                from PyJEM import detector
        
    except ImportError:
        print("Current sys.version is Python {}".format(sys.version.split()[0]))
        print("- PyJEM is supported under Python 3.5... sorry")
        Offline = None
        detector = None

try:
    detector.change_ip("172.17.41.1")
except AttributeError:
    pass

## REST client
##   Performs a single HTTP request.
##   The return value is a tuple of (response, content),
##   the first being an instance of the 'Response' class,
##   the second being a string that contains the response entity body.
## 
HTTP = httplib2.Http()
TEM_URL = "http://{}:49229/TEMService/TEM/{}".format
CAM_URL = "http://{}:49230/CameraStationService/{}".format
DET_URL = "http://{}:49226/DetectorRESTService/Detector/{}".format

HEADER = {"connection" : "close"}


def StartCreateCache(host):
    """ライブ像のキャッシュを受け取るようにする処理の開始"""
    url = DET_URL(host, "StartCreateRawDataCache")
    res, con = HTTP.request(url, "POST", headers=HEADER)
    return con

def StopCreateCache(host):
    """ライブ像のキャッシュを受け取るようにする処理の停止"""
    url = DET_URL(host, "StopCreateRawDataCache")
    res, con = HTTP.request(url, "POST", headers=HEADER)
    return con

def CreateCache(host, name):
    """ライブ像のキャッシュを受け取る"""
    url = DET_URL(host, name + "/CreateRawDataCache")
    res, data = HTTP.request(url, "GET", headers=HEADER)
    return data


hostnames = [
    'localhost',
    '172.17.41.1',  # TEM server
]

typenames_info = { # 0:maxcnt, (pixel_size, bins, gains,
         "camera" : (65535, ), # dummy for offline
        "TVCAM_U" : (65535, ), # Flash cam
    "TVCAM_SCR_L" : ( 4095, ), # Large screen
    "TVCAM_SCR_F" : ( 4095, ), # Focus screen
}


class Camera(object):
    """Jeol Camera (proxy of Detector)
    
    name : name of selected camera
    host : localhost if offline (default) otherwise 172.17.41.1
    cont : camera controller
    
Camera property:
  pixel_size : raw pixel size [u/pix]
  pixel_unit : pixel (with binning) size [u/pix]
    exposure : exposure time [s]
     binning : binning number (typ. 1,2,4) in bins <list>
        gain : gain number (1 -- 10) in gains <list>
       shape : (h,w) height and width of image
   max_count : the maximum count (used to check if saturated)
    """
    busy = 0
    bins = (1,2,4)
    gains = np.arange(1, 10.1, 0.5)
    
    def __init__(self, name, host):
        self.name = name
        self.host = host
        self.cont = detector.Detector(name)
        self.pixel_size = 0.05
        self.__bin_index = 0
        self.__gain_index = 0
        self.cached_time = 0
        self.cached_image = None
        self.cached_saturation = None
        self.max_count = typenames_info[self.name][0]
    
    def __del__(self):
        try:
            StopCreateCache(self.host) # ▲不要みたいだがトレースバックがうぜえ
        except Exception:
            pass
    
    def start(self):
        StartCreateCache(self.host) # check status
        self.cont.livestart()
        return True
    
    def stop(self):
        StopCreateCache(self.host) # close connection
        self.cont.livestop()
    
    def cache(self):
        """Cache of the current image <uint16>"""
        try:
            while Camera.busy:
                time.sleep(0.01) # ここで通信待機
            Camera.busy += 1
            if time.time() - self.cached_time < self.exposure:
                if self.cached_image is not None:
                    return self.cached_image
            
            StartCreateCache(self.host)
            data = CreateCache(self.host, self.name)
            buf = np.frombuffer(data, dtype=np.uint16)
            buf.resize(self.shape)
            self.cached_image = buf
            self.cached_time = time.time()
            self.cached_saturation = (buf.max() == self.max_count)
            return buf
        finally:
            Camera.busy -= 1
    
    ## pixel size [mm/pix] without binning modification
    pixel_size = 0.05
    pixel_unit = property(lambda self: self.pixel_size * self.binning)
    
    @property
    def shape(self):
        ji = self.cont.get_detectorsetting()
        h = ji['OutputImageInformation']['ImageSize']['Height']
        w = ji['OutputImageInformation']['ImageSize']['Width']
        return h, w
    
    @property
    def exposure(self):
        ji = self.cont.get_detectorsetting()
        return ji['ExposureTimeValue'] /1e3
    
    @exposure.setter
    def exposure(self, sec):
        if abs(self.exposure - sec) > 1e-6:
            self.cont.set_exposuretime_value(sec * 1e3) # set as <msec>
    
    @property
    def binning(self):
        ji = self.cont.get_detectorsetting()
        return self.bins[ji.get('BinningIndex', self.__bin_index)]
    
    @binning.setter
    def binning(self, v):
        if 0 < v <= self.bins[-1]:
            j = np.searchsorted(self.bins, v)
            self.__bin_index = j
            self.cont.set_binningindex(int(j)) #<np.int64> crashes online▲
    
    @property
    def gain(self):
        ji = self.cont.get_detectorsetting()
        return self.gains[ji.get('GainIndex', self.__gain_index)]
    
    @gain.setter
    def gain(self, v):
        if 0 < v <= self.gains[-1]:
            j = np.searchsorted(self.gains, v)
            self.__gain_index = j
            self.cont.set_gainindex(int(j)) #<np.int64> crashes online▲


class DummyCamera(object):
    def __init__(self, parent):
        self.parent = parent
        self.name = 'camera'
        self.host = 'localhost'
        self.gain = 1
        self.binning = 1
        self.exposure = 0.05
        self.cached_time = 0
        self.cached_image = None
        self.cached_saturation = None
        self.max_count = typenames_info[self.name][0]
    
    def cache(self):
        ## n = 2048 // self.binning
        ## return np.uint16(np.random.randn(n,n) * self.max_count)
        buf = self.parent.graph.buffer
        self.cached_image = buf
        self.cached_time = time.time()
        self.cached_saturation = (buf.max() == self.max_count)
        return buf
    
    pixel_size = 0.05
    pixel_unit = property(lambda self: self.pixel_size * self.binning)
    
    @property
    def shape(self):
        return self.parent.graph.buffer.shape


class Plugin(Layer):
    """Jeol camera manager
    """
    menu = "Cameras"
    menustr = "&Jeol camera ver.2"
    
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
            type='vspin', lw=32, cw=-1, tw=40
        )
        self.layout((
                Button(self, "Capture", self.capture_ex, icon='cam'),
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
            title="Setup",
            row=1, show=0, type=None, lw=-1, tw=50,
        )
        self.__camera = None
    
    ## --------------------------------
    ## Camera Attribtues
    ## --------------------------------
    @property
    def camera(self):
        return self.__camera
    
    def set_exposure(self, p):
        if p.value < 0.001:
            p.value = 0.001
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

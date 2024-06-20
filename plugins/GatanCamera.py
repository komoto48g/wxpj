#! python3
"""Gatan Camera module.
"""
from datetime import datetime
import time
import traceback

from jgdk import Layer, Param, LParam, Button, Choice
from pyGatan import GatanSocket


hostnames = [
    'localhost',
    '172.17.41.3',
    '172.17.41.13',
]

typenames_info = { # pixel_size, h, w, ...
    "USC1000" : (0.0140, 2048, 2048, ),
    "SC200"   : (0.0074, 2048, 2048, ),
    "K2"      : (0.0050, 3710, 3838, ),
    "K3"      : (0.0050, 4092, 5760, ),
    "OneView" : (0.0150, 4096, 4096, ),
}


class Camera(GatanSocket):
    """Gatan camera (proxy of Detector).
    """
    busy = 0
    
    @property
    def pixel_unit(self):
        return self.pixel_size * self.binning
    
    def __init__(self, name, host):
        GatanSocket.__init__(self, host)
        
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
            type=None, lw=-1, tw=50, editable=0,
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
    
    def connect(self):
        name = self.name_selector.value
        host = self.host_selector.value
        if not name:
            self.message("- Camera name is not specified.")
            return
        try:
            self.message(f"Connecting to {name}...")
            self.camera = Camera(name, host)
            
            self.message("Connected to", self.camera)
            self.message("\b GMS ver.", self.camera.GetDMVersion())
            
            ## <--- set camera parameter
            self.camera.binning = self.binning_selector.value
            self.camera.exposure = self.exposure_selector.value
            
            ## ---> get camera info from system
            self.unit_selector.value = self.camera.pixel_size
            return self.camera
        
        except Exception as e:
            self.message("- Connection failed:", e)
            self.camera = None
    
    def insert(self, ins=True):
        if self.camera:
            if ins and not self.camera.IsCameraInserted(0):
                self.camera.InsertCamera(0, True)
                time.sleep(5)
            else:
                self.camera.InsertCamera(0, False)
    
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
                        localunit = self.camera.pixel_unit,
                           camera = self.camera.name,
                            pixel = self.camera.pixel_size,
                          binning = self.camera.binning,
                         exposure = self.camera.exposure,
                     acq_datetime = datetime.now())
                self.parent.handler('frame_cached', frame)
        return buf
    
    def capture_ex(self):
        """Capture image and load into the graph view."""
        return self.capture(blit=True)

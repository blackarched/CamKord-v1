import cv2 import glob import platform import logging import subprocess from typing import List, Dict, Optional

class CameraError(Exception): """Custom exception for camera errors.""" pass

class USBCameraManager: """ Manages detection and access of USB webcams on Linux and Windows. """

def __init__(self) -> None:
    self.logger = logging.getLogger(self.__class__.__name__)
    logging.basicConfig(level=logging.INFO)

def list_cameras(self) -> List[Dict[str, Optional[int]]]:
    """
    Detects connected USB cameras and returns a list of dicts with 'index' and 'name'.
    """
    system = platform.system()
    self.logger.info(f"Detecting cameras on {system}")

    if system == 'Linux':
        return self._list_linux()
    elif system == 'Windows':
        return self._list_windows()
    else:
        msg = f"Unsupported platform: {system}"  
        self.logger.error(msg)
        raise CameraError(msg)

def _list_linux(self) -> List[Dict[str, Optional[int]]]:
    cameras = []
    devices = glob.glob('/dev/video*')
    for dev in devices:
        try:
            idx = int(dev.replace('/dev/video', ''))
            cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            if cap is None or not cap.isOpened():
                continue
            name = self._get_linux_device_name(dev)
            cameras.append({'index': idx, 'name': name})
        except Exception as e:
            self.logger.warning(f"Error probing {dev}: {e}")
        finally:
            if 'cap' in locals() and cap.isOpened():
                cap.release()
    return cameras

def _get_linux_device_name(self, dev_path: str) -> Optional[str]:
    """
    Retrieves the device name using v4l2-ctl if available.
    """
    try:
        result = subprocess.run(
            ['v4l2-ctl', '--device', dev_path, '--info'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
            text=True
        )
        for line in result.stdout.splitlines():
            if line.strip().startswith('Driver name'):
                return line.split(':', 1)[1].strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # v4l2-ctl not installed or error running
        self.logger.debug("v4l2-ctl not available or failed")
    return None

def _list_windows(self) -> List[Dict[str, Optional[int]]]:
    cameras = []
    # Windows: probe indices 0-10 with DirectShow backend
    for idx in range(0, 10):
        try:
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap is None or not cap.isOpened():
                continue
            cameras.append({'index': idx, 'name': f'Camera {idx}'})
        except Exception as e:
            self.logger.warning(f"Error probing camera index {idx}: {e}")
        finally:
            if 'cap' in locals() and cap.isOpened():
                cap.release()
    return cameras

def open_camera(self, index: int, width: int = 640, height: int = 480) -> cv2.VideoCapture:
    """
    Opens and configures a camera by index with desired resolution.
    :param index: The index of the camera to open.
    :param width: Desired frame width.
    :param height: Desired frame height.
    :return: Configured cv2.VideoCapture object.
    :raises CameraError: If camera cannot be opened.
    """
    backend = cv2.CAP_DSHOW if platform.system() == 'Windows' else cv2.CAP_V4L2
    cap = cv2.VideoCapture(index, backend)
    if cap is None or not cap.isOpened():
        msg = f"Unable to open camera at index {index}"  
        self.logger.error(msg)
        raise CameraError(msg)

    # Configure resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Verify resolution
    actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if actual_width != width or actual_height != height:
        self.logger.warning(
            f"Requested resolution ({width}x{height}) not supported. "
            f"Got ({int(actual_width)}x{int(actual_height)})"
        )
    self.logger.info(f"Opened camera {index} at {int(actual_width)}x{int(actual_height)}")
    return cap

def get_supported_resolutions(self, index: int) -> List[Dict[str, int]]:
    """
    Attempts to determine supported resolutions by testing common presets.
    :return: List of resolutions as dicts {'width': w, 'height': h}.
    """
    common_res = [
        (1920,1080), (1280,720), (1024,768),
        (800,600), (640,480), (320,240)
    ]
    supported = []
    for w, h in common_res:
        try:
            cap = self.open_camera(index, w, h)
            actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            if int(actual_w) == w and int(actual_h) == h:
                supported.append({'width': w, 'height': h})
        except CameraError:
            continue
        finally:
            if 'cap' in locals() and cap.isOpened():
                cap.release()
    return supported

Example usage (for integration; remove or adjust logging in production)

if name == 'main': manager = USBCameraManager() cams = manager.list_cameras() for cam in cams: print(f"Index: {cam['index']}, Name: {cam['name']}") if cams: cap = manager.open_camera(cams[0]['index'], 1280, 720) ret, frame = cap.read() if ret: cv2.imwrite('test_capture.jpg', frame) cap.release()


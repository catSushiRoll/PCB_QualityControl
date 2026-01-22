import cv2
import platform

class CameraDetector:
    def __init__(self):
        self.system = platform.system()
    
    def get_camera_list(self):
        """
        Deteksi kamera yang tersedia di sistem
        Return: dictionary {nama_kamera: index}
        """
        available_cameras = {}
        
        if self.system == "Windows":
            available_cameras = self._detect_cameras_windows()
        else:
            available_cameras = self._detect_cameras_default()
        
        return available_cameras
    
    def _detect_cameras_windows(self):
        """Deteksi kamera khusus untuk Windows dengan multiple backends"""
        cameras = {}
        max_cameras = 10
        
        print("\n" + "="*60)
        print("CAMERA DETECTION - WINDOWS")
        print("="*60)
        
        # Method 1: DirectShow (CAP_DSHOW)
        print("\n[1] Trying DirectShow (CAP_DSHOW)...")
        dshow_cameras = self._try_backend(cv2.CAP_DSHOW, "DirectShow", max_cameras)
        cameras.update(dshow_cameras)
        
        # Method 2: MSMF (Microsoft Media Foundation)
        if not cameras:
            print("\n[2] DirectShow failed, trying MSMF (CAP_MSMF)...")
            msmf_cameras = self._try_backend(cv2.CAP_MSMF, "MSMF", max_cameras)
            cameras.update(msmf_cameras)
        
        # Method 3: Default (no backend specified)
        if not cameras:
            print("\n[3] All backends failed, trying default method...")
            default_cameras = self._try_backend(None, "Default", max_cameras)
            cameras.update(default_cameras)
        
        # Method 4: Try with different indices more aggressively
        if not cameras:
            print("\n[4] Aggressive scan without backend...")
            aggressive_cameras = self._aggressive_scan(max_cameras)
            cameras.update(aggressive_cameras)
        
        print("\n" + "="*60)
        print(f"TOTAL CAMERAS FOUND: {len(cameras)}")
        print("="*60 + "\n")
        
        # If still nothing found, add manual options
        if not cameras:
            print("⚠️  WARNING: No cameras auto-detected!")
            print("Adding manual options for testing...\n")
            cameras = {
                "Camera 0 (Manual - Try Me!)": 0,
                "Camera 1 (Manual - Try Me!)": 1,
                "Camera 2 (Manual - Try Me!)": 2,
            }
        
        return cameras
    
    def _try_backend(self, backend, backend_name, max_cameras):
        """Try to detect cameras with specific backend"""
        cameras = {}
        
        for i in range(max_cameras):
            try:
                # Open with specific backend or default
                if backend is not None:
                    cap = cv2.VideoCapture(i, backend)
                else:
                    cap = cv2.VideoCapture(i)
                
                # Check if opened
                if cap.isOpened():
                    # Try to read a frame to verify it actually works
                    ret, frame = cap.read()
                    
                    if ret and frame is not None:
                        # Get camera properties
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        
                        camera_name = f"Camera {i} - {width}x{height} ({backend_name})"
                        cameras[camera_name] = i
                        
                        print(f"  ✓ Camera {i}: {width}x{height} ({backend_name})")
                    else:
                        print(f"  ✗ Camera {i}: Opened but cannot read frame")
                    
                    cap.release()
                else:
                    # Silently skip if cannot open
                    pass
                    
            except Exception as e:
                print(f"  ✗ Camera {i}: Error - {e}")
        
        return cameras
    
    def _aggressive_scan(self, max_cameras):
        """Aggressive scan trying different approaches"""
        cameras = {}
        
        print("  Trying to force open cameras...")
        
        for i in range(max_cameras):
            # Try multiple times with delays
            for attempt in range(2):
                try:
                    cap = cv2.VideoCapture(i)
                    
                    # Force some properties
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    
                    if cap.isOpened():
                        # Multiple read attempts
                        ret = False
                        for read_attempt in range(3):
                            ret, frame = cap.read()
                            if ret:
                                break
                        
                        if ret and frame is not None:
                            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            
                            camera_name = f"Camera {i} - {width}x{height} (Forced)"
                            cameras[camera_name] = i
                            
                            print(f"  ✓ Camera {i}: Found with forced open!")
                            cap.release()
                            break
                    
                    cap.release()
                    
                except Exception as e:
                    pass
        
        return cameras
    
    def _detect_cameras_default(self):
        """Deteksi kamera dengan method default (Linux/Mac)"""
        cameras = {}
        max_cameras = 10
        
        print("\n" + "="*60)
        print("CAMERA DETECTION - LINUX/MAC")
        print("="*60 + "\n")
        
        for i in range(max_cameras):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        
                        cameras[f"Camera {i} - {width}x{height}"] = i
                        print(f"  ✓ Camera {i}: {width}x{height}")
                    cap.release()
            except Exception as e:
                print(f"  ✗ Camera {i}: {e}")
        
        print("\n" + "="*60)
        print(f"TOTAL CAMERAS FOUND: {len(cameras)}")
        print("="*60 + "\n")
        
        return cameras
    
    def test_camera(self, index, backend=None):
        """Test apakah kamera dengan index tertentu bisa dibuka"""
        try:
            if backend is not None:
                cap = cv2.VideoCapture(index, backend)
            else:
                cap = cv2.VideoCapture(index)
            
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                return ret and frame is not None
            return False
        except:
            return False
    
    def get_camera_info(self, index):
        """Dapatkan informasi detail kamera"""
        info = {}
        
        backends_to_try = [cv2.CAP_DSHOW, cv2.CAP_MSMF, None] if self.system == "Windows" else [None]
        
        for backend in backends_to_try:
            try:
                cap = cv2.VideoCapture(index, backend) if backend else cv2.VideoCapture(index)
                
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        info['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        info['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        info['fps'] = int(cap.get(cv2.CAP_PROP_FPS))
                        info['backend'] = backend
                        cap.release()
                        return info
                
                cap.release()
            except:
                continue
        
        return None
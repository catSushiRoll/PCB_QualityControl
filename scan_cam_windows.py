"""
Camera Diagnostic Tool
Jalankan script ini untuk test deteksi kamera Taffware
"""

import cv2
import platform

def test_all_backends():
    """Test semua backend yang tersedia"""
    print("\n" + "="*70)
    print("CAMERA DIAGNOSTIC TOOL")
    print("="*70)
    print(f"OS: {platform.system()}")
    print(f"OpenCV Version: {cv2.__version__}")
    print("="*70 + "\n")
    
    backends = {
        "DirectShow (CAP_DSHOW)": cv2.CAP_DSHOW,
        "MSMF (CAP_MSMF)": cv2.CAP_MSMF,
        "VFW (CAP_VFW)": cv2.CAP_VFW,
        "Default (No backend)": None,
    }
    
    max_index = 5
    found_cameras = []
    
    for backend_name, backend_id in backends.items():
        print(f"\n{'='*70}")
        print(f"Testing: {backend_name}")
        print(f"{'='*70}")
        
        for i in range(max_index):
            try:
                print(f"\n  Testing index {i}...", end=" ")
                
                # Open camera
                if backend_id is not None:
                    cap = cv2.VideoCapture(i, backend_id)
                else:
                    cap = cv2.VideoCapture(i)
                
                # Check if opened
                if not cap.isOpened():
                    print("❌ Cannot open")
                    continue
                
                # Try to read
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    print("⚠️  Opened but cannot read frame")
                    cap.release()
                    continue
                
                # Get properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                print(f"✅ SUCCESS!")
                print(f"     Resolution: {width}x{height}")
                print(f"     FPS: {fps}")
                print(f"     Backend: {backend_name}")
                
                found_cameras.append({
                    'index': i,
                    'backend': backend_name,
                    'backend_id': backend_id,
                    'width': width,
                    'height': height,
                    'fps': fps
                })
                
                cap.release()
                
            except Exception as e:
                print(f"❌ Error: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if found_cameras:
        print(f"\n✅ Found {len(found_cameras)} working camera(s):\n")
        for i, cam in enumerate(found_cameras, 1):
            print(f"{i}. Camera Index: {cam['index']}")
            print(f"   Backend: {cam['backend']}")
            print(f"   Resolution: {cam['width']}x{cam['height']}")
            print(f"   FPS: {cam['fps']}")
            print()
        
        print("\n💡 SOLUTION FOR YOUR PROGRAM:")
        print("="*70)
        best_cam = found_cameras[0]
        print(f"Use Camera Index: {best_cam['index']}")
        print(f"With Backend: {best_cam['backend']}")
        
        if best_cam['backend_id'] == cv2.CAP_DSHOW:
            print("\nIn your code, use:")
            print(f"  cap = cv2.VideoCapture({best_cam['index']}, cv2.CAP_DSHOW)")
        elif best_cam['backend_id'] == cv2.CAP_MSMF:
            print("\nIn your code, use:")
            print(f"  cap = cv2.VideoCapture({best_cam['index']}, cv2.CAP_MSMF)")
        else:
            print("\nIn your code, use:")
            print(f"  cap = cv2.VideoCapture({best_cam['index']})")
        
    else:
        print("\n❌ NO CAMERAS DETECTED!")
        print("\nPossible solutions:")
        print("1. Check if camera is properly connected")
        print("2. Check Device Manager (Windows)")
        print("3. Close other apps using the camera (Zoom, Teams, etc.)")
        print("4. Try updating camera drivers")
        print("5. Run this script as Administrator")
    
    print("\n" + "="*70 + "\n")

def test_specific_camera(index, backend=None):
    """Test kamera spesifik dengan detail"""
    print(f"\n{'='*70}")
    print(f"Testing Camera Index: {index}")
    if backend:
        print(f"Backend: {backend}")
    print(f"{'='*70}\n")
    
    try:
        # Open
        if backend == "DSHOW":
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        elif backend == "MSMF":
            cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
        else:
            cap = cv2.VideoCapture(index)
        
        if not cap.isOpened():
            print("❌ Cannot open camera")
            return False
        
        print("✅ Camera opened successfully")
        
        # Read frame
        ret, frame = cap.read()
        if not ret or frame is None:
            print("❌ Cannot read frame")
            cap.release()
            return False
        
        print("✅ Frame read successfully")
        
        # Properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"\nCamera Properties:")
        print(f"  Resolution: {width}x{height}")
        print(f"  FPS: {fps}")
        print(f"  Frame shape: {frame.shape}")
        
        # Show frame untuk 5 detik
        print("\nShowing camera feed for 5 seconds...")
        print("Press 'q' to quit early")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < 5:
            ret, frame = cap.read()
            if ret:
                cv2.imshow(f"Camera {index} Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cv2.destroyAllWindows()
        cap.release()
        
        print("\n✅ Camera test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    print("Select option:")
    print("1. Auto-detect all cameras (recommended)")
    print("2. Test specific camera index")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        test_all_backends()
    elif choice == "2":
        index = int(input("Enter camera index (0, 1, 2...): "))
        backend = input("Enter backend (DSHOW/MSMF/blank for default): ").strip().upper()
        if not backend:
            backend = None
        test_specific_camera(index, backend)
    else:
        print("Invalid choice")
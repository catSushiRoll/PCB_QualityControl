import cv2
import subprocess
import sys
import re
import glob

class CameraDetector:
    def __init__(self):
        self.cameras = {}
        self.hardware_info = {}
    
    def get_camera_hardware_id(self, video_index):
        try:
            # Get device info using udevadm
            device_path = f"/dev/video{video_index}"
            result = subprocess.run(
                ['udevadm', 'info', '--name', device_path, '--attribute-walk'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode != 0:
                return None
            
            output = result.stdout

            vendor_match = re.search(r'ATTRS{idVendor}=="([^"]+)"', output)
            product_match = re.search(r'ATTRS{idProduct}=="([^"]+)"', output)
            serial_match = re.search(r'ATTRS{serial}=="([^"]+)"', output)
            manufacturer_match = re.search(r'ATTRS{manufacturer}=="([^"]+)"', output)
            product_name_match = re.search(r'ATTRS{product}=="([^"]+)"', output)
            
            info = {}
            if vendor_match:
                info['idVendor'] = vendor_match.group(1)
            if product_match:
                info['idProduct'] = product_match.group(1)
            if serial_match:
                info['serial'] = serial_match.group(1)
            if manufacturer_match:
                info['manufacturer'] = manufacturer_match.group(1)
            if product_name_match:
                info['product_name'] = product_name_match.group(1)
            
            return info if info else None
        
        except Exception as e:
            print(e)
            return None
    
    def identify_camera_by_hardware_id(self, hw_info):
        """Identify camera type based on hardware ID"""
        if not hw_info:
            return None
        
        vendor = hw_info.get('idVendor', '').lower()
        product = hw_info.get('idProduct', '').lower()
        product_name = hw_info.get('product_name', '').lower()
        manufacturer = hw_info.get('manufacturer', '').lower()
        
        # Known camera mappings (customize based on your cameras)
        known_cameras = {
            ('30c9', '0002'): 'Integrated Camera',
            ('1224', '2825'): 'Taffware Camera',
            # from -> udevadm info --name=/dev/video2 --attribute-walk | grep -E "idVendor|idProduct"
        }
        
        camera_id = (vendor, product)
        if camera_id in known_cameras:
            return known_cameras[camera_id]
        
        # Fallback to product name
        if 'taffware' in product_name or 'taffware' in manufacturer:
            return 'Taffware Camera'
        
        if 'integrated' in product_name or product_name:
            return product_name.title()
        
        # Generic name
        if manufacturer:
            return f"{manufacturer.title()} Camera"
        
        return None
    
    def detect_with_hardware_id(self):
        try:
            # Check if udevadm is available
            subprocess.run(['udevadm', '--version'], 
                        capture_output=True, timeout=1, check=True)
        except:
            print("udevadm not available")
            return False
        
        found_count = 0
        
        for i in range(10):
            cap = cv2.VideoCapture(i, cv2.CAP_ANY)
            
            if not cap.isOpened():
                cap.release()
                continue
            
            ret, frame = cap.read()
            if not ret:
                cap.release()
                continue

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            backend = cap.getBackendName()
            cap.release()

            hw_info = self.get_camera_hardware_id(i)
            
            if hw_info:
                self.hardware_info[i] = hw_info
                camera_name = self.identify_camera_by_hardware_id(hw_info)
                
                if not camera_name:
                    camera_name = f"Camera {i}"
                
                vendor = hw_info.get('idVendor', 'unknown')
                product = hw_info.get('idProduct', 'unknown')
                serial = hw_info.get('serial', 'N/A')
                
                # print(f"\n /dev/video{i}:")
                # print(f"   Name        : {camera_name}")
                # print(f"   idVendor    : {vendor}")
                # print(f"   idProduct   : {product}")
                # print(f"   Serial      : {serial}")
                # print(f"   Resolution  : {width}x{height}")
                # print(f"   FPS         : {fps}")
                
                self.cameras[i] = {
                    'name': camera_name,
                    'index': i,
                    'resolution': f"{width}x{height}",
                    'fps': fps,
                    'backend': backend,
                    'idVendor': vendor,
                    'idProduct': product,
                    'serial': serial,
                    'hardware_info': hw_info
                }
                
                found_count += 1
            else:
                camera_name = f"Camera {i}"
                # print(f"/dev/video{i}: No hardware ID found, using generic name")
                
                self.cameras[i] = {
                    'name': camera_name,
                    'index': i,
                    'resolution': f"{width}x{height}",
                    'fps': fps,
                    'backend': backend,
                }
                found_count += 1
        
        return found_count > 0
    
    def detect_with_v4l2(self):
        try:
            result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                capture_output=True, text=True, timeout=3)
            
            if result.returncode != 0:
                print("v4l2-ctl command failed")
                return False
            
            print("v4l2-ctl output:")
            print(result.stdout)
            
            # Parse output
            lines = result.stdout.strip().split('\n')
            current_device = None
            
            for line in lines:
                line_stripped = line.strip()
                
                # Device name line
                if line and not line.startswith('\t') and not line.startswith(' ') and ':' in line:
                    current_device = line.rstrip(':')
                    # Clean device name
                    current_device = current_device.replace('(usb-', '').replace(')', '')
                
                # Device path line
                elif '/dev/video' in line:
                    try:
                        video_num = int(line.split('/dev/video')[-1].split()[0])
                        
                        if current_device:
                            # Detect common types
                            if 'integrated' in current_device.lower() or video_num == 0:
                                friendly_name = f"Integrated Camera"
                            elif 'taffware' in current_device.lower() or video_num == 2:
                                friendly_name = f"Taffware Camera"
                            else:
                                friendly_name = current_device.split(':')[0].strip()
                        else:
                            friendly_name = f"Camera {video_num}"
                        
                        self.cameras[video_num] = {
                            'name': friendly_name,
                            'index': video_num,
                            'raw_name': current_device or f"Unknown Device"
                        }
                    
                    except (ValueError, IndexError) as e:
                        print(f"Failed to parse: {line} - {e}")
            
            return len(self.cameras) > 0
        
        except FileNotFoundError:
            print("v4l2-ctl not found. Install with: sudo apt install v4l-utils")
            return False
        except Exception as e:
            print(e)
            return False
    
    def detect_manual(self):
        found_count = 0
        
        for i in range(10):
            print(f"Testing /dev/video{i}...", end=" ")
            
            cap = cv2.VideoCapture(i, cv2.CAP_ANY)
            
            if cap.isOpened():
                ret, frame = cap.read()
                
                if ret:
                    # Get camera info
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = int(cap.get(cv2.CAP_PROP_FPS))
                    backend = cap.getBackendName()
                    
                    # Assign friendly name
                    if i == 0:
                        name = "Integrated Camera"
                    elif i == 2:
                        name = "Taffware Camera"
                    else:
                        name = f"Camera {i}"
                    
                    self.cameras[i] = {
                        'name': name,
                        'index': i,
                        'resolution': f"{width}x{height}",
                        'fps': fps,
                        'backend': backend,
                        'raw_name': f"{name} ({backend})"
                    }

                    print(f"Found: {name} - {width}x{height} @ {fps}fps")
                    found_count += 1
                else:
                    print("Opened but no frame")
                
                cap.release()
            else:
                print("Not available")
        
        return found_count > 0
    
    def test_camera(self, index):
        """Test a specific camera"""
        print(f"\n{'='*60}")
        print(f"TESTING CAMERA: /dev/video{index}")
        print("="*60)
        
        cap = cv2.VideoCapture(index, cv2.CAP_ANY)
        
        if not cap.isOpened():
            print(f"Cannot open camera {index}")
            return False
        
        print("Camera opened successfully")
        
        # Get properties
        props = {
            'Width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'Height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'FPS': int(cap.get(cv2.CAP_PROP_FPS)),
            'Backend': cap.getBackendName(),
            'Brightness': cap.get(cv2.CAP_PROP_BRIGHTNESS),
            'Contrast': cap.get(cv2.CAP_PROP_CONTRAST),
            'Saturation': cap.get(cv2.CAP_PROP_SATURATION),
        }
        
        print("\nCamera Properties:")
        for key, value in props.items():
            print(f"  {key:15}: {value}")
        
        # Test frame capture
        print("\nTesting frame capture...")
        ret, frame = cap.read()
        
        if ret:
            print(f"   Frame captured: {frame.shape}")
            print(f"   Shape: {frame.shape}")
            print(f"   Type: {frame.dtype}")
            print(f"   Size: {frame.nbytes / 1024:.2f} KB")
        else:
            print("Failed to capture frame")
        
        cap.release()
        return ret
    
    def show_summary(self):
        if not self.cameras:
            print("No cameras detected!")
            return
        
        print(f"Found {len(self.cameras)} camera(s):\n")
        
        for idx, info in sorted(self.cameras.items()):
            print(f"📹 Camera {idx} (/dev/video{idx}):")
            print(f"   Name       : {info['name']}")
            
            if 'idVendor' in info:
                print(f"   Vendor ID  : {info['idVendor']}")
            if 'idProduct' in info:
                print(f"   Product ID : {info['idProduct']}")
            if 'serial' in info:
                print(f"   Serial     : {info['serial']}")
            
            if 'resolution' in info:
                print(f"   Resolution : {info['resolution']}")
            if 'fps' in info:
                print(f"   FPS        : {info['fps']}")
            if 'backend' in info:
                print(f"   Backend    : {info['backend']}")
            
            print()
    
    def find_camera_by_hardware_id(self, vendor_id, product_id, serial=None):
        """Find camera index by hardware ID"""
        for idx, info in self.cameras.items():
            if 'idVendor' not in info or 'idProduct' not in info:
                continue
            
            if info['idVendor'] == vendor_id and info['idProduct'] == product_id:
                # If serial specified, check it too
                if serial:
                    if info.get('serial') == serial:
                        return idx
                else:
                    return idx
        
        return None
    
    def get_camera_by_name(self, name_pattern):
        """Find camera by name pattern"""
        name_lower = name_pattern.lower()
        
        for idx, info in self.cameras.items():
            if name_lower in info['name'].lower():
                return idx
        
        return None
    
    def export_to_file(self, filename="camera_list.txt"):
        """Export camera list to file"""
        with open(filename, 'w') as f:
            f.write("="*60 + "\n")
            f.write("DETECTED CAMERAS\n")
            f.write("="*60 + "\n\n")
            
            for idx, info in sorted(self.cameras.items()):
                f.write(f"Camera {idx}:\n")
                f.write(f"  Name: {info['name']}\n")
                f.write(f"  Index: {info['index']}\n")
                
                if 'resolution' in info:
                    f.write(f"  Resolution: {info['resolution']}\n")
                if 'fps' in info:
                    f.write(f"  FPS: {info['fps']}\n")
                
                f.write("\n")
        
        print(f"Camera list exported to: {filename}")

    def get_camera_list(self):
        cameras = {}

        video_devices = sorted(glob.glob("/dev/video*"))

        for dev in video_devices:
            try:
                cmd = ["v4l2-ctl", "-d", dev, "--info"]
                result = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
                )

                if result.returncode == 0:
                    name = None
                    for line in result.stdout.splitlines():
                        if "Card type" in line or "Driver name" in line:
                            name = line.split(":", 1)[1].strip()
                            break

                    if name is None:
                        name = dev

                    index = int(dev.replace("/dev/video", ""))
                    cameras[f"{name} ({dev})"] = index
            except Exception:
                continue

        return cameras


def main():
    detector = CameraDetector()
    while True:
        print("\n1. Test a specific camera")
        print("2. Re-scan cameras")
        print("3. Export to file")
        print("4. Show summary")
        # print("5. Find camera by Hardware ID")
        print("5. Show hardware IDs")
        print("6. Exit")
        print("="*60)
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == '1':
            try:
                idx = int(input("Enter camera index (0-9): "))
                detector.test_camera(idx)
            except ValueError:
                print("Invalid input!")
            break
        
        elif choice == '2':
            detector.cameras = {}
            detector.hardware_info = {}
            detector.detect_with_hardware_id() or detector.detect_with_v4l2() or detector.detect_manual()
            detector.show_summary()
            break
        
        elif choice == '3':
            filename = input("Enter filename (default: camera_list.txt): ").strip()
            if not filename:
                filename = "camera_list.txt"
            detector.export_to_file(filename)
            break
        
        elif choice == '4':
            detector.show_summary()
            break
        
        # elif choice == '5':
        #     vendor = input("Enter Vendor ID (e.g., 0c45): ").strip()
        #     product = input("Enter Product ID (e.g., 6366): ").strip()
        #     serial = input("Enter Serial (optional, press Enter to skip): ").strip()
            
        #     idx = detector.find_camera_by_hardware_id(
        #         vendor, product, serial if serial else None
        #     )
            
        #     if idx is not None:
        #         print(f"\nFound: Camera {idx} (/dev/video{idx})")
        #         print(f"   Name: {detector.cameras[idx]['name']}")
        #     else:
        #         print("\nCamera not found with those IDs")
        #     break

        elif choice == '5':
            if detector.hardware_info:
                print("\n" + "="*60)
                print("HARDWARE IDs")
                print("="*60)
                for idx, hw_info in detector.hardware_info.items():
                    print(f"\n/dev/video{idx}:")
                    for key, value in hw_info.items():
                        print(f"  {key:15}: {value}")
            else:
                print("\nNo hardware ID info available")
            break
        
        elif choice == '6':
            print("-----End Task-----")
            break
        
        else:
            print("!!!!!Invalid Input!!!!!")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
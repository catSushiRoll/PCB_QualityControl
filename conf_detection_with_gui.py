from ultralytics import YOLO
import cv2
from collections import defaultdict
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading

class PCBDetectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PCB Quality Control Detection")
        self.root.geometry("1280x800")
        
        # Load model
        self.model = YOLO("/home/syahla/PCB_QualityControl/KP_best5.pt")
        self.CONF_THRESHOLD = 0.5
        
        # Video capture
        self.cap = None
        self.is_running = False
        self.is_recording = False
        self.out = None
        self.filename = None

        self.current_area = None
        self.area_counts = {
            "Area 1": defaultdict(int),
            "Area 2": defaultdict(int),
            "Area 3": defaultdict(int),
            "Area 4": defaultdict(int),
        }
        
        # # Stats
        # self.max_count = defaultdict(int)
        
        # Setup GUI
        self.setup_gui()
        
    def setup_gui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Camera selection frame
        camera_frame = ttk.LabelFrame(main_frame, text="Camera Selection", padding="5")
        camera_frame.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Label(camera_frame, text="Camera Index:").pack(side=tk.LEFT, padx=5)
        
        self.camera_var = tk.StringVar(value="2")
        self.camera_dropdown = ttk.Combobox(camera_frame, textvariable=self.camera_var, 
                                        values=["0", "1", "2", "3", "4"], 
                                        width=10, state="readonly")
        self.camera_dropdown.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(camera_frame, text="(0=Integrated, 2=Taffware)").pack(side=tk.LEFT, padx=5)
        
        # Video display
        self.video_label = ttk.Label(main_frame, text="Video Feed", relief=tk.SUNKEN)
        self.video_label.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.button_start = ttk.Button(button_frame, text="Start Camera", command=self.start_camera)
        self.button_start.pack(side=tk.LEFT, padx=5)
        
        self.button_stop = ttk.Button(button_frame, text="Stop Camera", command=self.stop_camera, state=tk.DISABLED)
        self.button_stop.pack(side=tk.LEFT, padx=5)
        
        self.button_record = ttk.Button(button_frame, text="Start Recording", command=self.toggle_recording, state=tk.DISABLED)
        self.button_record.pack(side=tk.LEFT, padx=5)
        
        self.button_capture = ttk.Button(button_frame, text="Capture Frame", command=self.capture_frame, state=tk.DISABLED)
        self.button_capture.pack(side=tk.LEFT, padx=5)
        
        # Stats panel
        stats_frame = ttk.LabelFrame(main_frame, text="Detection Statistics", padding="10")
        stats_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        self.stats_text = tk.Text(stats_frame, height=10, width=80)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar + quit button 
        self.status_label = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN)
        self.status_label.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E))

        self.button_quit = ttk.Button(main_frame, text="Quit", command=self.on_closing)
        self.button_quit.grid(row=4, column=1, columnspan=3, sticky=(tk.W, tk.E))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
    def start_camera(self):
        # Get selected camera index
        camera_index = int(self.camera_var.get())
        
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(camera_index, cv2.CAP_ANY)
            
            if not self.cap.isOpened():
                self.status_label.config(text=f"Error: Cannot open camera {camera_index}!")
                return
        
        self.is_running = True
        self.button_start.config(state=tk.DISABLED)
        self.button_stop.config(state=tk.NORMAL)
        self.button_record.config(state=tk.NORMAL)
        self.button_capture.config(state=tk.NORMAL)
        self.camera_dropdown.config(state=tk.DISABLED)  # Disable dropdown during running
        self.status_label.config(text=f"Camera {camera_index} started")
        
        # Start video thread
        self.video_thread = threading.Thread(target=self.update_frame, daemon=True)
        self.video_thread.start()
    
    def stop_camera(self):
        self.is_running = False
        
        if self.is_recording:
            self.stop_recording()
        
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.button_start.config(state=tk.NORMAL)
        self.button_stop.config(state=tk.DISABLED)
        self.button_record.config(state=tk.DISABLED)
        self.button_capture.config(state=tk.DISABLED)
        self.camera_dropdown.config(state="readonly")  # Enable dropdown lagi
        self.status_label.config(text="Camera stopped")
    
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        if self.cap is None or not self.cap.isOpened():
            return
        
        ret, test_frame = self.cap.read()
        if not ret:
            self.status_label.config(text="Cannot read frame for recording")
            return
        
        height, width = test_frame.shape[:2]
        
        codec_options = [
            ('XVID', '.avi'),
            ('MJPG', '.avi'),
            ('mp4v', '.mp4'),
        ]
        
        for codec, ext in codec_options:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            self.filename = f'output_{datetime.now().strftime("%Y%m%d_%H%M%S")}{ext}'
            self.out = cv2.VideoWriter(self.filename, fourcc, 20.0, (width, height))
            
            if self.out.isOpened():
                self.is_recording = True
                self.button_record.config(text="Stop Recording")
                self.status_label.config(text=f"Recording: {self.filename}")
                break
        else:
            self.status_label.config(text="All codecs failed!")
    
    def stop_recording(self):
        if self.out is not None:
            self.out.release()
            self.out = None
        
        self.is_recording = False
        self.button_record.config(text="Start Recording")
        self.status_label.config(text=f"Recording saved: {self.filename}")
    
    def capture_frame(self):
        if hasattr(self, 'current_frame') and self.current_frame is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.png"
            cv2.imwrite(filename, self.current_frame)
            self.status_label.config(text=f"Captured: {filename}")
    
    def update_frame(self):
        import time
        
        while self.is_running:
            start_time = time.time()
            
            if self.cap is None or not self.cap.isOpened():
                break
            
            ret, frame = self.cap.read()
            if not ret:
                self.root.after(0, lambda: self.status_label.config(text="Cannot read frame"))
                break
            
            # Run detection
            results = self.model(frame, conf=self.CONF_THRESHOLD, verbose=False)
            result = results[0]
            
            # Get best boxes per class
            best_boxes = {}
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                if cls_id not in best_boxes or conf >= best_boxes[cls_id]['conf']:
                    best_boxes[cls_id] = {'conf': conf, 'box': box}
            
            # Annotate frame
            frame_count = defaultdict(int)
            annotated = frame.copy()
            
            for cls_id, data in best_boxes.items():
                frame_count[cls_id] = 1
                box = data['box']
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = data['conf']
                label = f"{self.model.names[cls_id]}: {conf:.2f}"
                if label.startswith("No capacitor") or label.startswith("wrong component") or label.startswith("No jackcable"):
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(annotated, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                elif label.startswith("No resitor"): #typo pas anotasi hehehe
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(annotated, f"No resistor:{conf:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                elif label.startswith("Missalignment"):
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(annotated, f"Misalignment:{conf:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                else:
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(annotated, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Update max count
            for cls_id, cnt in frame_count.items():
                self.max_count[cls_id] = max(self.max_count[cls_id], cnt)
            
            # Save current frame
            self.current_frame = annotated.copy()
            
            # Record if enabled
            if self.is_recording and self.out is not None:
                self.out.write(annotated)
            
            # Convert to RGB for Tkinter
            frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            
            # Resize to fit display
            display_width = 1200
            height, width = frame_rgb.shape[:2]
            aspect_ratio = width / height
            display_height = int(display_width / aspect_ratio)
            frame_resized = cv2.resize(frame_rgb, (display_width, display_height))
            
            # Convert to ImageTk
            img = Image.fromarray(frame_resized)
            imgtk = ImageTk.PhotoImage(image=img)
            
            # ✅ FIX: Update GUI menggunakan after() untuk thread safety
            self.root.after(0, self.update_gui, imgtk)
            
            # ✅ FIX: Frame rate control (target ~30 FPS)
            elapsed = time.time() - start_time
            target_fps = 30
            delay = max(0, (1.0 / target_fps) - elapsed)
            if delay > 0:
                time.sleep(delay)
    
    def update_gui(self, imgtk):
        """Update GUI elements (harus dipanggil dari main thread)"""
        if self.is_running:
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            self.update_stats()
    
    def update_stats(self):
        stats_str = "=== Detection Statistics ===\n\n"
        
        if self.max_count:
            for cls_id, cnt in self.max_count.items():
                class_name = self.model.names[cls_id]
                stats_str += f"{class_name}: {cnt}\n"
        else:
            stats_str += "No detections yet\n"
        
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats_str)
    
    def on_closing(self):
        self.stop_camera()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = PCBDetectionApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
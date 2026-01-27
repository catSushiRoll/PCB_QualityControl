from unittest import result
from ultralytics import YOLO
import cv2
from collections import defaultdict
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import platform
import time

from cam_detection import CameraDetector
from filtering_area import filter_detections, get_area_component_list
from ocr_resistor import resistor_OCR

class PCBDetectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PCB Quality Control Detection")

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = int(screen_width *0.7)
        window_height = int(screen_height *0.7)
        position_x = int((screen_width - window_width)/2)
        position_y = int((screen_height - window_height)/2)

        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

        self.model = YOLO("c:/Users/syahla/Downloads/2_runs_merging_yolov8_100/content/runs/detect/train/weights/best.pt")
        self.CONF_THRESHOLD = 0.64

        self.cap = None
        self.is_running = False
        self.is_recording = False
        self.out = None
        self.filename = None
        self.system = platform.system()

        # Initialize OCR
        self.resistor_ocr = resistor_OCR()
        self.ocr_results = {}

        self.current_area = None
        self.current_area_mode = False  # TAMBAH ini
        self.last_validation = None 
        self.area_data = {
            "Area 1": {"components": defaultdict(int), "captured": False, "timestamp": None},
            "Area 2": {"components": defaultdict(int), "captured": False, "timestamp": None},
            "Area 3": {"components": defaultdict(int), "captured": False, "timestamp": None},
            "Area 4": {"components": defaultdict(int), "captured": False, "timestamp": None},
            "Area 5": {"components": defaultdict(int), "captured": False, "timestamp": None},
            "Area 6": {"components": defaultdict(int), "captured": False, "timestamp": None},
            "Area 7": {"components": defaultdict(int), "captured": False, "timestamp": None},
        }
        
        self.max_count = defaultdict(int)  # For current frame
        self.camera_devices = {}
        self.init_camera()
        self.setup_gui()
    
    def init_camera(self):
        try:
            detector = CameraDetector()
            self.camera_list = detector.get_camera_list()
            print(f"Detected cameras: {self.camera_list}")
            
            if not self.camera_list:
                print("WARNING: No cameras detected!")
                self.camera_list = {
                    "Camera 0 (Manual)": 0,
                    "Camera 1 (Manual)": 1,
                }
        except Exception as e:
            print(f"Error in camera detection: {e}")
            self.camera_list = {
                "Camera 0 (Manual)": 0,
                "Camera 1 (Manual)": 1,
            }
        
    def setup_gui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Camera selection frame
        camera_frame = ttk.LabelFrame(main_frame, text="Camera Selection", padding="5")
        camera_frame.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Label(camera_frame, text="Camera Index:").pack(side=tk.LEFT, padx=5)
        
        camera_names = list(self.camera_list.keys())
        default_camera = camera_names[0] if camera_names else "No cameras found"
        self.camera_var = tk.StringVar(value=default_camera)
        self.camera_dropdown = ttk.Combobox(
            camera_frame,
            textvariable=self.camera_var,
            values=camera_names,
            width=30,
            state="readonly"
        )
        self.camera_dropdown.pack(side=tk.LEFT, padx=5)
        
        self.button_refresh = ttk.Button(camera_frame, text="Refresh Cameras", command=self.refresh_cameras)
        self.button_refresh.pack(side=tk.LEFT, padx=5)
        
        # Video display
        self.video_label = ttk.Label(main_frame, text="Video Feed", relief=tk.SUNKEN)
        self.video_label.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right panel - Area Selection
        right_panel = ttk.Frame(main_frame, width=250)
        right_panel.grid(row=1, column=3, padx=10, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        area_frame = ttk.LabelFrame(right_panel, text="Area Selection & Capture", padding=10)
        area_frame.pack(fill=tk.BOTH, expand=True)
        
        # Info label
        info_label = ttk.Label(area_frame, text="Click area button to capture\ncomponents in that area:", 
                            foreground="blue", font=("Arial", 9, "italic"))
        info_label.pack(pady=(0, 10))
        
        self.area_buttons = {}
        self.area_status_labels = {}
        
        for area in ["Area 1", "Area 2", "Area 3", "Area 4", "Area 5", "Area 6", "Area 7"]:
            # Frame untuk setiap area
            area_container = ttk.Frame(area_frame)
            area_container.pack(fill=tk.X, pady=5)
            
            # Button area
            button = ttk.Button(area_container, text=area, 
                            command=lambda a=area: self.select_area(a),
                            width=15)
            button.pack(side=tk.LEFT, padx=(0, 5))
            self.area_buttons[area] = button
            
            # Status label
            status = ttk.Label(area_container, text="⭕ Not captured", 
                            foreground="gray", font=("Arial", 8))
            status.pack(side=tk.LEFT)
            self.area_status_labels[area] = status
        
        expected_frame = ttk.LabelFrame(area_frame, text="Expected Components", padding=5)
        expected_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.expected_text = tk.Text(expected_frame, height=6, width=25, wrap=tk.WORD, font=("Arial", 9))
        self.expected_text.pack(fill=tk.BOTH, expand=True)
        self.expected_text.insert(1.0, "Select an area to see\nexpected components")
        self.expected_text.config(state=tk.DISABLED)

        # Capture button untuk area yang dipilih
        self.button_capture_area = ttk.Button(area_frame, text="📸 Capture Current Area", 
                                        command=self.capture_area_data,
                                        state=tk.DISABLED)
        self.button_capture_area.pack(fill=tk.X, pady=5)

        # Separator
        ttk.Separator(area_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Summary button
        self.button_summary = ttk.Button(area_frame, text="📊 Show Full Summary", 
                                        command=self.show_full_summary,
                                        state=tk.NORMAL)
        self.button_summary.pack(fill=tk.X, pady=5)
        
        # Reset button
        self.button_reset = ttk.Button(area_frame, text="🔄 Reset All Areas", 
                                    command=self.reset_all_areas)
        self.button_reset.pack(fill=tk.X, pady=5)
        
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
        
        # Stats panel - Split into two columns
        stats_container = ttk.Frame(main_frame)
        stats_container.grid(row=3, column=0, columnspan=4, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Left: Current Detection
        current_stats_frame = ttk.LabelFrame(stats_container, text="Current Frame Detection", padding="10")
        current_stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.stats_text = tk.Text(current_stats_frame, height=8, width=50)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Right: Area Summary
        area_stats_frame = ttk.LabelFrame(stats_container, text="Captured Areas Summary", padding="10")
        area_stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.area_stats_text = tk.Text(area_stats_frame, height=8, width=50)
        self.area_stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        status_container = ttk.Frame(main_frame)
        status_container.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E))
        
        self.status_label = ttk.Label(status_container, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.button_quit = ttk.Button(status_container, text="Quit", command=self.on_closing)
        self.button_quit.pack(side=tk.RIGHT)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(3, weight=0)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=0)
    
    def refresh_cameras(self):
        """Refresh daftar kamera yang tersedia"""
        self.status_label.config(text="Refreshing cameras...")
        self.init_camera()
        camera_names = list(self.camera_list.keys())
        self.camera_dropdown['values'] = camera_names
        if camera_names:
            self.camera_var.set(camera_names[0])
            self.status_label.config(text=f"Found {len(camera_names)} camera(s)")
        else:
            self.status_label.config(text="No cameras found")
    
    def select_area(self,area_name):
        if not self.is_running:
            messagebox.showwarning("Warning", "Please start the camera first!")
            return

        self.current_area = area_name
        self.current_area_mode = True

        # Update button states - highlight yang dipilih
        for area, button in self.area_buttons.items():
            if area == area_name:
                button.state(['pressed'])
            else:
                button.state(['!pressed'])

        self.button_capture_area.config(state=tk.NORMAL)

        expected_list = get_area_component_list(area_name)
        resistor_summary = self.resistor_ocr.get_area_resistor_summary(area_name)
        if resistor_summary != "No resistor data for this area":
            expected_list += "\n\n" + resistor_summary

        self.expected_text.config(state=tk.NORMAL)
        self.expected_text.delete(1.0, tk.END)
        self.expected_text.insert(1.0, f"Expected in {area_name}:\n\n{expected_list}")
        self.expected_text.config(state=tk.DISABLED)
        self.status_label.config(text=f"🎯 Inspecting {area_name} - Point camera then click Capture")
    
    def capture_area_data(self):  # HAPUS parameter area_name
        """Capture dan validasi data komponen untuk area yang sedang dipilih"""
        if not self.current_area:
            messagebox.showwarning("Warning", "Please select an area first!")
            return

        if not self.is_running:
            messagebox.showwarning("Warning", "Please start the camera first!")
            return

        if not self.max_count:
            messagebox.showwarning("Warning", "No components detected in current frame!")
            return

        area_name = self.current_area

        # Simpan data deteksi saat ini ke area
        self.area_data[area_name]["components"] = dict(self.max_count.copy())
        self.area_data[area_name]["captured"] = True
        self.area_data[area_name]["timestamp"] = datetime.now().strftime("%H:%M:%S")

        # TAMBAH: Simpan hasil validasi jika ada
        if self.last_validation:
            self.area_data[area_name]["validation"] = self.last_validation

        # TAMBAH: Update status berdasarkan validasi
        if self.last_validation:
            status = self.last_validation.get("status", "ok")
            if status == "ok":
                status_text = "✅ OK"
                status_color = "green"
            elif status == "warning":
                status_text = "⚠️ Warning"
                status_color = "orange"
            else:
                status_text = "❌ Error"
                status_color = "red"

            self.area_status_labels[area_name].config(
                text=f"{status_text}", 
                foreground=status_color
            )
        else:
            self.area_status_labels[area_name].config(
                text="✅ Captured", 
                foreground="green"
            )

        # Update area summary
        self.update_area_summary()

        # Check if all areas captured
        # all_captured = all(data["captured"] for data in self.area_data.values())
        # if all_captured:
        #     self.button_summary.config(state=tk.NORMAL)
        #     self.status_label.config(text=f"✅ {area_name} captured! All areas completed")
        # else:
        #     self.status_label.config(text=f"✅ {area_name} captured at {self.area_data[area_name]['timestamp']}")
    
    # def highlight_button(self, area_name):
    #     """Highlight button yang baru di-capture"""
    #     # Reset semua button
    #     for area, button in self.area_buttons.items():
    #         button.state(['!pressed'])
        
    #     # Highlight button yang aktif sementara
    #     self.area_buttons[area_name].state(['pressed'])
        
    #     # Reset setelah 1 detik
    #     self.root.after(1000, lambda: self.area_buttons[area_name].state(['!pressed']))
    
    def reset_all_areas(self):
        """Reset semua data area"""
        confirm = messagebox.askyesno("Confirm Reset", 
                                    "Are you sure you want to reset all captured area data?")
        if not confirm:
            return
        
        # TAMBAH baris-baris ini di bagian reset:
        for area in self.area_data.keys():
            self.area_data[area] = {"components": defaultdict(int), "captured": False, "timestamp": None, "validation": None}  # TAMBAH "validation": None
            self.area_status_labels[area].config(text="⭕ Not inspected", foreground="gray")  # GANTI dari "Not captured"
            self.area_buttons[area].state(['!pressed'])  # TAMBAH ini

        self.current_area = None
        self.current_area_mode = False  # TAMBAH ini
        self.last_validation = None     # TAMBAH ini
        self.button_summary.config(state=tk.DISABLED)
        self.button_capture_area.config(state=tk.DISABLED)  # TAMBAH ini

        # TAMBAH ini untuk reset expected text:
        self.expected_text.config(state=tk.NORMAL)
        self.expected_text.delete(1.0, tk.END)
        self.expected_text.insert(1.0, "Select an area to see\nexpected components")
        self.expected_text.config(state=tk.DISABLED)
    
    def show_full_summary(self):
        summary_window = tk.Toplevel(self.root)
        summary_window.title("PCB Quality Control - Full Summary Report")
        summary_window.geometry("700x600")
        
        # Header
        header_frame = ttk.Frame(summary_window, padding="10")
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(header_frame, text="📊 Complete PCB Inspection Report", 
                            font=("Arial", 14, "bold"))
        title_label.pack()
        
        time_label = ttk.Label(header_frame, text=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                            font=("Arial", 9))
        time_label.pack()
        
        # Summary text
        text_frame = ttk.Frame(summary_window, padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        summary_text = tk.Text(text_frame, height=25, width=80, yscrollcommand=scrollbar.set)
        summary_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=summary_text.yview)
        
        # Generate report
        report = self.generate_full_report()
        summary_text.insert(1.0, report)
        summary_text.config(state=tk.DISABLED)
        
        # Export button
        button_frame = ttk.Frame(summary_window, padding="10")
        button_frame.pack(fill=tk.X)
        
        export_btn = ttk.Button(button_frame, text="💾 Export to File", 
                                command=lambda: self.export_report(report))
        export_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = ttk.Button(button_frame, text="Close", command=summary_window.destroy)
        close_btn.pack(side=tk.RIGHT, padx=5)
    
    def generate_full_report(self):
        report = "=" * 70 + "\n"
        report += "PCB QUALITY CONTROL - INSPECTION REPORT\n"
        report += "=" * 70 + "\n\n"
        
        # Summary by area
        for area in ["Area 1", "Area 2", "Area 3", "Area 4", "Area 5", "Area 6", "Area 7"]:
            data = self.area_data[area]
            report += f"\n{'=' * 70}\n"
            report += f"{area.upper()}\n"
            report += f"{'=' * 70}\n"
            
            if data["captured"]:
                report += f"Captured at: {data['timestamp']}\n"
                report += f"Status: ✅ INSPECTED\n\n"
                
                if data["components"]:
                    report += "Components Detected:\n"
                    report += "-" * 70 + "\n"
                    
                    # Pisahkan OK dan Defect
                    ok_components = {}
                    incomplete_components = {}
                    
                    for cls_id, count in data["components"].items():
                        class_name = self.model.names[cls_id]
                        if any(incomplete in class_name for incomplete in ["No "]):
                            incomplete_components[class_name] = count
                        else:
                            ok_components[class_name] = count
                    
                    # Display OK components
                    if ok_components:
                        report += "\n✅ OK Components:\n"
                        for name, count in ok_components.items():
                            report += f"  • {name}: {count}\n"
                    
                    # Display Defects
                    if incomplete_components:
                        report += "\n❌ INCOMPLETE COMPONENTS FOUND:\n"
                        for name, count in incomplete_components.items():
                            report += f"  • {name}: {count}\n"
                    
                    # Summary
                    total = sum(data["components"].values())
                    defect_total = sum(incomplete_components.values())
                    report += f"\n{'─' * 70}\n"
                    report += f"Total Components: {total}\n"
                    # report += f"Defects: {defect_total}\n"
                    # report += f"Quality Rate: {((total - defect_total) / total * 100):.1f}%\n" if total > 0 else "Quality Rate: N/A\n"
                else:
                    report += "No components detected\n"
            else:
                report += "Status: ⭕ NOT INSPECTED\n"
        
        # Overall summary
        report += f"\n\n{'=' * 70}\n"
        report += "OVERALL SUMMARY\n"
        report += f"{'=' * 70}\n"
        
        total_areas_inspected = sum(1 for data in self.area_data.values() if data["captured"])
        report += f"Areas Inspected: {total_areas_inspected}/7\n"
        
        # Aggregate all components
        all_components = defaultdict(int)
        for data in self.area_data.values():
            if data["captured"]:
                for cls_id, count in data["components"].items():
                    all_components[cls_id] += count
        
        if all_components:
            total_all = sum(all_components.values())
            defects_all = sum(count for cls_id, count in all_components.items() 
                            if any(defect in self.model.names[cls_id] for defect in ["No ", "wrong", "Missalignment"]))
            
            report += f"Total Components Detected: {total_all}\n"
            report += f"Total Defects: {defects_all}\n"
            report += f"Overall Quality Rate: {((total_all - defects_all) / total_all * 100):.1f}%\n" if total_all > 0 else "Overall Quality Rate: N/A\n"
        
        report += "\n" + "=" * 70 + "\n"
        report += f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += "=" * 70 + "\n"
        
        return report
    
    def export_report(self, report):
        """Export report ke file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"PCB_Inspection_Report_{timestamp}.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write(report)
            messagebox.showinfo("Export Success", f"Report saved to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save report:\n{str(e)}")
    
    def update_area_summary(self):
        """Update tampilan summary area yang sudah di-capture"""
        summary = ""
        
        captured_count = sum(1 for data in self.area_data.values() if data["captured"])
        summary += f"Areas Captured: {captured_count}/4\n"
        summary += "=" * 50 + "\n\n"
        
        for area in ["Area 1", "Area 2", "Area 3", "Area 4", "Area 5", "Area 6", "Area 7"]:
            data = self.area_data[area]
            
            if data["captured"]:
                summary += f"✅ {area} (at {data['timestamp']})\n"
                
                if data["components"]:
                    defects = sum(count for cls_id, count in data["components"].items() 
                                if any(d in self.model.names[cls_id] for d in ["No ", "wrong", "Missalignment"]))
                    total = sum(data["components"].values())
                    
                    summary += f"   Components: {total} | Defects: {defects}\n"
                    sorted_components = sorted(data["components"].items(), key=lambda x: x[1], reverse=True)[:3]
                    for cls_id, count in sorted_components:
                        summary += f"   • {self.model.names[cls_id]}: {count}\n"
                else:
                    summary += "   No components detected\n"
                summary += "\n"
            else:
                summary += f"⭕ {area} - Not captured yet\n\n"
        
        self.area_stats_text.delete(1.0, tk.END)
        self.area_stats_text.insert(1.0, summary)
    
    def start_camera(self):
        camera_name = self.camera_var.get()
        camera_index = self.camera_list.get(camera_name)

        if camera_index is None:
            self.status_label.config(text="Invalid camera selection")
            return
        
        if self.system == "Windows":
            self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(camera_index)
        
        if not self.cap.isOpened():
            self.status_label.config(text=f"Cannot open camera {camera_index}")
            self.cap = cv2.VideoCapture(camera_index)
            if not self.cap.isOpened():
                self.status_label.config(text=f"Failed to open camera {camera_index} with all methods")
                return

        self.is_running = True
        self.button_start.config(state=tk.DISABLED)
        self.button_stop.config(state=tk.NORMAL)
        self.button_record.config(state=tk.NORMAL)
        self.button_capture.config(state=tk.NORMAL)
        self.camera_dropdown.config(state=tk.DISABLED)
        self.button_refresh.config(state=tk.DISABLED)
        self.status_label.config(text=f"Camera {camera_index} started - Click area buttons to capture data")
        
        self.video_thread = threading.Thread(target=self.main_detection, daemon=True)
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
        self.camera_dropdown.config(state="readonly")
        self.button_refresh.config(state=tk.NORMAL)
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
        
        if self.system == "Windows":
            codec_options = [
                ('MJPG', '.avi'),
                ('XVID', '.avi'),
                ('mp4v', '.mp4'),
            ]
        else:
            codec_options = [
                ('XVID', '.avi'),
                ('MJPG', '.avi'),
                ('mp4v', '.mp4'),
            ]
        
        for codec, ext in codec_options:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                self.filename = f'output_{datetime.now().strftime("%Y%m%d_%H%M%S")}{ext}'
                self.out = cv2.VideoWriter(self.filename, fourcc, 20.0, (width, height))
                
                if self.out.isOpened():
                    self.is_recording = True
                    self.button_record.config(text="Stop Recording")
                    self.status_label.config(text=f"Recording: {self.filename} (codec: {codec})")
                    print(f"Recording started with codec: {codec}")
                    break
            except Exception as e:
                print(f"Failed to initialize codec {codec}: {e}")
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
    
    def main_detection(self):
        while self.is_running:
            start_time = time.time()
            
            if self.cap is None or not self.cap.isOpened():
                break
            
            ret, frame = self.cap.read()
            if not ret:
                self.root.after(0, lambda: self.status_label.config(text="Cannot read frame"))
                break

            results = self.model(frame, conf=self.CONF_THRESHOLD, verbose=False)
            result = results[0]
            
            if self.current_area_mode and self.current_area:
                filtered_boxes, validation = filter_detections(self.current_area, result.boxes, self.model)
                self.last_validation = validation  # Simpan untuk capture nanti
                boxes_to_process = filtered_boxes
            else:
                boxes_to_process = result.boxes
                self.last_validation = None
            
            best_boxes = {}
            for box in boxes_to_process:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                if cls_id not in best_boxes or conf >= best_boxes[cls_id]['conf']:
                    best_boxes[cls_id] = {'conf': conf, 'box': box}
            
            # Reset max_count untuk frame saat ini
            self.max_count = defaultdict(int)
            annotated = frame.copy()
            
            for cls_id, data in best_boxes.items():
                self.max_count[cls_id] = 1
                box = data['box']
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = data['conf']
                class_name = self.model.names[cls_id]
                label = f"{class_name}:{conf:.2f}"
                color = (0, 255, 0) 
                
                # if label.startswith("No capacitor") or label.startswith("wrong component") or label.startswith("No jackcable"):
                #     cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                #     cv2.putText(annotated, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                # elif label.startswith("No resitor"):
                #     cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                #     cv2.putText(annotated, f"No resistor: {conf:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                # elif label.startswith("Missalignment"):
                #     cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                #     cv2.putText(annotated, f"Misalignment: {conf:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                # else:
                #     cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                #     cv2.putText(annotated, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # OCR buat resistor
                if "Resistor" in class_name and "No resistor" not in class_name:
                    bbox = [x1, y1, x2, y2]
                    marking, ocr_conf = self.resistor_ocr.read_classify_resistor(bbox,frame)
                    if marking and self.current_area:
                        validation = self.resistor_ocr.validate_resistor(self.current_area, marking)
                        self.ocr_results[cls_id]={
                            "marking":marking,
                            "validation":validation,
                            "confidence":ocr_conf
                        }
                        decoded = validation.get("decoded")
                        if decoded:
                            label = f"{label}: marking ({decoded['value_str']}){conf:.2f}"
                        else:
                            label = f"{label}:{conf:.2f}"
                        
                        if validation["status"]=="ok":
                            color = (0,255,0)
                        elif validation["status"]=="unknown":
                            color = (0, 165, 255)
                        else: color= (0,0,255)
                        # cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                        # cv2.putText(annotated, label, (x1, y1 -10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                # elif "No resistor" in class_name:
                    # color = (0,0,255)

                
                if any(incomplete in label for incomplete in ["No "]):
                    # cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    # cv2.putText(annotated, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    color = (0,0,255)
                else: 
                    color = (0,255,0)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                cv2.putText(annotated, label, (x1, y1 -10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            # else:
            #         cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            #         cv2.putText(annotated, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            self.current_frame = annotated.copy()
            
            if self.is_recording and self.out is not None:
                self.out.write(annotated)

            frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            label_w = self.video_label.winfo_width()
            label_h = self.video_label.winfo_height()

            if label_w > 1 and label_h > 1:
                h, w = frame_rgb.shape[:2]
                scale = min(label_w / w, label_h / h)

                new_w = int(w * scale)
                new_h = int(h * scale)

                frame_resized = cv2.resize(frame_rgb, (new_w, new_h))
            else:
                frame_resized = frame_rgb
            
            img = Image.fromarray(frame_resized)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.root.after(0, self.update_gui, imgtk)
            
            elapsed = time.time() - start_time
            target_fps = 30
            delay = max(0, (1.0 / target_fps) - elapsed)
            if delay > 0:
                time.sleep(delay)
    
    def update_gui(self, imgtk):
        if self.is_running:
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            self.update_stats()
    
    def update_stats(self):
        stats_str = "=== Current Frame Detection ===\n"

        if self.current_area_mode and self.current_area:
            stats_str += f"🎯 Inspecting: {self.current_area}\n"
            stats_str += f"{'─' * 35}\n\n"

            # ocr result
            if self.ocr_results:
                stats_str += "Resistor results:\n"
                for cls_id, ocr_data in self.ocr.results.items():
                    val = ocr_data["validation"]
                    stats_str +=f"{val['message']}\n"
                    stats_str += f"  Confidence: {ocr_data['confidence']:.2f}\n"
                    if val.get("designator"):
                        stats_str += f"  Position: {val['designator']}\n"
                    stats_str += "\n"
            # Tampilkan hasil validasi jika ada
            if self.last_validation:
                val = self.last_validation
                stats_str += f"{val['message']}\n\n"

                if val.get('missing'):
                    stats_str += "⚠️ Missing Components:\n"
                    for item in val['missing']:
                        stats_str += f"  • {item['component']}: need {item['expected']}, found {item['actual']}\n"
                    stats_str += "\n"
                    
                if val.get('excess'):
                    stats_str += "⚠️ Excess Components:\n"
                    for item in val['excess']:
                        stats_str += f"  • {item['component']}: need {item['expected']}, found {item['actual']}\n"
                    stats_str += "\n"

                if val.get('defects'):
                    stats_str += "❌ Defects Detected:\n"
                    for defect in val['defects']:
                        stats_str += f"  • {defect['class_name']}\n"
                    stats_str += "\n"

                stats_str += "\n💡 Click 'Capture Current Area' to save"

        elif self.max_count:
            full_components = {}
            incomplete_area = {}

            for cls_id, cnt in self.max_count.items():
                class_name = self.model.names[cls_id]
                if any(incomplete in class_name for incomplete in ["No "]):
                    incomplete_area[class_name] = cnt
                else:
                    full_components[class_name] = cnt

            if full_components:
                stats_str += "✅ OK Components:\n"
                for name, cnt in full_components.items():
                    stats_str += f"  • {name}: {cnt}\n"
                stats_str += "\n"

            if incomplete_area:
                stats_str += "❌ Incomplete components:\n"
                for name, cnt in incomplete_area.items():
                    stats_str += f"  • {name}: {cnt}\n"
                stats_str += "\n"

            total = sum(self.max_count.values())
            defects = sum(incomplete_area.values())
            stats_str += f"{'─' * 35}\n"
            stats_str += f"Total: {total} | Defects: {defects}\n"
            stats_str += "\n💡 Select an area to start inspection"
        else:
            stats_str += "No detections in current frame\n"
            if self.current_area_mode:
                stats_str += "\n💡 Point camera at PCB area"
            else:
                stats_str += "\n💡 Select an area to start inspection"

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
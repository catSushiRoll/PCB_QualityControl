from ultralytics import YOLO
import cv2
from collections import defaultdict
import os
from datetime import datetime

# Load model
model = YOLO("KP_best2.pt")

cap = cv2.VideoCapture(0)
path = "/home/syahla/kp/0706dfa3-62ca-4803-94ee-b51bfec14bc6.jpeg"

# Simpan count maksimum per class
max_count = defaultdict(int)

CONF_THRESHOLD = 0.59

def mode_video(record=False):
    out = None
    filename = None
    
    if record:
        print("xxxxxx RECORD NIH!!! xxxxx")
        ret, test_frame = cap.read()
        if not ret:
            return
        
        height, width = test_frame.shape[:2]
        
        codec_options = [
            ('XVID', '.avi'),
            ('MJPG', '.avi'),
            ('mp4v', '.mp4'),
        ]
        
        for codec, ext in codec_options:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            filename = f'output_{datetime.now().strftime("%Y%m%d_%H%M%S")}{ext}'
            out = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))
            
            if out.isOpened():
                print(f"Using codec: {codec} → {filename}")
                break
        else:
            print("Semua codec gagal!")
            cap.release()
            return
    try:    
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            results = model(frame, conf=CONF_THRESHOLD, verbose=False)
            result = results[0]
            # Count per frame
            best_boxes = {}
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                if cls_id not in best_boxes or conf >= best_boxes[cls_id]['conf']:
                    best_boxes[cls_id] = {'conf': conf, 'box': box}
            frame_count = defaultdict(int)
            annotated=frame.copy()
            for cls_id, data in best_boxes.items():
                frame_count[cls_id] = 1
                box = data['box']
                x1,y1, x2, y2 = map(int, box.xyxy[0])
                conf = data['conf']
                label = f"{model.names[cls_id]}: {conf:.2f}"
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(annotated, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0,255), 2)
            for cls_id, cnt in frame_count.items():
                max_count[cls_id] = max(max_count[cls_id], cnt)
    
            if out is not None:
                out.write(annotated)
            cv2.imshow("Component counter", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        if out is not None:
            out.release()
        cv2.destroyAllWindows()
        print(f"Video record as : {filename}")

def mode_img():
    # path = "/home/syahla/kp/stitching result/stitched_panorama2026-01-07_09-39-01.jpg"
    results = model(path, conf=CONF_THRESHOLD, verbose=False)
    annotated_images = results[0].plot()
    best_boxes = {}
    # for box in results[0].boxes:
    #     cls_id = int(box.cls[0])
    #     conf = float(box.conf[0])
    #     if cls_id not in best_boxes or conf > best_boxes[cls_id]['conf']:
    #         best_boxes[cls_id] = {'conf': conf, 'box': box}

    for r in results:
        img = r.orig_img
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            if cls_id not in best_boxes or conf >= best_boxes[cls_id]['conf']:
                best_boxes[cls_id] = {'conf': conf, 'box': box}


    frame_count = defaultdict(int)
    # annotated=annotated_images.copy()

    for cls_id, data in best_boxes.items():
        b = data['box'].xyxy[0].cpu().numpy().astype(int)
        frame_count[cls_id] = 1
        box = data['box']
        # x1,y1, x2, y2 = map(int, box.xyxy[0])
        conf = data['conf']
        label = f"{model.names[cls_id]}: {conf:.2f}"
        # cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.rectangle(img, (b[0], b[1]), (b[2], b[3]), (0, 255, 0), 2)
        cv2.putText(img, label, (b[0], b[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    for cls_id, cnt in frame_count.items():
        max_count[cls_id] = max(max_count[cls_id], cnt)
    cv2.imshow("Component counter", cv2.resize(img, (1024, 768)))
    cv2.waitKey(0)

if __name__ == "__main__":
    choice = input("PILIH FORMAT FILE: \n1. VIDEO\n2. IMAGE\n")
    if choice == "1":
        record = input("Record ga? [y/N]")
        if record.lower() == "y":
            is_record = True
            print("xxxxxx RECORD NIH!!! xxxxx")
        else: 
            is_record = False
            print("xxxxxx GA RECORD YAAA xxxxxx")
        mode_video(record=is_record)
    elif choice == "2":
        mode_img()
    else: 
        print("invalid input")
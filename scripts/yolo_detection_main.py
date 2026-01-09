import ultralytics
from ultralytics import YOLO
import numpy as np
import cv2
# import supervision
import supervision as sv

model = YOLO("KP_best2.pt")
# results=model(source="/home/syahla/kp/2026-01-06_152717/captured_frame10.png", save=False)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(source=frame, save=False)
    result = results[0]
    annotated_frame = result.plot()
    key=cv2.waitKey(1)

    cv2.imshow('Cam', annotated_frame)
    boxes = result.boxes
    if boxes is not None:
        for box in boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0]
            # print(model.names[cls_id], conf)

    if key == ord('q'):
        break
# for result in results:
#     boxes = result.boxes  # Boxes object for bounding box outputs
#     masks = result.masks  # Masks object for segmentation masks outputs
#     keypoints = result.keypoints  # Keypoints object for pose outputs
#     probs = result.probs  # Probs object for classification outputs
#     obb = result.obb  # Oriented boxes object for OBB outputs
#     result.show()  # display to screen
#     # result.save(filename="result.jpg")

cap.release()
cv2.destroyAllWindows()
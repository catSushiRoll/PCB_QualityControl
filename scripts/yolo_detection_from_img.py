import ultralytics
from ultralytics import YOLO
import cv2

model = YOLO("c:/Users/syahla/Downloads/w5_runs_merging_yolov8_100/content/runs/detect/train/weights/best.pt")
results = model(source="c:/Users/syahla/Downloads/photo_6305086216612810761_y.jpg", save=False)

annotated_images = results[0].plot()
cv2.imshow('detection result', annotated_images)
cv2.waitKey(0)
cv2.destroyAllWindows()
import ultralytics
from ultralytics import YOLO
import cv2

model = YOLO("KP_best2.pt")
results = model(source="/home/syahla/kp/4e1d56ec-c94a-4840-8f1f-47d307dfa798.jpeg", save=False)

annotated_images = results[0].plot()
cv2.imshow('detection result', annotated_images)
cv2.waitKey(0)
cv2.destroyAllWindows()
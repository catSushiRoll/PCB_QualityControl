import cv2
import os
from datetime import datetime

# 0 = webcam, 2 = taffware
#TROUBLESHOOTING 101:
#BAKAL GELAP KALO = type c nyolok duluan sebelum on
#BAKAL TERANG KALO = on dulu baru colok type c

cap = cv2.VideoCapture(2)
date_folder = datetime.now().strftime('%Y-%m-%d_%H%M%S')
folder_path = os.path.join("..","dataset",date_folder)

folder_created = False
saved_count = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow('Cam', frame)
    
    key=cv2.waitKey(1)

    # print(f"folder created:{folder_path}")
    if key == ord('s'):
        if not folder_created:
            os.makedirs(folder_path, exist_ok=True)
            folder_created = True

        filename = f"{folder_path}/captured_frame{saved_count}.png"
        cv2.imwrite(filename, frame)
        print(f"Gambar berhasil disimpan: {filename}")
        saved_count += 1
    # print(f"folder created:{folder_path}")

    if key == ord('q'):
        break
    
if saved_count > 0: print(f"folder created:{folder_path}")
cap.release()
cv2.destroyAllWindows()
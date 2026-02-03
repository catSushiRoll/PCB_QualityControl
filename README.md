# PCB_QualityControl
Developed a quality control system used for PCB by using deep learning (YOLOv8) due to fulfill my Kerja Praktik project

# For Linux User
On branch `for_linux`, clone this repository with Terminal
```
git clone --branch for_linux https://github.com/catSushiRoll/PCB_QualityControl.git
cd ./PCB_QualityControl
pip install -r requirements.txt
```
# Table Of Contents
Here are lists of all scripts used to perfecting the code for detection
|Program            |Location                |Function                                          |
|---------------------|------------------------|------------------------------------------------|
|`area_rules.py`                 |./PCB_QualityControl    |Listing all components that exist for each area                          |
|`cam_detection.py`              |./PCB_QualityControl    |Detects all cameras that connected to the device                         |
|`conf_detection_gui.py`         |./PCB_QualityControl    |Main program for detects components using YOLOv8 with GUI                |
|`conf_detection_with_ocr.py`    |./PCB_QualityControl    |Main program for detects components using YOLOv8 + OCR with GUI          |
|`filtering_area.py`             |./PCB_QualityControl    |Filtering object detected that should be displayed if an area selected   |
|`ocr_resistor.py`               |./PCB_QualityControl    |Optical Character Recognition (OCR) program for reading resistor's value |

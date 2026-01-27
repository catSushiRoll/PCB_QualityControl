import cv2
import numpy as np
import easyocr

class resistor_OCR:
    def __init__(self):
        self. reader = easyocr.Reader(['en'], gpu=False)
        self.resistor_database={
            "Area 4":{
                "Resistor": ["1003","1003"],
                "footprint": ["R53", "R54"]
            },
            "Area 5":{
                "Resistor": ["1001"],
                "footprint": ["R32"]
            },
            "Area 6":{
                "Resistor": ["1002","133","2002","3003"],
                "footprint": ["R42", "R43"," R44", "R41"]
            }
        }

    def preprocess_ocr(self, image):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        h, w = gray.shape
        if h< 50 or w< 50:
            scale = max(50/h, 50/w)
            gray = cv2.resize(gray, None, fx=scale*2, fy=scale*2, interpolation=cv2.INTER_CUBIC)

        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        denoised = cv2.fastNlMeansDenoising(binary, None, 30, 7, 21)
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        return sharpened
    
    def read_classify_resistor(self, bbox, frame):
        x1, y1, x2, y2 = map(int, bbox)
        margin = 5
        y1=max(0, y1 - margin)
        x1=max(0, x1 - margin)
        y2=min(frame.shape[0],y2+margin)
        x2=min(frame.shape[1],x2+margin)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        processed = self.preprocess_ocr(roi)
        try:
            results = self.reader.readtext(processed, detail=1)
            
            if results:
                # Ambil hasil dengan confidence tertinggi
                best_result = max(results, key=lambda x: x[2])
                text = best_result[1]
                confidence = best_result[2]
                
                # Clean up text (hanya angka dan huruf)
                cleaned = ''.join(filter(str.isalnum, text))
                
                return cleaned, confidence
        except Exception as e:
            print(f"OCR Error: {e}")
        
        return None, 0.0
    
    def decode_resistor_marking(self, marking):
        """
        Decode marking code SMD ke nilai resistance
        """
        if not marking:
            return None
        
        marking = marking.upper().strip()
        value = None
        
        try:
            # 4-digit code (e.g., "1003" = 100 x 10^3 = 100kΩ)
            if len(marking) == 4 and marking.isdigit():
                base = int(marking[:3])
                multiplier = int(marking[3])
                value = base * (10 ** multiplier)
            
            # 3-digit code (e.g., "133" = 13 x 10^3 = 13kΩ)
            elif len(marking) == 3 and marking.isdigit():
                base = int(marking[:2])
                multiplier = int(marking[2])
                value = base * (10 ** multiplier)
            
            # R-notation (e.g., "R100" = 0.1Ω)
            elif marking.startswith('R') and len(marking) > 1:
                value = float(marking[1:]) / 10
        except:
            pass
        
        return {
            "value_ohms": value,
            "value_str": self.format_resistance(value) if value else "Unknown",
            "raw_marking": marking
        }
    
    def format_resistance(self, ohms):
        """Format nilai resistor ke string readable"""
        if ohms is None:
            return "Unknown"
        
        if ohms >= 1_000_000:
            return f"{ohms/1_000_000:.1f}MΩ"
        elif ohms >= 1_000:
            return f"{ohms/1_000:.1f}kΩ"
        else:
            return f"{ohms:.1f}Ω"
    
    def validate_resistor(self, area_name, marking):
        """
        Validasi resistor: cek apakah marking ada di list expected area
        """
        if not marking:
            return {
                "status": "error",
                "message": "OCR failed to read marking",
                "match": False
            }
        
        # Decode marking untuk info nilai
        decoded = self.decode_resistor_marking(marking)
        
        # Cek apakah area ada di database
        if area_name not in self.resistor_database:
            return {
                "status": "unknown",
                "message": f"[WARN]{area_name} not in database",
                "match": False,
                "detected_marking": marking,
                "decoded": decoded
            }
        
        area_data = self.resistor_database[area_name]
        expected_markings = area_data["Resistor"]
        designators = area_data["footprint"]
        
        # Cek apakah marking ada di expected list
        if marking in expected_markings:
            # Cari index untuk dapat designator
            try:
                idx = expected_markings.index(marking)
                designator = designators[idx] if idx < len(designators) else "?"
            except:
                designator = "?"
            
            # Count berapa kali marking ini muncul di expected
            count_expected = expected_markings.count(marking)
            
            return {
                "status": "ok",
                "message": f"{marking} = {decoded['value_str']} ({designator})",
                "match": True,
                "detected_marking": marking,
                "detected_value": decoded['value_str'],
                "expected_count": count_expected,
                "designator": designator,
                "decoded": decoded
            }
        else:
            # Marking tidak sesuai
            return {
                "status": "error",
                "message": f"Wrong: {marking} ({decoded['value_str']})\n   Expected: {', '.join(set(expected_markings))}",
                "match": False,
                "detected_marking": marking,
                "detected_value": decoded['value_str'],
                "expected_markings": expected_markings,
                "decoded": decoded
            }
    
    def get_area_resistor_summary(self, area_name):
        """
        Get summary expected resistor untuk area
        """
        if area_name not in self.resistor_database:
            return "No resistor data for this area"
        
        area_data = self.resistor_database[area_name]
        resistors = area_data["Resistor"]
        designators = area_data["footprint"]
        
        summary = f"Expected Resistors in {area_name}:\n"
        summary += "=" * 40 + "\n"
        
        # Group by marking
        from collections import Counter
        marking_counts = Counter(resistors)
        
        for marking, count in marking_counts.items():
            decoded = self.decode_resistor_marking(marking)
            value_str = decoded['value_str'] if decoded else "Unknown"
            
            # Find designators for this marking
            indices = [i for i, x in enumerate(resistors) if x == marking]
            desig_list = [designators[i] for i in indices if i < len(designators)]
            
            summary += f"• {marking} ({value_str}): {count}x\n"
            summary += f"  Positions: {', '.join(desig_list)}\n"
        
        return summary

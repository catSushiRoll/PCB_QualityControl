from area_rules import AREA_RULES, parse_area_rules

def filter_detections(area_name, detections, model):
    rules = parse_area_rules(area_name)

    if not rules:
        return detections

    allowed_components = set(rules.keys())
    ok_detections = []
    defect_detections = []
    component_counts = {}

    for box in detections:
        cls_id = int(box.cls[0])
        cls_name=model.names[cls_id]

        if cls_name.startswith("No "):
            base_component = cls_name.replace("No ","")
            defect_detections.append({
                "box": box,
                "type": "missing",
                "component": base_component,
                "class_name": cls_name
            })
        elif cls_name in allowed_components:
            ok_detections.append(box)
            component_counts[cls_name] = component_counts.get(cls_name, 0) + 1

    validation_results = validate_component_counts(area_name, component_counts, defect_detections, rules)
    all_detections = ok_detections + [d["box"] for d in defect_detections]
    return all_detections, validation_results

def validate_component_counts(area_name, component_counts, defect_detections, rules):
    validation = {
        "status": "ok",
        "area": area_name,
        "expected": {},
        "actual": {},
        "missing": [],
        "excess": [],
        "defects": [],
        "message": ""
    }
    
    # Check setiap komponen yang diharapkan
    for component, expected_count in rules.items():
        actual_count = component_counts.get(component, 0)
        
        validation["expected"][component] = expected_count
        validation["actual"][component] = actual_count
        
        # Komponen kurang
        if actual_count < expected_count:
            validation["missing"].append({
                "component": component,
                "expected": expected_count,
                "actual": actual_count,
                "shortage": expected_count - actual_count
            })
            validation["status"] = "error"
        
        # Komponen lebih
        elif actual_count > expected_count:
            validation["excess"].append({
                "component": component,
                "expected": expected_count,
                "actual": actual_count,
                "excess": actual_count - expected_count
            })
            validation["status"] = "warning" if validation["status"] == "ok" else validation["status"]
    
    # Process defect detections
    for defect in defect_detections:
        validation["defects"].append({
            "type": defect["type"],
            "component": defect["component"],
            "class_name": defect["class_name"]
        })
        validation["status"] = "error"
    
    # Generate message
    if validation["status"] == "ok":
        validation["message"] = f"✅ {area_name}: All components OK"
    else:
        messages = []
        if validation["missing"]:
            messages.append(f"Missing: {len(validation['missing'])} type(s)")
        if validation["excess"]:
            messages.append(f"Excess: {len(validation['excess'])} type(s)")
        if validation["defects"]:
            messages.append(f"Defects: {len(validation['defects'])} issue(s)")
        validation["message"] = f"❌ {area_name}: {', '.join(messages)}"
    
    return validation


def get_area_component_list(area_name):
    rules = parse_area_rules(area_name)
    
    if not rules:
        return "No components defined for this area"
    
    component_list = []
    for component, count in sorted(rules.items()):
        component_list.append(f"• {component}: {count}")
    
    return "\n".join(component_list)
from typing import Dict

AREA_RULES:Dict[str, Dict[str, int]]={
    "Area 1": {
        "Dioda": 2,
        "Resistor": 2,
        "Oscillator": 1,
        "IC": 1,
        "Connector": 1
    },

    "Area 2": {
        "IC": 1,
        "Capasitor": 1
    },

    "Area 3": {
        "IC": 2,
        "Button": 1,
        "LED": 1,
        "Capasitor": 2,
        "Resistor": 1,
        "Jumper": 1
    },

    "Area 4": {
        "Resistor": 2,
        "Capasitor": 3
    },

    "Area 5": {
        "Inductor": 1,
        "Capasitor": 1,
        "Transistor": 1,
        "Resistor": 1
    },

    "Area 6": {
        "Dioda": 1,
        "Resistor": 4,
        "Switch": 1,
        "Jumper": 1
    },

    "Area 7": {
        "Buzzer": 1,
        "Regulator": 1
    }
}

def parse_area_rules(area_name: str) -> Dict[str, int]:
    rules_set = AREA_RULES.get(area_name, set())
    parsed : Dict[str, int] = {}
    
    for rule in rules_set:
        if ":" in rule:
            component, count = rule.split(":")
            parsed[component.strip()] = int(count.strip())
    return parsed
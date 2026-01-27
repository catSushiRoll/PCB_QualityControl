AREA_RULES:dict[str, dict[str, int]]={
    "Area 1": {
        "Dioda : 2",
        "Resistor: 2",
        "Oscillator: 1",
        "IC: 1",
        "Connector: 1"
    },

    "Area 2": {
        "IC:1",
        "Capasitor: 1"
    },

    "Area 3": {
        "IC: 2",
        "Button: 1",
        "LED: 1",
        "Capasitor: 2",
        "Resistor: 1",
        "Jumper: 1"
    },

    "Area 4": {
        "Resistor: 2",
        "Capasitor: 3"
    },

    "Area 5": {
        "Inductor: 1",
        "Capasitor: 1",
        "Transistor: 1",
        "Resistor: 1"
    },

    "Area 6": {
        "Dioda: 1",
        "Resistor: 4",
        "Switch: 1",
        "Jumper: 1"
    },

    "Area 7": {
        "Buzzer: 1",
        "Regulator: 1"
    }
}

def parse_area_rules(area_name: str) -> dict[str, int]:
    """
    Convert set of 'Component: count' strings to dict
    Returns: {"Component": count}
    """
    rules_set = AREA_RULES.get(area_name, set())
    parsed = {}
    
    for rule in rules_set:
        if ":" in rule:
            parts = rule.split(":")
            component = parts[0].strip()
            count = int(parts[1].strip())
            parsed[component] = count
    
    return parsed
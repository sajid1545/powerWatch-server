"""Download and normalize Bangladesh administrative data into one local JSON file.

This is a maintenance utility only. The running application reads the generated
JSON and never depends on the remote service.
"""
import json
from pathlib import Path
from urllib.request import urlopen

BASE = "https://bdapis.pro.bd/geo/v2.0"
OUTPUT = Path(__file__).parent / "data" / "bangladesh_areas.json"

def fetch(path):
    with urlopen(f"{BASE}/{path}", timeout=30) as response:
        return json.load(response)["data"]

divisions = {str(x["id"]): x for x in fetch("divisions")}
districts = {str(x["id"]): x for x in fetch("districts")}
areas = []
for item in fetch("upazilas"):
    district = districts[str(item["district_id"])]
    division = divisions[str(district["division_id"])]
    areas.append({
        "id": str(item["id"]),
        "name": item["name"],
        "bn_name": item.get("bn_name", ""),
        "district_id": str(district["id"]),
        "district": district["name"],
        "district_bn": district.get("bn_name", ""),
        "division_id": str(division["id"]),
        "division": division["name"],
        "division_bn": division.get("bn_name", ""),
    })

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(areas, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved {len(areas)} Bangladesh areas to {OUTPUT}")

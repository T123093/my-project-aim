import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys

def generate_route_file(volume_level="medium"):
    # 交通量レベルに応じた設定（1方向あたりの台数/時）
    volumes = {
        "low": [300, 250, 200],
        "medium": [850, 720, 450],
        "high": [1500, 1300, 1100]
    }
    
    selected_volumes = volumes.get(volume_level.lower(), volumes["medium"])
    print(f"--- 交通量レベル [{volume_level.upper()}] でルートファイルを生成します ---")

    # 1. chino.net.xml から普通車が通行可能なエッジを取得
    net_tree = ET.parse("chino.net.xml")
    net_root = net_tree.getroot()

    passenger_edges = []
    for edge in net_root.findall("edge"):
        edge_id = edge.get("id")
        if not edge_id or edge_id.startswith(":") or edge.get("function") == "internal":
            continue

        has_passenger_lane = False
        for lane in edge.findall("lane"):
            allow = lane.get("allow")
            disallow = lane.get("disallow")
            if (not disallow or "passenger" not in disallow) and (not allow or "passenger" in allow):
                has_passenger_lane = True
                break

        if has_passenger_lane:
            passenger_edges.append(edge_id)

    if not passenger_edges:
        print("エラー: 通行可能なエッジが見つかりませんでした。")
        return

    # 2. XML 要素の作成
    routes = ET.Element("routes")
    ET.SubElement(routes, "vType", id="passenger", accel="2.6", decel="4.5", length="4.5", maxSpeed="14.0")
    ET.SubElement(routes, "vType", id="heavy_truck", accel="1.2", decel="4.0", length="10.0", maxSpeed="10.0")

    sample_ratios = [0.15, 0.12, 0.08]

    for idx, edge_id in enumerate(passenger_edges[:3]):
        total_volume = selected_volumes[idx % len(selected_volumes)]
        heavy_ratio = sample_ratios[idx % len(sample_ratios)]

        heavy_volume = int(total_volume * heavy_ratio)
        passenger_volume = total_volume - heavy_volume

        if passenger_volume > 0:
            ET.SubElement(routes, "flow", {
                "id": f"flow_passenger_{idx}",
                "type": "passenger",
                "from": edge_id,
                "begin": "0",
                "end": "3600",
                "vehsPerHour": str(passenger_volume),
                "departLane": "free",
                "departSpeed": "max"
            })

        if heavy_volume > 0:
            ET.SubElement(routes, "flow", {
                "id": f"flow_heavy_{idx}",
                "type": "heavy_truck",
                "from": edge_id,
                "begin": "0",
                "end": "3600",
                "vehsPerHour": str(heavy_volume),
                "departLane": "free",
                "departSpeed": "max"
            })

    xml_str = minidom.parseString(ET.tostring(routes)).toprettyxml(indent="    ")
    with open("chino.rou.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"chino.rou.xml の生成完了 (Level: {volume_level})")

if __name__ == "__main__":
    level = sys.argv[1] if len(sys.argv) > 1 else "medium"
    generate_route_file(level)
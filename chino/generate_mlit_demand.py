import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys
import random

def generate_route_file(volume_level="medium"):
    # 交通量レベルに応じた設定（全体にバランスよく配置するための中庸なボリューム）
    volumes = {
        "low": [200, 150, 100],
        "medium": [600, 400, 300],
        "high": [2500, 2000, 1500]
    }
    
    selected_volumes = volumes.get(volume_level.lower(), volumes["medium"])
    print(f"--- 交通量レベル [{volume_level.upper()}] (ネットワーク全体・バランス型) でルートファイルを生成します ---")

    # 1. chino.net.xml から通行可能なエッジを幅広く抽出
    net_tree = ET.parse("chino.net.xml")
    net_root = net_tree.getroot()

    passenger_edges = []
    for edge in net_root.findall("edge"):
        edge_id = edge.get("id")
        if not edge_id or edge_id.startswith(":") or edge.get("function") == "internal":
            continue

        # 普通車が通れるかチェック
        has_passenger_lane = False
        for lane in edge.findall("lane"):
            allow = lane.get("allow")
            disallow = lane.get("disallow")
            if (not disallow or "passenger" not in disallow) and (not allow or "passenger" in allow):
                has_passenger_lane = True
                break

        if has_passenger_lane:
            passenger_edges.append(edge_id)

    print(f"通行可能な全エッジ数: {len(passenger_edges)}本")

    if not passenger_edges:
        print("エラー: 有効なエッジが見つかりませんでした。")
        return

    # 発生源が極端に偏らないよう、適度な数（例: 最大30本）をランダムに選択
    num_sources = min(30, len(passenger_edges))
    target_edges = random.sample(passenger_edges, num_sources)
    print(f"選択された発生源エッジ数: {len(target_edges)}本")

    # 2. XML 要素の作成
    routes = ET.Element("routes")
    ET.SubElement(routes, "vType", id="passenger", accel="2.6", decel="4.5", length="4.5", maxSpeed="14.0")
    ET.SubElement(routes, "vType", id="heavy_truck", accel="1.2", decel="4.0", length="10.0", maxSpeed="10.0")

    # 選択された各エッジに対してフローを生成
    for idx, edge_id in enumerate(target_edges):
        base_vol = selected_volumes[idx % len(selected_volumes)]
        heavy_ratio = 0.1  # 大型車の割合を10%程度に設定

        heavy_volume = int(base_vol * heavy_ratio)
        passenger_volume = base_vol - heavy_volume

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
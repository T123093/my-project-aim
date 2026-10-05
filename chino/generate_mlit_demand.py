import xml.etree.ElementTree as ET
from xml.dom import minidom

# 1. chino.net.xml から普通車が走行可能なエッジIDのみを自動抽出
net_tree = ET.parse("chino.net.xml")
net_root = net_tree.getroot()

passenger_edges = []

for edge in net_root.findall("edge"):
    edge_id = edge.get("id")
    # 内部交差点エッジ（:で始まるもの）を除外
    if not edge_id or edge_id.startswith(":") or edge.get("function") == "internal":
        continue

    # エッジ内の各レーンをチェックし、普通車が通行可能か確認
    has_passenger_lane = False
    for lane in edge.findall("lane"):
        allow = lane.get("allow")
        disallow = lane.get("disallow")

        # disallowにpassengerが含まれておらず、allowが未設定（全許可）またはpassengerを含む場合
        if (not disallow or "passenger" not in disallow) and (not allow or "passenger" in allow):
            has_passenger_lane = True
            break

    if has_passenger_lane:
        passenger_edges.append(edge_id)

if not passenger_edges:
    print("エラー: chino.net.xml から普通車が走行可能なエッジが見つかりませんでした。")
    exit(1)

print(f"マップから普通車が通行可能な {len(passenger_edges)} 個のエッジを検出しました。")

# 2. XMLルート要素の作成
routes = ET.Element("routes")

# 車種定義（普通車・大型車）
ET.SubElement(routes, "vType", id="passenger", accel="2.6", decel="4.5", length="4.5", maxSpeed="14.0")
ET.SubElement(routes, "vType", id="heavy_truck", accel="1.2", decel="4.0", length="10.0", maxSpeed="10.0")

# 通行可能なエッジ（先頭から最大3つ）を使用して Flow を作成
sample_volumes = [850, 720, 450]
sample_ratios = [0.15, 0.12, 0.08]

for idx, edge_id in enumerate(passenger_edges[:3]):
    total_volume = sample_volumes[idx % len(sample_volumes)]
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

# 書き出し
xml_str = minidom.parseString(ET.tostring(routes)).toprettyxml(indent="    ")
with open("chino.rou.xml", "w", encoding="utf-8") as f:
    f.write(xml_str)

print("走行可能なエッジを反映した chino.rou.xml の再生成が完了しました！")
import xml.etree.ElementTree as ET
import pandas as pd

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

# 2. 検出したエッジ ID で census_chino.csv を更新
if len(passenger_edges) >= 3:
    df = pd.DataFrame({
        "edge_id": passenger_edges[:3],
        "hourly_volume": [850, 720, 450],
        "vehicle_type_ratio_heavy": [0.15, 0.12, 0.08]
    })
    df.to_csv("census_chino.csv", index=False)
    print("census_chino.csv を実際のエッジ ID で更新しました！")
    print(df)
else:
    print("通行可能なエッジが十分に見つかりませんでした。")
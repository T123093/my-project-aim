import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom

# 国交省センサスデータの読み込み
df = pd.read_csv("census_chino.csv")

# XMLルート要素の作成
routes = ET.Element("routes")

# 車種定義（普通車・大型車）
vtype_passenger = ET.SubElement(routes, "vType", id="passenger", accel="2.6", decel="4.5", length="4.5", maxSpeed="14.0")
vtype_heavy = ET.SubElement(routes, "vType", id="heavy_truck", accel="1.2", decel="4.0", length="10.0", maxSpeed="10.0")

# センサスデータからFlow要素を自動構築
for idx, row in df.iterrows():
    edge_id = str(row['edge_id'])
    total_volume = int(row['hourly_volume'])
    heavy_ratio = float(row['vehicle_type_ratio_heavy'])

    heavy_volume = int(total_volume * heavy_ratio)
    passenger_volume = total_volume - heavy_volume

    # 普通車のFlow定義
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

    # 大型車のFlow定義
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

# インデントを整えて XML ファイルとして出力
xml_str = minidom.parseString(ET.tostring(routes)).toprettyxml(indent="    ")
with open("chino.rou.xml", "w", encoding="utf-8") as f:
    f.write(xml_str)

print("国土交通省データに基づく chino.rou.xml の生成が完了しました！")
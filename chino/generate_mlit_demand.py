import xml.etree.ElementTree as ET
from xml.dom import minidom
from collections import defaultdict, deque
import sys
import random


def get_reachable_edges(start_edge, adj):
    """start_edge から connection をたどって到達可能なエッジ集合を返す"""
    visited = set()
    queue = deque([start_edge])
    while queue:
        cur = queue.popleft()
        for nxt in adj.get(cur, ()):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return visited


def generate_route_file(volume_level="medium", seed=42):
    random.seed(seed)

    volumes = {
        "low": [200, 150, 100],
        "medium": [600, 400, 300],
        "high": [2500, 2000, 1500],
    }
    selected_volumes = volumes.get(volume_level.lower(), volumes["medium"])
    print(f"--- 交通量レベル [{volume_level.upper()}] (seed={seed}) でルートファイルを生成します ---")

    net_tree = ET.parse("chino.net.xml")
    net_root = net_tree.getroot()

    # 普通車が通行可能な通常エッジを収集
    passenger_edges = set()
    for edge in net_root.findall("edge"):
        eid = edge.get("id")
        if not eid or eid.startswith(":") or edge.get("function") == "internal":
            continue
        for lane in edge.findall("lane"):
            allow = lane.get("allow")
            disallow = lane.get("disallow")
            if (not disallow or "passenger" not in disallow) and (not allow or "passenger" in allow):
                passenger_edges.add(eid)
                break

    # 接続グラフと信号機（tl）制御エッジを構築
    adj = defaultdict(list)
    out_conns = defaultdict(int)
    tls_edges = set()

    for conn in net_root.findall("connection"):
        f = conn.get("from")
        t = conn.get("to")
        if f and t and not f.startswith(":") and not t.startswith(":"):
            if f in passenger_edges and t in passenger_edges:
                adj[f].append(t)
                out_conns[f] += 1
                if conn.get("tl"):
                    tls_edges.add(f)
                    tls_edges.add(t)

    # 出口接続があり、信号機関連エッジを含む候補を優先
    valid_sources = [e for e in passenger_edges if out_conns[e] > 0]
    tls_sources = [e for e in valid_sources if e in tls_edges]
    source_pool = tls_sources if len(tls_sources) >= 10 else valid_sources

    if len(source_pool) < 2:
        print("エラー: 有効な発生源エッジが見つかりませんでした。")
        return

    num_sources = min(25, len(source_pool))
    selected_sources = random.sample(source_pool, num_sources)

    routes = ET.Element("routes")
    ET.SubElement(routes, "vType", id="passenger", accel="2.6", decel="4.5", length="4.5", maxSpeed="14.0")
    ET.SubElement(routes, "vType", id="heavy_truck", accel="1.2", decel="4.0", length="10.0", maxSpeed="10.0")

    flow_count = 0
    for idx, src in enumerate(selected_sources):
        reachable = [e for e in get_reachable_edges(src, adj) if e != src]
        if not reachable:
            continue

        # できれば信号機付近を目的地に優先
        tls_reachable = [e for e in reachable if e in tls_edges]
        dest_pool = tls_reachable if tls_reachable else reachable

        base_vol = selected_volumes[idx % len(selected_volumes)]
        heavy_volume = int(base_vol * 0.1)
        passenger_volume = base_vol - heavy_volume

        dest_pass = random.choice(dest_pool)
        dest_heavy = random.choice(dest_pool)

        if passenger_volume > 0:
            ET.SubElement(routes, "flow", {
                "id": f"flow_passenger_{idx}",
                "type": "passenger",
                "from": src,
                "to": dest_pass,
                "begin": "0",
                "end": "600",
                "vehsPerHour": str(passenger_volume),
                "departLane": "free",
                "departSpeed": "max",
            })
            flow_count += 1

        if heavy_volume > 0:
            ET.SubElement(routes, "flow", {
                "id": f"flow_heavy_{idx}",
                "type": "heavy_truck",
                "from": src,
                "to": dest_heavy,
                "begin": "0",
                "end": "3600",
                "vehsPerHour": str(heavy_volume),
                "departLane": "free",
                "departSpeed": "max",
            })
            flow_count += 1

    xml_str = minidom.parseString(ET.tostring(routes)).toprettyxml(indent="    ")
    with open("chino.rou.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"chino.rou.xml を生成しました（フロー数: {flow_count}）")


if __name__ == "__main__":
    level = sys.argv[1] if len(sys.argv) > 1 else "medium"
    seed_val = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    generate_route_file(level, seed_val)
import xml.etree.ElementTree as ET

#ファイルを読み込む
tree = ET.parse("edgeData.xml")
root = tree.getroot()

max_wait = 0
bottleneck_edge = ""

#edgeごとに確認する
for edge in root.iter("edge"):
    wait = float(edge.get("waitingTime", 0))
    if wait > max_wait:
        max_wait = wait
        bottleneck_edge = edge.get("id")

print("ボトルネックエッジ:", bottleneck_edge)
print("waitingTime:", max_wait)
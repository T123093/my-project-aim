import sys
import time
import csv
import traci

#SUMO toolsを追加
sys.path.append(r"C:\Program Files (x86)\Eclipse\Sumo\tools")

# SUMO GUI設定（作成した network.net.xml と routes.rou.xml を読み込む設定ファイル。なければ直指定も可）
sumoBinary = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo-gui.exe"
# 確実に対象ファイルが読み込まれるよう、コマンドライン引数で直接指定します
sumoCmd = [
    sumoBinary, 
    "-n", r"C:\Users\GLAB-PC002\Desktop\sumo_project\pt3\network.net.xml", 
    "-r", r"C:\Users\GLAB-PC002\Desktop\sumo_project\pt3\routes.rou.xml",
    "--start", "true"  # 起動時に自動でシミュレーションを開始
]

#SUMO起動
traci.start(sumoCmd)
tlsIDs = traci.trafficlight.getIDList()

#----------
#すべての信号を無効化
#----------
for tlsID in tlsIDs:
    try:
        logic = traci.trafficlight.getAllProgramLogics(tlsID)[0]
        num_links = len(logic.phases[0].state)
        #全方向を緑に
        traci.trafficlight.setRedYellowGreenState(tlsID, "G" * num_links)
    except Exception as e:
        continue

#ログ用のCSV作成
csv_path = r"C:\Users\GLAB-PC002\Desktop\sumo_project\pt3\traffic_log_aim_real.csv"
csv_file = open(csv_path, "w", newline="", encoding="utf-8")
writer = csv.writer(csv_file)
writer.writerow(["time_s", "avg_waiting_time", "max_waiting_time", "throughput", "conflict_count"])

try:
    #分散型予約管理用
    distributed_reservations = {}

    conflict_count_total = 0    #累積予約発生回数
    passed_vehicles = set() #交差点を通過した車両の累積管理
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
    "-c", r"C:\Users\GLAB-PC002\Desktop\sumo_project\pt3\pt3.sumocfg", 
    "--start", "true"  # 起動時に自動再生
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

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        time.sleep(0.02)
        #現在の秒数を取得
        current_time_s = traci.simulation.getTime()
        print(f"\n===== [Distributed AIM] Time: {current_time_s}s =====")

        vehicle_ids = traci.vehicle.getIDList()

        #1.期限切れスロットの開放
        for key in list(distributed_reservations.keys()):
            if distributed_reservations[key]["end_time"] < current_time_s:
                del distributed_reservations[key]
        
        step_waiting_times = []

        #2.車両ごとのアプローチ＆分散予約処理
        for vid in vehicle_ids:
            wait_time = traci.vehicle.getWaitingTime(vid)
            step_waiting_times.append(wait_time)
            road = traci.vehicle.getRoadID(vid)
            if not road.startswith(":") and road != "":
                continue

            #車両が次に接近している信号機の情報を取得
            next_tls = traci.vehicle.getNextTLS(vid)
            if next_tls:
                tls_id, link_idx, dist, state = next_tls[0]

                #交差点手前50m以内にアプローチした場合にAIMを作動
                if dist < 50:
                    res_key = (tls_id, link_idx)
                    if res_key in distributed_reservations:
                        res = distributed_reservations[res_key]
                        if res["vehicle"] != vid:
                            #予約競合
                            print(f"予約競合[{tls_id}]: {vid} に減速指示")
                            traci.vehicle.slowDown(vid, 2.0, 2.0)
                            conflict_count_total += 1
                    else:
                        #分散予約成功:
                        distributed_reservations[res_key] = {"vehicle": vid, "end_time": current_time_s + 5.0}
                        print(f"予約成功 [{tls_id}]: {vid} → {link_idx}を確保")

        #3.統計データ計算、CSVへの書き込み 
        avg_wait = sum(step_waiting_times) /len(step_waiting_times) if step_waiting_times else 0
        max_wait = max(step_waiting_times) if step_waiting_times else 0
        throughput = len(passed_vehicles)

        writer.writerow([current_time_s, avg_wait, max_wait, throughput, conflict_count_total])

finally:
    csv_file.close()
    traci.close()
    print(f"シミュレーション終了: データが {csv_path} に保存されました。")

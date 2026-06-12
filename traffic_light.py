import sys
import time
import csv
import traci

# SUMO tools を追加
sys.path.append(r"C:\Program Files (x86)\Eclipse\Sumo\tools")

# SUMO GUI設定
sumoBinary = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo-gui.exe"
sumoCmd = [sumoBinary, "-c", r"C:\Users\GLAB-PC002\Desktop\sumo_project\test.sumocfg"]

# SUMO起動
traci.start(sumoCmd)
tlsIDs = traci.trafficlight.getIDList()

# ログ用CSV作成（比較しやすいよう、ヘッダーをAIM側の項目と一致させます）
csv_file = open(r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_tls.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(csv_file)
# AIMのグラフコードがそのまま使い回せるように項目を設定（conflict_countは信号なので常に0）
writer.writerow(["step", "avg_waiting_time", "max_waiting_time", "throughput", "conflict_count"])

try:
    step = 0
    passed_vehicles = set()   # 交差点を通過した車両の累積管理

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        time.sleep(0.1)

        print(f"\n===== [NORMAL TLS] STEP {step} =====")
        vehicle_ids = traci.vehicle.getIDList()
        step_waiting_times = []

        # 車両ごとの状況把握
        for vid in vehicle_ids:
            # 待ち時間の集計
            wait_time = traci.vehicle.getWaitingTime(vid)
            step_waiting_times.append(wait_time)

            # 通過車両数（スループット）のカウント用
            road = traci.vehicle.getRoadID(vid)
            if not road.startswith(":") and road != "":
                passed_vehicles.add(vid)

        # ---------------------------------
        # 通常の信号機制御：
        # TraCI側からは一切フェーズの変更指示を出さず、
        # SUMO本来のタイムスケジュール（一定周期）で自動で切り替えさせます。
        # ---------------------------------

        # 統計データの計算
        avg_wait = sum(step_waiting_times) / len(step_waiting_times) if step_waiting_times else 0
        max_wait = max(step_waiting_times) if step_waiting_times else 0
        throughput = len(passed_vehicles)
        conflict_count_total = 0  # 信号機制御なので予約競合は0固定

        # CSV保存（AIMのログと全く同じフォーマット）
        writer.writerow([step, avg_wait, max_wait, throughput, conflict_count_total])
        step += 1

finally:
    csv_file.close()
    traci.close()
    print("通常の信号機シミュレーション終了: traffic_log_tls.csv に保存されました")
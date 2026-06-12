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

# ログ用CSV作成（ファイル名をactuatedに変えて区別します）
csv_file = open(r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_actuated_tls.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(csv_file)
writer.writerow(["step", "avg_waiting_time", "max_waiting_time", "throughput", "conflict_count"])

try:
    step = 0
    passed_vehicles = set()   # 交差点を通過した車両の累積管理

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        time.sleep(0.1)

        print(f"\n===== [ACTUATED TLS CONTROL] STEP {step} =====")
        step_waiting_times = []

        # 各交差点ごとに動的制御を適用
        for tlsID in tlsIDs:
            lanes = list(set(traci.trafficlight.getControlledLanes(tlsID)))
            ns_vehicle = 0
            ew_vehicle = 0
            waiting_time_total = 0

            # レーンごとの状況把握
            for lane in lanes:
                vehicle_num = traci.lane.getLastStepVehicleNumber(lane)
                lane_wait = traci.lane.getWaitingTime(lane)
                waiting_time_total += lane_wait

                lane_lower = lane.lower()
                if "n" in lane_lower or "s" in lane_lower:
                    ns_vehicle += vehicle_num
                elif "e" in lane_lower or "w" in lane_lower:
                    ew_vehicle += vehicle_num

            current_phase = traci.trafficlight.getPhase(tlsID)

            # 動的信号制御ロジック (30ステップごと)
            if waiting_time_total > 40 and step % 30 == 0:
                if ns_vehicle > ew_vehicle + 3:
                    if current_phase != 0:
                        traci.trafficlight.setPhase(tlsID, 0)
                    traci.trafficlight.setPhaseDuration(tlsID, 20)
                elif ew_vehicle > ns_vehicle + 3:
                    if current_phase != 2:
                        traci.trafficlight.setPhase(tlsID, 2)
                    traci.trafficlight.setPhaseDuration(tlsID, 20)

        # 全車両の待ち時間と通過数を集計
        vehicle_ids = traci.vehicle.getIDList()
        for vid in vehicle_ids:
            wait_time = traci.vehicle.getWaitingTime(vid)
            step_waiting_times.append(wait_time)

            road = traci.vehicle.getRoadID(vid)
            if not road.startswith(":") and road != "":
                passed_vehicles.add(vid)

        # 統計データの計算
        avg_wait = sum(step_waiting_times) / len(step_waiting_times) if step_waiting_times else 0
        max_wait = max(step_waiting_times) if step_waiting_times else 0
        throughput = len(passed_vehicles)

        # CSV保存
        writer.writerow([step, avg_wait, max_wait, throughput, 0])
        step += 1

finally:
    csv_file.close()
    traci.close()
    print("動的信号シミュレーション終了: traffic_log_actuated_tls.csv に保存されました")
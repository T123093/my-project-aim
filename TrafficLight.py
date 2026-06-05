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

# ログ用CSV作成
csv_file = open(r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_tls.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(csv_file)
writer.writerow(["step", "tlsID", "ns_vehicle", "ew_vehicle", "phase", "waiting_time"])

try:
    step = 0

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        time.sleep(0.1)

        print(f"\n===== [TLS CONTROL] STEP {step} =====")
        max_waiting = 0
        max_tls = ""

        # 各交差点ごとに制御
        for tlsID in tlsIDs:
            lanes = list(set(traci.trafficlight.getControlledLanes(tlsID)))

            ns_vehicle = 0
            ew_vehicle = 0
            waiting_time = 0

            # レーンごとの状況把握
            for lane in lanes:
                vehicle_num = traci.lane.getLastStepVehicleNumber(lane)
                lane_wait = traci.lane.getWaitingTime(lane)
                waiting_time += lane_wait

                lane_lower = lane.lower()
                if "n" in lane_lower or "s" in lane_lower:
                    ns_vehicle += vehicle_num
                elif "e" in lane_lower or "w" in lane_lower:
                    ew_vehicle += vehicle_num

            if waiting_time > max_waiting:
                max_waiting = waiting_time
                max_tls = tlsID

            current_phase = traci.trafficlight.getPhase(tlsID)

            # ---------------------------------
            # 動的信号制御ロジック (30ステップごと)
            # ---------------------------------
            if waiting_time > 40 and step % 30 == 0:
                # 南北が激しく混雑（東西より3台以上多い）
                if ns_vehicle > ew_vehicle + 3:
                    if current_phase != 0:
                        print(f"🚦 [{tlsID}] 南北優先制御へ切り替え")
                        traci.trafficlight.setPhase(tlsID, 0)
                    traci.trafficlight.setPhaseDuration(tlsID, 20)

                # 東西が激しく混雑（南北より3台以上多い）
                elif ew_vehicle > ns_vehicle + 3:
                    if current_phase != 2:
                        print(f"🚦 [{tlsID}] 東西優先制御へ切り替え")
                        traci.trafficlight.setPhase(tlsID, 2)
                    traci.trafficlight.setPhaseDuration(tlsID, 20)
            
            # CSV保存
            writer.writerow([step, tlsID, ns_vehicle, ew_vehicle, current_phase, waiting_time])

        print(f"最大渋滞交差点: {max_tls} (待ち時間: {max_waiting})")
        step += 1

finally:
    csv_file.close()
    traci.close()
    print("シミュレーション終了")
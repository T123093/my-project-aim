import sys
import time
import csv
import traci

# SUMO tools 設定
sys.path.append(r"C:\Program Files (x86)\Eclipse\Sumo\tools")
sumoBinary = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo-gui.exe"
sumoCmd = [sumoBinary, "-c", r"C:\Users\GLAB-PC002\Desktop\sumo_project\test.sumocfg"]

traci.start(sumoCmd)

tlsIDs = traci.trafficlight.getIDList()

# --- AIM導入のための事前準備 ---
# 信号機による停止を防ぐため、全信号を「常に全方向青」のフェーズに固定する
# （本来のAIMは信号機が存在しない前提だが、SUMO上では全方向青が最も近い挙動になる）
for tlsID in tlsIDs:
    # 多くのネットワークでフェーズ0が南北青、2が東西青などになるが、
    # 完全に信号を無視させるには、全方向 'G' のカスタム状態を送るのが確実
    logic = traci.trafficlight.getAllProgramLogics(tlsID)[0]
    num_links = len(logic.phases[0].state)
    traci.trafficlight.setRedYellowGreenState(tlsID, "G" * num_links)

csv_file = open(r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(csv_file)
writer.writerow(["step", "tlsID", "ns_vehicle", "ew_vehicle", "phase", "waiting_time"])

try:
    step = 0
    reservation = {} # {tlsID: {"vehicle": vid, "arrival": time, "step": step}}
    slowed_vehicles = {} # {vid: original_max_speed}

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        time.sleep(0.1)
        
        current_time = traci.simulation.getTime()
        vehicle_ids = traci.vehicle.getIDList()
        arrival_times = []
        current_step_slowed = set()

        # 1. 期限切れ予約の削除（交差点を通過した、または一定時間経過した予約）
        for tls in list(reservation.keys()):
            res_vid = reservation[tls]["vehicle"]
            # 車両が消えた、または既にその交差点のエッジにいない（通過した）場合
            if res_vid not in vehicle_ids:
                del reservation[tls]
            else:
                # 交差点(内部エッジ)に入ったら予約枠を解放する（後続のため）
                if traci.vehicle.getRoadID(res_vid).startswith(":"):
                    del reservation[tls]

        # 2. 車両ごとの状況把握と予約処理
        for vid in vehicle_ids:
            edge = traci.vehicle.getRoadID(vid)
            if edge.startswith(":"): continue # 交差点内は判定除外

            lane = traci.vehicle.getLaneID(vid)
            speed = traci.vehicle.getSpeed(vid)
            lane_pos = traci.vehicle.getLanePosition(vid)
            lane_len = traci.lane.getLength(lane)
            dist = lane_len - lane_pos

            if speed > 0.5:
                arrival_time = current_time + (dist / speed)
                
                # 最寄りの交差点を特定
                target_tls = None
                for tlsID in tlsIDs:
                    if lane in traci.trafficlight.getControlledLanes(tlsID):
                        target_tls = tlsID
                        break
                
                if target_tls:
                    # --- AIM 予約ロジック ---
                    if target_tls not in reservation:
                        # 空きがあれば予約
                        reservation[target_tls] = {"vehicle": vid, "arrival": arrival_time}
                        print(f"DEBUG: {vid} 予約成功 @ {target_tls} (予測:{arrival_time:.1f}s)")
                    else:
                        res = reservation[target_tls]
                        if res["vehicle"] != vid:
                            # 他車が予約済みの場合、到達時間の差をチェック
                            time_diff = abs(arrival_time - res["arrival"])
                            if time_diff < 3.0: # 3秒以内の衝突リスク
                                print(f"DEBUG: {vid} 予約競合 -> 減速開始")
                                if vid not in slowed_vehicles:
                                    slowed_vehicles[vid] = traci.vehicle.getMaxSpeed(vid)
                                    traci.vehicle.slowDown(vid, 1.0, 2.0) # 2秒かけて1m/sまで落とす
                                current_step_slowed.add(vid)
                            else:
                                # 時間差があれば予約を上書き（またはキューに入れるが、ここでは簡易化のため更新）
                                # 先着順を維持する場合、ここは更新しない
                                pass

        # 3. 減速解除処理
        for vid in list(slowed_vehicles.keys()):
            if vid not in current_step_slowed:
                if vid in vehicle_ids:
                    traci.vehicle.setMaxSpeed(vid, slowed_vehicles[vid])
                    print(f"DEBUG: {vid} 減速解除")
                del slowed_vehicles[vid]

        # 4. 統計情報の取得とCSV保存
        for tlsID in tlsIDs:
            # (省略: 以前のコードと同様の車両数カウントとCSV書き込み)
            # ...
            pass

        step += 1

finally:
    csv_file.close()
    traci.close()
    print("終了")
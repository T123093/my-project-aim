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

# ---------------------------------
# AIM環境の準備: 信号機による強制停止を無効化
# ---------------------------------
for tlsID in tlsIDs:
    logic = traci.trafficlight.getAllProgramLogics(tlsID)[0]
    num_links = len(logic.phases[0].state)
    # 全方向を大文字の 'G' (優先権ありの緑) に固定
    traci.trafficlight.setRedYellowGreenState(tlsID, "G" * num_links)

# ログ用CSV作成
csv_file = open(r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_aim.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(csv_file)
writer.writerow(["step", "tlsID", "ns_vehicle", "ew_vehicle", "reserved_vehicle", "waiting_time"])

try:
    step = 0
    reservation = {}      # 交差点の予約状況 { tlsID: {"vehicle": vid, "arrival": 絶対時刻} }
    slowed_vehicles = {}  # 減速中の車両管理 { vid: 元の最高速度 }

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        time.sleep(0.1)

        print(f"\n===== [AIM CONTROL] STEP {step} =====")
        current_time = traci.simulation.getTime()
        vehicle_ids = traci.vehicle.getIDList()
        current_step_slowed = set()

        # 1. 通過済み車両の予約キャンセル処理
        for tls in list(reservation.keys()):
            res_vid = reservation[tls]["vehicle"]
            # 車両が消えた、またはすでに交差点内（内部レーン ":"）に入ったら予約を解放
            if res_vid not in vehicle_ids or traci.vehicle.getRoadID(res_vid).startswith(":"):
                print(f"🔓 予約解放: {res_vid} が交差点を通過または進入しました")
                del reservation[tls]

        # 2. 車両ごとのアプローチ＆予約要求処理
        for vid in vehicle_ids:
            edge = traci.vehicle.getRoadID(vid)
            if edge.startswith(":"):
                continue  # 交差点内部にいる車両は判定から除外

            lane = traci.vehicle.getLaneID(vid)
            speed = traci.vehicle.getSpeed(vid)
            dist = traci.lane.getLength(lane) - traci.vehicle.getLanePosition(vid)

            if speed > 0.5:
                # 到着予測時刻（絶対時刻）を計算
                arrival_time = current_time + (dist / speed)

                # その車両が向かっている交差点（tlsID）を特定
                target_tls = None
                for tlsID in tlsIDs:
                    if lane in traci.trafficlight.getControlledLanes(tlsID):
                        target_tls = tlsID
                        break

                # AIM予約ロジック
                if target_tls:
                    if target_tls not in reservation:
                        # 交差点が空いていれば予約成功
                        reservation[target_tls] = {"vehicle": vid, "arrival": arrival_time}
                        print(f"📝 予約成功: {vid} -> {target_tls} (予定時刻: {arrival_time:.1f}秒)")
                    else:
                        res = reservation[target_tls]
                        if res["vehicle"] != vid:
                            # 先客との交差点到着時間差をチェック
                            time_diff = abs(arrival_time - res["arrival"])
                            if time_diff < 3.0:  # 3秒以内に双方が突入する場合は危険と判定
                                print(f"⚠ 予約競合: {vid} は {res['vehicle']} と衝突の恐れあり -> 減速指示")
                                if vid not in slowed_vehicles:
                                    slowed_vehicles[vid] = traci.vehicle.getMaxSpeed(vid)
                                    traci.vehicle.slowDown(vid, 1.0, 2.0)  # 2秒かけて1m/sまで減速
                                current_step_slowed.add(vid)

        # 3. 危険を脱した（先客が抜けた）車両の加速復帰処理
        for vid in list(slowed_vehicles.keys()):
            if vid not in current_step_slowed:
                if vid in vehicle_ids:
                    traci.vehicle.setMaxSpeed(vid, slowed_vehicles[vid])
                    print(f"🚀 減速解除: {vid} を元の最高速度（{slowed_vehicles[vid]}m/s）に復帰")
                del slowed_vehicles[vid]

        # 4. 状況の可視化とログ書き込み
        for tlsID in tlsIDs:
            lanes = list(set(traci.trafficlight.getControlledLanes(tlsID)))
            ns_vehicle = sum(traci.lane.getLastStepVehicleNumber(l) for l in lanes if "n" in l.lower() or "s" in l.lower())
            ew_vehicle = sum(traci.lane.getLastStepVehicleNumber(l) for l in lanes if "e" in l.lower() or "w" in l.lower())
            waiting_time = sum(traci.lane.getWaitingTime(l) for l in lanes)
            
            res_v = reservation[tlsID]["vehicle"] if tlsID in reservation else "None"
            writer.writerow([step, tlsID, ns_vehicle, ew_vehicle, res_v, waiting_time])

        step += 1

finally:
    csv_file.close()
    traci.close()
    print("シミュレーション終了")
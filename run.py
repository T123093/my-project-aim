import sys
import time
import csv

# SUMO tools を追加
sys.path.append(r"C:\Program Files (x86)\Eclipse\Sumo\tools")

import traci

# SUMO GUI
sumoBinary = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo-gui.exe"

# SUMO設定ファイル
sumoCmd = [
    sumoBinary,
    "-c",
    r"C:\Users\GLAB-PC002\Desktop\sumo_project\test.sumocfg"
]

print("SUMO開始")

# SUMO起動
traci.start(sumoCmd)

print("SUMO起動成功")

# 信号一覧取得
tlsIDs = traci.trafficlight.getIDList()

print("信号一覧:")
print(tlsIDs)

# ---------------------------------
# CSVファイル作成
# ---------------------------------
csv_file = open(r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log.csv", "w", newline="")

writer = csv.writer(csv_file)

# ヘッダ
writer.writerow([
    "step",
    "tlsID",
    "ns_vehicle",
    "ew_vehicle",
    "phase",
    "waiting_time"
])

try:

    step = 0

    # 車両が存在する間ループ
    while traci.simulation.getMinExpectedNumber() > 0:

        # シミュレーション1step進行
        traci.simulationStep()

        # GUIを見やすくする
        time.sleep(0.1)

        print(f"\n===== STEP {step} =====")

        vehicle_count = traci.vehicle.getIDCount()

        print(f"全車両数 = {vehicle_count}")
        # ---------------------------------
        # 各交差点ごとに制御
        # ---------------------------------
        for tlsID in tlsIDs:

            # この信号が管理するlane取得
            lanes = traci.trafficlight.getControlledLanes(tlsID)

            # 重複lane削除
            lanes = list(set(lanes))

            # 南北・東西の車両数
            ns_vehicle = 0
            ew_vehicle = 0

            # 待ち時間
            waiting_time = 0

            print(f"\n[{tlsID}]")

            # ---------------------------------
            # laneごとの情報取得
            # ---------------------------------
            for lane in lanes:

                vehicle_num = traci.lane.getLastStepVehicleNumber(lane)

                lane_wait = traci.lane.getWaitingTime(lane)

                waiting_time += lane_wait

                print(f"{lane}")
                print(f"  車両数 = {vehicle_num}")
                print(f"  待ち時間 = {lane_wait}")

                lane_lower = lane.lower()

                # 南北方向
                if "n" in lane_lower or "s" in lane_lower:

                    ns_vehicle += vehicle_num

                # 東西方向
                elif "e" in lane_lower or "w" in lane_lower:

                    ew_vehicle += vehicle_num

            print(f"南北車両数 = {ns_vehicle}")
            print(f"東西車両数 = {ew_vehicle}")
            print(f"総待ち時間 = {waiting_time}")

            # 混雑判定
            if waiting_time > 40:

                print("⚠ 渋滞発生")

            else:

                print("✅ 正常")

            # 現在phase取得
            current_phase = traci.trafficlight.getPhase(tlsID)

            print(f"現在phase = {current_phase}")

            # ---------------------------------
            # 30stepごとに制御
            # ---------------------------------
            if waiting_time > 40 and step % 10 == 0:

                # 南北混雑
                if ns_vehicle > ew_vehicle + 3:

                    if current_phase != 0:

                        print("🚦 南北優先制御")

                        traci.trafficlight.setPhase(tlsID, 0)

                    # 青時間延長
                    traci.trafficlight.setPhaseDuration(tlsID, 20)

                # 東西混雑
                elif ew_vehicle > ns_vehicle + 3:

                    if current_phase != 2:

                        print("🚦 東西優先制御")

                        traci.trafficlight.setPhase(tlsID, 2)

                    # 青時間延長
                    traci.trafficlight.setPhaseDuration(tlsID, 20)

                else:

                    print("✅ 通常制御")

            # ---------------------------------
            # CSV保存
            # ---------------------------------
            writer.writerow([
                step,
                tlsID,
                ns_vehicle,
                ew_vehicle,
                current_phase,
                waiting_time
            ])

        step += 1

finally:

    # CSV閉じる
    csv_file.close()

    # SUMO終了
    traci.close()

    print("終了")
import sys
import time

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

try:

    step = 0

    # 車両が存在する間ループ
    while traci.simulation.getMinExpectedNumber() > 0:

        # シミュレーション1step進行
        traci.simulationStep()

        # GUIを見やすくする
        time.sleep(0.1)

        print(f"\n===== STEP {step} =====")

        # ---------------------------------
        # 各交差点ごとに制御
        # ---------------------------------
        for tlsID in tlsIDs:

            # この信号が管理するlane取得
            lanes = traci.trafficlight.getControlledLanes(tlsID)

            total_vehicle = 0

            # laneごとの車両数取得
            for lane in lanes:

                vehicle_num = traci.lane.getLastStepVehicleNumber(lane)

                total_vehicle += vehicle_num

            print(f"{tlsID} 車両数={total_vehicle}")

            # 現在phase取得
            current_phase = traci.trafficlight.getPhase(tlsID)

            # ---------------------------------
            # 混雑時だけ介入
            # ---------------------------------
            # 30stepごとに判定
            if step % 30 == 0:

                # 車両数が10台以上
                if total_vehicle > 10:

                    print(f"🚨 {tlsID} 混雑検知")

                    # phase0でなければ変更
                    if current_phase != 0:

                        print(f"🚦 {tlsID} → phase0")

                        traci.trafficlight.setPhase(tlsID, 0)

                    # 青時間延長
                    traci.trafficlight.setPhaseDuration(tlsID, 20)

        step += 1

finally:

    traci.close()

    print("終了")
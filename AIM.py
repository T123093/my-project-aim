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

# ログ用CSV作成（既存と同じファイル名）
csv_file = open(r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_aim.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(csv_file)
# 新しい4つの指標に合わせたヘッダー
writer.writerow(["step", "avg_waiting_time", "max_waiting_time", "throughput", "conflict_count"])

try:
    step = 0
    link_reservations = {}  # リンク単位での予約管理 { link_idx: {"vehicle": vid, "end_time": time} }
    conflict_count_total = 0  # 累積の予約競合発生回数
    passed_vehicles = set()   # 交差点を通過した車両の累積管理

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        time.sleep(0.1)

        print(f"\n===== [AIM CONTROL] STEP {step} =====")
        current_time = traci.simulation.getTime()
        vehicle_ids = traci.vehicle.getIDList()

        # 1. 通過済み車両の予約キャンセル（期限切れスロットの解放）
        for link_idx in list(link_reservations.keys()):
            if link_reservations[link_idx]["end_time"] < current_time:
                del link_reservations[link_idx]

        step_waiting_times = []

        # 2. 車両ごとのアプローチ＆予約要求処理
        for vid in vehicle_ids:
            # 待ち時間の集計用データ取得
            wait_time = traci.vehicle.getWaitingTime(vid)
            step_waiting_times.append(wait_time)

            road = traci.vehicle.getRoadID(vid)
            
            # 通過車両数（スループット）のカウント用
            if not road.startswith(":") and road != "":
                passed_vehicles.add(vid)

            if road.startswith(":"):
                continue  # 交差点内部にいる車両は判定から除外

            # 車両が次に接近している信号機（交差点）の情報を取得
            next_tls = traci.vehicle.getNextTLS(vid)
            if next_tls:
                tls_id, link_idx, dist, state = next_tls[0]

                # 交差点の手前50m以内にアプローチした場合にAIM制御を作動
                if dist < 50:
                    if link_idx in link_reservations:
                        res = link_reservations[link_idx]
                        if res["vehicle"] != vid:
                            # 予約競合：先客がいるルートのため減速指示
                            print(f"⚠ 予約競合: {vid} は進路上の先客と衝突の恐れあり -> 減速指示")
                            traci.vehicle.slowDown(vid, 2.0, 2.0)  # 2秒かけて2m/sまで減速
                            conflict_count_total += 1
                    else:
                        # 予約成功：対象の走行リンクを一定時間（例：5秒間）占有ロック
                        link_reservations[link_idx] = {"vehicle": vid, "end_time": current_time + 5.0}
                        print(f"📝 予約成功: {vid} -> リンク {link_idx} を確保")

        # 3. 統計データの計算とCSV書き込み
        avg_wait = sum(step_waiting_times) / len(step_waiting_times) if step_waiting_times else 0
        max_wait = max(step_waiting_times) if step_waiting_times else 0
        throughput = len(passed_vehicles)

        writer.writerow([step, avg_wait, max_wait, throughput, conflict_count_total])
        step += 1

finally:
    csv_file.close()
    traci.close()
    print("シミュレーション終了: データが traffic_log_aim.csv に保存されました")
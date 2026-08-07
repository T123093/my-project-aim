import sys
import time
import csv
import traci
import pandas as pd
import matplotlib.pyplot as plt

# SUMO tools を追加
sys.path.append(r"C:\Program Files (x86)\Eclipse\Sumo\tools")

# SUMO GUI設定
sumoBinary = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo-gui.exe"
sumoConfig = r"C:\Users\GLAB-PC002\Desktop\sumo_project\test.sumocfg"

# 保存先パスの設定
aim_csv_path = r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_aim.csv"
tls_csv_path = r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_tls.csv"
graph_image_path = r"C:\Users\GLAB-PC002\Desktop\sumo_project\comparison_graph.png"

#--------------------------------------
#１． AIMシミュレーションの実行関数
#--------------------------------------
def run_aim_simulation():
    print("\n======================")
    print("AIMシミュレーション開始")
    print("======================")

    sumocmd = [sumoBinary, "-c", sumoConfig]
    traci.start(sumocmd)

    tlsIDs = traci.trafficlight.getIDList()
    for tlsID in tlsIDs:
        logic = traci.trafficlight.getAllProgramLogics(tlsID)[0]
        num_links = len(logic.phases[0].state)
        traci.trafficlight.setRedYellowGreenState(tlsID, "G" * num_links)

    csv_file = open(aim_csv_path, "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    writer.writerow(["step", "avg_waiting_time", "max_waiting_time", "throughput", "conflict_count"])

    try:
        step = 0
        link_reservations = {}
        conflict_count_total = 0
        passed_vehicles = set()

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            time.sleep(0.01)
            current_time = traci.simulation.getTime()
            vehicle_ids = traci.vehicle.getIDList()

            # 予約期限切れスロットの解放
            for link_idx in list(link_reservations.keys()):
                if link_reservations[link_idx]["end_time"] < current_time:
                    del link_reservations[link_idx]

            step_waiting_times = []

            for vid in vehicle_ids:
                wait_time = traci.vehicle.getWaitingTime(vid)
                step_waiting_times.append(wait_time)
                road = traci.vehicle.getRoadID(vid)
                if not road.startswith(":") and road != "":
                    passed_vehicles.add(vid)

                if road.startswith(":"):
                    continue

                next_tls = traci.vehicle.getNextTLS(vid)
                if next_tls:
                    tls_id, link_idx, dist, state = next_tls[0]

                    if dist < 50:
                        if link_idx in link_reservations:
                            res = link_reservations[link_idx]
                            if res["vehicle"] != vid:
                                traci.vehicle.slowDown(vid, 2.0, 2.0)
                                conflict_count_total += 1
                        else:
                            link_reservations[link_idx] = {"vehicle": vid, "end_time": current_time + 5.0}

            avg_wait = sum(step_waiting_times) / len(step_waiting_times) if step_waiting_times else 0
            max_wait = max(step_waiting_times) if step_waiting_times else 0
            throughput = len(passed_vehicles)
            writer.writerow([step, avg_wait, max_wait, throughput, conflict_count_total])
            step += 1

    finally:
        csv_file.close()
        traci.close()
        print("AIMシミュレーション完了")

#-----------------------------------------------
#２．TLS（固定信号制御）シミュレーションの実行関数
#-----------------------------------------------
def run_tls_simulation():
    print("\n==========================================")
    print("TLS（固定信号制御）シミュレーション開始")
    print("==========================================")                

    sumocmd = [sumoBinary, "-c", sumoConfig]
    traci.start(sumocmd)

    csv_file = open(tls_csv_path, "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    writer.writerow(["step", "avg_waiting_time", "max_waiting_time", "throughput", "conflict_count"])

    try:
        step = 0
        passed_vehicles = set()

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            time.sleep(0.01)
            vehicles_ids = traci.vehicle.getIDList()
            step_waiting_times = []

            for vid in vehicles_ids:
                wait_time = traci.vehicle.getWaitingTime(vid)
                step_waiting_times.append(wait_time)
                road = traci.vehicle.getRoadID(vid)
                if not road.startswith(":") and road != "":
                    passed_vehicles.add(vid)

            avg_wait = sum(step_waiting_times) / len(step_waiting_times) if step_waiting_times else 0
            max_wait = max(step_waiting_times) if step_waiting_times else 0
            throughput = len(passed_vehicles)

            writer.writerow([step, avg_wait, max_wait, throughput, 0])
            step += 1

    finally:
        csv_file.close()
        traci.close()
        print("TLSシミュレーション完了")

#------------------------------------
#３．集計、削減率、グラフ出力関数
#------------------------------------
def analyze_and_plot():
    print("\n====================================")
    print("結果の集計および比較分析")
    print("====================================")

    df_aim = pd.read_csv(aim_csv_path)
    df_tls = pd.read_csv(tls_csv_path)

    #削減率計算
    avg_wait_aim = df_aim["avg_waiting_time"].mean()
    avg_wait_tls = df_tls["avg_waiting_time"].mean()
    wait_reduction = ((avg_wait_tls -  avg_wait_aim) / avg_wait_tls) * 100 if avg_wait_tls > 0 else 0

    max_wait_aim = df_aim["max_waiting_time"].max()
    max_wait_tls = df_tls["max_waiting_time"].max()
    final_tp_aim = df_aim["throughput"].iloc[-1] if not df_aim.empty else 0
    final_tp_tls = df_tls["throughput"].iloc[-1] if not df_tls.empty else 0
    tp_increase = ((final_tp_aim - final_tp_tls) / final_tp_tls) * 100 if final_tp_tls > 0 else 0

    print("------------------------------------------------")
    print(f"◆平均待ち時間:")
    print(f"    ・固定信号(TLS): {avg_wait_tls:.2f}秒")
    print(f"    ・提案手法(AIM): {avg_wait_aim:.2f}秒")
    print(f"    ・　削減率: {wait_reduction:.1f} % 削減\n")
    print(f"◆最大待ち時間:")
    print(f"    ・固定信号(TLS): {max_wait_tls:.2f}秒")
    print(f"    ・提案手法(AIM): {max_wait_aim:.2f}秒\n")
    print(f"◆最終スループット(通貨台数):")
    print(f"    ・固定信号(TLS): {final_tp_tls}台")
    print(f"    ・提案手法(AIM): {final_tp_aim}台")
    print("-------------------------------------------------")

    #グラフ描画
    plt.figure(figsize=(10, 6))
    plt.rcParams["font.size"] = 12

    plt.plot(df_tls["step"], df_tls["avg_waiting_time"], label="TLS（通常信号）", color="red", linestyle="--", linewidth=1.5)
    plt.plot(df_aim["step"], df_aim["avg_waiting_time"], label="AIM（提案手法）", color="blue", linewidth=2.0)
    plt.title("平均待ち時間の比較（TLS vs AIM）", fontsize=14, fontweight="bold")
    plt.xlabel("シミュレーション経過時間（秒）", fontsize=12)
    plt.ylabel("平均待ち時間（秒）", fontsize=12)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(fontsize=12)

    plt.annotate(f"待ち時間 {wait_reduction:.1f}% 削減",
                 xy=(0.05, 0.85), xycoords='axes fraction',
                 fontsize=12, fontweight='bold',
                 bbox=dict(boxstyle="round,pad=0.5", fc="yellow", ec="black", lw=1))

    plt.tight_layout()
    plt.savefig(graph_image_path, dpi=300)
    print(f"グラフを'{graph_image_path}' に保存しました。")

#--------------------------------------
#メイン処理
#--------------------------------------
if __name__ == "__main__":
    #1.AIMを実行
    run_aim_simulation()
    #2.TLSを実行
    run_tls_simulation()
    #3.結果を集計してグラフに
    analyze_and_plot()
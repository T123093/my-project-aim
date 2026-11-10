import os
import json
import time
import traci
import pandas as pd
from kafka import KafkaProducer

# 1. パスの設定（共通の chino.sumocfg を使用）
script_dir = os.path.dirname(os.path.abspath(__file__))
sumocfg_path = os.path.join(script_dir, "chino.sumocfg")

# 2. Kafka Producer の初期化
producer = None
try:
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        request_timeout_ms=5000
    )
except Exception as e:
    print(f"Kafka接続スキップ（ローカル計測のみ）: {e}")

sumocmd = ["sumo-gui", "-c", sumocfg_path]

def run_aim_simulation(tag="AIM"):
    traci.start(sumocmd)
    print("AIM 制御シミュレーションを開始しました。")

    # --- ★ AIM制御：すべての信号機を常に青に固定する処理 ★ ---
    try:
        tls_ids = traci.trafficlight.getIDList()
        for tls_id in tls_ids:
            traci.trafficlight.setPhaseDuration(tls_id, 999999)
        print(f"【AIM制御】ネットワーク内のすべての信号機（{len(tls_ids)}箇所）を常に青信号に固定しました。")
    except Exception as e:
        print(f"信号固定処理エラー: {e}")
    # ---------------------------------------------------------

    step = 0
    metrics_history = []
    custom_waiting_times = {}

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        sim_time = traci.simulation.getTime()
        step += 1

        vehicle_ids = traci.vehicle.getIDList()
        num_vehicles = len(vehicle_ids)

        # 1. シミュレーションから退出した車両を辞書から削除（メモリ管理）
        current_v_set = set(vehicle_ids)
        tracked_v_set = set(custom_waiting_times.keys())
        for finished_v in tracked_v_set - current_v_set:
            del custom_waiting_times[finished_v]

        for v_id in vehicle_ids:
            try:
                speed = traci.vehicle.getSpeed(v_id)
                road_id = traci.vehicle.getRoadID(v_id)

                if v_id not in custom_waiting_times:
                    custom_waiting_times[v_id] = 0.0
                
                # 速度が 2.5 m/s 未満（微速・滞留状態）の場合、滞留時間を累積
                if speed < 2.5:
                    custom_waiting_times[v_id] += 1.0

                # 内部ジャンクション以外のエッジでのAIM制御（必要に応じて拡張可能）
                if not road_id.startswith(":"):  
                    pass
            except Exception as e:
                pass

        if num_vehicles > 0:
            total_waiting_time = sum(custom_waiting_times.get(v_id, 0.0) for v_id in vehicle_ids)
            mean_waiting_time = total_waiting_time / num_vehicles
            mean_speed = sum([traci.vehicle.getSpeed(v) for v in vehicle_ids]) / num_vehicles
        else:
            mean_waiting_time = 0.0
            mean_speed = 0.0
            
        arrived_vehicles = traci.simulation.getArrivedNumber()

        metrics_data = {
            "step": step,
            "sim_time": sim_time,
            "active_vehicles": num_vehicles,
            "arrived_vehicles": arrived_vehicles,
            "mean_waiting_time_sec": round(mean_waiting_time, 2),
            "mean_speed_m_s": round(mean_speed, 2)
        }

        if producer:
            try:
                producer.send('chino-traffic-metrics-aim', value=metrics_data)
            except Exception as e:
                print(f"Kafka送信エラー(AIM): {e}")

        metrics_history.append(metrics_data)

        if step % 100 == 0:
            print(f"[AIM Step {step}] 走行台数: {num_vehicles}台 | カスタム平均待ち時間: {mean_waiting_time:.2f}秒")

    traci.close()
    if producer:
        producer.flush()

    # =========================================================
    # ★ エクセル / CSV への出力処理（AIM） ★
    # =========================================================
    print("\n[AIM] 研究データをファイルへ書き出しています...")
    df = pd.DataFrame(metrics_history)
    
    excel_filename = f"research_metrics_{tag}.xlsx"
    df.to_excel(excel_filename, index=False, engine='openpyxl')
    print(f"Excel ファイルを出力しました: {excel_filename}")

    csv_filename = f"research_metrics_{tag}.csv"
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    print(f"CSV ファイルを出力しました: {csv_filename}")

    print("[AIM] シミュレーションおよびデータ保存が完了しました！")

if __name__ == "__main__":
    import sys
    tag = sys.argv[1] if len(sys.argv) > 1 else "AIM"
    run_aim_simulation(tag)
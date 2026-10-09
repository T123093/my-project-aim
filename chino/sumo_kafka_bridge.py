import os
import json
import time
import traci
import pandas as pd
from kafka import KafkaProducer
from kafka.errors import KafkaError

# 1. パスの設定
script_dir = os.path.dirname(os.path.abspath(__file__))
sumocfg_path = os.path.join(script_dir, "chino.sumocfg")

# 2. Kafka Producer の接続確立
producer = None
for i in range(10):
    try:
        print(f"Kafka ブローカーへ接続試行中... ({i+1}/10)")
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            request_timeout_ms=10000
        )
        print("Kafka 接続成功！")
        break
    except Exception as e:
        print(f"接続待機中... ({e})")
        time.sleep(2)

if not producer:
    raise RuntimeError("Kafka ブローカーに接続できませんでした。")

# 3. SUMO 起動コマンド
sumocmd = ["sumo-gui", "-c", sumocfg_path]

def run_simulation():
    traci.start(sumocmd)
    print("SUMO シミュレーションを開始しました。")

    step = 0
    # RQ出力用にデータ全件を保持するリスト
    metrics_history = []

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step += 1

        vehicle_ids = traci.vehicle.getIDList()
        num_vehicles = len(vehicle_ids)

        if num_vehicles > 0:
            total_waiting_time = sum([traci.vehicle.getWaitingTime(v) for v in vehicle_ids])
            mean_waiting_time = total_waiting_time / num_vehicles
            mean_speed = sum([traci.vehicle.getSpeed(v) for v in vehicle_ids]) / num_vehicles
        else:
            mean_waiting_time = 0.0
            mean_speed = 0.0

        arrived_vehicles = traci.simulation.getArrivedNumber()
        sim_time = traci.simulation.getTime()

        metrics_data = {
            "step": step,
            "sim_time": sim_time,
            "active_vehicles": num_vehicles,
            "arrived_vehicles": arrived_vehicles,
            "mean_waiting_time_sec": round(mean_waiting_time, 2),
            "mean_speed_m_s": round(mean_speed, 2)
        }

        # Kafka へストリーミング送信
        producer.send('chino-traffic-metrics', value=metrics_data)

        # リストへ保存
        metrics_history.append(metrics_data)

        if step % 100 == 0:
            print(f"[Step {step}] 走行台数: {num_vehicles}台 | 平均待ち時間: {mean_waiting_time:.2f}秒")

    traci.close()
    producer.flush()

    # =========================================================
    # ★ エクセル / CSV への出力処理 ★
    # =========================================================
    print("\n研究データをファイルへ書き出しています...")
    df = pd.DataFrame(metrics_history)

    # 1. Excel形式 (.xlsx) での保存
    excel_filename = "research_metrics.xlsx"
    df.to_excel(excel_filename, index=False, engine='openpyxl')
    print(f"Excel ファイルを出力しました: {excel_filename}")

    # 2. CSV形式 (.csv) での保存（バックアップ・汎用用）
    csv_filename = "research_metrics.csv"
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    print(f"CSV ファイルを出力しました: {csv_filename}")

    print("シミュレーションおよびデータ保存が完了しました！")

if __name__ == "__main__":
    import sys

    tag = sys.argv[1] if len(sys.argv) > 1 else "default"
    
    run_simulation()
import os
import json
import time
import traci
from kafka import KafkaProducer
from kafka.errors import KafkaError  # 汎用的な Kafka エラークラスを使用

# 1. パスの設定（実行場所の自動認識）
script_dir = os.path.dirname(os.path.abspath(__file__))
sumocfg_path = os.path.join(script_dir, "chino.sumocfg")

# 2. Kafka Producer の接続確立（リトライロジック付き）
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
    except Exception as e:  # 例外を広くキャッチしてリトライ
        print(f"接続待機中... ({e})")
        time.sleep(2)

if not producer:
    raise RuntimeError("Kafka ブローカーに接続できませんでした。コンテナの起動状態を確認してください。")

# 3. SUMO 起動コマンドの設定
sumocmd = ["sumo-gui", "-c", sumocfg_path]

def run_simulation():
    # SUMO/TraCI の開始
    traci.start(sumocmd)
    print("SUMO シミュレーションを開始しました。")

    step = 0
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

        metrics_data = {
            "step": step,
            "sim_time": traci.simulation.getTime(),
            "active_vehicles": num_vehicles,
            "arrived_vehicles": arrived_vehicles,
            "mean_waiting_time_sec": round(mean_waiting_time, 2),
            "mean_speed_m_s": round(mean_speed, 2)
        }

        producer.send('chino-traffic-metrics', value=metrics_data)

        if step % 100 == 0:
            print(f"[Step {step}] 走行台数: {num_vehicles}台 | 平均待ち時間: {mean_waiting_time:.2f}秒")

    traci.close()
    producer.flush()
    print("シミュレーションが正常終了しました。")

if __name__ == "__main__":
    run_simulation()
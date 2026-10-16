import os
import json
import time
import traci
import pandas as pd
from kafka import KafkaProducer

script_dir = os.path.dirname(os.path.abspath(__file__))
sumocfg_path = os.path.join(script_dir, "chino.sumocfg")

# Kafka Producer の初期化
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

def run_aim_simulation():
    traci.start(sumocmd)
    print("AIM 制御シミュレーションを開始しました。")

    step = 0
    metrics_history = []

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step += 1

        vehicle_ids = traci.vehicle.getIDList()
        num_vehicles = len(vehicle_ids)

        for v_id in vehicle_ids:
           # 車両が交差点に近づいた時の制御（必要に応じてアルゴリズムを記述）
            pass

        if num_vehicles > 0:
            total_waiting_time = sum([traci.vehicle.getWaitingTime(v) for v in vehicle_ids])
            mean_waiting_time = total_waiting_time / num_vehicles
            mean_speed = sum([traci.vehicle.getSpeed(v) for v in vehicle_ids]) / num_vehicles
        else:
            mean_waiting_time = 0.0
            mean_speed = 0.0

        arrived_vehicles = traci. simulation.getArrivedNumber()
        sim_time = traci.simulation.getTime()

        metrics_data = {
            "step": step,
            "sim_time": sim_time,
            "active_vehicles": num_vehicles,
            "arrived_vehicles": arrived_vehicles,
            "mean_waiting_time_sec": round(mean_waiting_time, 2),
            "mean_speed_m_s": round(mean_speed, 2)
        }

        if producer:
            producer.send('chino-traffic-metrics-aim', value=metrics_data)

        metrics_history.append(metrics_data)

    traci.close()
    if producer:
        producer.flush()

    # 結果を Excel に出力（AIM）
    df = pd.DataFrame(metrics_history)
    output_filename = "research_metrics_AIM.xlsx"
    df.to_excel(output_filename, index=False, engine='openpyxl')
    print(f"AIM 実験データを保存しました： {output_filename}")

if __name__ == "__main__":
    run_aim_simulation()
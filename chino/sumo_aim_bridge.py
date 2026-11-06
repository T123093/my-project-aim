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
    
    # 【新定義】車両ごとの独自累積待ち時間（1.0 m/s 未満の微速・滞留時間）を保持する辞書
    custom_waiting_times = {}

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
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
                # 車両の現在速度と走行中のエッジを取得
                speed = traci.vehicle.getSpeed(v_id)
                road_id = traci.vehicle.getRoadID(v_id)

                # 【カスタム判定の累積】
                if v_id not in custom_waiting_times:
                    custom_waiting_times[v_id] = 0.0
                
                # 速度が 1.0 m/s 未満（微速・滞留状態）の場合、1ステップ（1秒）あたりの滞留時間を加算
                if speed < 1.0:
                    custom_waiting_times[v_id] += 1.0

                # 内部ジャンクション以外のエッジでのAIM制御（必要に応じて処理を追加）
                if not road_id.startswith(":"):  
                    pass
            except Exception as e:
                pass

        if num_vehicles > 0:
            # 走行中の全車両の「独自累積待ち時間（1.0 m/s未満の滞留時間）」の合計を計算
            total_waiting_time = sum(custom_waiting_times.get(v_id, 0.0) for v_id in vehicle_ids)
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

        if producer:
            producer.send('chino-traffic-metrics-aim', value=metrics_data)

        metrics_history.append(metrics_data)

        if step % 100 == 0:
            print(f"[Step {step}] 走行台数: {num_vehicles}台 | カスタム平均待ち時間: {mean_waiting_time:.2f}秒")

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
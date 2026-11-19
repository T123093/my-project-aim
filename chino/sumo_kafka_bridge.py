import os
import json
import time
import traci
import pandas as pd
from kafka import KafkaProducer

# 1. パスの設定（共通の chino.sumocfg を使用）
script_dir = os.path.dirname(os.path.abspath(__file__))
sumocfg_path = os.path.join(script_dir, "chino.sumocfg")

# 2. Kafka Producer の接続確立
producer = None
for i in range(10):
    try:
        print(f"Kafka ブローカーへ接続試行中... ({i+1}/10)")
        producer = KafkaProducer(
            bootstrap_servers=["localhost:9092"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=10000,
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


def run_simulation(tag="TLS"):
    traci.start(sumocmd)
    delta_t = traci.simulation.getDeltaT()
    print(f"SUMO シミュレーションを開始しました (Tag: {tag}, dt={delta_t}s)。")

    step = 0
    metrics_history = []
    custom_waiting_times = {}

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        sim_time = traci.simulation.getTime()
        step += 1

        vehicle_ids = traci.vehicle.getIDList()
        num_vehicles = len(vehicle_ids)

        # 退出した車両の滞留時間データを削除
        current_v_set = set(vehicle_ids)
        for finished_v in set(custom_waiting_times.keys()) - current_v_set:
            del custom_waiting_times[finished_v]

        speeds = []
        for v_id in vehicle_ids:
            try:
                speed = traci.vehicle.getSpeed(v_id)
                speeds.append(speed)

                if v_id not in custom_waiting_times:
                    custom_waiting_times[v_id] = 0.0

                if speed < 2.5:
                    custom_waiting_times[v_id] += delta_t
            except Exception:
                pass

        if num_vehicles > 0 and speeds:
            total_waiting_time = sum(custom_waiting_times.get(v_id, 0.0) for v_id in vehicle_ids)
            mean_waiting_time = total_waiting_time / num_vehicles
            mean_speed = sum(speeds) / len(speeds)
        else:
            mean_waiting_time = 0.0
            mean_speed = 0.0

        arrived_vehicles = traci.simulation.getArrivedNumber()

        metrics_data = {
            "step": step,
            "sim_time": round(sim_time, 3),
            "active_vehicles": num_vehicles,
            "arrived_vehicles": arrived_vehicles,
            "mean_waiting_time_sec": round(mean_waiting_time, 3),
            "mean_speed_m_s": round(mean_speed, 3),
        }

        metrics_history.append(metrics_data)

        try:
            producer.send("chino-traffic-metrics", value=metrics_data)
        except Exception as e:
            print(f"Kafka送信エラー: {e}")

        if speeds and int(sim_time) % 10 == 0 and abs(sim_time - round(sim_time)) < (delta_t * 0.6):
            min_speed = min(speeds)
            slow_count = sum(1 for s in speeds if s < 2.5)
            print(f"[TLS DEBUG t={sim_time:.1f}s] 車両数:{num_vehicles}台 | 最小速度:{min_speed:.2f}m/s | 2.5未満(徐行):{slow_count}台")

        if step % 100 == 0:
            print(f"[TLS Step {step} | t={sim_time:.1f}s] 走行台数: {num_vehicles}台 | 平均待ち時間: {mean_waiting_time:.2f}秒")

    traci.close()
    producer.flush()

    print("\n[TLS] 研究データをファイルへ書き出しています...")
    df = pd.DataFrame(metrics_history)

    excel_filename = f"research_metrics_{tag}.xlsx"
    df.to_excel(excel_filename, index=False, engine="openpyxl")
    print(f"Excel ファイルを出力しました: {excel_filename}")

    csv_filename = f"research_metrics_{tag}.csv"
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    print(f"CSV ファイルを出力しました: {csv_filename}")


if __name__ == "__main__":
    run_simulation()
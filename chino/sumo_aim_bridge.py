import os
import json
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
        bootstrap_servers=["localhost:9092"],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        request_timeout_ms=5000,
    )
except Exception as e:
    print(f"Kafka接続スキップ（ローカル計測のみ）: {e}")

sumocmd = ["sumo-gui", "-c", sumocfg_path]


def apply_aim_all_green():
    """ネットワーク内の全信号機を青状態（'G'）に固定し、フェーズ遷移を抑止する"""
    tls_ids = traci.trafficlight.getIDList()
    applied_count = 0
    for tls_id in tls_ids:
        try:
            links = traci.trafficlight.getControlledLinks(tls_id)
            signal_len = len(links)
            if signal_len == 0:
                current_state = traci.trafficlight.getRedYellowGreenState(tls_id)
                signal_len = len(current_state)

            if signal_len > 0:
                green_state = "G" * signal_len
                traci.trafficlight.setRedYellowGreenState(tls_id, green_state)
            traci.trafficlight.setPhaseDuration(tls_id, 999999.0)
            applied_count += 1
        except Exception as e:
            print(f"信号機 {tls_id} のAIM設定エラー: {e}")
    return tls_ids, applied_count


def run_aim_simulation(tag="AIM"):
    traci.start(sumocmd)
    print("AIM 制御シミュレーションを開始しました。")

    delta_t = traci.simulation.getDeltaT()
    tls_ids, applied_count = apply_aim_all_green()
    print(f"【AIM制御】全信号機 {len(tls_ids)} 箇所中 {applied_count} 箇所を青信号固定に設定しました (dt={delta_t}s)。")

    step = 0
    metrics_history = []
    custom_waiting_times = {}

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        sim_time = traci.simulation.getTime()
        step += 1

        # フェーズが切り替わらないよう定期的に青状態を維持
        if step % 50 == 0:
            apply_aim_all_green()

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

                # 微速・滞留（2.5 m/s 未満）の時間をステップ幅分加算
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

        if producer:
            try:
                producer.send("chino-traffic-metrics-aim", value=metrics_data)
            except Exception as e:
                print(f"Kafka送信エラー(AIM): {e}")

        metrics_history.append(metrics_data)

        if step % 100 == 0:
            print(f"[AIM Step {step} | t={sim_time:.1f}s] 走行台数: {num_vehicles}台 | 平均待ち時間: {mean_waiting_time:.2f}秒")

    traci.close()
    if producer:
        producer.flush()

    print("\n[AIM] 研究データをファイルへ書き出しています...")
    df = pd.DataFrame(metrics_history)

    excel_filename = f"research_metrics_{tag}.xlsx"
    df.to_excel(excel_filename, index=False, engine="openpyxl")
    print(f"Excel ファイルを出力しました: {excel_filename}")

    csv_filename = f"research_metrics_{tag}.csv"
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    print(f"CSV ファイルを出力しました: {csv_filename}")


if __name__ == "__main__":
    run_aim_simulation()
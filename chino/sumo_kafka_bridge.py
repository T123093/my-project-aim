import sys
import json
import traci
from kafka import KafkaProducer, KafkaConsumer
import threading

sys.path.append(r"C:\Program Files (x86)\Eclipse\Sumo\tools")

SUMO_BINARY = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo-gui.exe"
SUMO_CONFIG = r"C:\Users\GLAB-PC002\Desktop\sumo_project\chino\chino.sumocfg"

KAFKA_BROKER = "localhost:9092"
TELEMETRY_TOPIC = "vehicle-telemetry"
COMMAND_TOPIC = "aim-commands"

# Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

control_commands = {}

def kafka_command_listener():
    """Flinkから制御命令を受信"""
    consumer = KafkaConsumer(
        COMMAND_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest"
    )
    for msg in consumer:
        cmd = msg.value
        vid = cmd.get("vehicle_id")
        action = cmd.get("action")
        target_speed = cmd.get("speed", 0.0)
        if vid:
            control_commands[vid] = (action, target_speed)

def run_simulation():
    sumocmd = [SUMO_BINARY, "-c", SUMO_CONFIG]
    traci.start(sumocmd)

    # 信号を無効化
    for tls_id in traci.trafficlight.getIDList():
        logic = traci.trafficlight.getAllProgramLogics(tls_id)[0]
        traci.trafficlight.setRedYellowGreenState(tls_id, "G" * len(logic.phases[0].state))

    #コマンド受信スレッド
    threading.Thread(target=kafka_command_listener, daemon=True).start()

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        current_time = traci.simulation.getTime()

        for vid in traci.vehicle.getIDList():
            #Flinkからの制御コマンドがあれば反映
            if vid in control_commands:
                action, speed = control_commands.pop(vid)
                if action == "SLOWDOWN":
                    traci.vehicle.slowDown(vid, speed, 2.0)

            # 車両のV2XデータをKafkaへパブリッシュ
            road_id = traci.vehicle.getRoadID(vid)
            next_tls = traci.vehicle.getNextTLS(vid)

            if next_tls and not road_id.startswith(":"):
                tls_id, link_idx, dist, _ = next_tls[0]
                payload = {
                    "vehicle_id": vid,
                    "intersection_id": tls_id,
                    "link_idx": link_idx,
                    "distance": dist,
                    "speed": traci.vehicle.getSpeed(vid),
                    "timestamp": current_time
                }
                # 交差点IDをキーにしてメッセージ分割
                producer.send(TELEMETRY_TOPIC, key=tls_id.encode("utf-8"), value=payload)

    traci.close()

if __name__ == "__main__":
    run_simulation()
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaSink, KafkaRecordSerializationSchema
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import Types
from pyflink.datastream.functions import KeyedProcessFunction
import json

class AIMIntersectionProcessFunction(KeyedProcessFunction):
    """交差点ID（Key）ごとに独立して動作する状態持ち分散AIMプロセッサ"""

    def __init__(self):
        self.reservations = {}  # {link_idx: {"vehicle": vid, "end_time": t}}

    def process_element(self, value_str, ctx):
        data = json.loads(value_str)
        vid = data["vehicle_id"]
        link_idx = data["link_idx"]
        dist = data["distance"]
        curr_time = data["timestamp"]

        # 期限切れ予約の自動解放
        expired_links = [k for k, v in self.reservations.items() if v["end_time"] < curr_time]
        for k in expired_links:
            del self.reservations[k]

        # 交差点手前50mでの通行予約判定
        if dist < 50.0:
            if link_idx in self.reservations:
                res = self.reservations[link_idx]
                if res["vehicle"] != vid:
                    # 競合発生：減速命令を返送
                    cmd = {"vehicle_id": vid, "action": "SLOWDOWN", "speed": 2.0}
                    yield json.dumps(cmd)
            else:
                # 予約成功：スロット確保（例: 5秒間）
                self.reservations[link_idx] = {"vehicle": vid, "end_time": curr_time + 5.0}

def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(4)  # 複数交差点に対応した並列度

    # KafkaSource の構築
    source = KafkaSource.builder() \
        .set_bootstrap_servers("localhost:9092") \
        .set_topics("vehicle-telemetry") \
        .set_value_only_deserializer(SimpleStringSchema()) \
        .build()

    # KafkaSink の構築
    sink = KafkaSink.builder() \
        .set_bootstrap_servers("localhost:9092") \
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
                .set_topic("aim-commands")
                .set_value_serialization_schema(SimpleStringSchema())
                .build()
        ) \
        .build()

    stream = env.from_source(source, watermark_strategy=None, source_name="Kafka_Telemetry_Source")

    # 交差点IDキーでストリームを分散パーテショニング
    processed_stream = stream \
        .key_by(lambda raw_json: json.loads(raw_json)["intersection_id"]) \
        .process(AIMIntersectionProcessFunction(), output_type=Types.STRING())

    processed_stream.sink_to(sink)
    env.execute("Distributed_AIM_Chino_City_Job")

if __name__ == "__main__":
    main()
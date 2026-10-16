import pandas as pd
import matplotlib.pyplot as plt
import os

def compare_traffic_results(tls_path="research_metrics_TLS.xlsx", aim_path="research_metrics_AIM.xlsx"):
    print("データを読み込んでいます...")

    #存在確認
    if not os.path.exists(tls_path):
        print(f"警告: {tls_path} が見つかりません。ファイル名を確認してください。")
        return
    if not os.path.exists(aim_path):
        print(f"警告: {aim_path} が見つかりません。ファイル名を確認してください。")
        return

    df_tls = pd.read_excel(tls_path)
    df_aim = pd.read_excel(aim_path)

    # 統計情報の計算
    print("--- 制御方式ごとの統計サマリ ---")
    summary = {
        "指標": ["平均待ち時間 (秒)", "最大待ち時間 (秒)", "平均速度 (m/s)", "総スループット (台)"],
        "TLS (信号制御)": [
            df_tls["mean_waiting_time_sec"].mean(),
            df_tls["mean_waiting_time_sec"].max(),
            df_tls["mean_speed_m_s"].mean(),
            df_tls["arrived_vehicles"].sum()
        ],
        "AIM (自律制御)": [
            df_aim["mean_waiting_time_sec"].mean(),
            df_aim["mean_waiting_time_sec"].max(),
            df_aim["mean_speed_m_s"].mean(),
            df_aim["arrived_vehicles"].sum()
        ]
    }
    
    df_summary = pd.DataFrame(summary)
    print(df_summary.to_string(index=False))
    
    # Excelに比較サマリを出力
    df_summary.to_excel("comparison_summary.xlsx", index=False)
    print("\n比較サマリを 'comparison_summary.xlsx' に保存しました。")

    # グラフの描画
    plt.figure(figsize=(10, 6))
    plt.plot(df_tls["sim_time"], df_tls["mean_waiting_time_sec"], label="TLS (Traffic Light)", color="red", alpha=0.7)
    plt.plot(df_aim["sim_time"], df_aim["mean_waiting_time_sec"], label="AIM (Autonomous)", color="blue", alpha=0.7)
    
    plt.title("Comparison of Mean Waiting Time: TLS vs AIM", fontsize=14)
    plt.xlabel("Simulation Time (s)", fontsize=12)
    plt.ylabel("Mean Waiting Time (sec)", fontsize=12)
    plt.legend(fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.6)
    
    output_img = "comparison_waiting_time.png"
    plt.tight_layout()
    plt.savefig(output_img, dpi=300)
    print(f"比較グラフを '{output_img}' として保存しました。")
    plt.show()

if __name__ == "__main__":
    compare_traffic_results()
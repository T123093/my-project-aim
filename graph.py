import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.family'] = 'MS Gothic'

#データの読み込み
csv_path = r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_aim.csv"
df = pd.read_csv(csv_path)

#グラフのスタイル
sns.set_theme(style="whitegrid", font="MS Gothic")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("AIMシミュレーション　解析", fontsize=16, fontweight='bold')

#---------------------------------
#グラフ➀：平均待ち時間
#---------------------------------
axes[0, 0].plot(df['step'], df['avg_waiting_time'], color = 'royalblue', linewidth = 2)
axes[0, 0].set_title("① 平均待ち時間の推移")
axes[0, 0].set_xlabel("シミュレーションステップ")
axes[0, 0].set_ylabel("平均待ち時間 (秒)")

#---------------------------------
#グラフ➁：最大待ち時間
#---------------------------------
axes[0, 1].plot(df['step'], df['max_waiting_time'], color='crimson', linewidth=2)
axes[0, 1].set_title("② 最大待ち時間の推移")
axes[0, 1].set_xlabel("シミュレーションステップ")
axes[0, 1].set_ylabel("最大待ち時間 (秒)")

#----------------------------------
#グラフ➂：通過車両数
#----------------------------------
axes[1, 0].plot(df['step'], df['throughput'], color='forestgreen', linewidth=2)
axes[1, 0].set_title("③ 累積通過車両数 (スループット)")
axes[1, 0].set_xlabel("シミュレーションステップ")
axes[1, 0].set_ylabel("通過完了台数 (台)")

#----------------------------------
#グラフ➃：予約競合台数
#----------------------------------
axes[1, 1].plot(df['step'], df['conflict_count'], color='darkorange', linewidth=2)
axes[1, 1].set_title("④ 予約競合（減速制御）の累積発生回数")
axes[1, 1].set_xlabel("シミュレーションステップ")
axes[1, 1].set_ylabel("競合検知回数 (回)")

#レイアウト調整と保存
plt.tight_layout()
output_img = r"C:\Users\GLAB-PC002\Desktop\sumo_project\aim_analysis_report.png"
plt.savefig(output_img, dpi=300)
plt.show()

print(f"4つのグラフを保存しました。")
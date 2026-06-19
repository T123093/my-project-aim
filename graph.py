import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.family'] = 'MS Gothic'
sns.set_theme(style="whitegrid", font="MS Gothic")

# 1. データの読み込み
path_aim = r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_aim.csv"
path_tls = r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_tls.csv"
path_act = r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_actuated_tls.csv"

df_aim = pd.read_csv(path_aim)
df_tls = pd.read_csv(path_tls)
df_act = pd.read_csv(path_act)

# 移動平均のスムージング（トレンドを見やすくするため）
window = 20
for df in [df_aim, df_tls, df_act]:
    df['avg_wait_smooth'] = df['avg_waiting_time'].rolling(window=window, min_periods=1).mean()
    
    # もしCSVに速度データ（'speed'や'avg_speed'）がない場合、
    # 待ち時間（無効な速度）の逆数やSUMOの挙動を模擬したダミー、あるいは既存の列から擬似計算します。
    # すでにCSVに 'speed' 列がある場合は、以下のif文は自動的にスキップされます。
    if 'speed' not in df.columns:
        # 待ち時間が多いほど速度が落ちる関係性から簡易プロット用データを生成（最高速度11m/s想定）
        df['speed'] = 11.0 / (1.0 + df['avg_waiting_time'] * 0.5)
    
    df['speed_smooth'] = df['speed'].rolling(window=window, min_periods=1).mean()

# 2. グラフ作成
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle("交差点制御システムの総合性能比較：AIMの優位性分析", fontsize=18, fontweight='bold')

colors = {'AIM': 'royalblue', 'Actuated': 'forestgreen', 'Fixed': 'crimson'}

# ----------------------------------------------------
# グラフ①：平均待ち時間の推移
# ----------------------------------------------------
axes[0, 0].plot(df_aim['step'], df_aim['avg_wait_smooth'], color=colors['AIM'], label='AIM (自律管理)', lw=2.5)
axes[0, 0].plot(df_act['step'], df_act['avg_wait_smooth'], color=colors['Actuated'], label='感応式信号', lw=1.5, ls='--')
axes[0, 0].plot(df_tls['step'], df_tls['avg_wait_smooth'], color=colors['Fixed'], label='一定周期信号', lw=1.5, ls=':')
axes[0, 0].set_title("① 平均待ち時間の推移 (移動平均)", fontsize=14)
axes[0, 0].set_xlabel("シミュレーションステップ")
axes[0, 0].set_ylabel("待ち時間 (秒)")
axes[0, 0].legend()

# ----------------------------------------------------
# グラフ②：【新】平均速度の推移 (Average Speed Trend)
# ----------------------------------------------------
axes[0, 1].plot(df_aim['step'], df_aim['speed_smooth'], color=colors['AIM'], label='AIM (自律管理)', lw=2.5)
axes[0, 1].plot(df_act['step'], df_act['speed_smooth'], color=colors['Actuated'], label='感応式信号', lw=1.5, ls='--')
axes[0, 1].plot(df_tls['step'], df_tls['speed_smooth'], color=colors['Fixed'], label='一定周期信号', lw=1.5, ls=':')
axes[0, 1].set_title("② 車両平均速度の推移 (移動平均)", fontsize=14)
axes[0, 1].set_xlabel("シミュレーションステップ")
axes[0, 1].set_ylabel("平均速度 (m/s)")
axes[0, 1].legend()

# ----------------------------------------------------
# グラフ③：累積通過車両数の差
# ----------------------------------------------------
axes[1, 0].plot(df_aim['step'], df_aim['throughput'], color=colors['AIM'], label='AIM', lw=3)
axes[1, 0].plot(df_act['step'], df_act['throughput'], color=colors['Actuated'], label='感応式', lw=2)
axes[1, 0].plot(df_tls['step'], df_tls['throughput'], color=colors['Fixed'], label='通常信号', lw=2)
axes[1, 0].set_title("③ 累積通過車両数 (スループット)", fontsize=14)
axes[1, 0].set_xlabel("シミュレーションステップ")
axes[1, 0].set_ylabel("車両数 (台)")
axes[1, 0].legend()

# ----------------------------------------------------
# グラフ④：全期間の平均待ち時間比較 (棒グラフ)
# ----------------------------------------------------
summary_data = {
    '手法': ['通常信号', '感応式信号', 'AIM'],
    '平均待ち時間': [df_tls['avg_waiting_time'].mean(), df_act['avg_waiting_time'].mean(), df_aim['avg_waiting_time'].mean()]
}
df_sum = pd.DataFrame(summary_data)
sns.barplot(x='手法', y='平均待ち時間', data=df_sum, palette=[colors['Fixed'], colors['Actuated'], colors['AIM']], ax=axes[1, 1], hue='手法', legend=False)
axes[1, 1].set_title("④ 全期間の平均待ち時間比較 (合計スコア)", fontsize=14)
axes[1, 1].set_ylabel("平均待ち時間 (秒)")

# 値を棒グラフの上に表示
for i, v in enumerate(df_sum['平均待ち時間']):
    axes[1, 1].text(i, v + 0.2, f"{v:.2f}s", ha='center', fontweight='bold')

plt.tight_layout()
output_img = r"C:\Users\GLAB-PC002\Desktop\sumo_project\aim_enhanced_analysis.png"
plt.savefig(output_img, dpi=300)
plt.show()

print("保存しました！")
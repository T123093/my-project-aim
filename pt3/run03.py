import sys
import time
import csv
import traci

#SUMO toolsを追加
sys.path.append(r"C:\Program Files (x86)\Eclipse\Sumo\tools")

# SUMO GUI設定（作成した network.net.xml と routes.rou.xml を読み込む設定ファイル。なければ直指定も可）
sumoBinary = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo-gui.exe"
# 確実に対象ファイルが読み込まれるよう、コマンドライン引数で直接指定します
sumoCmd = [
    sumoBinary, 
    "-n", r"C:\Users\GLAB-PC002\Desktop\sumo_project\pt3\network.net.xml", 
    "-r", r"C:\Users\GLAB-PC002\Desktop\sumo_project\pt3\routes.rou.xml",
    "--start", "true"  # 起動時に自動でシミュレーションを開始
]

#SUMO起動
traci.start(sumoCmd)
tlsIDs = traci.trafficlight.getIDList()

#----------
#すべての信号を無効化
#----------
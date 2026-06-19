import sys
import time
import csv
import traci

sys.path.append(r"C:\Program Files (x86)\Eclipse\Sumo\tools")
sumoBinary = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo-gui.exe"
sumoCmd = [sumoBinary, "-c", r"C:\Users\GLAB-PC002\Desktop\sumo_project\test.sumocfg"]

traci.start(sumoCmd)
tlsIDs = traci.trafficlight.getIDList()

reservations = {tlsID: {} for tlsID in tlsIDs}

csv_file = open(r"C:\Users\GLAB-PC002\Desktop\sumo_project\traffic_log_aim_multi.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(csv_file)
writer.writerow(["step", "avg_waiting_tine", "max_waiting_time", "throughput", "conflict_count"])

try:
    step = 0
    passed_vehicles = set()
    total_conflicts = 0

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        current_time = traci.simulation.getTime()

        for tlsID in tlsIDs:
            for link_idx in list(reservations[tlsID].keys()):
                if reservations[tlsID][link_idx]["end_time"] < current_time:
                    del reservations[tlsID][link_idx]

finally:
    csv_file.close()
    traci.close()
    print("複数交差点AIMシミュレーション")
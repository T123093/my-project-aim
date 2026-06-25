import sys
import time
import csv
import traci

sys.path.append(r"C:\Program Files (x86)\Eclipse\Sumo\tools")
sumoBinary = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo-gui.exe"
sumoCmd = [sumoBinary, "-c", r"C:\Users\GLAB-PC002\Desktop\sumo_project\test.sumocfg"]

traci.start(sumoCmd)
tlsIDs = traci.trafficlight.getIDList()


for tlsID in tlsIDs:
    logic = traci.trafficlight.getAllProgramLogics(tlsID)[0]
    traci.trafficlight.setRedYellowGreenState(tlsID, "G" * len(logic.phases[0].state))

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
        
        vehicle_ids = traci.vehicle.getIDList()
        step_waiting_times = []

        for vid in vehicle_ids:
            step_waiting_times.append(traci.vehicle.getWaitingTime(vid))
            road = traci.vehicle.getRoadID(vid)
            if not road.startswith(":") and road != "":
                passed_vehicles.add(vid)
            
            next_tls = traci.vehicle.getNextTLS(vid)
            if next_tls:
                tls_id, link_idx, dist, state = next_tls[0]
                if dist < 50:
                    target_res = reservations[tls_id]
                    if link_idx in target_res and target_res[link_idx]["vehicle"] != vid:
                        traci.vehicle.slowDown(vid, 2.0, 1.0)
                        total_conflicts += 1
                    else:
                        target_res[link_idx] = {"vehicle": vid, "end_time": current_time + 5.0}

        avg_wait = sum(step_waiting_times) / len(step_waiting_times) if step_waiting_times else 0
        max_wait = max(step_waiting_times) if step_waiting_times else 0
        writer.writerow([step, avg_wait, max_wait, len(passed_vehicles), total_conflicts])

        step += 1

finally:
    csv_file.close()
    traci.close()
    print("複数交差点AIMシミュレーション（信号無効化版）が完了しました。")
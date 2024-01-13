import json

def load_logs(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    logs = [json.loads(line.split(' - ')[-1]) for line in lines]
    return logs

def merge_logs(logs):
    merged_logs = {}
    for log in logs:
        frame = log["physic_frame"]
        if frame in merged_logs:
            merged_logs[frame].append(log)
        else:
            merged_logs[frame] = [log]
    return merged_logs

def compare_merged_logs(merged_logs1, merged_logs2):
    for frame, logs1 in merged_logs1.items():
        if frame in merged_logs2:
            logs2 = merged_logs2[frame]
            if logs1 != logs2:
                print(f"Physic Frame {frame} mismatch:")
                print(f"Logs1: {logs1}")
                print(f"Logs2: {logs2}")
                print("")


if __name__ == "__main__":
    file_path1 = "run_physic.log"
    file_path2 = "run_physic_2.log"

    logs1 = load_logs(file_path1)
    logs2 = load_logs(file_path2)

    merged_logs1 = merge_logs(logs1)
    merged_logs2 = merge_logs(logs2)

    compare_merged_logs(merged_logs1, merged_logs2)
    print('all log data has been checked! ')

import os
import subprocess
import shutil
import signal
import sys
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

def control_c(signum, frame):
    print("Exiting...")
    sys.exit(1)

signal.signal(signal.SIGINT, control_c)

def main():
    dirname = '11be-mlo'
    ns3_path = os.path.join('../../../../ns3')

    if not os.path.exists(ns3_path):
        print(f"Please run this program from within the correct directory.")
        sys.exit(1)

    results_dir = os.path.join(os.getcwd(), 'results', f"{dirname}-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(results_dir, exist_ok=True)

    os.chdir('../../../../')

    check_and_remove('wifi-mld.dat')

    rng_run = 1
    max_packets = 1500
    simulation_time = 10
    mcs1 = 2
    mcs2 = 2
    channel_width1 = 20
    channel_width2 = 40
    num_stations_values = [5, 10, 15, 20, 25, 30]

    HeMcs2_20MHz = calculate_bianchi(num_stations_values, mcs=2, channel_width=20)
    HeMcs4_20MHz = calculate_bianchi(num_stations_values, mcs=4, channel_width=40)

    ns3_throughput_link1_results = []
    ns3_throughput_link2_results = []
    ns3_total_throughput_results = []
    fixed_throughput_results = []
    fixed_throughput_results2 = []

    for num_stations in num_stations_values:
        cmd = (
            f"./ns3 run 'single-bss-mld "
            f"--rngRun={rng_run} "
            f"--payloadSize={max_packets} "
            f"--mcs={mcs1} "
            f"--mcs2={mcs2} "
            f"--channelWidth={channel_width1} "
            f"--channelWidth2={channel_width2} "
            f"--nMldSta={num_stations} "
            f"--mldPerNodeLambda=0.1'"
        )
        print(f"Running: {cmd}")
        subprocess.run(cmd, shell=True)

        ns3_thpt_link1, ns3_thpt_link2, ns3_thpt_total = parse_throughput('wifi-mld.dat')
        ns3_throughput_link1_results.append((num_stations, ns3_thpt_link1))
        ns3_throughput_link2_results.append((num_stations, ns3_thpt_link2))
        ns3_total_throughput_results.append((num_stations, ns3_thpt_total))

        fixed_throughput = HeMcs4_20MHz.get(num_stations, 0)
        fixed_throughput2 = HeMcs2_20MHz.get(num_stations, 0)
        fixed_throughput_results.append((num_stations, fixed_throughput))
        fixed_throughput_results2.append((num_stations, fixed_throughput2))

        move_file('wifi-mld.dat', results_dir, f'wifi-mld-nSta{num_stations}.dat')

    plot_combined_throughput(
        ns3_link1=ns3_throughput_link1_results,
        ns3_link2=ns3_throughput_link2_results,
        ns3_total=ns3_total_throughput_results,
        fixed=fixed_throughput_results,
        fixed2=fixed_throughput_results2,
        results_dir=results_dir
    )

def calculate_bianchi(num_stations_values, mcs, channel_width):
    bianchi_results = {}
    cw_min = 15
    cw_max = 1023
    slot_time = 9e-6
    sifs = 16e-6
    ack_time = 44e-6
    for n in num_stations_values:
        tau = 2 / (cw_min + 1)
        p = 1 - (1 - tau) ** (n - 1)
        throughput = (mcs * channel_width * (1 - p) * (1500 * 8)) / (
            sifs + ack_time + ((cw_min / 2) * slot_time))
        bianchi_results[n] = max(0, throughput)
    return bianchi_results

def check_and_remove(filename):
    if os.path.exists(filename):
        response = input(f"Remove existing file {filename}? [Yes/No]: ").strip().lower()
        if response == 'yes':
            os.remove(filename)
            print(f"Removed {filename}")
        else:
            print("Exiting...")
            sys.exit(1)

def parse_throughput(file_path):
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            last_line = lines[-1].strip()
            tokens = last_line.split(',')
            mld_thpt_link1 = float(tokens[3])
            mld_thpt_link2 = float(tokens[4])
            mld_thpt_total = float(tokens[5])
        return mld_thpt_link1, mld_thpt_link2, mld_thpt_total
    except (IndexError, ValueError, FileNotFoundError) as e:
        print(f"Error parsing throughput from the output file: {e}")
        return 0, 0, 0

def plot_combined_throughput(ns3_link1, ns3_link2, ns3_total, fixed, fixed2, results_dir):
    ns3_x1 = [item[0] for item in ns3_link1]
    ns3_y1 = [item[1] for item in ns3_link1]

    ns3_x2 = [item[0] for item in ns3_link2]
    ns3_y2 = [item[1] for item in ns3_link2]

    ns3_x_total = [item[0] for item in ns3_total]
    ns3_y_total = [item[1] for item in ns3_total]

    fixed_x = [item[0] for item in fixed]
    fixed_y = [item[1] for item in fixed]

    bianchi_x2 = [item[0] for item in fixed2]
    bianchi_y2 = [item[1] for item in fixed2]

    plt.figure()
    plt.title('Throughput vs Number of Stations (Combined)')
    plt.xlabel('Number of Stations')
    plt.ylabel('Throughput (Mbps)')
    plt.grid()

    plt.plot(ns3_x1, ns3_y1, marker='o', label='ns-3 Link 1')
    plt.plot(ns3_x2, ns3_y2, marker='s', label='ns-3 Link 2')
    plt.plot(ns3_x_total, ns3_y_total, marker='^', label='ns-3 Total')
    plt.plot(fixed_x, fixed_y, marker='x', label='Bianchi MCS4 40MHz')
    plt.plot(bianchi_x2, bianchi_y2, marker='x', label='Bianchi MCS2 20MHz')

    plt.legend()
    plt.savefig(os.path.join(results_dir, 'throughput_combined.png'))
    plt.show()

def move_file(filename, destination_dir, new_filename=None):
    if os.path.exists(filename):
        dst = os.path.join(destination_dir, new_filename or os.path.basename(filename))
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(filename, dst)

if __name__ == "__main__":
    main()

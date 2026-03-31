#!/usr/bin/env python
import os
import sys
import subprocess
from multiprocessing import Pool

if "SUMO_HOME" in os.environ:
    sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))

from sumolib import checkBinary
from sumolib.xml import parse

sumoBinary = checkBinary('sumo')

def run_sim(args):
    route_idx, step_length = args
    
    step_str = str(step_length).replace(".", "_")
    name = f"sim_r{route_idx}_s{step_str}_extrapOn"
    output_dir = os.path.join(name, "output")

    os.makedirs(output_dir, exist_ok=True)

    route_file = f"sampledRoutes{route_idx}.rou.xml"
    output_prefix = output_dir + "/"

    cmd = [
        sumoBinary,
        "-n", "osm.net.xml",
        "-r", f"{route_file}",
        "--additional-files", "detectors.det.xml",
        "--statistic-output", "stats.xml",
        "--output-prefix", output_prefix,
        "--begin", "0",
        "--end", "86400",
        "--step-length", str(step_length),
        "--no-step-log",
        "--duration-log.statistics",
        "--extrapolate-departpos"
    ]

    ret = subprocess.call(cmd)
 
    if ret != 0:
        print(f"!!! {name} failed with return code {ret}", flush=True)

if __name__ == "__main__":
    # parameters
    route_indices = [2]
    step_lengths = [0.1]

    sims = [
        (r, s) 
        for r in route_indices 
        for s in step_lengths ]

    # parallel
    with Pool(processes=12) as pool:
        results = pool.map(run_sim, sims)
    
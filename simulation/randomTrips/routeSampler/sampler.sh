#!/bin/bash

python3 /usr/share/sumo/tools/routeSampler.py -r ../randomRoutes1.rou.xml -d edgedata4routeSampler_clean.xml -o sampledRoutes2.rou.xml --attributes="departLane=\"best_prob\" departSpeed=\"avg\"" --mismatch-output mismatch2.xml

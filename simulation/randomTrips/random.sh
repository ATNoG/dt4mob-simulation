#!/bin/bash

python3 /usr/share/sumo/tools/randomTrips.py -n ../simulation/osm.net.xml -r randomRoutes1.rou.xml -b 0 -e 86400 --trip-attributes="departLane=\"best_prob\" departSpeed=\"avg\"" --fringe-factor max --random-routing-factor 10 -v

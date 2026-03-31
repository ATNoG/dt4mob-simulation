FROM ghcr.io/eclipse-sumo/sumo:latest

WORKDIR /sim2

COPY osm.net.xml .
COPY detectors.det.xml .
COPY sampledRoutes*.rou.xml .
COPY main.py .

CMD ["python3", "main.py"]
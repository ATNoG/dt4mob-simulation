## SUMO Simulation of Via de Cintura Interna

Microscopic traffic simulation of the VCI (Via de Cintura Interna) in Porto, Portugal, using SUMO. The goal is to reproduce a realistic full-day traffic consistent with observed flows.

### Data 

Data available consists of hourly traffic flows collected at fixed checkpoints along the VCI.

### Traffic Network

The traffic network is generated using SUMO’s OSM WebWizard tool (osm.net.xml). Detector locations match real-world checkpoint positions (detectors.det.xml).

### Demand generation and Routing

Traffic demand is modeled using real-world hourly flow data for a selected example day.

- A candidate route set is generated with randomTrips tool (script random.sh). 
- Checkpoint data is converted into edge-based flows (edgedata4routeSampler_clean.xml).
- routeSampler tool uses this data and routes to create vehicles and match to routes with depart times (script sampler.sh).

### Validation

Simulation performance is evaluated by comparing simulated detector outputs with real-world traffic counts. 

Calibration involved adjusting randomTrips, routeSampler, and SUMO simulation parameters.

Evaluation metrics used are:
- RMSE (Root Mean Square Error)
- MAE (Mean Absolute Error)
- SMAPE (Symmetric Mean Absolute Percentage Error)
- R² (Coefficient of Determination)

The final parameter selection takes into account the above metrics, and the simulation time.

### Software

- Eclipse SUMO: 1.24.0
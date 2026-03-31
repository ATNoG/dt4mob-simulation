import traci
from src.settings import settings
from src.Models.traci_vehicle import TraciVehicle, VType
from src.services.geotile.geotiles_conversor import GeotilesConversor
import logging

class SumoSimulator():
    finalized_trip_vehicles: list[str] = []
    vehicles: list[TraciVehicle] = []
    removed_vehicles: list[str] = []
    _prev_raw_ids: set[str] = set()
    time: int = 0
    def __init__(self):
        logging.debug("Connecting to traci traci")
        traci.start(["sumo", "-c", settings.sumo.config_file])
        logging.debug("started traci")

    def simulationStep(self):
        if traci.simulation.getMinExpectedNumber() <= 0:
            return 0
    
        traci.simulationStep()
        self.time = traci.simulation.getTime()

        raw_current_ids = set(traci.vehicle.getIDList())
        raw_arrived_ids = traci.simulation.getArrivedIDList()
        
        self.finalized_trip_vehicles = [v.replace("#", "_") for v in raw_arrived_ids]
        
        self.vehicles.clear()
        for v_id in raw_current_ids:
            # Pass the raw ID for TraCI queries, but the function returns a clean object
            vehicle = self.__processVehicleId(v_id)
            self.vehicles.append(vehicle)

        prev_raw = getattr(self, '_prev_raw_ids', set())
        self.removed_vehicles = [v.replace("#", "_") for v in (prev_raw - raw_current_ids)]
        
        # Update for next step
        self._prev_raw_ids = raw_current_ids

    def __processVehiclesInSimulation(self) -> None:
        for v_id in traci.vehicle.getIDList():
            vehicle: TraciVehicle = self.__processVehicleId(v_id=v_id)
            self.vehicles.append(vehicle)
            
    def __processVehiclesEndedTrip(self) -> None:
        for v_id in traci.simulation.getArrivedIDList():
            v_id = v_id.replace("#","_")
            logging.debug(f"ENDED TRIP: {v_id}")
            self.finalized_trip_vehicles.append(v_id)

    def __processVehicleId(self,v_id:str) -> TraciVehicle:
        x,y = traci.vehicle.getPosition(v_id)
        lon,lat = traci.simulation.convertGeo(x,y)
        quadkey = GeotilesConversor.get_quadkey(lat, lon, settings.sumo.zoom_level)

        speed:float = traci.vehicle.getSpeed(v_id)
        angle:float = traci.vehicle.getAngle(v_id)
        accel:float = traci.vehicle.getAcceleration(v_id)
        length:float = traci.vehicle.getLength(v_id)
        width:float = traci.vehicle.getWidth(v_id)
        height:float = traci.vehicle.getHeight(v_id)
        v_type:str = traci.vehicle.getTypeID(v_id)

        v_id = v_id.replace("#","_")
        
        vehicle = TraciVehicle(
            id=v_id,
            speed=speed,
            latitude=lat,
            longitude=lon,
            quadkey=quadkey,
            angle=angle,
            accel=accel,
            length=length,
            width=width,
            height=height,
            vehicle_Type=VType(v_type)
            )
        return vehicle


    def __del__(self):
        traci.close()
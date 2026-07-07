import asyncio
import time
import logging
import sys
from datetime import datetime

from src.Models.vehicle_message import VehicleDataMessage,VehicleCreateMessage,VehicleDeleteMessage

from src.services.ditto_api import ditto_client
from src.services.ditto_api.ditto_class import DittoConnectionError
from src.services.simulator import sumo_simulator
from src.services.envelope_formatter.ditto_thing import envelop_formater
message_queue = asyncio.Queue(maxsize=10000)

async def ditto_client_worker():
    logging.info("Ditto sender Worker started")
    while True:
        payload = await message_queue.get()
        try:
            await ditto_client.send_envelope(payload)
        except DittoConnectionError as e:
            pass
            # logging.warning(f"Ditto disconnected, discarding message: {e}")
        finally:
            message_queue.task_done()

async def run_simulation_producer(created_ids:dict[str,datetime]):
    logging.info("Simulation Producer Started")
    
    while True:
        start = time.monotonic()
        is_active = await asyncio.to_thread(sumo_simulator.simulationStep)
        
        if is_active == 0:
            logging.info("Simulation finished.")
            break
        
        for vehicle in sumo_simulator.vehicles:
            if vehicle.id not in created_ids:
                message = VehicleCreateMessage(
                    id=vehicle.id,
                    length=vehicle.length,
                    width=vehicle.width,
                    height=vehicle.height,
                    vehicle_Type=vehicle.vehicle_Type.value,
                )
                formated_message = envelop_formater.format(message)

                try:
                    message_queue.put_nowait(formated_message.model_dump_json(by_alias=True))
                except asyncio.QueueFull:
                    logging.warning("Message queue full, dropping create message")
                created_ids[vehicle.id] = datetime.now()
                continue

            message = VehicleDataMessage(
                id=vehicle.id,
                geotile=vehicle.quadkey,
                extra=vehicle.model_dump(
                    exclude={"id", "length", "width", "height", "vehicle_Type","quadkey"}
                ),
            )
            formated_message = envelop_formater.format(message)
            
            try:
                message_queue.put_nowait(formated_message.model_dump_json(by_alias=True))
            except asyncio.QueueFull:
                # logging.warning("Message queue full, dropping data message")
                pass

        for v_id in sumo_simulator.removed_vehicles + sumo_simulator.finalized_trip_vehicles:
            formated_message = envelop_formater.format(
                vehicle_message=VehicleDeleteMessage(id=v_id)
            )
            if v_id in created_ids:
                created_ids.pop(v_id)
            try:
                message_queue.put_nowait(formated_message.model_dump_json())
            except asyncio.QueueFull:
                logging.warning("Message queue full, dropping delete message")
        
        logging.info(f"size of message queue: {message_queue.qsize()}")
        elapsed = time.monotonic() - start
        sleep_time = max(0, 1.0 - elapsed)
        if elapsed > 1.0:
            logging.warning(f"Sim Lag! Step took {elapsed:.3f}s")
        
        await asyncio.sleep(sleep_time)

async def main():
    logging.info("Connecting Ditto")
    await ditto_client.connect()
    logging.info("Connected")

    created_ids: dict[str, datetime] = {}

    worker = asyncio.create_task(ditto_client_worker())

    try:
        await run_simulation_producer(created_ids)
    except KeyboardInterrupt:
        logging.info("Stopping")
    finally:
        logging.info("Cleaning up...")

        if not message_queue.empty():
            logging.info(f"Draining {message_queue.qsize()} pending messages...")
            try:
                await asyncio.wait_for(message_queue.join(), timeout=5.0)
            except asyncio.TimeoutError:
                logging.warning("Abandoned some messages during shutdown")

        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass

        logging.info("Closing connections")
        await ditto_client.close()

        logging.info("Shutdown complete.")



if __name__ == "__main__":
    asyncio.run(main())

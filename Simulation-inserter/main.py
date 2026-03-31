import asyncio
import time
import logging
from datetime import datetime

from src.Models.vehicle_message import VehicleDataMessage,VehicleCreateMessage,VehicleDeleteMessage

from src.services.sender import mqtt_sender
from src.services.simulator import sumo_simulator
from src.services.envelope_formatter.ditto_thing import envelop_formater
message_queue = asyncio.Queue(maxsize=10000)

async def mqtt_worker():
    """Independent worker that pulls from the queue and sends to MQTT."""
    logging.info("MQTT Worker started")
    while True:
        payload = await message_queue.get()
        
        await mqtt_sender.send(payload)
        logging.debug(f"Sended: {payload}")
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

                await message_queue.put(formated_message.model_dump_json(by_alias=True).encode())
                created_ids[vehicle.id] = datetime.now()
                continue

            message = VehicleDataMessage(
                id=vehicle.id,
                extra=vehicle.model_dump(
                    exclude={"id", "length", "width", "height", "vehicle_Type"}
                ),
            )
            formated_message = envelop_formater.format(message)
            
            await message_queue.put(formated_message.model_dump_json(by_alias=True).encode())

        for v_id in sumo_simulator.removed_vehicles + sumo_simulator.finalized_trip_vehicles:
            formated_message = envelop_formater.format(
                vehicle_message=VehicleDeleteMessage(id=v_id)
            )
            if v_id in created_ids:
                created_ids.pop(v_id)
            await message_queue.put(formated_message.model_dump_json().encode())
        
        logging.debug(f"size of message queue: {message_queue.qsize()}")
        elapsed = time.monotonic() - start
        sleep_time = max(0, 1.0 - elapsed)
        if elapsed > 1.0:
            logging.warning(f"Sim Lag! Step took {elapsed:.3f}s")
        
        await asyncio.sleep(sleep_time)

async def main():
    logging.info("Connecting MQTT")
    await mqtt_sender.connect()
    logging.info("Connected")

    created_ids: dict[str, datetime] = {}

    worker = asyncio.create_task(mqtt_worker())

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
        await mqtt_sender.disconnect()

        logging.info("Shutdown complete.")



if __name__ == "__main__":
    asyncio.run(main())

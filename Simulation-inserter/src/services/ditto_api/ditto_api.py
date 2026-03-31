import httpx
import logging
from src.settings import settings
from src.Models.ditto import SearchResponse

SEARCH_SIZE = 200

class DittoClient:
    def __init__(self):
        logging.debug(settings.ditto.get_base_url())
        self._client = httpx.Client(
            base_url=settings.ditto.get_base_url(),
            headers={"x-ditto-pre-authenticated": settings.ditto.main_auth_username},
            verify=False,
        )
    
    def close(self):
        self._client.close()
    
    def delete_thing(self,car_id):
        query = f"/things/{car_id}"
        self._client.delete(query)
        

    def get_all_cars_ids(self) -> list[str]:
        ids: list[str] = []
        query = '/search/things?filter=like(thingId,"traci:Car*")&fields=thingId'
        params = {"filter": 'like(thingId,"traci:Car*")',
                  "fields": "thingId",
                  "option": f"size({SEARCH_SIZE})"}
        current_cursor = None
        while True:
            if current_cursor:
                params["option"] = f"size({SEARCH_SIZE}),cursor({current_cursor})"
            resp = self._client.get(url=query,params=params)
            logging.debug("status=%s", resp.status_code)
            logging.debug("headers=%s", resp.headers)
            logging.debug("body=%s", resp.text)

            raw_data = resp.json()
            data: SearchResponse = SearchResponse(**raw_data)
            if data.items:
                ids.extend([thing["thingId"] for thing in data.items])
            
            if not data.cursor:
                break

            current_cursor = data.cursor
        
        return ids

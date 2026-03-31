import logging
import httpx
import time

from src.Models.ditto import SearchResponse

SEARCH_SIZE = 200
class DittoClient:
    def __init__(self):
        auth = httpx.BasicAuth(
            username="ditto",
            password="OCrmqsgJz13iRpB5"
        )
        self._client = httpx.Client(
            base_url="http://tomastest.com/api/2",
            auth=auth,
            verify=False,
        )
    
    def close(self):
        self._client.close()
    
    def delete_thing(self,car_id):
        query = f"/things/{car_id}"
        self._client.delete(query)
        
    def _extract_time_to_live(self,body:dict):
        atributes = body.get("attributes",None)
        if atributes:
            return atributes.get("time_to_live",None)
        return None
    
    def get_all_cars_ids(self) -> list[str]:
        ids: list[str] = []
        query = '/search/things'
        params = {"fields": "thingId,_modified,attributes/time_to_live",
                  "filter": "like(thingId,'t*')",
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
                ids.extend([
                    {"thing":thing["thingId"],"up":thing["_modified"],"ttl":self._extract_time_to_live(thing)}
                      for thing in data.items])
            
            if not data.cursor:
                break

            current_cursor = data.cursor
        
        return ids

def main():
    ditto_client = DittoClient()
    start = time.time() * 1000
    things = ditto_client.get_all_cars_ids()
    stop = time.time() * 1000
    for t in things:
        print(t)
        ditto_client.delete_thing(t["thing"])
        print("delete thing",t["thing"])


if __name__ == "__main__":
    main()
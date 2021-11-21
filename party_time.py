import logging
import requests
import time
import json

from pprint import pprint

import secrets
api_key = secrets.api_key

server = 'Excalibur'
players = [
    'Helm Royce',
    'Furlyn Mewnglow',
    "Pokina Da'eye",
    'Julian Dereschabbot'
]

def lookup_by_name(name: str) -> int:
    name.replace(' ','+')
    for n in [name.lower(), name.upper(), name.title()]:
        time.sleep(2)
        r = requests.get(f"https://xivapi.com/character/search?name={n}&server={server}?private_key={api_key}")
        assert r.status_code == 200 or f"There was an error requesting {n}"
        data = r.json()
        if not 'Pagination' in data:
            pprint(data)
        if data['Pagination']['Page'] == 0:
            print(f" * There was no data returned for {n}")
        else:
            return data['Results'][0]['ID']

def lookup_by_id(id: int) -> dict:
    time.sleep(2)
    r = requests.get(f"https://xivapi.com/character/{id}?private_key={api_key}")
    jobs = {job['UnlockedState']['Name']: job['Level'] for job in r.json()['Character']['ClassJobs'] if job['Level'] > 0}
    return jobs

def main() -> None:
    player_data = {}
    for player in players:
        print(f"Looking up player: {player}")
        id = lookup_by_name(player)
        jobs = lookup_by_id(id)
        player_data[player] = {
            'id': id,
            'jobs': jobs
        }

    print(json.dumps(player_data, sort_keys=True, indent=4))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s', datefmt='%H:%M')
    main()
    # id = lookup_by_name("Excalibur", "Pokina+Da'eye")
    # lookup_by_id(id)






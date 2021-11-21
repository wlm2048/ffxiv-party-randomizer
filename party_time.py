import logging
import requests

import pyxivapi
from pyxivapi.models import Filter, Sort
from pprint import pprint

import secrets
api_key = secrets.api_key

def lookup_by_name(server: str, name: str) -> int:
    r = requests.get(f"https://xivapi.com/character/search?name={name}&server={server}?private_key={api_key}")
    data = r.json()
    return data['Results'][0]['ID']

def lookup_by_id(id: int) -> dict:
    r = requests.get(f"https://xivapi.com/character/{id}?private_key={api_key}")
    jobs = {job['UnlockedState']['Name']: job['Level'] for job in r.json()['Character']['ClassJobs'] if job['Level'] > 0}
    pprint(jobs)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s', datefmt='%H:%M')
    id = lookup_by_name("Excalibur", "Pokina+Da'eye")
    lookup_by_id(id)

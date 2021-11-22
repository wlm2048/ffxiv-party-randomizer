import logging
import requests
import time
import json
from bs4 import BeautifulSoup
from cachetools import cached, TTLCache

from pprint import pprint


base_url = 'https://na.finalfantasyxiv.com'
server = 'Excalibur'
players = [
    'Helm Royce',
    'Furlyn Mewnglow',
    "Pokina Da'eye",
    'Julian Dereschabbot'
]

@cached(cache=TTLCache(maxsize=16, ttl=7200))
def _lookup_by_name(name: str) -> object:
    r = requests.get(f"{base_url}/lodestone/character/?q={name}&worldname={server}")
    assert r.status_code == 200 or f"There was an error requesting {name}"
    return r

@cached(cache=TTLCache(maxsize=16, ttl=7200))
def _lookup_by_id(id: str) -> object:
    r = requests.get(f"{base_url}/{id}/class_job/")
    assert r.status_code == 200 or f"There was an error requesting {id}"
    return r

def lookup_by_name(name: str) -> str:
    name.replace(' ','+')
    r = _lookup_by_name(name)
    soup = BeautifulSoup(r.content, 'html5lib')
    entry = soup.find('a', attrs={'class': 'entry__link'})
    return entry['href']

def lookup_by_id(id: int) -> dict:
    r = _lookup_by_id(id)
    soup = BeautifulSoup(r.content, 'html5lib')
    roles = {}
    role_divs = soup.findAll('div', attrs={'class': 'character__job__role'})
    for rd in role_divs:
        x = rd.find('h4')
        print(f" - {x.text}")
        c = rd.findAll('li')
        for y in c:
            job_name = y.find('div', attrs={'class': 'character__job__name'}).text
            job_level = y.find('div', attrs={'class': 'character__job__level'}).text
            print(f"    * {job_name}: {job_level}")

    exit()

    # entry = soup.find('a', attrs={'class': 'entry__link'})
    # return entry['href']

def main() -> None:
    player_data = {}
    for player in players:
        print(f"Looking up player: {player}")
        id = lookup_by_name(player)
        print(f"got url {id}")
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






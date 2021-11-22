import logging
import requests
import random
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
duty_roles = {
    'Tank': None,
    'Healer': None,
    'DPS1': None,
    'DPS2': None
}

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

@cached(cache=TTLCache(maxsize=16, ttl=7200))
def lookup_by_name(name: str) -> str:
    name.replace(' ','+')
    r = _lookup_by_name(name)
    soup = BeautifulSoup(r.content, 'html5lib')
    entry = soup.find('a', attrs={'class': 'entry__link'})
    return entry['href']

@cached(cache=TTLCache(maxsize=16, ttl=7200))
def lookup_by_id(id: int, min_level: int = 0) -> dict:
    r = _lookup_by_id(id)
    soup = BeautifulSoup(r.content, 'html5lib')
    roles = {}
    role_divs = soup.findAll('div', attrs={'class': 'character__job__role'})
    for rd in role_divs:
        heading = rd.find('h4')
        if 'Disciples' in heading.text:
            continue
        # print(f" - {heading.text}")
        classes = rd.findAll('li')
        c = {}
        for cl in classes:
            job_name = cl.find('div', attrs={'class': 'character__job__name'}).text
            job_level = cl.find('div', attrs={'class': 'character__job__level'}).text
            if job_level != '-' and int(job_level) > min_level:
                c[job_name] = {'level': job_level}
                # print(f"    * {job_name}: {job_level}")
        if c:
            roles[heading.text] = c
    
    return roles

def main() -> None:
    player_data = {}
    for player in players:
        print(f"Getting job data for player: {player}")
        id = lookup_by_name(player)
        # print(f"got url {id}")
        jobs = lookup_by_id(id)
        player_data[player] = {
            'id': id,
            'jobs': jobs
        }

    random_role = list(duty_roles.keys())
    random.shuffle(random_role)
    random.shuffle(players)

    for i, player in enumerate(players):
        print(f"{player} will be {random_role[i]}")

    print(json.dumps(player_data, sort_keys=True, indent=4))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s', datefmt='%H:%M')
    main()
    # id = lookup_by_name("Excalibur", "Pokina+Da'eye")
    # lookup_by_id(id)






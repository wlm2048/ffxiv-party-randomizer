import logging
from logging import config
import requests
import random
import json
import time
from bs4 import BeautifulSoup
from diskcache import Cache
from pprint import pprint
import argparse
import re

parser = argparse.ArgumentParser(description='Do the duty!')
parser.add_argument('-l', '--level', type=int, help='Minimum level to consider', default=16)
parser.add_argument('-d', '--dps', action='store_true', help='Prioritize ranged AND melee dps', default=False)
parser.add_argument('-v', '--verbose', action='count', help='Increase logging verbosity', default=0)
args = parser.parse_args()

cache = Cache(".cache")
cache.expire()
cache_time = 7200

base_url = 'https://na.finalfantasyxiv.com'
server = 'Excalibur'
players = [
    'Helm Royce',
    'Furlyn Mewnglow',
    "Pokina Da'eye",
    'Julian Dereschabbot'
]
duty_roles = ['Tank', 'Healer']
if args.dps:
    duty_roles.extend(['Melee DPS', 'Physical Ranged DPS'])
else:
    duty_roles.extend(['DPS1', 'DPS2'])

class Logger:
    def getLogger(name: str) -> object:
        logger = logging.getLogger(name)
        config.dictConfig(Logger.config())
        return logger

    def config():
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "root": {
                "handlers": ["hand_so", "hand_se"],
                "formatter": "o",
                "level": "INFO"
            },
            "handlers": {
                "hand_so": {
                    "class": "logging.StreamHandler",
                    "level": "NOTSET",
                    "formatter": "default",
                    "filters": ["no_errors"],
                    "stream": "ext://sys.stdout"
                },
                "hand_se": {
                    "class": "logging.StreamHandler",
                    "level": "ERROR",
                    "formatter": "default",
                    "stream": "ext://sys.stderr"
                }
            },
            "formatters": {
                "default": {
                    "format": "%(levelname)s [%(filename)s:%(lineno)d] %(message)s"
                }
            },
            "filters": {
                "no_errors": {
                    "()": NoErrors
                }
            }
        }

class NoErrors:
    def filter(self: object, record: object) -> bool:
        if record.levelno >= 40:  # error or better, don't log
            return False
        else:
            return True

logger = logging.getLogger(__name__)
if args.verbose >= 2:
    ll = 'DEBUG'
elif args.verbose == 1:
    ll = 'INFO'
else:
    ll = 'WARNING'
logger.setLevel(ll)
config.dictConfig(Logger.config())

logger.debug(f"args are: {args}")

class Character:
    def __init__(self: object, name: str) -> None:
        self.name = name
        self.get()

    def get(self: object) -> object:
        self.id = self.lookup_by_name()
        self.jobs = self.lookup_by_id()

    def not_do(self: object, role: str) -> bool:
        return not self.can_do(role)

    def can_do(self: object, role: str) -> bool:
        return role in self.jobs.keys()

    def _lookup_by_name(self: object, name: str) -> object:
        key = f'character_{name}'
        if cache.get(key):
            logger.debug(f"cache hit for {key}")
            return cache.get(key)
        else:
            logger.debug(f"cache miss for {key}")
            r = requests.get(f"{base_url}/lodestone/character/?q={name}&worldname={server}")
            assert r.status_code == 200 or f"There was an error requesting {name}"
            cache.set(key, r, expire=cache_time)
            return r

    def _lookup_by_id(self: object) -> object:
        if cache.get(self.id):
            logger.debug(f"cache hit for {self.id}")
            return cache.get(self.id)
        else:
            logger.debug(f"cache miss for {self.id}")
            r = requests.get(f"{base_url}/{self.id}/class_job/")
            assert r.status_code == 200 or f"There was an error requesting {self.id}"
            cache.set(self.id, r, expire=cache_time)
            return r

    def lookup_by_name(self: object) -> str:
        name = self.name
        name.replace(' ','+')
        r = self._lookup_by_name(name)
        soup = BeautifulSoup(r.content, 'html5lib')
        entry = soup.find('a', attrs={'class': 'entry__link'})
        return entry['href']

    def lookup_by_id(self: object) -> dict:
        r = self._lookup_by_id()
        soup = BeautifulSoup(r.content, 'html5lib')
        roles = {}
        role_divs = soup.findAll('div', attrs={'class': 'character__job__role'})
        for rd in role_divs:
            role = rd.find('h4')
            if 'Disciples' in role.text:
                continue
            role_name = role.text
            if not args.dps and "DPS" in role_name:
                role_name = "DPS"
            classes = rd.findAll('li')
            c = {}
            for cl in classes:
                job_name = cl.find('div', attrs={'class': 'character__job__name'}).text
                job_level = cl.find('div', attrs={'class': 'character__job__level'}).text
                if job_level != '-' and int(job_level) >= args.level:
                    c[job_name] = {'level': job_level}
            if c:
                if role_name in roles:
                    for job in c:
                        roles[role_name][job] = c[job]
                else:
                    roles[role_name] = c
                logger.debug(f" - can do {role_name}: {roles[role_name]}")

        return roles

def main() -> None:
    player_data = {}
    for player in players:
        logger.info(f"Getting job data for player: {player}")
        ch = Character(player)
        player_data[player] = ch

    who_can = {}
    for role in duty_roles:
        _role = role
        if re.match(r"DPS\d", role):
            _role = "DPS"
        who_can[role] = [player for player in player_data if player_data[player].can_do(_role)]

    sorted_whocan = {k: v for k, v in sorted(who_can.items(), key=lambda item: len(item[1]), reverse=True)}

    picked = []
    final = {}
    success = False
    while not success:
        for role, who in sorted_whocan.items():
            while True:
                random.shuffle(who)
                for lucky in who:
                    if lucky in picked:
                        continue
                    else:
                        picked.append(lucky)
                        break
                break
            final[role] = lucky
        if len(set(final.values())) == 4:
            success = True

    for role in duty_roles:
        _role = role
        if re.match(r"DPS\d", role):
            _role = "DPS"
        jobs = dict(player_data[final[role]].jobs)[_role]
        j = list(jobs.keys())
        random.shuffle(j)
        print(f"{final[role]}: {role} ({j[0]} - {jobs[j[0]]['level']})")

if __name__ == '__main__':
    main()

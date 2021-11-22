import logging
from logging import config
import requests
import random
import json
from bs4 import BeautifulSoup
from diskcache import Cache
from pprint import pprint

cache = Cache(".cache")
cache.expire()

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
logger.setLevel('DEBUG')
config.dictConfig(Logger.config())

class Character:
    def __init__(self: object, name: str, config: dict = {}) -> None:
        self.name = name
        self.info = self.get()
        self.config = config
        self.config.setdefault('level', 16)

    def get(self: object) -> object:
        print(self.name)
        self.id = self.lookup_by_name()
        self.jobs = self.lookup_by_id()
    
    def i_can_be(self: object, role: str) -> bool:
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
            cache.set(key, r, expire=3600)
            return r

    def _lookup_by_id(self: object) -> object:
        if cache.get(self.id):
            logger.debug(f"cache hit for {self.id}")
            return cache.get(self.id)
        else:
            logger.debug(f"cache miss for {self.id}")
            r = requests.get(f"{base_url}/{self.id}/class_job/")
            assert r.status_code == 200 or f"There was an error requesting {self.id}"
            cache.set(id, r, expire=3600)
            return r

    def lookup_by_name(self: object) -> str:
        name = self.name
        name.replace(' ','+')
        r = self._lookup_by_name(name)
        soup = BeautifulSoup(r.content, 'html5lib')
        entry = soup.find('a', attrs={'class': 'entry__link'})
        return entry['href']

    def lookup_by_id(self: object, min_level: int = 0) -> dict:
        r = self._lookup_by_id()
        soup = BeautifulSoup(r.content, 'html5lib')
        roles = {}
        role_divs = soup.findAll('div', attrs={'class': 'character__job__role'})
        for rd in role_divs:
            heading = rd.find('h4')
            if 'Disciples' in heading.text:
                continue
            logger.debug(f" - {heading.text}")
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
    for player in random.shuffle(players):
        print(f"Getting job data for player: {player}")
        ch = Character(player)
        pprint(ch.i_can_be('Tank'))
    #     id = lookup_by_name(player)
    #     # print(f"got url {id}")
    #     jobs = lookup_by_id(id)
    #     player_data[player] = {
    #         'id': id,
    #         'jobs': jobs
    #     }

    # random_role = list(duty_roles.keys())
    # random.shuffle(random_role)
    # random.shuffle(players)

    # for i, player in enumerate(players):
    #     print(f"{player} will be {random_role[i]}")

    # print(json.dumps(player_data, sort_keys=True, indent=4))

if __name__ == '__main__':
    main()
    # id = lookup_by_name("Excalibur", "Pokina+Da'eye")
    # lookup_by_id(id)






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
import redis

redis_server = redis.Redis() # Create access to Redis

parser = argparse.ArgumentParser(description='Do the duty!')
parser.add_argument('-l', '--level', type=int, help='Minimum level to consider', default=16)
parser.add_argument('-m', '--level2', type=int, help='Maximum level to consider', default=90)
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

roles = [
    "dps",
    "healer",
    "tank"
]

jobs = {
    "acn": "arcanist",
    "arc": "archer",
    "ast": "astrologian",
    "blm": "black mage",
    "blu": "blue mage",
    "brd": "bard",
    "cnj": "conjurer",
    "dnc": "dancer",
    "drg": "dragoon",
    "drk": "dark knight",
    "gla": "gladiator",
    "gnb": "gunbreaker",
    "lnc": "lancer",
    "mch": "machinist",
    "mnk": "monk",
    "mrd": "marauder",
    "nin": "ninja",
    "pgl": "pugilist",
    "pld": "paladin",
    "rdm": "red mage",
    "rog": "rogue",
    "rpr": "reaper",
    "sam": "samurai",
    "sch": "scholar",
    "sge": "sage",
    "smn": "summoner",
    "thm": "thaumaturge",
    "war": "warrior",
    "whm": "white mage"
}

base_classes = {
    "Bard": "Archer",
    "Black Mage": "Thaumaturge",
    "Dragoon": "Lancer",
    "Monk": "Pugilist",
    "Ninja": "Rogue",
    "Paladin": "Gladiator",
    "Scholar": "Arcanist",
    "Summoner": "Arcanist",
    "Warrior": "Marauder",
    "White Mage": "Conjurer"
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
                "handlers": ["file", "hand_so", "hand_se"],
                "formatter": "o",
                "level": "INFO"
            },
            "handlers": {
                "file": {
                    'class': 'logging.FileHandler',
                    'filename': 'roleroll.log',
                    'formatter': 'default',
                    'level': 'DEBUG',
                },
                "hand_so": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
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

    def characters(self: object) -> list:
        return players

    def get(self: object) -> object:
        logger.info(f"Looking up {self.name}")
        self.id = self.lookup_by_name()
        logger.info(f"Got {self.id}")
        logger.info(f"Checking for role locks")
        self.role_lock = self.role_locks()
        logger.info(f"Checking for job locks")
        self.job_lock = self.job_locks()
        logger.info(f"Getting jobs")
        self.jobs = self.get_jobs()

    def job_locks(self: object) -> object:
        job_locks = redis_server.keys("job:*")
        if job_locks:
            for rl in job_locks:
                pc = (rl.decode('utf-8').split(":", 1))[1]
                job = redis_server.get(rl).decode('utf-8').split(",")
                if pc in self.name.lower():
                    logger.info(f"Blacklisting {pc} from {job}")
                    return job


    def role_locks(self: object) -> object:
        role_locks = redis_server.keys("role:*")
        if role_locks:
            for rl in role_locks:
                pc = (rl.decode('utf-8').split(":", 1))[1]
                role = redis_server.get(rl).decode('utf-8').split(",")
                if pc in self.name.lower():
                    logger.info(f"Locking {pc} to {role}")
                    return role

    def not_do(self: object, role: str) -> bool:
        return not self.can_do(role)

    def can_do(self: object, role: str) -> bool:
        if self.role_lock and role.lower() not in self.role_lock:
            return False
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

    def get_jobs(self: object) -> dict:
        r = self._lookup_by_id()
        soup = BeautifulSoup(r.content, 'html5lib')
        roles = {}
        cc = soup.find('div', attrs={'class': 'character__content'})
        role_headings = cc.findAll('h4', attrs={'class': 'heading--lead'})
        for role_heading in role_headings:
            role = role_heading.text
            if 'Disciples' in role:
                continue
            if not args.dps and "DPS" in role:
                role = "DPS"
            job_list = role_heading.find_next_sibling()
            classes = job_list.findAll('li')
            c = {}
            for cl in classes:
                job_name = cl.find('div', attrs={'class': 'character__job__name'}).text
                job_level = cl.find('div', attrs={'class': 'character__job__level'}).text
                if job_level != '-' and int(job_level) >= args.level and int(job_level) <= args.level2:
                    c[job_name] = {'level': job_level}
            if c:
                if role in roles:
                    for job in c:
                        roles[role][job] = c[job]
                else:
                    roles[role] = c
                logger.debug(f" - can do {role}: {roles[role]}")

        # remove base jobs if never progressed
        for role in roles:
            for job in roles[role]:
                if job in base_classes:
                    for role2 in roles:
                        if base_classes[job] in roles[role2]:
                            logger.debug(f"    ** found {job} removing {base_classes[job]}")
                            del roles[role2][base_classes[job]]


        # remove jobs if blacklisted
        for role, jobs in roles.items():
            for job in jobs.copy():
                if self.job_lock and job.lower() in self.job_lock:
                    logger.info(f"Removing {job} because of blacklist")
                    del roles[role][job]

        # if a role is empty, remove it
        roles = dict((k, v) for k, v in roles.items() if len(roles[k]) > 0)

        return roles

def find_winners(more_args: dict = {}) -> list:
    winners = []

    if 'level' in more_args:
        args.level = int(more_args['level'])
    if 'level2' in more_args:
        args.level2 = int(more_args['level2'])
    if 'dps' in more_args:
        args.dps = True
        
    duty_roles = ['Tank', 'Healer']
    if args.dps:
        duty_roles.extend(['Melee DPS'])
        duty_roles.extend(random.sample(['Physical Ranged DPS', 'Magical Ranged DPS'], 1))
    else:
        duty_roles.extend(['DPS1', 'DPS2'])

    player_data = {}
    for player in players:
        logger.info(f"Getting job data for player: {player}")
        ch = Character(player)
        player_data[player] = ch

    who_can = {}
    for role in duty_roles:
        print(f"--- {role}")
        _role = role
        if re.match(r"DPS\d", role):
            _role = "DPS"
        who_can[role] = [player for player in player_data if player_data[player].can_do(_role)]

    sorted_whocan = {k: v for k, v in sorted(who_can.items(), key=lambda item: len(item[1]), reverse=True)}

    picked = []
    final = {}
    success = False
    max_attempts = 100
    attempts = 0
    while not success:
        logger.debug("Trying to find a group... ")
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
        if attempts >= max_attempts:
            break
        attempts = attempts + 1

    if success is False:
        return([f"Could not find a solution after {attempts} attempts"])
    else:
        logger.info(f"Found a solution after {attempts} attempts")

    for role in duty_roles:
        # (f"Checking {role}")
        _role = role
        if re.match(r"DPS\d", role):
            _role = "DPS"
        # (final[role])
        # (player_data[final[role]].jobs)
        jobs = dict(player_data[final[role]].jobs)[_role]
        j = list(jobs.keys())
        random.shuffle(j)
        # ("Final:")
        # (final)
        # ("Jobs:")
        # (jobs)
        winner = f"{final[role]}: {role} ({j[0]} - {jobs[j[0]]['level']})"
        logger.info(winner)
        winners.append(winner)

    return winners

def main() -> None:
    winners = find_winners()
    for w in winners:
        print(w)

if __name__ == '__main__':
    main()

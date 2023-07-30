from datetime import timedelta
from party_time import Logger, Character, players
from re import finditer
import asyncio
import discord
from discord.ext import commands
import logging
import party_time
import re
import redis
import time

redis_server = redis.Redis() # Create access to Redis

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents) # starts the discord client

logger = logging.getLogger(__name__)
party_time.logger.setLevel(logging.DEBUG)

AUTH_TOKEN = str(redis_server.get("AUTH_KEY").decode("utf-8"))

async def take_action(mc: str) -> bool:
    mc = mc.lower()

    print(f"Actioning: {mc}")

    command = "(roleroll|rr)"
    
    rrm = re.match(fr'!{command}\s+(?P<action>\w+)\s+(?P<the_rest>.*)$', mc, re.IGNORECASE)
    action = rrm['action']
    the_rest = rrm['the_rest']

    name_line = "|".join([x.lower() for x in party_time.players]) + "|" + "|".join([x.lower().split(" ",1)[0] for x in party_time.players])
    if "lock" in action:
        action_line = "|".join([x.lower() for x in party_time.roles])
    elif "blacklist" in action:
        action_line = "|".join([x.lower() for x in party_time.jobs.keys()])
    else:
        print(f"Don't know how to handle {action}")
    
    name_regex = re.compile(r'\b(' + name_line + r')\b')
    action_regex = re.compile(r'\b(' + action_line + r')\b')
    
    name_match = re.search(name_regex, the_rest)
    the_rest = re.sub(name_match.group(), "", the_rest)
    action_items = ",".join([m.group() for m in action_regex.finditer(the_rest)])
    name = name_match.group().split(" ", 1)[0]
    
    if "un" in action:
        time_d = 1
    else:
        time_d = timedelta(hours=8)
        
    if "lock" in action:
        key = "role"
    else:
        key = "job"

    print(f"ACTION: {action} - key: {key}, name: {name}, items: {action_items}, expire: {time_d}")

    redis_server.setex(
        f"{key}:{name}",
        time_d,
        value=f"{action_items}"
    )
    await asyncio.sleep(1)
    return True

@bot.event 
async def on_ready():
    print(f"Successful Launch!!! {bot.user}")
    
@bot.command()
async def ping(ctx):
    await ctx.send("pong")
        
@bot.event

async def on_message(message):
    if f'!{command}' in message.content.lower():
        new_args = {}
        mc = message.content


        logger.info(f"Parsing command: {mc}")
        level_match = re.match(fr'!{command}\s+level\s+(?P<level>\d+)(?P<level2>\s*\d+)?(?P<dps>\s*dps)?', mc, re.IGNORECASE)
        if level_match:
            logger.info(f"Using level {level_match.group('level')}")
            new_args['level'] = level_match.group('level')
            
        if level_match and level_match.group('level2'):
            new_args['level2'] = level_match.group('level2')
            
        if level_match and level_match.group('dps'):
            new_args['dps'] = True

        if re.match(fr'!{command}\s+(?:(?:un)?lock|(?:un)?blacklist)\s+', mc, re.IGNORECASE):
            return await take_action(mc)
        
        role_locks = redis_server.keys("role:*")
        if role_locks:
            locks = "Current character locks are:\n"
            for rl in role_locks:
                pc = (rl.decode('utf-8').split(":", 1))[1]
                role = redis_server.get(rl).decode('utf-8').split(",")
                locks = locks + f" * {pc}: {', '.join(role)}\n"
            await message.channel.send(locks)

        job_locks = redis_server.keys("job:*")
        if job_locks:
            locks = "Current character blacklisted jobs are:\n"
            for rl in job_locks:
                pc = (rl.decode('utf-8').split(":", 1))[1]
                jobs = redis_server.get(rl).decode('utf-8').split(",")
                locks = locks + f" * {pc}: {', '.join(jobs)}\n"
            await message.channel.send(locks)

        winners = "\n".join(party_time.find_winners(new_args))
        await message.channel.send(winners)
        return True
        
bot.run(AUTH_TOKEN) # Pull Auth Token from above

from pprint import pprint
import json
import re
from diskcache import Cache
import math
import requests
import requests_cache
import time
import numpy as np
import csv

with open('bank.data', 'r') as f:
    lines = f.readlines()

with open('items.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

items = []

for line in lines:
    line = line.strip()
    parts = re.match(r'(?P<item>.*?)(?:\s(?P<hq>\*))?\s\((?P<count>\d+)\)', line)
    if parts:
        item = parts.group('item')
        num = parts.group('count')
        hq = True if parts.group('hq') else False
        id = data[item]
        items.append({
            "item": item,
            "quantity": num,
            "hq": hq,
            "id": id
        })

def reject_outliers(data, m = 2.):
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d/mdev if mdev else np.zeros(len(d))
    return data[s<m]


session = requests_cache.CachedSession('demo_cache', expire_after=86400)
with open('my_file.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Item', 'HQ', 'Quantity', 'Avg', 'Min', 'Max', 'ID'])

for item in items:
    print(f"Looking up {item['item']} ({item['id']})")
    response = session.get(f"https://universalis.app/api/v2/history/Excalibur/{item['id']}?minSalePrice=0&maxSalePrice=2147483647")
    if not response.from_cache:
        time.sleep(1)
    entries = response.json()
    raw_prices = np.array([x['pricePerUnit'] for x in entries['entries'] if (x['hq'] == item['hq'])])
    prices = reject_outliers(raw_prices)
    price_min = min(prices)
    price_max = max(prices)
    price_avg = np.mean(prices)
    with open('my_file.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([item['item'], item['hq'], item['quantity'], price_avg, price_min, price_max, item['id']])

# {
#   "itemID": 5317,
#   "worldID": 93,
#   "lastUploadTime": 1694236331187,
#   "entries": [
#     {
#       "hq": false,
#       "pricePerUnit": 1401,
#       "quantity": 3,
#       "buyerName": "Melodramatic Pidgeon",
#       "onMannequin": false,
#       "timestamp": 1693523161
#     },
#     {
# https://universalis.app/api/v2/Excalibur/7608,27734?fields=items.listings.pricePerUnit%2Citems.listings.hq%2Citems.listings.quantity
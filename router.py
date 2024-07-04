import requests
from requests.auth import HTTPBasicAuth

basic = HTTPBasicAuth('admin', 'password')
r = requests.get('http://192.168.100.1/', auth=basic)
print(r.content)


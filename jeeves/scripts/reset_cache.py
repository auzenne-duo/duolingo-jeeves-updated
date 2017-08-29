import requests

print(requests.get('https://jeeves.duolingo.com/api/1/init').content)

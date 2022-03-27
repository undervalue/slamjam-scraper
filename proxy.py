import random

# loads proxies
proxies = []

with open('proxies.txt', 'r') as f:
  for line in f.read().splitlines():
    l = line.split(':')
    proxies.append(f'http://{l[2]}:{l[3]}@{l[0]}:{l[1]}')

def getProxy():
  return random.choice(proxies)


from bs4 import BeautifulSoup
from datetime import datetime
import aiohttp
import asyncio
import random
import json

from product import Product
from proxy import getProxy
from config import config
import db

api = 'https://www.slamjam.com/on/demandware.store/Sites-slamjam-Site/en_IT'

async def fetch(url, session):
  """Fetches an url asynchronously"""
 
  try:
    async with session.get(url, proxy=getProxy()) as res:
      return await res.json()
  
  except aiohttp.ClientResponseError as e:
    if config['monitor']['verbose']:
      print(f'Failed to fetch {url.replace(api, "")}: error {e.status} ({e.message})')

    if e.status in config['monitor']['retryStop']:
      return False

  except aiohttp.client_exceptions.ServerDisconnectedError:
    if config['monitor']['verbose']:
      print(f'Failed to fetch {url.replace(api, "")}: server disconnected')

  except asyncio.exceptions.TimeoutError:
    if config['monitor']['verbose']:
      print(f'Failed to fetch {url.replace(api, "")}: timeout')

  except Exception as e:
    if config['monitor']['verbose']:
      print(f'Failed to fetch {url.replace(api, "")}: {e}')

async def wishlistGetProduct(pid, session):
  """Gets product information via the WishList-GetProduct endpoint"""

  url = f'{api}/Wishlist-GetProduct?pid={pid}'

  res = await fetch(url, session)
  if res == None or res == False : return res

  p = res['product']
  name = p['productName']
  brand = p['brand']
  createdAt = datetime.strptime(p['creationDate'].split('T')[0], '%Y-%m-%d').date()

  try:
    image = p['images']['hi-res'][0]['absURL']
  except:
    image = None

  try:
    price = p['price']['sales']['formatted']
  except:
    price = None

  sizes = {}
  for v in p['variationAttributes']:
    if v['attributeId'] == 'size':
      for size in v['values']:
        sizes[size['displayValue']] = {'id': size['productID'], 'instock': size['selectable']}

  return Product(pid=pid, name=name, brand=brand, createdAt=createdAt, price=price, image=image, sizes=sizes, wishlist=True)

async def quickviewGetProduct(pid, session):
  """Gets product information via the Product-ShowQuickView endpoint"""

  url = f'{api}/Product-ShowQuickView?pid={pid}'

  res = await fetch(url, session)
  if res == None or res == False: return res

  soup = BeautifulSoup(res['renderedTemplate'], 'html.parser')

  name = soup.find('h1', class_='product-name').text.strip()
  image = soup.find('div', class_='slider-data-large').find('div')['data-image-url']
  brand = soup.find('div', class_='product-quickview__main').find('h2', class_='t-up').text.strip()
  price = soup.find('div', class_='price').find('span', class_='value').text.strip()

  j = json.loads(soup.find('script', type='application/ld+json').string)
  createdAt = datetime.strptime(j['datePublished'], '%Y-%m-%d').date()

  if price == 'null': price = None
  if 'product-no-image' in image: image = None

  return Product(pid=pid, name=name, brand=brand, createdAt=createdAt, price=price, image=image)

lastEndpoint = random.choice(['wishlist', 'quickview'])

async def alternateGetProduct(pid, session, wishlist=False):
  """Gets product information alternating between endpoints"""

  global lastEndpoint
  r = None
 
  for attempt in range(config['monitor']['retry']):
    if wishlist:
      r = await wishlistGetProduct(pid, session)
    else:
      if lastEndpoint == 'wishlist':
        lastEndpoint = 'quickview'
        r = await quickviewGetProduct(pid, session)
      else:
        lastEndpoint = 'wishlist'
        r = await wishlistGetProduct(pid, session)
    
    if r == False:
      return None

    if r != None:
      return r

    if attempt != config['monitor']['retry'] - 1:
      print(f'Retrying pid {pid}...')

async def getProduct(pid, wishlist=False, cache=True):
  """Gets product information with caching"""

  if cache:
    res = await db.select(pid, wishlist=wishlist)
    if res != None: return res
  
  headers = { 'referer': 'x' }
  connector = aiohttp.TCPConnector(ssl=False)
  timeout = aiohttp.ClientTimeout(total=config['monitor']['timeout'])

  async with aiohttp.ClientSession(headers=headers, raise_for_status=True, connector=connector, timeout=timeout) as session:
    product = await alternateGetProduct(pid, session, wishlist=wishlist)

  if product == None: return

  if product.wishlist:
    cached = await db.select(pid)

    if cached != None:
      await db.update(pid, product, True)
    else:
      await db.insert(pid, product, True)
  else:
    await db.insert(pid, product, False)

  return product

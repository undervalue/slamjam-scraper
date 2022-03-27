from discord.ext import commands
from discord import DMChannel
from datetime import datetime
import discord
import asyncio
import pickle

from slamjam import getProduct
from config import config
import db

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
  print(f'logged in as {bot.user.name} ({bot.user.id})')

  await db.initialize()
  await monitor()

def check(ctx):
  if isinstance(ctx.message.channel, DMChannel):
    return False
  
  if config['discord']['allow']['everyone']:
    return True

  author = ctx.message.author

  for role in ctx.message.author.roles:
    if role.id in config['discord']['allow']['role']:
      return True

  return False

@bot.command()
@commands.check(check)
async def search(ctx, pid: str):
  """Search for a product by pid"""

  embed = discord.Embed(
    title='Just a moment...',
    description=f'Fetching PID {pid}. If the bot takes too long to respond, re-send the command.',
    color=config['discord']['embedColor']['normal']
  )

  msg = await ctx.send(embed=embed)

  semaphore = asyncio.Semaphore(1)
  await checkPid(pid, semaphore)

  product = await getProduct(pid, wishlist=True, cache=False)

  if product == None:
    embed = discord.Embed(
      title='PID not found',
      description=f'Failed to fetch pid {pid}.',
      color=config['discord']['embedColor']['error']
    )
  else:
    embed = product.get_embed()

  author = ctx.message.author
  embed.set_footer(text=f'Fetched by {author.name}#{author.discriminator} | Powered by Ganz', icon_url=author.avatar_url)
  
  await msg.edit(embed=embed)

@bot.command()
@commands.check(check)
async def searchRange(ctx, start: int, end: int):
  """Checks all pids in a range"""

  embed = discord.Embed(
    title='Scraper started...',
    description=f'Checking all pids from {start} to {end}...',
    color=config['discord']['embedColor']['normal']
  )

  author = ctx.message.author
  embed.set_footer(text=f'Fetched by {author.name}#{author.discriminator} | Powered by Ganz', icon_url=author.avatar_url)
  
  msg = await ctx.send(embed=embed)
  try:
    await checkRange(start, end)

    embed = discord.Embed(
      title='Successfully scraped PIDs!',
      description=f'Checked all PIDs from {start} to {end}.',
      color=config['discord']['embedColor']['success']
    )

    embed.set_footer(text=f'Fetched by {author.name}#{author.discriminator} | Powered by Ganz', icon_url=author.avatar_url)
    await msg.edit(embed=embed)
  except:
    embed = discord.Embed(
      title='Error',
      description=f'Error when checking pids from {start} to {end}.',
      color=config['discord']['embedColor']['error']
    )

    embed.set_footer(text=f'Fetched by {author.name}#{author.discriminator} | Powered by Ganz', icon_url=author.avatar_url)
    await msg.edit(embed=embed)

@search.error
async def search_error(ctx, error):
  if isinstance(error, commands.errors.CheckFailure):
    if not isinstance(ctx.message.channel, DMChannel):
      print(f'Refusing to run command for {ctx.message.author.name}#{ctx.message.author.discriminator} on #{ctx.message.channel.name}')
    else:
      print(f'Refusing to run command for {ctx.message.author.name}#{ctx.message.author.discriminator} in DMs')

async def checkCache(pid):
  """Checks if a product is cached"""

  res = await db.select(pid)
  return res != None

async def checkPid(pid, semaphore):
  """Checks if a pid contains a new product"""

  async with semaphore:
    inCache = await checkCache(pid)
    
    if not inCache:
      res = await getProduct(pid)
      
      if res != None:
        delta = (datetime.today().date()-res.createdAt).days
        
        if delta <= config['monitor']['delta']:
          channel = bot.get_channel(config['discord']['notify'])
          embed = res.get_embed(new=True)
          embed.title = f'[New Product Fetched]\n{embed.title}'
          embed.set_footer(text=f'SlamJam Scraper | Powered by Ganz')


          await channel.send(embed=embed)

async def checkRange(start, end):
  """Checks if there are any new products on a range"""

  semaphore = asyncio.Semaphore(config['monitor']['maxConcurrent'])
  tasks = []

  for pid in range(start, end+1):
    tasks.append(checkPid(f'J{pid:06}', semaphore))
    
  await asyncio.gather(*tasks)

try:
  lastMonitored = pickle.load(open('lastMonitored.p', 'rb'))
except:
  lastMonitored = None

async def monitor():
  """Checks the configured range periodically"""

  global lastMonitored

  while True:
    if lastMonitored != None:
      diff = (datetime.now()-lastMonitored).seconds
    else:
      diff = config['monitor']['interval']
    
    if diff >= config['monitor']['interval']:
      await checkRange(config['monitor']['start'], config['monitor']['end'])

      lastMonitored=datetime.now()
      pickle.dump(lastMonitored, open('lastMonitored.p', 'wb'))
      
      await asyncio.sleep(config['monitor']['interval'])

    await asyncio.sleep(config['monitor']['interval']-diff)

bot.run(config['discord']['token'])

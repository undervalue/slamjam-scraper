import aiosqlite
import sqlite3
import asyncio
import pickle

from product import Product

aiosqlite.register_converter('pickle', pickle.loads)
aiosqlite.register_adapter(Product, pickle.dumps)
dbfile = 'cache.sqlite'

async def initialize():
  """Initializes the database"""

  async with aiosqlite.connect(dbfile) as db:
    await db.execute("""
      create table if not exists products (
        pid       text not null unique,
        data      pickle not null,
        wishlist  boolean not null,
        check     (wishlist in(0,1))
    );
    """)
    
    await db.commit()

async def insert(pid, product, wishlist):
  """Inserts a product on the database"""

  try:
    async with aiosqlite.connect(dbfile) as db:
      await db.execute("""
        insert into
          products (pid, data, wishlist)
          values (?, ?, ?)
      """, (pid, product, wishlist))
      
      await db.commit()

  except sqlite3.IntegrityError as e:
    print(f'Failed to insert {pid} to database: {e}')

async def select(pid, wishlist=False):
  """Selects a product from the database"""

  async with aiosqlite.connect(dbfile, detect_types=sqlite3.PARSE_DECLTYPES) as db:
    sql = 'select * from products where pid = ?'
    
    async with db.execute(sql, (pid,)) as cursor:
      res = await cursor.fetchone()
      if res == None: return

      pid, data, isWishlist = res

      if wishlist:
        return data if isWishlist else None

      return data

async def update(pid, product, wishlist):
  """Updates a product on the database"""

  async with aiosqlite.connect(dbfile) as db:
    await db.execute("""
      update products set
        data = ?,
        wishlist = ?
      where
        pid = ?
    """, (product, wishlist, pid))

    await db.commit()

from dataclasses import dataclass
from typing import Optional
from datetime import date
from discord import Embed

from config import config

@dataclass()
class Product():
  pid: str
  name: str
  brand: str
  createdAt: date
  price: Optional[str] = None
  image: Optional[str] = None
  sizes: Optional[dict] = None
  wishlist: bool = False
  
  def get_embed(self, new=False):
    e = Embed(
      title=self.name,
      description=f'**Fetched PID:** {self.pid}\n\n**Brand:** {self.brand}\n**Price:** {self.price}',
      color=config['discord']['embedColor']['normal']
    )
    
    if self.image != None:
      e.set_thumbnail(url=self.image)

    if self.sizes != None and not new:
      e.add_field(name='Sizes:', value='\n'.join(f"`{k}`" for k in self.sizes.keys()))
      e.add_field(name='Checkout PIDs:', value='\n'.join(f"`{v['id']}`" for v in self.sizes.values()))
      e.add_field(name='Availability:', value='\n'.join('`🟩`' if v['instock'] else '`🟥`' for v in self.sizes.values()))

    return e

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class Product:
    url: str
    sizes: List[str]
    store: str
    name: Optional[str] = None
    price: Optional[str] = None
    last_check: Optional[datetime] = None
    channel_id: Optional[int] = None
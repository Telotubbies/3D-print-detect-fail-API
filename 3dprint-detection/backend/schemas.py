from pydantic import BaseModel
from typing import Dict

class Card(BaseModel):
    card_id: str
    detected_image_url: str
    status: str
    scores: Dict[str, float] | None = None
    updated_at: str
    model: str

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.template_suggestion import SuggestionType, SuggestionStatus
 
 
class TemplateSuggestionBase(BaseModel):
    type: SuggestionType
    content: str
 
 
class TemplateSuggestionCreate(TemplateSuggestionBase):
    pass  # id_user se obtiene del token JWT
 
 
class TemplateSuggestionUpdate(BaseModel):
    status: Optional[SuggestionStatus] = None
 
 
class TemplateSuggestionResponse(TemplateSuggestionBase):
    id_suggestion: int
    id_user: int
    status: SuggestionStatus
    id_admin: Optional[int] = None
    date: datetime
 
    model_config = {"from_attributes": True}
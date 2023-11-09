from typing import Optional
from pydantic import BaseModel
from fastapi import UploadFile
from datetime import datetime
from bson import ObjectId

class User(BaseModel):
    username: str = ""
    email: str = ""
    password: str = ""

class Token(BaseModel):
    access_token: str = ""
    token_type: str = ""


class TokenData(BaseModel):
    email: Optional[str] = None

class POSTS(BaseModel):
    id: str = ""
    username: str = ""
    texts: Optional[str]=None
    image_url: Optional[str]=None

class PostCreation(BaseModel):
    username: str = ""
    texts: str = ""
    image_file: Optional[UploadFile]=None

class Notification(BaseModel):
    username:str = ""
    timeStamp: datetime 
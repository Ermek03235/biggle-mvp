from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

app = FastAPI(title="Biggle API (MVP)")

class SignupIn(BaseModel):
    email: str
    password: str

class LoginIn(BaseModel):
    email: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ChatIn(BaseModel):
    text: str

class ChatOut(BaseModel):
    reply: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth/signup", response_model=TokenOut)
def signup(data: SignupIn):
    # Заглушка: всегда "успех"
    return TokenOut(access_token="fake-signup-token")

@app.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn):
    # Заглушка: всегда "успех"
    return TokenOut(access_token="fake-login-token")

@app.post("/chat/message", response_model=ChatOut)
def chat_message(data: ChatIn, authorization: Optional[str] = Header(default=None)):
    # Простейшая проверка токена (заглушка)
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    # Эхо-ответ как MVP
    return ChatOut(reply=f"Biggle: ты сказал — '{data.text}'")

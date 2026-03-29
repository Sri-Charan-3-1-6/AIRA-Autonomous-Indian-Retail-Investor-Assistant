"""AIRA module: api/user.py"""

from fastapi import APIRouter, HTTPException

from db.crud import create_user, get_user
from models.user import User, UserCreate

router = APIRouter()


@router.post("/register", response_model=User)
async def register_user(payload: UserCreate) -> User:
    try:
        return await create_user(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{user_id}", response_model=User)
async def fetch_user(user_id: str) -> User:
    user = await get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

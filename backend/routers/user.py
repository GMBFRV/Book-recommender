from fastapi import APIRouter
router = APIRouter(tags=["filters"])
from fastapi import APIRouter

# ---------------------------------------------------- Users -----------------------------------------------------------

@router.get("/registration")
def registration():
    return {"Registration form"}

@router.get("/login")
def login():
    return {"Login"}

@router.get("/user")
def user():
    return {"User information"}
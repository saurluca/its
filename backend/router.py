from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def read_root():
    return {"status": "ok"}


@router.get("/health")
async def health_check():
    return {"status": "ok"}

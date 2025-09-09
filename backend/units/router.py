from uuid import UUID
from backend.units.models import Unit
from fastapi import APIRouter


router = APIRouter(prefix="/units", tags=["units"])


@router.get("")
async def get_units():
    return {"status": "ok"}


@router.get("/{unit_id}")
async def get_unit(unit_id: UUID):
    return {"status": "ok"}


@router.post("")
async def create_unit(unit: Unit):
    return {"status": "ok"}


@router.patch("/{unit_id}")
async def update_unit(unit_id: UUID, unit: Unit):
    return {"status": "ok"}


@router.delete("/{unit_id}")
async def delete_unit(unit_id: UUID):
    return {"status": "ok"}

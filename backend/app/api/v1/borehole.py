from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.borehole import Borehole

router = APIRouter()

@router.get("/")
async def get_boreholes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取钻孔列表"""
    boreholes = db.query(Borehole).offset(skip).limit(limit).all()
    return boreholes

@router.get("/{borehole_id}")
async def get_borehole(borehole_id: int, db: Session = Depends(get_db)):
    """获取单个钻孔详情"""
    borehole = db.query(Borehole).filter(Borehole.id == borehole_id).first()
    if not borehole:
        raise HTTPException(status_code=404, detail="Borehole not found")
    return borehole

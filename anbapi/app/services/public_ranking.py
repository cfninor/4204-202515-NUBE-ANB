import os
import json
from typing import List

import redis
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Video, VideoVote, User

router = APIRouter(prefix="/api/public", tags=["public_ranking"])

_redis_client = None


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(url, decode_responses=True)
    return _redis_client


@router.get("/ranking")
def ranking(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    ttl = int(os.getenv("RANKING_CACHE_TTL_SECONDS", "120"))
    offset = (page - 1) * size

    cache_key = f"ranking:page:{page}:size:{size}"
    r = get_redis_client()
    cached = None
    try:
        cached = r.get(cache_key)
    except Exception:
        cached = None

    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    subq = (
        db.query(
            Video.id.label("video_id"),
            Video.user_id.label("user_id"),
            func.count(VideoVote.id).label("votes"),
        )
        .join(VideoVote, Video.id == VideoVote.video_id)
        .group_by(Video.id)
        .subquery()
    )

    q = (
        db.query(
            subq.c.video_id,
            subq.c.votes,
            User.user_name.label("username"),
            User.city.label("city"),
        )
        .join(User, User.id == subq.c.user_id)
        .order_by(subq.c.votes.desc())
        .offset(offset)
        .limit(size)
    )

    results = q.all()

    items: List[dict] = []
    for idx, row in enumerate(results, start=1):
        position = offset + idx
        items.append(
            {
                "position": position,
                "username": row.username,
                "city": row.city,
                "votes": int(row.votes),
            }
        )

    payload = json.dumps(items)
    try:
        r.setex(cache_key, ttl, payload)
    except Exception:
        pass

    return items

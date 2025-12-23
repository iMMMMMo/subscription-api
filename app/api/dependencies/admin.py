from fastapi import Depends, HTTPException, status

from app.core.security import get_current_subject
from app.db.session import get_session
from app.services.user_service import get_user_by_id


async def require_superuser(
    subject: str = Depends(get_current_subject),
    session = Depends(get_session),
):
    try:
        user_id = int(subject)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    user = await get_user_by_id(session, user_id)
    if not user or not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return user

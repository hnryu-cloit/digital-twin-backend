from fastapi import APIRouter, Depends, HTTPException, Response, status
from jose import JWTError

from app.core.dependencies import get_current_user_id
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshTokenRequest, TokenResponse, UserResponse
from app.services.mock_store import store

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = store.get_user_by_email(body.email)
    if user is None or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    response_user = UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        is_active=user["is_active"],
    )
    return TokenResponse(
        access_token=create_access_token(user["id"]),
        refresh_token=create_refresh_token(user["id"]),
        user=response_user,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshTokenRequest):
    if body.refresh_token in store.revoked_refresh_tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked.")

    try:
        payload = decode_token(body.refresh_token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.") from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token is required.")

    user = store.get_user(payload.get("sub", ""))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    return TokenResponse(
        access_token=create_access_token(user["id"]),
        refresh_token=create_refresh_token(user["id"]),
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            is_active=user["is_active"],
        ),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        payload = decode_token(body.refresh_token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.") from exc

    if payload.get("type") != "refresh" or payload.get("sub") != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject mismatch.")

    store.revoked_refresh_tokens.add(body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

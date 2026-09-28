"""API Router for User Registration, Login, and Session Authentication using Redis."""

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.auth_service import (
    AuthError,
    AuthService,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from .dependencies import get_auth_service, get_current_user_id
from .schemas import (
    AuthResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    body: UserRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user account with Redis storage."""
    try:
        result = auth_service.register(
            username=body.username,
            password=body.password,
            display_name=body.display_name,
        )
        return AuthResponse(
            success=True,
            token=result["token"],
            user=UserResponse(
                user_id=result["user_id"],
                username=result["username"],
                display_name=result["display_name"],
                created_at=result["created_at"],
            ),
            message="注册并登录成功",
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"注册异常: {exc}")


@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
def login_user(
    body: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate with username and password, returns session token."""
    try:
        result = auth_service.login(
            username=body.username,
            password=body.password,
        )
        return AuthResponse(
            success=True,
            token=result["token"],
            user=UserResponse(
                user_id=result["user_id"],
                username=result["username"],
                display_name=result["display_name"],
                created_at=result["created_at"],
            ),
            message="登录成功",
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"登录异常: {exc}")


@router.get("/me", response_model=UserResponse)
def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Retrieve currently authenticated user profile."""
    token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None
    if not token:
        token = request.headers.get("X-API-Key") or request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供身份凭证")

    user_data = auth_service.get_user_by_token(token)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="凭证无效或已过期，请重新登录")

    return UserResponse(
        user_id=user_data["user_id"],
        username=user_data["username"],
        display_name=user_data["display_name"],
        created_at=user_data.get("created_at"),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Log out and revoke current session token from Redis."""
    token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None
    if not token:
        token = request.headers.get("X-API-Key") or request.query_params.get("token")

    if token:
        auth_service.logout(token)

    return {"success": True, "message": "已安全退出登录"}

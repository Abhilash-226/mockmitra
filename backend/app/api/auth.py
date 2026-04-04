from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from beanie import PydanticObjectId
import httpx
from pydantic import BaseModel, EmailStr

from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, UserLogin, LoginResponse, GoogleAuth

router = APIRouter()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    target_exam: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/register", response_model=LoginResponse)
async def register(user_data: UserCreate):
    """Register a new user"""
    # Check if email exists
    existing_user = await User.find_one(User.email == user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        target_exam=user_data.target_exam
    )
    await user.insert()
    
    # Create token and return with user
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            _id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            target_exam=user.target_exam,
            is_active=user.is_active,
            created_at=user.created_at,
            auth_provider=user.auth_provider,
            profile_picture=user.profile_picture
        )
    )


@router.post("/login", response_model=LoginResponse)
async def login(credentials: UserLogin):
    """Login with JSON body and get access token + user info"""
    # Find user
    user = await User.find_one(User.email == credentials.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user signed up with Google (no password)
    if user.auth_provider == "google" and not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses Google Sign-In. Please use 'Continue with Google' to login."
        )
    
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            _id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            target_exam=user.target_exam,
            is_active=user.is_active,
            created_at=user.created_at,
            auth_provider=user.auth_provider,
            profile_picture=user.profile_picture
        )
    )


@router.post("/token", response_model=Token)
async def login_for_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token endpoint (form data)"""
    user = await User.find_one(User.email == form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user_id: str = Depends(get_current_user)):
    """Get current user info"""
    user = await User.get(PydanticObjectId(user_id))
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        _id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        target_exam=user.target_exam,
        is_active=user.is_active,
        created_at=user.created_at,
        auth_provider=user.auth_provider,
        profile_picture=user.profile_picture
    )


@router.post("/google", response_model=LoginResponse)
async def google_auth(data: GoogleAuth):
    """Authenticate with Google OAuth"""
    # Verify Google ID token
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={data.credential}"
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Google token"
                )
            
            google_data = response.json()
            
            # Verify the token is for our app (optional but recommended)
            if settings.GOOGLE_CLIENT_ID and google_data.get("aud") != settings.GOOGLE_CLIENT_ID:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token not issued for this application"
                )
            
            email = google_data.get("email")
            google_id = google_data.get("sub")
            full_name = google_data.get("name")
            profile_picture = google_data.get("picture")
            
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email not provided by Google"
                )
    
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to verify Google token"
        )
    
    # Check if user exists
    user = await User.find_one(User.email == email)
    
    if user:
        # Update Google info if user exists but signed up with different method
        if user.auth_provider == "local":
            user.auth_provider = "google"
            user.google_id = google_id
            user.profile_picture = profile_picture
            if not user.full_name and full_name:
                user.full_name = full_name
            await user.save()
        elif user.google_id != google_id:
            # Update profile picture if changed
            user.profile_picture = profile_picture
            await user.save()
    else:
        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            auth_provider="google",
            google_id=google_id,
            profile_picture=profile_picture,
            is_verified=True  # Google accounts are verified by default
        )
        await user.insert()
    
    # Create token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            _id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            target_exam=user.target_exam,
            is_active=user.is_active,
            created_at=user.created_at,
            auth_provider=user.auth_provider,
            profile_picture=user.profile_picture
        )
    )


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    """Accepted endpoint for frontend parity. Email dispatch should be integrated externally."""
    user = await User.find_one(User.email == data.email)
    if not user:
        # Do not leak account existence.
        return {"message": "If an account exists, a reset link has been sent."}
    return {"message": "If an account exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(_data: ResetPasswordRequest):
    """Password reset token flow placeholder. Requires external token issuance mechanism."""
    return {
        "message": "Password reset token flow is not configured. Use change-password after login."
    }


@router.post("/verify-email")
async def verify_email(_data: VerifyEmailRequest):
    """Email verification placeholder endpoint for frontend parity."""
    return {"message": "Email verification flow is not configured."}


@router.put("/me", response_model=UserResponse)
async def update_profile(data: UpdateProfileRequest, user_id: str = Depends(get_current_user)):
    user = await User.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.target_exam is not None:
        user.target_exam = data.target_exam
    await user.save()

    return UserResponse(
        _id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        target_exam=user.target_exam,
        is_active=user.is_active,
        created_at=user.created_at,
        auth_provider=user.auth_provider,
        profile_picture=user.profile_picture,
    )


@router.put("/change-password")
async def change_password(data: ChangePasswordRequest, user_id: str = Depends(get_current_user)):
    user = await User.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.auth_provider == "google" and not user.hashed_password:
        raise HTTPException(status_code=400, detail="Google sign-in account has no local password")
    if not user.hashed_password or not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.hashed_password = get_password_hash(data.new_password)
    await user.save()
    return {"message": "Password updated successfully"}

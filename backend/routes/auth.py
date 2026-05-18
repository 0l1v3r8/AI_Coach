import os
import requests
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models import schema
from backend.core.dependencies import get_current_user

# Create a router to organize our auth endpoints
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Pydantic model for incoming Intervals request
class IntervalsRequest(BaseModel):
    api_key: str

@router.get("/strava/login")
def strava_login():
    """Step 1: Redirect the user to Strava's authorization page."""
    client_id = os.getenv("STRAVA_CLIENT_ID")
    base_url = os.getenv("NEXT_PUBLIC_BASE_URL", "http://localhost:8000")
    redirect_uri = f"{base_url}/api/auth/strava/callback"
    
    scope = "activity:read_all,profile:read_all"
    auth_url = f"https://www.strava.com/oauth/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&approval_prompt=force&scope={scope}"
    
    return RedirectResponse(auth_url)

@router.get("/strava/callback")
def strava_callback(code: str = None, error: str = None, db: Session = Depends(get_db)):
    """Step 2: Catch the callback from Strava and exchange the code for tokens."""
    if error or not code:
        return RedirectResponse("/?error=strava_denied")

    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")

    res = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code"
    })

    data = res.json()
    if "access_token" not in data:
        return RedirectResponse("/?error=strava_token_failed")

    # NOTE: For this specific OAuth redirect prototype, we default to the active user.
    # In a fully multi-tenant production app, we would pass the JWT in the OAuth 'state' param.
    user = db.query(schema.User).first()
    if user:
        user.stravaAccessToken = data["access_token"]
        user.stravaRefreshToken = data["refresh_token"]
        user.stravaAthleteId = str(data["athlete"]["id"])
        db.commit()

    return RedirectResponse("/?success=strava_connected")

@router.get("/google/login")
def google_login():
    """Redirect to Google's OAuth consent screen."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = f"{os.getenv('NEXT_PUBLIC_BASE_URL', 'http://localhost:8000')}/api/auth/google/callback"
    scope = "openid email profile"
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"
    return RedirectResponse(auth_url)

@router.get("/google/callback")
def google_callback(code: str = None, db: Session = Depends(get_db)):
    """Exchange code for Google user info and issue a JWT."""
    if not code:
        return RedirectResponse("/?error=google_denied")

    # 1. Exchange the code for a token
    token_response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": f"{os.getenv('NEXT_PUBLIC_BASE_URL', 'http://localhost:8000')}/api/auth/google/callback"
    })
    
    token_res = token_response.json()

    # 2. CHECK FOR ERRORS BEFORE PROCEEDING
    if "access_token" not in token_res:
        # Print the exact error to the backend terminal so you know how to fix it!
        print("\n" + "="*50)
        print("🚨 GOOGLE OAUTH ERROR 🚨")
        print(f"Google responded with: {token_res}")
        print("Check your .env variables and Authorized Redirect URIs in Google Cloud Console.")
        print("="*50 + "\n")
        return RedirectResponse("/?error=google_token_failed")

    # 3. Fetch user profile from Google
    user_info_res = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {token_res['access_token']}"}
    ).json()

    # 4. Database operations
    user = db.query(schema.User).filter(schema.User.email == user_info_res["email"]).first()
    if not user:
        user = schema.User(
            googleId=user_info_res["id"],
            email=user_info_res["email"],
            name=user_info_res.get("name", "Athlete")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 5. Generate your local JWT
    payload = {
        "sub": str(user.id),
        "exp": datetime.now(timezone.utc) + timedelta(days=30)
    }
    # Ensure JWT_SECRET has a fallback if missing, to prevent another potential crash
    jwt_secret = os.getenv("JWT_SECRET", "super-secret-fallback-key-change-in-production")
    jwt_token = jwt.encode(payload, jwt_secret, algorithm="HS256")

    return RedirectResponse(f"/?token={jwt_token}")

@router.post("/intervals")
def connect_intervals(req: IntervalsRequest, db: Session = Depends(get_db), user: schema.User = Depends(get_current_user)):
    """Save the Intervals.icu API Key securely using the JWT token."""
    if not req.api_key:
        raise HTTPException(status_code=400, detail="API Key required")

    user.intervalsApiKey = req.api_key
    db.commit()
        
    return {"success": True, "message": "Intervals.icu connected"}
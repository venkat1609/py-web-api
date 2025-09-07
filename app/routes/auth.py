from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from fastapi.responses import RedirectResponse
from app.models.user import User, UserOut, LoginRequest, UserResponse
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, get_current_user
from app.db.mongo import db
from app.utils.helpers import fix_id  # assuming you use the helper
from typing import Union, List
from pydantic import BaseModel
import httpx
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os
import random
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Ensure .env is loaded before accessing environment variables below
load_dotenv()

router = APIRouter()
security = HTTPBasic()
bearer_scheme = HTTPBearer()
collection = db["users"]
client = os.getenv("GOOGLE_CLIENT_ID")
smtp_email = os.getenv("SMTP_EMAIL")
smtp_password = os.getenv("SMTP_PASSWORD")


class TokenPayload(BaseModel):
    id_token: str


def generate_verification_code():
    return "{:06d}".format(random.randint(0, 999999))  # Always 6 digits, leading


def send_verification_email(recipient_email: str, email_content: str, alt_text: str):
    EMAIL_ADDRESS = smtp_email
    EMAIL_PASSWORD = smtp_password

    msg = EmailMessage()
    msg["Subject"] = "Your Email Verification Code"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient_email

    # Plain text fallback
    text = alt_text

    # HTML content
    html = email_content

    # Plain text fallback for email clients that don't render HTML
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")  # Add the HTML part

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)


@router.post("/register")
async def register(user: User):

    # Check for existing email
    existing_email = await collection.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate verification code and hash password
    email_verification_code = generate_verification_code()
    hashed_password = hash_password(user.password)

    # Create user document and insert
    user_data = {
        "email": user.email,
        "email_verification_code": email_verification_code,
        "is_email_verified": False,
        "hashed_password": hashed_password,
        "first_name": "",
        "last_name": "",
        "user_name": "",
        "date_of_birth": "",
        "profile_image": "",
        "phone": "",
        "phone_verification_code": "",
        "is_phone_verified": False,
    }

    await collection.insert_one(user_data)

    # Plain text fallback
    text = f"Your email verification code is: {email_verification_code}"

    # HTML content
    html = f"""
    <html>
      <body>
        <h2>Email Verification</h2>
        <p>Your verification code is:</p>
        <h3 style="color:blue;">{email_verification_code}</h3>
      </body>
    </html>
    """

    # Sending verification email (consider running in a background thread/task)
    send_verification_email(user_data["email"], html, text)
    access_token = create_access_token(data={"sub": user_data["email"]})

    # Create response to force email verification step
    user = {
        "id": str(user_data["_id"]),
        "email": user_data["email"],
        "is_email_verified": user_data.get("is_email_verified", False),
        "access_token": access_token,
    }

    return user


@router.post("/verify-email")
async def verify_email(email: str = Query(...), code: str = Query(...)):
    user = await collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("is_email_verified", False):
        raise HTTPException(status_code=400, detail="Email already verified")
    if user["email_verification_code"] != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    await collection.update_one(
        {"email": email},
        {"$set": {"is_email_verified": True, "email_verification_code": ""}},
    )

    access_token = create_access_token(data={"sub": user["email"]})
    user_data = {
        "id": str(user["_id"]),
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "user_name": user.get("user_name", ""),
        "email": user["email"],
        "phone_number": user.get("phone_number", ""),
        "date_of_birth": user.get("date_of_birth", ""),
        "profile_image": user.get("profile_image", ""),
        "is_phone_verified": user.get("is_phone_verified", False),
        "is_email_verified": True,
        "access_token": access_token,
    }

    return user_data


@router.post("/login")
async def login(credentials: LoginRequest):
    user = await collection.find_one({"email": credentials.email})
    print(user)
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user["email"]})

    user_data = {
        "id": str(user["_id"]),
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "user_name": user.get("user_name", ""),
        "email": user["email"],
        "phone_number": user.get("phone_number", ""),
        "date_of_birth": user.get("date_of_birth", ""),
        "profile_image": user.get("profile_image", ""),
        "is_phone_verified": user.get("is_phone_verified", False),
        "is_email_verified": user.get("is_email_verified", False),
        "access_token": access_token,
    }

    return user_data


@router.post("/google/token")
async def google_login_token(payload: TokenPayload):
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.id_token, google_requests.Request(), client
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    # Check for existing email
    existing_email = await collection.find_one({"email": idinfo.get("email")})
    if existing_email:
        user = await collection.find_one({"email": existing_email["email"]})

        access_token = create_access_token(data={"sub": user["email"]})

        user_data = {
            "id": str(user["_id"]),
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "user_name": user["user_name"],
            "email": user["email"],
            "phone_number": user["phone_number"],
            "date_of_birth": user["date_of_birth"],
            "profile_image": user["profile_image"],
            "is_phone_verified": user["is_phone_verified"],
            "is_email_verified": user["is_email_verified"],
            "access_token": access_token,
        }

        return user_data

    else:
        user_data = {
            "email": idinfo.get("email"),
            "email_verification_code": "",
            "is_email_verified": True,
            "hashed_password": None,
            "first_name": idinfo.get("given_name"),
            "last_name": idinfo.get("family_name"),
            "user_name": None,
            "date_of_birth": None,
            "profile_image": idinfo.get("picture"),
            "phone": None,
            "phone_verification_code": "",
            "is_phone_verified": False,
        }

        await collection.insert_one(user_data)

        access_token = create_access_token(data={"sub": user_data["email"]})

        user = {
            "id": str(user_data["_id"]),
            "email": user_data["email"],
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "user_name": user_data["user_name"],
            "phone": user_data["phone"],
            "date_of_birth": user_data["date_of_birth"],
            "profile_image": user_data["profile_image"],
            "is_phone_verified": user_data["is_phone_verified"],
            "is_email_verified": user_data["is_email_verified"],
            "access_token": access_token,
        }

        return user

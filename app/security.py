import jwt
import bcrypt
from datetime import datetime, timedelta, timezone

# Production-grade configuration variables
SECRET_KEY = "SUPER_SECRET_ALGORITHM_KEY_CHANGE_THIS_IN_PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def hash_password(password: str) -> str:
    # 1. Convert password string into raw system bytes
    password_bytes = password.encode('utf-8')
    # 2. Generate a random cryptographic salt noise pattern
    salt = bcrypt.gensalt()
    # 3. Hash the bytes and decode back into a clean string for storage
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Convert both fields to raw system bytes and compare safely
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return str(encoded_jwt)

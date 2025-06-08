import bcrypt
import os

PASSWORD_FILE = "config/password.hash"

def create_password(password: str):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    os.makedirs("config", exist_ok=True)
    with open(PASSWORD_FILE, "wb") as f:
        f.write(hashed)

def verify_password(password: str) -> bool:
    if not os.path.exists(PASSWORD_FILE):
        return False
    with open(PASSWORD_FILE, "rb") as f:
        hashed = f.read()
    return bcrypt.checkpw(password.encode(), hashed)

def is_password_set() -> bool:
    return os.path.exists(PASSWORD_FILE)

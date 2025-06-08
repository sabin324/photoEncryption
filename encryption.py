import os
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PIL import Image
import io

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(password.encode())

def encrypt_file(filepath: str, password: str, output_dir: str):
    with open(filepath, "rb") as f:
        data = f.read()

    salt = os.urandom(16)
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    encrypted = aesgcm.encrypt(nonce, data, None)

    os.makedirs(output_dir, exist_ok=True)
    outpath = os.path.join(output_dir, os.path.basename(filepath) + ".enc")
    with open(outpath, "wb") as f:
        f.write(salt + nonce + encrypted)

def decrypt_file(encrypted_path: str, password: str) -> bytes:
    with open(encrypted_path, "rb") as f:
        content = f.read()
    salt, nonce, encrypted = content[:16], content[16:28], content[28:]
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, encrypted, None)

def generate_thumbnail(image_data: bytes, size=(100, 100)):
    from PIL import Image
    import io

    try:
        img = Image.open(io.BytesIO(image_data))
        img = img.convert("RGB")  # ensure consistent mode
        img.thumbnail(size)
        return img
    except Exception as e:
        print(f"[Thumbnail Error] {e}")
        return None


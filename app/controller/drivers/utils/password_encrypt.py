# utils/password_crypto.py
import base64
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import hashlib

class PasswordCrypto:
    """Symmetric encryption untuk password"""
    
    # KEY harus 16, 24, atau 32 bytes untuk AES
    SECRET_KEY = os.environ.get('PASSWORD_ENCRYPTION_KEY')
    
    @staticmethod
    def _get_key():
        """Generate 32-byte key dari secret"""
        # Hash secret untuk dapat 32 byte
        key = hashlib.sha256(PasswordCrypto.SECRET_KEY.encode()).digest()
        return key
    
    @staticmethod
    def encrypt(plain_text: str) -> str:
        """Encrypt password dengan AES-CBC"""
        if not plain_text:
            return ""
        
        try:
            key = PasswordCrypto._get_key()
            iv = get_random_bytes(16)  # Initialization vector
            
            cipher = AES.new(key, AES.MODE_CBC, iv)
            padded_text = pad(plain_text.encode(), AES.block_size)
            encrypted = cipher.encrypt(padded_text)
            
            # Gabungkan IV + encrypted data, encode ke base64
            combined = iv + encrypted
            return base64.b64encode(combined).decode('utf-8')
            
        except Exception as e:
            print(f"[PasswordCrypto] Encryption failed: {e}")
            return ""
    
    @staticmethod
    def decrypt(encrypted_text: str) -> str:
        """Decrypt password dari AES-CBC"""
        if not encrypted_text:
            return ""
        
        try:
            key = PasswordCrypto._get_key()
            combined = base64.b64decode(encrypted_text.encode())
            
            # Pisahkan IV (16 byte pertama) dan encrypted data
            iv = combined[:16]
            encrypted = combined[16:]
            
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted_padded = cipher.decrypt(encrypted)
            plain_text = unpad(decrypted_padded, AES.block_size)
            
            return plain_text.decode('utf-8')
            
        except Exception as e:
            print(f"[PasswordCrypto] Decryption failed: {e}")
            return ""
    
    @staticmethod
    def is_encrypted(text: str) -> bool:
        """Cek apakah text terenkripsi dengan AES"""
        if not text:
            return False
        
        try:
            # Coba decode base64
            decoded = base64.b64decode(text.encode())
            # AES encrypted minimal 32 bytes (16 IV + min 16 data)
            return len(decoded) >= 32
        except:
            return False
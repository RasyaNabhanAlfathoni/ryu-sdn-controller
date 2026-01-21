# utils/password_hash.py
import hashlib
import bcrypt
import base64
import os
from typing import Union

class PasswordHasher:
    """Utility class untuk hashing password"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """ Hash password menggunakan bcrypt (recommended) """
        if not password or password.strip() == "":
            return ""
        
        # Generate salt dan hash dengan bcrypt
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """ Verifikasi password dengan hash yang tersimpan """
        if not hashed_password or hashed_password.strip() == "":
            return False
        
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False
    
    @staticmethod
    def hash_sha256(password: str) -> str:
        """ Alternatif: Hash menggunakan SHA-256 dengan salt """
        if not password or password.strip() == "":
            return ""
        
        # Tambah salt
        salt = os.urandom(32)
        pwd_bytes = password.encode('utf-8')
        
        # Hash password + salt
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            pwd_bytes,
            salt,
            100000  # Iterasi
        )
        
        # Gabungkan salt dan hash
        combined = salt + hashed
        
        # Encode ke base64 untuk penyimpanan
        return base64.b64encode(combined).decode('utf-8')
    
    @staticmethod
    def verify_sha256(plain_password: str, hashed_password: str) -> bool:
        """ Verifikasi password SHA-256 """
        if not hashed_password or hashed_password.strip() == "":
            return False
        
        try:
            # Decode dari base64
            decoded = base64.b64decode(hashed_password.encode('utf-8'))
            
            # Ekstrak salt (32 byte pertama) dan hash (sisa)
            salt = decoded[:32]
            stored_hash = decoded[32:]
            
            # Hash password input dengan salt yang sama
            pwd_bytes = plain_password.encode('utf-8')
            hashed = hashlib.pbkdf2_hmac(
                'sha256',
                pwd_bytes,
                salt,
                100000
            )
            
            return hashed == stored_hash
        except Exception:
            return False
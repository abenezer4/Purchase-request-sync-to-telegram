from cryptography.fernet import Fernet
import os
import base64
from .config import ENCRYPTION_KEY

class CryptoManager:
    def __init__(self):
        key = ENCRYPTION_KEY
        if not key:
            raise ValueError("ENCRYPTION_KEY must be set in environment variables")
        
        # Ensure key is properly formatted for Fernet (32 url-safe base64-encoded bytes)
        try:
            self.cipher_suite = Fernet(key)
        except Exception as e:
            raise ValueError(f"Invalid ENCRYPTION_KEY: {e}")

    def encrypt(self, plain_text: str) -> str:
        if not plain_text:
            return ""
        encrypted_bytes = self.cipher_suite.encrypt(plain_text.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    def decrypt(self, encrypted_text: str) -> str:
        if not encrypted_text:
            return ""
        decrypted_bytes = self.cipher_suite.decrypt(encrypted_text.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')

crypto_manager = CryptoManager()

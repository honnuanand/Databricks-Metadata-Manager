#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta
from jose import jwt

# Use the SECRET_KEY from Databricks secrets
SECRET_KEY = "LrM0Shhrw0MhIzRtQhbUF30o4dTjE4d5m6PRDZhGUPM"
ALGORITHM = "HS256"

# Create a token
data = {"sub": "test-user", "type": "access"}
expire = datetime.utcnow() + timedelta(minutes=480)
data.update({"exp": expire})

token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
print(f"Generated token: {token[:50]}...")

# Immediately try to decode it
try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print(f"\n✅ Token decoded successfully!")
    print(f"Payload: {payload}")
except Exception as e:
    print(f"\n❌ Token decode failed: {e}")


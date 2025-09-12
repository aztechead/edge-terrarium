#!/usr/bin/env python3
"""
test-db-app - Test app with database
"""

import asyncio
from fastapi import FastAPI, HTTPException
import os
from datetime import datetime
from typing import List, Dict
import psycopg2

app = FastAPI(
    title="test-db-app",
    description="Test app with database",
    version="1.0.0"
)

# Database configuration from environment variables
DB_HOST = os.getenv("POSTGRES_DB_HOST", "test-db-app-db")
DB_PORT = os.getenv("POSTGRES_DB_PORT", "5432")
DB_USER = os.getenv("POSTGRES_DB_USER", "test-db-app_user")
DB_PASSWORD = os.getenv("POSTGRES_DB_PASSWORD", "default_password")
DB_NAME = os.getenv("POSTGRES_DB_NAME", "test_app_db")

def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise

@app.get("/")
async def root():
    return {"message": "Hello from test-db-app!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/db/test")
async def db_test():
    """Test database connectivity and return sample data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get database version
        cursor.execute("SELECT version()")
        db_version = cursor.fetchone()[0]
        
        # Get test messages
        cursor.execute("SELECT id, message, created_at FROM test_messages ORDER BY created_at DESC LIMIT 5")
        messages = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "database_version": db_version,
            "test_data": [
                {
                    "id": msg[0],
                    "message": msg[1],
                    "created_at": msg[2].isoformat() if msg[2] else None
                }
                for msg in messages
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database test failed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

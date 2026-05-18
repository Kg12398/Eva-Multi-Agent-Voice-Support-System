import asyncio
import os
import sys
from sqlalchemy import text
from app.services.db_service import db_service

async def migrate():
    print("--- DATABASE MIGRATION ---")
    await db_service.connect()
    
    queries = [
        "ALTER TABLE call_records ADD COLUMN IF NOT EXISTS customer_name VARCHAR;",
        "ALTER TABLE call_records ADD COLUMN IF NOT EXISTS contact_number VARCHAR;",
        "ALTER TABLE call_records ADD COLUMN IF NOT EXISTS city VARCHAR;",
        "ALTER TABLE call_records ADD COLUMN IF NOT EXISTS error_code VARCHAR;",
        
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS contact_number VARCHAR;",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS city VARCHAR;",
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS error_code VARCHAR;"
    ]
    
    async with db_service._engine.begin() as conn:
        for query in queries:
            try:
                await conn.execute(text(query))
                print(f"Executed: {query}")
            except Exception as e:
                print(f"Error executing {query}: {e}")
                
    await db_service.disconnect()
    print("Migration finished!")

if __name__ == "__main__":
    asyncio.run(migrate())

"""
Migration script to add leverage column to trades table
Run this script once to update your existing database
"""

import sqlite3
import sys

def add_leverage_column():
    try:
        # Connect to database
        conn = sqlite3.connect('trading_system.db')
        cursor = conn.cursor()
        
        # Check if leverage column already exists
        cursor.execute("PRAGMA table_info(trades)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'leverage' in columns:
            print("Leverage column already exists. No migration needed.")
            return
        
        # Add leverage column
        print("Adding leverage column to trades table...")
        cursor.execute("""
            ALTER TABLE trades 
            ADD COLUMN leverage INTEGER DEFAULT 1
        """)
        
        conn.commit()
        print("Successfully added leverage column!")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(trades)")
        columns = cursor.fetchall()
        print("\nUpdated table structure:")
        for col in columns:
            print(f"  {col[1]} - {col[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    add_leverage_column()
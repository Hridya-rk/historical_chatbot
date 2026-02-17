import sqlite3

# 1️⃣ Connect to database (creates file if it doesn't exist)
conn = sqlite3.connect("historical_chatbot.db")

# 2️⃣ Create cursor
cursor = conn.cursor()

# 3️⃣ Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    history TEXT,
    culture TEXT,
    architecture TEXT,
    best_time TEXT4          
)
""")

# 4️⃣ Save changes
conn.commit()

# 5️⃣ Close connection
conn.close()

print("✅ Database and table created successfully")

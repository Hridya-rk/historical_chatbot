import sqlite3

conn = sqlite3.connect("historical_chatbot.db")
cursor = conn.cursor()

cursor.execute("""
INSERT OR IGNORE INTO places (
    name, history, culture, architecture, best_time
) VALUES (?, ?, ?, ?, ?)
""", (
    "hampi",
    "Hampi was the capital of the Vijayanagara Empire in the 14th century and is now a UNESCO World Heritage Site.",
    "Hampi has a rich cultural heritage influenced by South Indian traditions, temples, and festivals.",
    "Hampi is famous for its Dravidian-style temples, stone chariots, and massive ruins.",
    "The best time to visit Hampi is from October to February due to ."
    
))

conn.commit()
conn.close()

print("✅ Hampi data inserted successfully")

from flask import Flask, request, jsonify
import requests
import urllib.parse
from difflib import get_close_matches
import json
import sqlite3
import os
import sys
from groq import Groq
from dotenv import load_dotenv

# Make console logging safe on Windows terminals with cp1252 encoding.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Load .env from the same directory as app.py
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)
print(f"DEBUG: Loading .env from: {env_path}")
print(f"DEBUG: API Key loaded: {'Yes' if os.getenv('GROQ_API_KEY') else 'No'}")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def fetch_place_from_db(place):
    db_path = os.path.join(os.path.dirname(__file__), "historical_chatbot.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT history, culture, architecture, best_time FROM places WHERE name = ?",
        (place.lower(),)
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "history": row[0],
        "culture": row[1],
        "architecture": row[2],
        "best_time": row[3]
    }


# -------------------------
# Known Historical Places
# -------------------------
KNOWN_PLACES = [
    "hampi",
    "taj mahal",
    "qutub minar",
    "red fort",
    "konark sun temple",
    "ajanta caves",
    "ellora caves",
    "india gate",
    "gateway of india",
    "mysore palace",
    "golden temple",
    "hawa mahal",
    "fatehpur sikri",
    "victoria memorial"
]

app = Flask(__name__)

# -------------------------
# Smart Query Classification
# -------------------------
def classify_query_type(message):
    """
    Classifies if a query needs structured data (Wikipedia/DB/Wikidata) 
    or AI-powered response (general travel advice, conversational queries)
    
    Returns: 'structured' or 'ai_powered'
    """
    msg_lower = message.lower()
    
    # Patterns that indicate structured historical data queries
    structured_patterns = [
        "history", "historical", "past", "built", "constructed", "founded",
        "architecture", "monument", "temple", "fort", "palace",
        "culture", "tradition", "festival", "heritage",
        "when was", "who built", "what year", "facts about",
        "tell me about", "information about", "details of",
        "best time to visit", "when to visit", "weather"
    ]
    
    # Patterns that indicate AI-powered general queries
    ai_patterns = [
        "what should i", "what can i", "how do i", "should i",
        "recommend", "suggest", "advice", "tips",
        "pack", "packing", "bring", "carry",
        "plan", "planning", "itinerary", "trip",
        "food", "eat", "cuisine", "dishes",
        "safe", "safety", "scam", "precaution",
        "budget", "cost", "expensive", "cheap",
        "transport", "travel", "flight", "train",
        "visa", "permit", "document",
        "compare", "difference between", "better",
        "why", "how come", "explain"
    ]
    
    # Check for AI patterns first (priority)
    ai_score = sum(1 for pattern in ai_patterns if pattern in msg_lower)
    
    # Check for structured patterns
    structured_score = sum(1 for pattern in structured_patterns if pattern in msg_lower)
    
    # If message is very short and conversational
    if len(msg_lower.split()) <= 3 and ai_score == 0 and structured_score == 0:
        return 'ai_powered'
    
    # If AI patterns dominate
    if ai_score > structured_score:
        return 'ai_powered'
    
    # If structured patterns are present
    if structured_score > 0:
        return 'structured'
    
    # Default to AI for ambiguous queries
    return 'ai_powered'


# -------------------------
# Greeting Detection
# -------------------------
def is_greeting(message):
    """Only detect pure greetings, not messages with greeting words as substrings"""
    msg_lower = message.lower().strip()
    
    # Pure greeting patterns - message should start/end with greeting or be just the greeting
    pure_greetings = ["hi", "hello", "hey", "greetings", "sup", "namaste", "howdy", "good morning", "good evening"]
    
    # Check if message is exactly a greeting or greeting with minimal text
    if msg_lower in pure_greetings:
        return True
    
    # Check if message starts with greeting followed by punctuation/spaces only
    for greeting in pure_greetings:
        if msg_lower.startswith(greeting):
            remainder = msg_lower[len(greeting):].strip()
            # If remainder is empty or just punctuation, it's a greeting
            if not remainder or remainder in ["!", "?", ".", ",", "!!!", "???", "there", "!"]:
                return True
    
    return False

# -------------------------
# AI Response Generation (Groq)
# -------------------------
def generate_ai_response(message, context=None):
    """
    Generate AI-powered responses for general travel queries, greetings, and conversations
    
    Args:
        message: User's message
        context: Optional context about detected places or intents
    """
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("ERROR: GROQ_API_KEY not found in .env file!")
            return None
        
        print(f"\n{'='*60}")
        print("GROQ AI RESPONSE REQUEST")
        print(f"{'='*60}")
        print(f"Message: {message}")
        print(f"Context: {context}")
        print(f"API Key (first 20 chars): {api_key[:20]}...")
        print(f"{'='*60}\n")
        
        # Build system prompt based on context
        system_prompt = """You are an expert Indian travel assistant chatbot with deep knowledge of Indian culture, history, and travel. 

Your expertise includes:
- Historical monuments and their significance
- Travel planning and itinerary suggestions
- Packing advice for different regions and seasons
- Indian cuisine and food recommendations
- Cultural etiquette and local customs
- Safety tips and travel precautions
- Transportation options
- Budget planning
- Festival information
- Best times to visit different regions

Personality:
- Friendly, warm, and enthusiastic about Indian travel
- Provide practical, actionable advice
- Keep responses concise (2-4 sentences) but informative
- Use emojis sparingly to add personality
- Be culturally sensitive and accurate

When responding:
- For greetings: Be warm and briefly introduce your capabilities
- For travel advice: Give specific, practical recommendations
- For comparisons: Provide balanced insights
- For planning questions: Offer structured suggestions"""

        if context:
            system_prompt += f"\n\nContext: {context}"
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Groq's fast and capable model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=300,
            top_p=0.9
        )
        
        print("Groq API call successful")
        result = response.choices[0].message.content
        preview = result[:100].encode("ascii", errors="replace").decode("ascii")
        print(f"Result: {preview}...")
        print(f"{'='*60}\n")
        return result
        
    except Exception as e:
        print(f"\n{'='*60}")
        print("GROQ AI RESPONSE ERROR")
        print(f"{'='*60}")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return None

# -------------------------
# Intent Detection (for structured queries)
# -------------------------
def detect_intent(message):
    message = message.lower()

    if any(word in message for word in ["history", "historical", "past", "origin", "founded"]):
        return "history"
    elif any(word in message for word in ["culture", "tradition", "festival", "heritage"]):
        return "culture"
    elif any(word in message for word in ["architecture", "monument", "temple", "fort", "design", "structure"]):
        return "architecture"
    elif any(word in message for word in ["when", "year", "built", "constructed", "located", "facts", "details"]):
         return "facts"
    elif any(word in message for word in [
        "best time",
        "when to visit",
        "when should i visit",
        "visit",
        "weather",
        "season"
    ]):
        return "visit"
    else:
        return "general"

# -------------------------
# Intelligent Place Detection (Misspelling Support)
# -------------------------
def detect_place(text):
    text = text.lower()

    # 1️⃣ Direct match (fast path)
    for place in KNOWN_PLACES:
        if place in text:
            return place

    # 2️⃣ Fuzzy match for misspellings
    words = text.split()
    for word in words:
        matches = get_close_matches(word, KNOWN_PLACES, n=1, cutoff=0.7)
        if matches:
            return matches[0]

    # 3️⃣ Multi-word place names
    for i in range(len(words)):
        for j in range(i + 1, min(i + 4, len(words) + 1)):  # Check up to 3-word combinations
            phrase = " ".join(words[i:j])
            matches = get_close_matches(phrase, KNOWN_PLACES, n=1, cutoff=0.75)
            if matches:
                return matches[0]

    return None

# -------------------------
# Wikipedia Fetch
# -------------------------
def fetch_wikipedia_summary(place):
    try:
        encoded_place = urllib.parse.quote(place.title())
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_place}"

        headers = {
            "User-Agent": "HistoricalChatbot/1.0 (student project)"
        }

        response = requests.get(url, headers=headers, timeout=10)

        print("DEBUG -> Wikipedia URL:", url)
        print("DEBUG -> Status Code:", response.status_code)

        if response.status_code != 200:
            return None

        data = response.json()
        return data.get("extract")

    except Exception as e:
        print("Wikipedia Fetch Error:", e)
        return None
    

# -------------------------
# Wikidata Facts Fetch
# -------------------------
def fetch_wikidata_facts(place):
    query = f"""
    SELECT ?placeLabel ?countryLabel ?inception ?instanceLabel WHERE {{
      ?place rdfs:label "{place.title()}"@en.
      OPTIONAL {{ ?place wdt:P17 ?country. }}
      OPTIONAL {{ ?place wdt:P571 ?inception. }}
      OPTIONAL {{ ?place wdt:P31 ?instance. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 1
    """

    url = "https://query.wikidata.org/sparql"
    headers = {
        "Accept": "application/json",
        "User-Agent": "HistoricalChatbot/1.0 (student project)"
    }

    try:
        response = requests.get(url, headers=headers, params={"query": query}, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        bindings = data["results"]["bindings"]

        if not bindings:
            return None

        result = bindings[0]

        facts = {
            "place": result.get("placeLabel", {}).get("value"),
            "country": result.get("countryLabel", {}).get("value"),
            "type": result.get("instanceLabel", {}).get("value"),
            "year": result.get("inception", {}).get("value", "")[:4]
        }

        return facts
    except Exception as e:
        print(f"Wikidata fetch error: {e}")
        return None

# -------------------------
# Best Time to Visit
# -------------------------
def best_time_to_visit(place):
    tropical_places = [
        "hampi",
        "taj mahal",
        "qutub minar",
        "red fort",
        "konark sun temple",
        "ajanta caves",
        "ellora caves",
        "india gate",
        "gateway of india",
        "fatehpur sikri",
        "hawa mahal"
    ]

    if place.lower() in tropical_places:
        return (
            f"The best time to visit {place.title()} is from October to February. "
            "The weather is pleasant and ideal for sightseeing. "
            "Summers are extremely hot, and monsoons may affect travel."
        )

    return None

# -------------------------
# Chat API (SMART ROUTING)
# -------------------------
@app.route("/chat", methods=["POST"])
def chat():
    message = request.json.get("message", "").strip()
    
    if not message:
        return jsonify({
            "intent": "error",
            "response": "Please send a message!"
        })
    
    print(f"\n{'='*60}")
    print("NEW CHAT REQUEST")
    print(f"{'='*60}")
    print(f"Message: {message}")
    print(f"{'='*60}\n")

    # ============================================================
    # STEP 1: Handle Pure Greetings with AI
    # ============================================================
    if is_greeting(message):
        print("Detected as PURE GREETING")
        ai_response = generate_ai_response(
            message, 
            context="User is greeting you. Introduce yourself as a travel assistant for Indian historical places and general travel."
        )
        if ai_response:
            return jsonify({
                "intent": "greeting",
                "response": ai_response
            })
        # Fallback greeting
        return jsonify({
            "intent": "greeting",
            "response": "Namaste! 🙏 I'm your Indian travel assistant. I can help you with historical places, travel tips, packing advice, and planning your trip to India. What would you like to know?"
        })

    # ============================================================
    # STEP 2: Classify Query Type
    # ============================================================
    query_type = classify_query_type(message)
    place = detect_place(message)
    
    print(f"Query Type: {query_type}")
    print(f"Detected Place: {place}")
    
    # ============================================================
    # STEP 3: Handle STRUCTURED DATA queries (Wikipedia/DB/Wikidata)
    # ============================================================
    if query_type == 'structured' and place:
        print(f"STRUCTURED query about {place}")
        
        intent = detect_intent(message)
        db_data = fetch_place_from_db(place)
        
        print(f"Intent: {intent}")
        print(f"Has DB Data: {bool(db_data)}")
        
        # Try database first
        if db_data:
            if intent == "history":
                return jsonify({
                    "intent": "history",
                    "place": place,
                    "response": db_data["history"]
                })
            elif intent == "culture":
                return jsonify({
                    "intent": "culture",
                    "place": place,
                    "response": db_data["culture"]
                })
            elif intent == "architecture":
                return jsonify({
                    "intent": "architecture",
                    "place": place,
                    "response": db_data["architecture"]
                })
            elif intent == "visit":
                return jsonify({
                    "intent": "visit",
                    "place": place,
                    "response": db_data["best_time"]
                })
        
        # Handle "best time to visit"
        if intent == "visit":
            visit_info = best_time_to_visit(place)
            if visit_info:
                return jsonify({
                    "intent": "visit",
                    "place": place,
                    "response": visit_info
                })
        
        # Handle "facts" intent with Wikidata
        if intent == "facts":
            facts = fetch_wikidata_facts(place)
            if facts:
                reply = f"""📍 Place: {facts.get('place')}
🏛 Type: {facts.get('type')}
🌍 Country: {facts.get('country')}
🗓 Year Built: {facts.get('year')}"""
                return jsonify({
                    "intent": "facts",
                    "place": place,
                    "response": reply.strip()
                })
        
        # Fallback to Wikipedia summary
        summary = fetch_wikipedia_summary(place)
        if summary:
            if intent == "history":
                reply = f"📜 History of {place.title()}:\n\n{summary}"
            elif intent == "culture":
                reply = f"🎭 Culture of {place.title()}:\n\n{summary}"
            elif intent == "architecture":
                reply = f"🏛 Architecture of {place.title()}:\n\n{summary}"
            else:
                reply = f"ℹ️ About {place.title()}:\n\n{summary}"
            
            return jsonify({
                "intent": intent,
                "place": place,
                "response": reply
            })
        
        # If no data found for the place
        return jsonify({
            "intent": intent,
            "place": place,
            "response": f"I don't have detailed information about {place.title()} right now. Try asking about its history, culture, architecture, or when to visit!"
        })
    
    # ============================================================
    # STEP 4: Handle AI-POWERED queries (general travel, advice, planning)
    # ============================================================
    print("AI-POWERED query")
    
    # Build context if place was detected but query needs AI response
    context = None
    if place:
        context = f"User is asking about {place.title()}. They want travel advice, not just historical facts."
    
    ai_response = generate_ai_response(message, context)
    
    if ai_response:
        return jsonify({
            "intent": "ai_response",
            "place": place,
            "response": ai_response
        })
    
    # Fallback response if AI fails
    print("AI failed, using fallback")
    return jsonify({
        "intent": "general",
        "response": "I'm here to help with Indian travel and historical places! I can answer questions about monuments, give travel tips, suggest what to pack, help plan your trip, and more. What would you like to know? 🇮🇳"
    })

# -------------------------
# Health Check Endpoint
# -------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "groq_configured": bool(os.getenv("GROQ_API_KEY"))
    })

# -------------------------
# Run Server
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)

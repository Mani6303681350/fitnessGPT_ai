from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv
import os
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

app = Flask(__name__)

# Initialize Groq
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# Initialize Firebase Admin SDK
# REPLACE this string with the name of your newly downloaded secure JSON file
cred = credentials.Certificate("FIREBASE-KEY-FILE.json")
firebase_admin.initialize_app(cred)

# Initialize Firestore database client
db = firestore.client()

# Global variable for current chat state
# Note: For production with multiple users, you should handle 'current_chat' 
# on the frontend and pass it in API requests instead of using a global variable.
current_chat = None

system_prompt = """
You are FitnessGPT AI.

Answer ONLY fitness related questions.

If user asks outside fitness reply:
'I am FitnessGPT AI. Please ask only fitness-related questions.'
"""

# Home
@app.route("/")
def home():
    return render_template("index.html")

# Get Chats
@app.route("/get_chats")
def get_chats():
    # Fetch all documents from the 'chats' collection
    docs = db.collection('chats').stream()
    chat_names = [doc.id for doc in docs]
    
    messages = []
    if current_chat and current_chat in chat_names:
        chat_doc = db.collection('chats').document(current_chat).get()
        if chat_doc.exists:
            messages = chat_doc.to_dict().get('messages', [])
            
    return jsonify({
        "chats": chat_names,
        "current": current_chat,
        "messages": messages
    })

# New Chat
@app.route("/new_chat", methods=["POST"])
def new_chat():
    global current_chat

    chat_name = "New Chat"
    
    # Create or overwrite a document named "New Chat" with empty messages
    db.collection('chats').document(chat_name).set({"messages": []})
    current_chat = chat_name

    return jsonify({
        "chat": chat_name
    })

# Switch Chat
@app.route("/switch_chat", methods=["POST"])
def switch_chat():
    global current_chat

    data = request.get_json()
    current_chat = data["chat"]
    
    # Fetch messages for the selected chat
    chat_doc = db.collection('chats').document(current_chat).get()
    messages = chat_doc.to_dict().get('messages', []) if chat_doc.exists else []

    return jsonify({
        "messages": messages
    })

# Chat API
@app.route("/chat", methods=["POST"])
def chat():
    global current_chat

    data = request.get_json()
    user_message = data["message"]

    if current_chat is None:
        current_chat = "New Chat"
        db.collection('chats').document(current_chat).set({"messages": []})

    # Fetch current chat history
    chat_ref = db.collection('chats').document(current_chat)
    chat_doc = chat_ref.get()
    messages = chat_doc.to_dict().get('messages', []) if chat_doc.exists else []

    # First message becomes chat title logic
    if len(messages) == 0:
        chat_title = user_message[:30]
        # In Firestore, to rename a doc, we delete the old one and create a new one
        if chat_title != current_chat:
            db.collection('chats').document(current_chat).delete()
            current_chat = chat_title
            chat_ref = db.collection('chats').document(current_chat)

    # Append user message
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    # Save user message to database immediately
    chat_ref.set({"messages": messages})

    # Prepare Groq API call
    groq_messages = [{"role": "system", "content": system_prompt}]
    groq_messages.extend(messages)

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=groq_messages
    )

    ai_response = completion.choices[0].message.content

    # Append AI message
    messages.append({
        "role": "assistant",
        "content": ai_response
    })
    
    # Update database with AI response
    chat_ref.set({"messages": messages})

    return jsonify({
        "reply": ai_response,
        "current_chat": current_chat
    })

# DELETE CHAT 
@app.route("/delete_chat", methods=["POST"])
def delete_chat():
    global current_chat

    data = request.get_json()
    chat_to_delete = data["chat"]

    # Delete the document from Firestore
    db.collection('chats').document(chat_to_delete).delete()

    # If deleted chat was active, reset
    if current_chat == chat_to_delete:
        current_chat = None
        
        # Fetch remaining chats to auto-switch
        docs = list(db.collection('chats').stream())
        if len(docs) > 0:
            current_chat = docs[0].id

    # Get updated list of chats
    remaining_chats = [doc.id for doc in db.collection('chats').stream()]

    return jsonify({
        "chats": remaining_chats,
        "current": current_chat
    })


if __name__ == "__main__":
    app.run(debug=True)
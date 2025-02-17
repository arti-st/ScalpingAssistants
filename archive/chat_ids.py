import firebase_admin
from firebase_admin import credentials, db
import os
import base64
from dotenv import load_dotenv

load_dotenv()

# Get the Base64 encoded string from environment variables
key_json_base64 = os.getenv('KEY_JSON_BASE64')
databaseURL = os.getenv('DATABASE_URL')

# Decode the string
key_json_content = base64.b64decode(key_json_base64).decode('utf-8')

# Path to your service account key file (optional step, if you want to keep the key in memory)
SERVICE_ACCOUNT_KEY = 'key.json'

# Write the decoded content to key.json file temporarily
with open(SERVICE_ACCOUNT_KEY, 'w') as f:
    f.write(key_json_content)

# Initialize the Firebase Admin SDK
cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
firebase_admin.initialize_app(cred, {
    'databaseURL': databaseURL
})

# Reference to your Realtime Database
ref = db.reference('chat_ids')


def get_existed_chat_ids():
    return ref.get() or []


def save_new_chat_id(new_chat_id=None):
    existed_chat_ids = get_existed_chat_ids()
    if new_chat_id and new_chat_id not in existed_chat_ids:
        existed_chat_ids.append(new_chat_id)
    ref.set(existed_chat_ids)

# def save_new_chat_id(new_chat_id=None):
#     return None

# Видалення None значень зі списку id's
# ids = get_existed_chat_ids()
# ids = [i for i in ids if i != None]
# ref.set(ids)

from flask import Flask, request, jsonify
import sys
import os
import random
import string
import json
from datetime import datetime, timedelta
import logging 

# Vercel-কে রুট ফোল্ডার চেনানোর জন্য
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# আপনার মূল স্ক্রিপ্ট থেকে ফাংশন ইম্পোর্ট করা হচ্ছে
try:
    from XGE_core import create_acc, REGION_URLS
except ImportError:
    logging.error("ImportError: XGE_core.py not found or has errors.")
    def create_acc(region):
        return {"data": None, "status_code": 500, "uid": None, "password": None, "name": "IMPORT_ERROR"}
    REGION_URLS = {}

app = Flask(__name__)

# --- Static Key Management Setup (আগের মতোই) ---

# Admin Key (MUST be set in Vercel Environment Variables)
ADMIN_KEY = os.environ.get('ADMIN_KEY', 'DEFAULT-ADMIN-PASS') 

# Get API Keys as a JSON string from Vercel Environment Variable
API_KEYS_JSON_STRING = os.environ.get('API_KEYS_JSON', '[]')
STATIC_KEYS = {} 

try:
    keys_list = json.loads(API_KEYS_JSON_STRING)
    for key_data in keys_list:
        key_str = key_data.get('key')
        if key_str:
            STATIC_KEYS[key_str] = {
                'limit': key_data.get('limit', float('inf')),
                'usage_count': 0, 
                'expiry_date': datetime.strptime(key_data['expiry_date'], '%Y-%m-%d') if key_data.get('expiry_date') and key_data['expiry_date'] is not None else None,
                'is_active': key_data.get('is_active', True)
            }
except Exception as e:
    logging.error(f"Error loading API_KEYS_JSON: {e}. Check if the JSON format is valid.")


# --- Helper Functions (আগের মতোই) ---

def is_admin(req):
    auth_header = req.headers.get('Authorization')
    if not auth_header or auth_header != ADMIN_KEY:
        return False
    return True

def generate_random_key():
    chars = string.ascii_uppercase + string.digits
    return 'JOY-' + ''.join(random.choice(chars) for _ in range(16))

# --- ১. অ্যাকাউন্ট জেনারেশন রুট (ব্যবহারকারীদের জন্য) ---
@app.route('/', methods=['GET'])
def handle_generation_request():
    if not STATIC_KEYS:
        return jsonify({"error": "No API Keys loaded. Contact admin to set API_KEYS_JSON."}), 503

    # --- ব্যবহারকারীর ইনপুট URL থেকে নেওয়া ---
    api_key = request.args.get('key')
    region = request.args.get('region', '').upper()
    amount_str = request.args.get('amount', '1')

    # --- ১. কী ভ্যালিডেশন ---
    key_data = STATIC_KEYS.get(api_key)

    if not api_key or not key_data:
        return jsonify({"error": "Invalid API key."}), 403

    if not key_data.get("is_active", True):
        return jsonify({"error": "This key has been disabled."}), 403

    # --- ২. এক্সপায়ার (Expiry) সিস্টেম চেক ---
    expiry_date = key_data.get("expiry_date")
    if expiry_date and datetime.utcnow() > expiry_date:
        return jsonify({"error": "This key has expired."}), 403

    # --- ৩. লিমিট (Limit) সিস্টেম চেক ---
    limit = key_data.get("limit", float('inf')) 
    
    try:
        amount = int(amount_str)
        if amount < 1: amount = 1
        # এখানে আপনি যে সংখ্যাটি সেট করবেন, তার বেশি অ্যাকাউন্ট তৈরি হবে না
        if amount > 100: amount = 100 
    except ValueError:
        amount = 1
        
    if 0 + amount > limit: 
        return jsonify({"error": f"Key limit exceeded. Limit is {limit}. Usage is not tracked without a database."}), 403

    # --- ৪. রিজিয়ন ভ্যালিডেশন ---
    if not region:
        return jsonify({"error": "Missing 'region' parameter. Example: ?region=ME"}), 400
    if region not in REGION_URLS:
         return jsonify({"error": f"Region '{region}' not supported."}), 400

    # --- ৫. অ্যাকাউন্ট জেনারেশন লুপ ---
    successful_accounts = []
    
    for i in range(amount):
        try:
            r = create_acc(region) 
            if r and r.get('data') and r.get('status_code') == 200:
                # 🔴 শুধুমাত্র uid এবং password সেভ করা হচ্ছে
                successful_accounts.append({
                    "uid": r.get("uid"),
                    "password": r.get("password")
                })
            # ব্যর্থ অ্যাকাউন্ট ট্র্যাক করার দরকার নেই, কারণ আমরা শুধু সফল অ্যাকাউন্টই রিটার্ন করব
        except Exception as e:
            pass # এরর এড়িয়ে যাওয়া হলো
    
    # --- ৬. শুধুমাত্র সফল অ্যাকাউন্টগুলো পাঠানো ---
    # 🔴 আউটপুট এখন শুধুই একটি পরিষ্কার JSON অ্যারে
    return jsonify(successful_accounts), 200


# --- ২. অ্যাডমিন রুট (কী ম্যানেজমেন্টের জন্য - আগের মতোই থাকবে) ---

def admin_instruction_response():
    """Admin routes now return instructions for manual Vercel configuration."""
    current_keys_json = json.dumps(list(STATIC_KEYS.keys()), indent=2)
    return jsonify({
        "WARNING": "Database not in use. Key management is now STATIC.",
        "ACTION_REQUIRED": "To CREATE, REMOVE, or UPDATE a key, you MUST manually edit the 'API_KEYS_JSON' Environment Variable in your Vercel Dashboard.",
        "Vercel_Path": "Vercel Project -> Settings -> Environment Variables",
        "JSON_Format_Example": [
            {
                "key": "MY_CUSTOM_KEY",
                "limit": 50,
                "expiry_date": "2025-12-31", 
                "is_active": True
            }
        ],
        "Current_Loaded_Keys": current_keys_json
    }), 200


@app.route('/admin/create_key', methods=['POST'])
@app.route('/admin/remove_key', methods=['POST'])
@app.route('/admin/update_key', methods=['POST'])
def admin_manual_update():
    if not is_admin(request):
        return jsonify({"error": "Access Denied. Invalid admin key."}), 401
    return admin_instruction_response()

@app.route('/admin/show_keys', methods=['GET'])
def show_all_keys():
    if not is_admin(request):
        return jsonify({"error": "Access Denied."}), 401
    
    if not STATIC_KEYS:
        return jsonify({"error": "No API Keys loaded."}), 503
        
    formatted_keys = []
    for k, v in STATIC_KEYS.items():
        formatted_keys.append({
            "key": k,
            "limit": v['limit'] if v['limit'] != float('inf') else "Unlimited",
            "is_active": v['is_active'],
            "expiry_date": v['expiry_date'].strftime('%Y-%m-%d') if v['expiry_date'] else "Never",
            "usage_tracked": "No"
        })
        
    return jsonify({"total_keys": len(formatted_keys), "keys": formatted_keys}), 200


# Vercel-এ চালানোর জন্য
if __name__ == "__main__":
    app.run()

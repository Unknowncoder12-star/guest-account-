from flask import Flask, request, jsonify
import sys
import os
import random
import string
import json
from datetime import datetime, timedelta
import logging # লগিং যোগ করা হলো

# Vercel-কে রুট ফোল্ডার চেনানোর জন্য
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# আপনার মূল স্ক্রিপ্ট থেকে ফাংশন ইম্পোর্ট করা হচ্ছে
try:
    # নিশ্চিত করুন আপনার ফাইলটির নাম XGE_core.py বা XGE.py
    from XGE_core import create_acc, REGION_URLS
except ImportError:
    logging.error("ImportError: XGE_core.py not found or has errors.")
    def create_acc(region):
        return {"data": None, "status_code": 500, "uid": None, "password": None, "name": "IMPORT_ERROR"}
    REGION_URLS = {}

app = Flask(__name__)

# --- Static Key Management Setup ---

# Admin Key (MUST be set in Vercel Environment Variables)
ADMIN_KEY = os.environ.get('ADMIN_KEY', 'DEFAULT-ADMIN-PASS') 

# Get API Keys as a JSON string from Vercel Environment Variable
API_KEYS_JSON_STRING = os.environ.get('API_KEYS_JSON', '[]')
STATIC_KEYS = {} 

try:
    # Load keys statically. Usage_count cannot be updated without a database.
    keys_list = json.loads(API_KEYS_JSON_STRING)
    for key_data in keys_list:
        key_str = key_data.get('key')
        if key_str:
            STATIC_KEYS[key_str] = {
                # Limit will be checked, but usage_count will always be 0
                'limit': key_data.get('limit', float('inf')),
                'usage_count': 0, 
                'expiry_date': datetime.strptime(key_data['expiry_date'], '%Y-%m-%d') if key_data.get('expiry_date') else None,
                'is_active': key_data.get('is_active', True)
            }
except Exception as e:
    logging.error(f"Error loading API_KEYS_JSON: {e}. Check if the JSON format is valid.")
    # If JSON is invalid, STATIC_KEYS will remain empty, blocking all API calls.


# --- Helper Functions (Same as before) ---

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

    # --- ৩. লিমিট (Limit) সিস্টেম চেক (ব্যবহার ট্র্যাক হবে না) ---
    limit = key_data.get("limit", float('inf')) 
    
    try:
        amount = int(amount_str)
        if amount < 1: amount = 1
        if amount > 5: amount = 5 
    except ValueError:
        amount = 1
        
    # যেহেতু usage_count সবসময় 0, তাই limit চেক শুধু একটি সতর্কীকরণ হিসেবে কাজ করবে।
    if 0 + amount > limit: 
        return jsonify({"error": f"Key limit exceeded. Limit is {limit}. Usage is not tracked without a database."}), 403

    # --- ৪. রিজিয়ন ভ্যালিডেশন ---
    if not region:
        return jsonify({"error": "Missing 'region' parameter. Example: ?region=ME"}), 400
    if region not in REGION_URLS:
         return jsonify({"error": f"Region '{region}' not supported."}), 400

    # --- ৫. অ্যাকাউন্ট জেনারেশন লুপ ---
    successful_accounts = []
    failed_accounts = 0
    
    for i in range(amount):
        try:
            r = create_acc(region) 
            if r and r.get('data') and r.get('status_code') == 200:
                successful_accounts.append({
                    "uid": r.get("uid"),
                    "password": r.get("password"),
                    "name": r.get("name")
                })
            else:
                failed_accounts += 1
        except Exception as e:
            failed_accounts += 1
    
    # --- ৬. ফলাফল পাঠানো ---
    return jsonify({
        "status": "success",
        "region": region,
        "key_info": {
            "limit": limit if limit != float('inf') else "unlimited",
            "usage_tracked": "No (No Database)",
            "expires_on": key_data.get("expiry_date", "never").strftime('%Y-%m-%d') if key_data.get('expiry_date') else "never"
        },
        "successful_count": len(successful_accounts),
        "failed_count": failed_accounts,
        "accounts": successful_accounts
    }), 200

# --- ২. অ্যাডমিন রুট (কী ম্যানেজমেন্টের জন্য - এখন শুধু ইনস্ট্রাকশন দেখাবে) ---

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
                "is_active": true
            },
            {
                "key": "ANOTHER_KEY",
                "limit": 1000,
                "expiry_date": null, 
                "is_active": true
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

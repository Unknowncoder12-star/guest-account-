from flask import Flask, request, jsonify
import sys
import os
import pymongo
from datetime import datetime, timedelta
import random
import string

# Vercel-কে রুট ফোল্ডার চেনানোর জন্য
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# আপনার মূল স্ক্রিপ্ট থেকে ফাংশন ইম্পোর্ট করা হচ্ছে
try:
    from XGE_core import create_acc, REGION_URLS
except ImportError:
    print("Error: XGE_core.py import failed.")
    def create_acc(region):
        return {"data": None, "status_code": 500, "uid": None, "password": None, "name": "IMPORT_ERROR"}
    REGION_URLS = {}

app = Flask(__name__)

# =================================================================
# 🔴 WARNING: HARDCODED KEYS (নিরাপত্তা ঝুঁকি)
# এই কী গুলো সরাসরি কোডের ভেতরে বসানো হয়েছে
# =================================================================
# ব্যবহারকারীর দেওয়া MongoDB URI, ?appName=Cluster0 অংশটি বাদ দেওয়া হয়েছে
MONGODB_URI = "mongodb+srv://spacemore635_db_user:IDuXJrcd4IKgRkjL@cluster0.dcl2zdn.mongodb.net/"
# অ্যাডমিন পাসওয়ার্ড
ADMIN_KEY = "JOY-100K-ADMIN-MASTER-KEY"
# =================================================================


# --- ডেটাবেস সংযোগ চেষ্টা ---
keys_collection = None
try:
    # ডেটাবেস সংযোগ
    client = pymongo.MongoClient(MONGODB_URI)
    db = client.get_database("joy100k_api_db") # ডেটাবেসের নাম
    keys_collection = db.api_keys # "keys" নামে একটি কালেকশন
    # একটি ডামি অ্যাক্সেস চেক করে দেখা
    db.command('ping') 
    print("MongoDB connection successful.")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    # যদি সংযোগ ব্যর্থ হয়, তাহলে keys_collection None থাকবে এবং API এরর দেবে
    pass

# --- হেলপার ফাংশন ---

def is_admin(req):
    """অ্যাডমিন কী চেক করে"""
    auth_header = req.headers.get('Authorization')
    if not auth_header or auth_header != ADMIN_KEY:
        return False
    return True

def generate_random_key():
    """র‍্যান্ডম কী তৈরি করে"""
    chars = string.ascii_uppercase + string.digits
    return 'JOY-' + ''.join(random.choice(chars) for _ in range(16))

# --- ১. অ্যাকাউন্ট জেনারেশন রুট (ব্যবহারকারীদের জন্য) ---
@app.route('/', methods=['GET'])
def handle_generation_request():
    if not keys_collection:
        return jsonify({"error": "Database connection failed. Contact admin."}), 500

    # --- ব্যবহারকারীর ইনপুট URL থেকে নেওয়া ---
    api_key = request.args.get('key')
    region = request.args.get('region', '').upper()
    amount_str = request.args.get('amount', '1')

    # --- ১. কী ভ্যালিডেশন ---
    if not api_key:
        return jsonify({"error": "Missing 'key' parameter."}), 401

    key_data = keys_collection.find_one({"key": api_key})

    if not key_data:
        return jsonify({"error": "Invalid API key."}), 403

    if not key_data.get("is_active", True):
        return jsonify({"error": "This key has been disabled."}), 403

    # --- ২. এক্সপায়ার (Expiry) সিস্টেম চেক ---
    expiry_date = key_data.get("expiry_date")
    if expiry_date and datetime.utcnow() > expiry_date:
        return jsonify({"error": "This key has expired."}), 403

    # --- ৩. লিমিট (Limit) সিস্টেম চেক ---
    limit = key_data.get("limit", float('inf')) 
    usage_count = key_data.get("usage_count", 0)
    
    try:
        amount = int(amount_str)
        if amount < 1: amount = 1
        if amount > 5: amount = 5 
    except ValueError:
        amount = 1

    if (usage_count + amount) > limit:
        remaining_uses = limit - usage_count
        return jsonify({"error": f"Key limit exceeded. Remaining uses: {remaining_uses}"}), 403

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
    
    # --- ৬. কী ব্যবহার আপডেট করা ---
    keys_collection.update_one(
        {"key": api_key},
        {"$inc": {"usage_count": len(successful_accounts)}}
    )

    # --- ৭. ফলাফল পাঠানো ---
    return jsonify({
        "status": "success",
        "region": region,
        "key_info": {
            "uses_remaining": (limit - (usage_count + len(successful_accounts))) if limit != float('inf') else "unlimited",
            "expires_on": key_data.get("expiry_date", "never")
        },
        "successful_count": len(successful_accounts),
        "failed_count": failed_accounts,
        "accounts": successful_accounts
    }), 200

# --- ২. অ্যাডমিন রুট (কী ম্যানেজমেন্টের জন্য) ---

@app.route('/admin/create_key', methods=['POST'])
def create_key():
    """নতুন কী তৈরি করা"""
    if not is_admin(request):
        return jsonify({"error": "Access Denied. Invalid admin key."}), 401
    
    data = request.json
    key_type = data.get('type', 'random') 
    limit = data.get('limit') 
    expiry_days = data.get('expiry_days') 

    if key_type == 'custom':
        new_key = data.get('custom_key')
        if not new_key:
            return jsonify({"error": "'custom_key' is required for type 'custom'"}), 400
        if keys_collection.find_one({"key": new_key}):
            return jsonify({"error": "This custom key already exists."}), 400
    else:
        new_key = generate_random_key()

    expiry_date_obj = None
    if expiry_days:
        expiry_date_obj = datetime.utcnow() + timedelta(days=int(expiry_days))

    limit_obj = float('inf') 
    if limit:
        limit_obj = int(limit)

    key_doc = {
        "key": new_key,
        "limit": limit_obj,
        "usage_count": 0,
        "expiry_date": expiry_date_obj,
        "is_active": True,
        "created_at": datetime.utcnow()
    }

    try:
        keys_collection.insert_one(key_doc)
        key_doc.pop('_id', None)
        key_doc['expiry_date'] = str(key_doc['expiry_date']) if key_doc['expiry_date'] else "Never"
        key_doc['created_at'] = str(key_doc['created_at'])
        return jsonify({"message": "Key created successfully", "key_details": key_doc}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create key: {e}"}), 500

@app.route('/admin/remove_key', methods=['POST'])
def remove_key():
    """কী ডিলিট করা"""
    if not is_admin(request):
        return jsonify({"error": "Access Denied."}), 401
    
    data = request.json
    key_to_delete = data.get('key')
    if not key_to_delete:
        return jsonify({"error": "'key' is required."}), 400

    result = keys_collection.delete_one({"key": key_to_delete})
    
    if result.deleted_count > 0:
        return jsonify({"message": f"Key '{key_to_delete}' removed successfully."}), 200
    else:
        return jsonify({"error": "Key not found."}), 404

@app.route('/admin/update_key', methods=['POST'])
def update_key():
    """কী-এর লিমিট, এক্সপায়ার বা স্ট্যাটাস আপডেট করা"""
    if not is_admin(request):
        return jsonify({"error": "Access Denied."}), 401
    
    data = request.json
    key_to_update = data.get('key')
    if not key_to_update:
        return jsonify({"error": "'key' is required."}), 400

    key_data = keys_collection.find_one({"key": key_to_update})
    if not key_data:
        return jsonify({"error": "Key not found."}), 404

    updates = {}
    if 'new_limit' in data:
        updates["limit"] = int(data['new_limit'])
    if 'add_days' in data:
        current_expiry = key_data.get("expiry_date", datetime.utcnow())
        updates["expiry_date"] = current_expiry + timedelta(days=int(data['add_days']))
    if 'is_active' in data: 
        updates["is_active"] = bool(data['is_active'])

    if not updates:
        return jsonify({"error": "No update fields provided (e.g., 'new_limit', 'add_days', 'is_active')."}), 400
    
    keys_collection.update_one({"key": key_to_update}, {"$set": updates})
    return jsonify({"message": f"Key '{key_to_update}' updated successfully."}), 200

@app.route('/admin/show_keys', methods=['GET'])
def show_all_keys():
    """সব কী-এর তথ্য দেখানো"""
    if not is_admin(request):
        return jsonify({"error": "Access Denied."}), 401
    
    all_keys = []
    for key in keys_collection.find({}):
        # JSON-এ দেখানোর জন্য ফরম্যাট করা
        key.pop('_id', None)
        key['limit'] = "Unlimited" if key['limit'] == float('inf') else key['limit']
        key['expiry_date'] = str(key.get('expiry_date', 'N/A'))
        key['created_at'] = str(key.get('created_at', 'N/A'))
        all_keys.append(key)
        
    return jsonify({"total_keys": len(all_keys), "keys": all_keys}), 200

# Vercel-এ চালানোর জন্য
if __name__ == "__main__":
    app.run()

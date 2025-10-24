import hmac
import hashlib
import requests
import string
import random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import json
from protobuf_decoder.protobuf_decoder import Parser
import codecs
import time
from datetime import datetime
from colorama import Fore,Style
import urllib3
import os
import sys

# Disable only the InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Color Definitions (from original code) ---
red = Fore.RED
lg = Fore.LIGHTGREEN_EX
green = Fore.GREEN
bold = Style.BRIGHT
purpel = Fore.MAGENTA
reset = Style.RESET_ALL # Added reset for clarity and use in header

# --- Configuration (from original code) ---
hex_key = "32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533"
key = bytes.fromhex(hex_key)

REGION_LANG = {"ME": "ar","IND": "hi","ID": "id","VN": "vi","TH": "th","BD": "bn","PK": "ur","TW": "zh","EU": "en","CIS": "ru","NA": "en","SAC": "es","BR": "pt"}
REGION_URLS = {"IND": "https://client.ind.freefiremobile.com/","ID": "https://clientbp.ggblueshark.com/","BR": "https://client.us.freefiremobile.com/","ME": "https://clientbp.common.ggbluefox.com/","VN": "https://clientbp.ggblueshark.com/","TH": "https://clientbp.common.ggbluefox.com/","CIS": "https://clientbp.ggblueshark.com/","BD": "https://clientbp.ggblueshark.com/","PK": "https://clientbp.ggblueshark.com/","SG": "https://clientbp.ggblueshark.com/","NA": "https://client.us.freefiremobile.com/","SAC": "https://client.us.freefiremobile.com/","EU": "https://clientbp.ggblueshark.com/","TW": "https://clientbp.ggblueshark.com/"}

# --- Core Functions (kept as is from original code) ---

def get_region(language_code: str) -> str:
    return REGION_LANG.get(language_code)

def get_region_url(region_code: str) -> str:
    """Return URL for a given region code"""
    return REGION_URLS.get(region_code, None)

def EnC_Vr(N):
    if N < 0: ''
    H = []
    while True:
        BesTo = N & 0x7F ; N >>= 7
        if N: BesTo |= 0x80
        H.append(BesTo)
        if not N: break
    return bytes(H)
    
def DEc_Uid(H):
    n = s = 0
    for b in bytes.fromhex(H):
        n |= (b & 0x7F) << s
        if not b & 0x80: break
        s += 7
    return n
    
def CrEaTe_VarianT(field_number, value):
    field_header = (field_number << 3) | 0
    return EnC_Vr(field_header) + EnC_Vr(value)

def CrEaTe_LenGTh(field_number, value):
    field_header = (field_number << 3) | 2
    encoded_value = value.encode() if isinstance(value, str) else value
    return EnC_Vr(field_header) + EnC_Vr(len(encoded_value)) + encoded_value

def CrEaTe_ProTo(fields):
    packet = bytearray()    
    for field, value in fields.items():
        if isinstance(value, dict):
            nested_packet = CrEaTe_ProTo(value)
            packet.extend(CrEaTe_LenGTh(field, nested_packet))
        elif isinstance(value, int):
            packet.extend(CrEaTe_VarianT(field, value))           
        elif isinstance(value, str) or isinstance(value, bytes):
            packet.extend(CrEaTe_LenGTh(field, value))           
    return packet


def E_AEs(Pc):
    Z = bytes.fromhex(Pc)
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    K = AES.new(key , AES.MODE_CBC , iv)
    R = K.encrypt(pad(Z , AES.block_size))
    return bytes.fromhex(R.hex())


def generate_random_name():
    super_digits = '⁰¹²³⁴⁵⁶⁷⁸⁹'
    # Changed prefix from 'XR07' to 'JOY'
    name = 'JOY' + ''.join(random.choice(super_digits) for _ in range(6))
    return name

def generate_custom_password(random_length=9):
    characters = string.ascii_letters + string.digits
    random_part = ''.join(random.choice(characters) for _ in range(random_length)).upper()
    return f"JOY-100K-{random_part}"


def create_acc(region):
    password = generate_custom_password()
    data = f"password={password}&client_type=2&source=2&app_id=100067"
    message = data.encode('utf-8')
    signature = hmac.new(key, message, hashlib.sha256).hexdigest()

    url = "https://100067.connect.garena.com/oauth/guest/register"

    headers = {
        "User-Agent": "GarenaMSDK/4.0.19P8(ASUS_Z01QD ;Android 12;en;US;)",
        "Authorization": "Signature " + signature,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive"
    }
    
    # sys.stdout.write(f"\r{lg}>> Initializing Registration...{reset}")
    # sys.stdout.flush()

    response = requests.post(url, headers=headers, data=data)
    try:
        uid = response.json()['uid']
        # Removed internal prints to keep output clean during batch run
        return token(uid, password,region)
    except Exception as e:
        # Removed internal prints to keep output clean during batch run
        return create_acc(region)


def token(uid , password , region):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"

    headers = {
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "100067.connect.garena.com",
        "User-Agent": "GarenaMSDK/4.0.19P8(ASUS_Z01QD ;Android 12;en;US;)",
    }

    body = {
        "uid": uid,
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": key,
        "client_id": "100067"
    }

    response = requests.post(url, headers=headers, data=body)
    try:
        open_id = response.json()['open_id']
        access_token = response.json()["access_token"]
        refresh_token = response.json()['refresh_token']
    except:
        # Removed internal prints to keep output clean during batch run
        return None
    
    result = encode_string(open_id)
    field = to_unicode_escaped(result['field_14'])
    field = codecs.decode(field, 'unicode_escape').encode('latin1')
    # Removed internal prints to keep output clean during batch run
    return Major_Regsiter(access_token , open_id , field, uid, password,region)

def encode_string(original):
    keystream = [
    0x30, 0x30, 0x30, 0x32, 0x30, 0x31, 0x37, 0x30,
    0x30, 0x30, 0x30, 0x30, 0x32, 0x30, 0x31, 0x37,
    0x30, 0x30, 0x30, 0x30, 0x30, 0x32, 0x30, 0x31,
    0x37, 0x30, 0x30, 0x30, 0x30, 0x30, 0x32, 0x30
    ]
    encoded = ""
    for i in range(len(original)):
        orig_byte = ord(original[i])
        key_byte = keystream[i % len(keystream)]
        result_byte = orig_byte ^ key_byte
        encoded += chr(result_byte)
    return {
        "open_id": original,
        "field_14": encoded
        }

def to_unicode_escaped(s):
    """Convert string to Python-style Unicode escaped string"""
    return ''.join(
        c if 32 <= ord(c) <= 126 else f'\\u{ord(c):04x}'
        for c in s
    )

def Major_Regsiter(access_token , open_id , field , uid , password,region):
    url = "https://loginbp.ggblueshark.com/MajorRegister"
    name = generate_random_name()

    headers = {
        "Accept-Encoding": "gzip",
        "Authorization": "Bearer",   
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "Host": "loginbp.ggblueshark.com",
        "ReleaseVersion": "OB50",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
        "X-GA": "v1 1",
        "X-Unity-Version": "2018.4."
    }

    payload = {
        1: name,
        2: access_token,
        3: open_id,
        5: 102000007,
        6: 4,
        7: 1,
        13: 1,
        14: field,
        15: "en",
        16: 1,
        17: 1
    }

    payload = CrEaTe_ProTo(payload).hex()
    payload = E_AEs(payload).hex()
    body = bytes.fromhex(payload)
    
    response = requests.post(url, headers=headers, data=body,verify=False)
    # Removed internal prints to keep output clean during batch run
    return login(uid , password, access_token , open_id , response.content.hex() , response.status_code , name , region)

def encrypt_api(plain_text):
    plain_text = bytes.fromhex(plain_text)
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(plain_text, AES.block_size))
    return cipher_text.hex()


def chooseregion(data_bytes, jwt_token):
    url = "https://loginbp.ggblueshark.com/ChooseRegion"
    payload = data_bytes
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 12; M2101K7AG Build/SKQ1.210908.001)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/x-www-form-urlencoded",
        'Expect': "100-continue",
        'Authorization': f"Bearer {jwt_token}",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': "OB50"
    }
    response = requests.post(url, data=payload, headers=headers,verify=False)
    # Removed internal prints to keep output clean during batch run
    return response.status_code


def login(uid , password, access_token , open_id, response , status_code , name , region):
    
    lang = get_region(region)
    lang_b = lang.encode("ascii")
    headers = {
        "Accept-Encoding": "gzip",
        "Authorization": "Bearer",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "Host": "loginbp.ggblueshark.com",
        "ReleaseVersion": "OB50",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
        "X-GA": "v1 1",
        "X-Unity-Version": "2018.4.11f1"
    }    

    # Payload template (assuming 'payload' is the correct one with placeholders)
    payload_template = b'\x1a\x132025-08-30 05:19:21"\tfree fire(\x01:\x081.114.13B2Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)J\x08HandheldR\nATM MobilsZ\x04WIFI`\xb6\nh\xee\x05r\x03300z\x1fARMv7 VFPv3 NEON VMH | 2400 | 2\x80\x01\xc9\x0f\x8a\x01\x0fAdreno (TM) 640\x92\x01\rOpenGL ES 3.2\x9a\x01+Google|dfa4ab4b-9dc4-454e-8065-e70c733fa53f\xa2\x01\x0e105.235.139.91\xaa\x01\x02'+lang_b+b'\xb2\x01 1d8ec0240ede109973f3321b9354b44d\xba\x01\x014\xc2\x01\x08Handheld\xca\x01\x10Asus ASUS_I005DA\xea\x01@afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390\xf0\x01\x01\xca\x02\nATM Mobils\xd2\x02\x04WIFI\xca\x03 7428b253defc164018c604a1ebbfebdf\xe0\x03\xa8\x81\x02\xe8\x03\xf6\xe5\x01\xf0\x03\xaf\x13\xf8\x03\x84\x07\x80\x04\xe7\xf0\x01\x88\x04\xa8\x81\x02\x90\x04\xe7\xf0\x01\x98\x04\xa8\x81\x02\xc8\x04\x01\xd2\x04=/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/lib/arm\xe0\x04\x01\xea\x04_2087f61c19f57f2af4e7feff0b24d9d9|/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/base.apk\xf0\x04\x03\xf8\x04\x01\x8a\x05\x0232\x9a\x05\n2019118692\xb2\x05\tOpenGLES2\xb8\x05\xff\x7f\xc0\x05\x04\xe0\x05\xf3F\xea\x05\x07android\xf2\x05pKqsHT5ZLWrYljNb5Vqh//yFRlaPHSO9NWSQsVvOmdhEEn7W+VHNUK+Q+fduA3ptNrGB0Ll0LRz3WW0jOwesLj6aiU7sZ40p8BfUE/FI/jzSTwRe2\xf8\x05\xfb\xe4\x06\x88\x06\x01\x90\x06\x01\x9a\x06\x014\xa2\x06\x014\xb2\x06"GQ@O\x00\x0e^\x00D\x06UA\x0ePM\r\x13hZ\x07T\x06\x0cm\\V\x0ejYV;\x0bU5'
    data = payload_template
    
    # Replace placeholders with actual values
    data = data.replace('afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390'.encode(),access_token.encode())
    data = data.replace('1d8ec0240ede109973f3321b9354b44d'.encode(),open_id.encode())
    
    d = encrypt_api(data.hex())
    Final_Payload = bytes.fromhex(d)

    URL = "https://loginbp.ggblueshark.com/MajorLogin"
    RESPONSE = requests.post(URL, headers=headers, data=Final_Payload,verify=False) 
    # Removed internal prints to keep output clean during batch run
    
    if RESPONSE.status_code == 200:
        if len(RESPONSE.text) < 10:
            return {"data":None ,"response" : response , "status_code" : RESPONSE.status_code ,"name" : name, "uid" : uid, "password" : password}

        if lang.lower() not in ["ar", "en"]:
            json_result = get_available_room(RESPONSE.content.hex())
            parsed_data = json.loads(json_result)
            BASE64_TOKEN = parsed_data['8']['data']
            
            # Simplified JWT parsing to avoid unnecessary index errors
            try:
                # Find the start of the JWT signature (usually 44 chars of the signature)
                start_index = BASE64_TOKEN.find(".")
                if start_index != -1:
                    second_dot_index = BASE64_TOKEN.find(".", start_index + 1)
                    if second_dot_index != -1 and len(BASE64_TOKEN) > second_dot_index + 44:
                         BASE64_TOKEN = BASE64_TOKEN[:second_dot_index+44]
            except Exception as e:
                pass
                
            
            if region.lower() == "cis":
                region_code = "RU"
            else:
                region_code = region
                
            fields = {1:region_code}
            fields = bytes.fromhex(encrypt_api(CrEaTe_ProTo(fields).hex()))
            
            r = chooseregion(fields, BASE64_TOKEN)

            if r == 200:
                # Removed internal prints to keep output clean during batch run
                return login_server(uid , password, access_token , open_id, response , status_code , name , region)
            
        else:
            # For AR/EN, find the token directly in the response text
            BASE64_TOKEN = RESPONSE.text[RESPONSE.text.find("eyJhbGciOiJIUzI1NiIsInN2ciI6IjEiLCJ0eXAiOiJKV1QifQ"):-1]
        
        # Final JWT trimming logic
        second_dot_index = BASE64_TOKEN.find(".", BASE64_TOKEN.find(".") + 1)     
        # Removed time.sleep(0.2)
        BASE64_TOKEN = BASE64_TOKEN[:second_dot_index+44]
        dat = GET_PAYLOAD_BY_DATA(BASE64_TOKEN,access_token,1,response , status_code , name , uid , password,region)
        return dat
    
    return {"data":None ,"response" : response , "status_code" : RESPONSE.status_code ,"name" : name, "uid" : uid, "password" : password}


def login_server(uid , password, access_token , open_id, response , status_code , name , region):
    lang = get_region(region)
    lang_b = lang.encode("ascii")

    headers = {
        "Accept-Encoding": "gzip",
        "Authorization": "Bearer",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "Host": "loginbp.ggblueshark.com",
        "ReleaseVersion": "OB50",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_I005DA Build/PI)",
        "X-GA": "v1 1",
        "X-Unity-Version": "2018.4.11f1"
    }    

    payload_template = b'\x1a\x132025-08-30 05:19:21"\tfree fire(\x01:\x081.114.13B2Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)J\x08HandheldR\nATM MobilsZ\x04WIFI`\xb6\nh\xee\x05r\x03300z\x1fARMv7 VFPv3 NEON VMH | 2400 | 2\x80\x01\xc9\x0f\x8a\x01\x0fAdreno (TM) 640\x92\x01\rOpenGL ES 3.2\x9a\x01+Google|dfa4ab4b-9dc4-454e-8065-e70c733fa53f\xa2\x01\x0e105.235.139.91\xaa\x01\x02'+lang_b+b'\xb2\x01 1d8ec0240ede109973f3321b9354b44d\xba\x01\x014\xc2\x01\x08Handheld\xca\x01\x10Asus ASUS_I005DA\xea\x01@afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390\xf0\x01\x01\xca\x02\nATM Mobils\xd2\x02\x04WIFI\xca\x03 7428b253defc164018c604a1ebbfebdf\xe0\x03\xa8\x81\x02\xe8\x03\xf6\xe5\x01\xf0\x03\xaf\x13\xf8\x03\x84\x07\x80\x04\xe7\xf0\x01\x88\x04\xa8\x81\x02\x90\x04\xe7\xf0\x01\x98\x04\xa8\x81\x02\xc8\x04\x01\xd2\x04=/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/lib/arm\xe0\x04\x01\xea\x04_2087f61c19f57f2af4e7feff0b24d9d9|/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/base.apk\xf0\x04\x03\xf8\x04\x01\x8a\x05\x0232\x9a\x05\n2019118692\xb2\x05\tOpenGLES2\xb8\x05\xff\x7f\xc0\x05\x04\xe0\x05\xf3F\xea\x05\x07android\xf2\x05pKqsHT5ZLWrYljNb5Vqh//yFRlaPHSO9NWSQsVvOmdhEEn7W+VHNUK+Q+fduA3ptNrGB0Ll0LRz3WW0jOwesLj6aiU7sZ40p8BfUE/FI/jzSTwRe2\xf8\x05\xfb\xe4\x06\x88\x06\x01\x90\x06\x01\x9a\x06\x014\xa2\x06\x014\xb2\x06"GQ@O\x00\x0e^\x00D\x06UA\x0ePM\r\x13hZ\x07T\x06\x0cm\\V\x0ejYV;\x0bU5'
    data = payload_template
    
    data = data.replace('afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390'.encode(),access_token.encode())
    data = data.replace('1d8ec0240ede109973f3321b9354b44d'.encode(),open_id.encode())
    d = encrypt_api(data.hex())

    Final_Payload = bytes.fromhex(d)
    
    # URL selection based on region (original logic)
    if region.lower() == "me":
        URL = "https://loginbp.common.ggbluefox.com/MajorLogin"
    else:
        URL = "https://loginbp.ggblueshark.com/MajorLogin"
        
    RESPONSE = requests.post(URL, headers=headers, data=Final_Payload,verify=False) 
    # Removed internal prints to keep output clean during batch run
    
    if RESPONSE.status_code == 200:
        if len(RESPONSE.text) < 10:
            return {"data":None ,"response" : response , "status_code" : RESPONSE.status_code ,"name" : name, "uid" : uid, "password" : password}

        json_result = get_available_room(RESPONSE.content.hex())
        parsed_data = json.loads(json_result)
        BASE64_TOKEN = parsed_data['8']['data']

        # Final JWT trimming logic
        second_dot_index = BASE64_TOKEN.find(".", BASE64_TOKEN.find(".") + 1)     
        # Removed time.sleep(0.2)
        BASE64_TOKEN = BASE64_TOKEN[:second_dot_index+44]
        # Removed internal prints to keep output clean during batch run
        dat = GET_PAYLOAD_BY_DATA(BASE64_TOKEN,access_token,1,response , status_code , name , uid , password, region)
        return dat
    
    return {"data":None ,"response" : response , "status_code" : RESPONSE.status_code ,"name" : name, "uid" : uid, "password" : password}


import base64
def GET_PAYLOAD_BY_DATA(JWT_TOKEN, NEW_ACCESS_TOKEN, date,response , status_code , name, uid, password, region):
        try:
            token_payload_base64 = JWT_TOKEN.split('.')[1]
            token_payload_base64 += '=' * ((4 - len(token_payload_base64) % 4) % 4)
            decoded_payload = base64.urlsafe_b64decode(token_payload_base64).decode('utf-8')
            decoded_payload = json.loads(decoded_payload)
            NEW_EXTERNAL_ID = decoded_payload['external_id']
            SIGNATURE_MD5 = decoded_payload['signature_md5']
            now = datetime.now()
            now = str(now)[:len(str(now))-7]
            formatted_time = date
            
            # Payload template (assuming 'PAYLOAD' is the correct one with placeholders)
            PAYLOAD_template = b':\x071.111.2\xaa\x01\x02ar\xb2\x01 55ed759fcf94f85813e57b2ec8492f5c\xba\x01\x014\xea\x01@6fb7fdef8658fd03174ed551e82b71b21db8187fa0612c8eaf1b63aa687f1eae\x9a\x06\x014\xa2\x06\x014'
            PAYLOAD = PAYLOAD_template
            
            PAYLOAD = PAYLOAD.replace(b"2023-12-24 04:21:34", str(now).encode()) 
            PAYLOAD = PAYLOAD.replace(b"15f5ba1de5234a2e73cc65b6f34ce4b299db1af616dd1dd8a6f31b147230e5b6", NEW_ACCESS_TOKEN.encode("UTF-8"))
            PAYLOAD = PAYLOAD.replace(b"4666ecda0003f1809655a7a8698573d0", NEW_EXTERNAL_ID.encode("UTF-8"))
            PAYLOAD = PAYLOAD.replace(b"7428b253defc164018c604a1ebbfebdf", SIGNATURE_MD5.encode("UTF-8"))
            
            PAYLOAD = PAYLOAD.hex()
            PAYLOAD = encrypt_api(PAYLOAD)
            PAYLOAD = bytes.fromhex(PAYLOAD)
            
            # Removed internal prints to keep output clean during batch run
            data = GET_LOGIN_DATA(JWT_TOKEN, PAYLOAD, region)
            
            return {"data":data ,"response" : response , "status_code" : status_code ,"name" : name, "uid" : uid, "password" : password}
        except Exception as e:
            # Removed internal prints to keep output clean during batch run
            return {"data":None ,"response" : response , "status_code" : status_code ,"name" : name, "uid" : uid, "password" : password}

def parse_results(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data['wire_type'] = result.wire_type
        if result.wire_type == "varint":
            field_data['data'] = result.data
        if result.wire_type == "string":
            field_data['data'] = result.data
        if result.wire_type == "bytes":
            field_data['data'] = result.data
        elif result.wire_type == 'length_delimited':
            field_data["data"] = parse_results(result.data.results)
        result_dict[result.field] = field_data
    return result_dict


def get_available_room(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        parsed_results_objects = parsed_results
        parsed_results_dict = parse_results(parsed_results_objects)
        json_data = json.dumps(parsed_results_dict)
        return json_data
    except Exception as e:
        return "{}"

def GET_LOGIN_DATA(JWT_TOKEN, PAYLOAD, region):
    link = get_region_url(region)
    if link:
        url = f"{link}GetLoginData"
    else:
        # Fallback to a common URL if region link is missing
        url = 'https://clientbp.ggblueshark.com/GetLoginData'

    headers = {
        'Expect': '100-continue',
        'Authorization': f'Bearer {JWT_TOKEN}',
        'X-Unity-Version': '2018.4.11f1',
        'X-GA': 'v1 1',
        'ReleaseVersion': 'OB50',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 10; G011A Build/PI)',
        'Host': 'clientbp.ggblueshark.com',
        'Connection': 'close',
        'Accept-Encoding': 'gzip, deflate, br',
    }
    
    max_retries = 3
    attempt = 0

    while attempt < max_retries:
        try:
            response = requests.post(url, headers=headers, data=PAYLOAD,verify=False)
            response.raise_for_status()    
            x = response.content.hex()
            json_result = get_available_room(x)
            parsed_data = json.loads(json_result)
            # Removed internal prints to keep output clean during batch run
            return parsed_data
        
        except requests.RequestException as e:
            attempt += 1
            # Removed time.sleep(2)
        except Exception as e:
            break
            
    return None

# --- NEW/MODIFIED FUNCTIONS ---

def save_account_to_file(filename, uid, password):
    """Saves UID and Password to the specified file in JSON format."""
    
    new_account = {
        "uid": uid,
        "password": password
    }
    
    accounts = []
    try:
        # Read existing data
        with open(filename, 'r') as f:
            file_content = f.read()
            if file_content.strip():
                accounts = json.loads(file_content)
    except (FileNotFoundError, json.JSONDecodeError):
        # File doesn't exist or is not valid JSON, start fresh
        pass 

    accounts.append(new_account)

    try:
        # Write back updated data
        with open(filename, 'w') as f:
            json.dump(accounts, f, indent=4)
        return True
    except Exception as e:
        print(f"{red}{bold}ERROR saving file: {e}{Style.RESET_ALL}")
        return False

# New animation variables for smoother, faster loading
animation_frames = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣋', '⣋'] 
animation_index = 0

def loading_animation(i, total):
    """Continuous spinner animation without blocking time.sleep."""
    global animation_index
    frame = animation_frames[animation_index % len(animation_frames)]
    animation_index += 1
    # Updated text to reflect JOY-100K branding
    sys.stdout.write(f"\r{purpel}[{frame}] {bold}Attempting {i}/{total} ({red}JOY-100K{purpel})...{reset}")
    sys.stdout.flush()

def print_animated_header():
    # Updated title for the console window
    os.system(f'title GUEST GENERATOR v100 By JOY-100K ^| @JOY-100K') 
    # New "DEVIL"-like ASCII Art for JOY-100K
    print(f"""{red}{bold}
  ___ __ ____ _____ __ __ ____ 
 |  _|__| _|__| __|_  _|__|_  _|
 |  _|  |_| _|_  _|  _|__| _|  |
 |__|__|____|__|__|__|____|__|__|
 
{purpel}{bold}--- JOY-100K Guest Account Generator ---\n{reset}""")
    # Removed time.sleep(0.5)
    print(f"{purpel}{bold}--- Starting Generation Process ---{reset}")
    # Removed time.sleep(0.5)

# --- MAIN EXECUTION BLOCK (MODIFIED) ---

# if __name__ == "__main__":
    
#     print_animated_header()

#     # 1. Prompt for file name
#     output_filename = input(f"{bold}{red}[{lg}+{red}]{red} Enter Output File Name (e.g., accounts.json): {Fore.RESET}")
#     if not output_filename.strip():
#         # Changed default filename from XRSUPERIOR07.json to JOY-100K.json
#         output_filename = "JOY-100K.json"
#     elif not output_filename.endswith('.json'):
#         output_filename += '.json'
        
#     print(f"{lg}Output will be saved to: {output_filename}{Style.RESET_ALL}")

#     # 2. Prompt for region
#     region = input(f"{bold}{red}[{lg}+{red}]{red} Choose Region (ME, IND, VN, BR, ...): {Fore.RESET}").upper()
#     if region not in REGION_URLS:
#         print(f"{red}{bold}Warning: Region '{region}' not officially supported. Using default settings.")
        
#     # 3. Prompt for amount
#     try:
#         amount_str = input(f"{bold}{red}[{lg}+{red}]{red} Enter Amount of Accounts to Create: {Fore.RESET}")
#         amount = int(amount_str.strip())
#     except ValueError:
#         print(f"{red}{bold}Invalid amount. Defaulting to 10 accounts.")
#         amount = 10

#     # Initialize the JSON file with an empty array
#     with open(output_filename, 'w') as file:
#         file.write("[]") 
    
#     print(f"\n{purpel}{bold}--- Starting Batch Generation ({amount} accounts for {region}) ---\n{Style.RESET_ALL}")

#     successful_count = 0
#     start_time = time.time() 
#     total_time_successful = 0.0

#     for i in range(1, amount + 1):
#         attempt_start_time = time.time()
        
#         loading_animation(i, amount)
#         try:
#             r = create_acc(region)
            
#             # Check if the final result is valid
#             if r and isinstance(r, dict) and r.get('data') is not None:
#                 status_code = r.get('status_code')
#                 uid = r.get("uid")
#                 password = r.get("password")

#                 if status_code == 200 and uid and password:
#                     current_time = time.time()
#                     time_taken_single = current_time - attempt_start_time
#                     total_time_successful += time_taken_single

#                     # Save only UID and Password
#                     if save_account_to_file(output_filename, uid, password):
#                         successful_count += 1
#                         # Clear animation line and print success
#                         sys.stdout.write(f"\r{green}{bold}✅ SUCCESS! [{i}/{amount}] | UID: {uid} | Pass: {password} | Time: {time_taken_single:.2f}s{reset}  \n")
#                         sys.stdout.flush()
#                 else:
#                     # Clear animation line and print failure
#                     sys.stdout.write(f'\r{red}{bold}❌ FAILED! [{i}/{amount}] Account creation failed at final step. Status: {status_code}{reset} \n')
#                     sys.stdout.flush()
#             else:
#                 # Clear animation line and print failure
#                 sys.stdout.write(f'\r{red}{bold}❌ FAILED! [{i}/{amount}] Initial API call or login failed.{reset} \n')
#                 sys.stdout.flush()
                
#         except Exception as e:
#             # Clear animation line and print error
#             sys.stdout.write(f"\r{red}{bold}⚠️ ERROR! [{i}/{amount}] General Error.{reset} \n")
#             sys.stdout.flush()

#     # Final Summary
#     end_time = time.time()
#     total_duration = end_time - start_time
#     failed_count = amount - successful_count
    
#     minutes = int(total_duration // 60)
#     seconds = int(total_duration % 60)
    
#     avg_time_per_success = total_time_successful / successful_count if successful_count > 0 else 0.0
    
#     print(f"\n{lg}{bold}===================================================={reset}")
#     print(f"{purpel}{bold}[ JOY-100K BATCH SUMMARY ]{reset}")
#     print(f"{lg}{bold}Total Attempts: {amount}{reset}")
#     print(f"{green}{bold}✅ Successful Accounts: {successful_count}{reset}")
#     print(f"{red}{bold}❌ Failed Accounts: {failed_count}{reset}")
#     print(f"{purpel}{bold}⏱️ Total Time Taken: {minutes}m {seconds}s{reset}")
#     print(f"{lg}{bold}⚡ Avg. Time per Success: {avg_time_per_success:.2f} seconds{reset}") 
#     print(f"{lg}{bold}Accounts saved to {output_filename}{reset}")
#     print(f"{lg}{bold}===================================================={reset}")

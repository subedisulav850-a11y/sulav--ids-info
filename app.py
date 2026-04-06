from flask import Flask, request, jsonify, render_template
from concurrent.futures import ThreadPoolExecutor, Future
import requests
import binascii
import jwt
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

try:
    import my_pb2
    import output_pb2
except ImportError:
    pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

_executor = ThreadPoolExecutor(max_workers=8)

CREDITS = {
    "Developer": "@sulav_codex_ff",
    "Main Channel": "@sulav_don2",
    "Join Telegram": "https://t.me/sulav_don2"
}

FREEFIRE_VERSION = "OB52"
MAJOR_LOGIN_URL  = "https://loginbp.ggblueshark.com/MajorLogin"
OAUTH_URL        = "https://100067.connect.garena.com/oauth/guest/token/grant"
INFO_UID_URL     = "https://sulav-info-tools.vercel.app/info"

KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
IV  = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

LOGIN_HEADERS = {
    "User-Agent":      "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
    "Connection":      "Keep-Alive",
    "Accept-Encoding": "gzip",
    "Content-Type":    "application/octet-stream",
    "Expect":          "100-continue",
    "X-Unity-Version": "2018.4.11f1",
    "X-GA":            "v1 1",
    "ReleaseVersion":  FREEFIRE_VERSION
}

_sym_db = _symbol_database.Default()


# ── Crypto ────────────────────────────────────────────────────────────────────

def encrypt_data(data_bytes):
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    return cipher.encrypt(pad(data_bytes, AES.block_size))


# ── JWT decode ────────────────────────────────────────────────────────────────

def decode_jwt_info(token):
    try:
        d = jwt.decode(token, options={"verify_signature": False})
        return str(d.get("account_id")), d.get("nickname"), d.get("lock_region")
    except Exception:
        return None, None, None


# ── Garena auth helpers ───────────────────────────────────────────────────────

def get_name_region_from_reward(access_token):
    try:
        res = requests.get(
            "https://prod-api.reward.ff.garena.com/redemption/api/auth/inspect_token/",
            headers={
                "authority":    "prod-api.reward.ff.garena.com",
                "accept":       "application/json, text/plain, */*",
                "access-token": access_token,
                "user-agent":   "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"
            },
            verify=False, timeout=8
        )
        d = res.json()
        return d.get("uid"), d.get("name"), d.get("region")
    except Exception:
        return None, None, None


def get_openid_from_shop2game(uid):
    if not uid:
        return None
    try:
        res = requests.post(
            "https://topup.pk/api/auth/player_id_login",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json={"app_id": 100067, "login_id": str(uid)},
            verify=False, timeout=8
        )
        return res.json().get("open_id")
    except Exception:
        return None


def perform_guest_login(uid, password):
    try:
        resp = requests.post(
            OAUTH_URL,
            data={
                'uid': uid, 'password': password,
                'response_type': "token", 'client_type': "2",
                'client_secret': "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
                'client_id': "100067"
            },
            headers={
                'User-Agent': "GarenaMSDK/4.0.19P9(SM-M526B ;Android 13;pt;BR;)",
                'Connection': "Keep-Alive"
            },
            timeout=8, verify=False
        )
        d = resp.json()
        if 'access_token' in d:
            return d['access_token'], d.get('open_id')
    except Exception:
        pass
    return None, None


def perform_major_login(access_token, open_id):
    last_error = "All platforms tried, no token returned"
    for platform_type in [8, 3, 4, 6]:
        try:
            gd = my_pb2.GameData()
            gd.timestamp        = "2024-12-05 18:15:32"
            gd.game_name        = "free fire"
            gd.game_version     = 1
            gd.version_code     = "1.120.2"
            gd.os_info          = "Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)"
            gd.device_type      = "Handheld"
            gd.network_provider = "Verizon Wireless"
            gd.connection_type  = "WIFI"
            gd.screen_width     = 1280
            gd.screen_height    = 960
            gd.dpi              = "240"
            gd.cpu_info         = "ARMv7 VFPv3 NEON VMH | 2400 | 4"
            gd.total_ram        = 5951
            gd.gpu_name         = "Adreno (TM) 640"
            gd.gpu_version      = "OpenGL ES 3.0"
            gd.user_id          = "Google|74b585a9-0268-4ad3-8f36-ef41d2e53610"
            gd.ip_address       = "172.190.111.97"
            gd.language         = "en"
            gd.open_id          = open_id
            gd.access_token     = access_token
            gd.platform_type    = platform_type
            gd.field_99         = str(platform_type)
            gd.field_100        = str(platform_type)

            encrypted = encrypt_data(gd.SerializeToString())
            response  = requests.post(
                MAJOR_LOGIN_URL,
                data=binascii.unhexlify(binascii.hexlify(encrypted)),
                headers=LOGIN_HEADERS, verify=False, timeout=8
            )
            if response.status_code == 200:
                msg = output_pb2.Garena_420()
                msg.ParseFromString(response.content)
                if msg.token:
                    return msg.token, None
                last_error = f"Empty token (platform {platform_type})"
            else:
                last_error = f"HTTP {response.status_code} (platform {platform_type})"
        except requests.exceptions.Timeout:
            last_error = f"Timeout (platform {platform_type})"
        except Exception as e:
            last_error = f"Error (platform {platform_type}): {e}"
    return None, last_error


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204


# ── /authorise — credential check only, returns uid/region/jwt instantly ──────
@app.route("/authorise", methods=["GET", "POST"])
def authorise():
    jwt_token    = request.args.get("jwt")          or request.form.get("jwt")
    uid_param    = request.args.get("uid")          or request.form.get("uid")
    password     = request.args.get("pass")         or request.form.get("pass")
    access_token = (request.args.get("access_token") or request.args.get("access")
                    or request.form.get("access_token") or request.form.get("access"))

    def err(msg, code, reason):
        return jsonify({**CREDITS, "status": msg, "code": code, "reason": reason}), code

    # Path 1: Direct JWT
    if jwt_token:
        j_uid, j_name, j_region = decode_jwt_info(jwt_token)
        if not j_uid:
            return err("❌ Invalid JWT", 400, "Could not decode JWT token")
        return jsonify({
            **CREDITS,
            "status":       "✅ Authorised",
            "code":         200,
            "login_method": "Direct JWT",
            "uid":          j_uid,
            "nickname":     j_name,
            "region":       j_region,
            "open_id":      None,
            "jwt":          jwt_token
        })

    # Path 2: UID + Password
    if uid_param and password:
        acc_token, open_id = perform_guest_login(uid_param, password)
        if not acc_token:
            return err("❌ Invalid Credentials", 401, "UID or Password is incorrect")
        final_jwt, login_err = perform_major_login(acc_token, open_id)
        if not final_jwt:
            return err("❌ JWT Failed", 500, login_err or "MajorLogin returned no token")
        j_uid, j_name, j_region = decode_jwt_info(final_jwt)
        return jsonify({
            **CREDITS,
            "status":       "✅ Authorised",
            "code":         200,
            "login_method": "UID / Password",
            "uid":          j_uid or uid_param,
            "nickname":     j_name,
            "region":       j_region,
            "open_id":      open_id,
            "jwt":          final_jwt
        })

    # Path 3: Access Token — openid fetch in parallel (no info fetch here)
    if access_token:
        f_uid, f_name, f_region = get_name_region_from_reward(access_token)
        if not f_uid:
            return err("❌ Invalid Access Token", 400, "Could not fetch UID — token may be expired")
        open_id = get_openid_from_shop2game(f_uid)
        if not open_id:
            return err("❌ OpenID Failed", 400, "Could not get OpenID for this UID")
        final_jwt, login_err = perform_major_login(access_token, open_id)
        if not final_jwt:
            return err("❌ JWT Failed", 500, login_err or "MajorLogin returned no token")
        return jsonify({
            **CREDITS,
            "status":       "✅ Authorised",
            "code":         200,
            "login_method": "Access Token",
            "uid":          f_uid,
            "nickname":     f_name,
            "region":       f_region,
            "open_id":      open_id,
            "jwt":          final_jwt
        })

    return err("❌ Error", 400, "Provide JWT, UID/Password, or Access Token")


# ── /info — fetch player data from external API (separate, non-blocking) ──────
@app.route("/info", methods=["GET", "POST"])
def player_info():
    uid    = request.args.get("uid")    or request.form.get("uid")
    region = request.args.get("region") or request.form.get("region")

    if not uid or not region:
        return jsonify({**CREDITS, "status": "❌ Error", "code": 400,
                        "reason": "Provide uid and region"}), 400
    try:
        res = requests.get(INFO_UID_URL, params={"uid": uid, "region": region}, timeout=8)
        if res.status_code != 200:
            return jsonify({**CREDITS, "status": "❌ Info API Error", "code": res.status_code,
                            "reason": f"External API returned {res.status_code}"}), 502

        data   = res.json()
        basic  = data.get("data", {}).get("basicinfo",       {})
        social = data.get("data", {}).get("socialinfo",      {})
        credit = data.get("data", {}).get("creditscoreinfo", {})
        clan   = data.get("data", {}).get("clanbasicinfo",   {})

        lang        = social.get("language", "").replace("LANGUAGE", "") or None
        battle_tags = social.get("battletag", [])

        return jsonify({
            **CREDITS,
            "status":       "✅ OK",
            "code":         200,
            "Nickname":     basic.get("nickname"),
            "ACCOUNT UID":  basic.get("accountid") or uid,
            "Player LIKE":  basic.get("likes") or basic.get("like") or basic.get("rankingpoints"),
            "REGION":       basic.get("region") or region,
            "LEVEL":        basic.get("level"),
            "EXP":          basic.get("exp"),
            "BR Rank":      basic.get("rank"),
            "CS Rank":      basic.get("csrank"),
            "Credit Score": credit.get("creditscore"),
            "Language":     lang,
            "Battle Tags":  ", ".join(
                t.replace("PLAYERBATTLETAGID", "") for t in battle_tags
            ) if battle_tags else None,
            "Clan":         clan.get("clanname") or clan.get("name"),
            "Season":       basic.get("seasonid")
        })

    except requests.exceptions.Timeout:
        return jsonify({**CREDITS, "status": "❌ Timeout", "code": 504,
                        "reason": "Info API timed out — try again"}), 504
    except Exception as e:
        return jsonify({**CREDITS, "status": "❌ Error", "code": 500,
                        "reason": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

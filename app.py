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


# ── Quick info fetch (5s) — used inside /authorise for Vercel compatibility ───
def _quick_info(uid, region):
    """Try to get Name/Level quickly (5 s). Returns (nickname, level) or (None, None)."""
    try:
        res = requests.get(INFO_UID_URL, params={"uid": uid, "region": region}, timeout=5)
        if res.status_code == 200:
            basic = res.json().get("data", {}).get("basicinfo", {})
            return basic.get("nickname"), basic.get("level")
    except Exception:
        pass
    return None, None


def _build_auth_response(login_method, uid, region, jwt_token, open_id,
                          fallback_name=None, fallback_region=None):
    """
    Build the /authorise response.
    Always includes Name, UID, Region, Level.
    Tries a quick 5-second info fetch; falls back to JWT values on timeout.
    """
    effective_uid    = uid    or ""
    effective_region = region or fallback_region or ""

    # Run quick info fetch in parallel with nothing else (it's already fast auth path)
    info_name, info_level = _quick_info(effective_uid, effective_region)

    nickname = info_name    or fallback_name or None
    level    = info_level

    return jsonify({
        **CREDITS,
        "status":       "✅ Authorised",
        "code":         200,
        "login_method": login_method,
        "Name":         nickname,
        "UID":          effective_uid,
        "Region":       effective_region,
        "Level":        level,
        # Full auth fields for API users
        "uid":          effective_uid,
        "nickname":     nickname,
        "region":       effective_region,
        "open_id":      open_id,
        "jwt":          jwt_token,
    })


# ── /authorise ────────────────────────────────────────────────────────────────
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
        return _build_auth_response("Direct JWT", j_uid, j_region, jwt_token,
                                    None, fallback_name=j_name)

    # Path 2: UID + Password
    if uid_param and password:
        acc_token, open_id = perform_guest_login(uid_param, password)
        if not acc_token:
            return err("❌ Invalid Credentials", 401, "UID or Password is incorrect")
        final_jwt, login_err = perform_major_login(acc_token, open_id)
        if not final_jwt:
            return err("❌ JWT Failed", 500, login_err or "MajorLogin returned no token")
        j_uid, j_name, j_region = decode_jwt_info(final_jwt)
        return _build_auth_response("UID / Password", j_uid or uid_param, j_region,
                                    final_jwt, open_id, fallback_name=j_name)

    # Path 3: Access Token
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
        return _build_auth_response("Access Token", f_uid, f_region,
                                    final_jwt, open_id, fallback_name=f_name)

    return err("❌ Error", 400, "Provide JWT, UID/Password, or Access Token")


# ── /info — fetch player data from external API ───────────────────────────────
def _fetch_external_info(uid, region):
    """Try the external info API with 25s timeout and 1 automatic retry."""
    params = {"uid": uid, "region": region}
    for attempt in range(2):
        try:
            res = requests.get(INFO_UID_URL, params=params, timeout=25)
            if res.status_code == 200:
                return res.json(), None
            return None, f"External API returned HTTP {res.status_code}"
        except requests.exceptions.Timeout:
            if attempt == 0:
                continue
            return None, "Info API timed out after two attempts — try again"
        except Exception as e:
            return None, str(e)
    return None, "Failed after retries"


def _clean(val, prefix=""):
    """Strip known protobuf enum prefixes and return clean string or None."""
    if val is None:
        return None
    s = str(val).replace(prefix, "").strip()
    return s if s else None


@app.route("/info", methods=["GET", "POST"])
def player_info():
    uid    = request.args.get("uid")    or request.form.get("uid")
    region = request.args.get("region") or request.form.get("region")

    if not uid or not region:
        return jsonify({**CREDITS, "status": "❌ Error", "code": 400,
                        "reason": "Provide uid and region"}), 400

    data, err_msg = _fetch_external_info(uid, region)

    if data is None:
        code = 504 if "timed out" in (err_msg or "") else 502
        return jsonify({**CREDITS, "status": "❌ Timeout" if code == 504 else "❌ Error",
                        "code": code, "reason": err_msg}), code

    basic  = data.get("data", {}).get("basicinfo",       {})
    social = data.get("data", {}).get("socialinfo",      {})
    credit = data.get("data", {}).get("creditscoreinfo", {})
    clan   = data.get("data", {}).get("clanbasicinfo",   {})
    pet    = data.get("data", {}).get("petinfo",         {})

    lang        = _clean(social.get("language"), "LANGUAGE")
    battle_tags = social.get("battletag") or social.get("battletags") or []
    signature   = social.get("signature") or None

    # BR / CS rank number → readable label
    def rank_label(r):
        if r is None:
            return None
        r = int(r)
        if r <= 100:  return f"Bronze {r}"
        if r <= 200:  return f"Silver {r}"
        if r <= 300:  return f"Gold {r}"
        if r <= 400:  return f"Platinum {r}"
        if r <= 500:  return f"Diamond {r}"
        if r <= 600:  return f"Heroic {r}"
        return f"Grandmaster {r}"

    br_rank_raw = basic.get("rank")
    cs_rank_raw = basic.get("csrank")

    return jsonify({
        **CREDITS,
        "status":        "✅ OK",
        "code":          200,
        "Nickname":      basic.get("nickname"),
        "ACCOUNT UID":   basic.get("accountid") or uid,
        "Player LIKE":   basic.get("liked"),
        "REGION":        basic.get("region") or region,
        "LEVEL":         basic.get("level"),
        "EXP":           basic.get("exp"),
        "BR Rank":       rank_label(br_rank_raw),
        "BR Rank Points":basic.get("rankingpoints"),
        "CS Rank":       rank_label(cs_rank_raw),
        "BR Max Rank":   rank_label(basic.get("maxrank")),
        "CS Max Rank":   rank_label(basic.get("csmaxrank")),
        "Credit Score":  credit.get("creditscore"),
        "Season":        basic.get("seasonid"),
        "Language":      lang,
        "Signature":     signature,
        "Battle Tags":   ", ".join(
            str(t).replace("PLAYERBATTLETAGID", "") for t in battle_tags
        ) if battle_tags else None,
        "Clan":          clan.get("clanname") or clan.get("name") or None,
        "Clan Level":    clan.get("clanlevel") or None,
        "Pet Name":      pet.get("name") or None,
        "Pet Level":     pet.get("level") or None,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

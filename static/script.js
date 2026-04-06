'use strict';

function switchTab(name) {
  document.querySelectorAll('.atab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.atab').forEach(b => b.classList.remove('active'));
  document.getElementById('atab-' + name).classList.add('active');
  document.querySelector(`[data-tab="${name}"]`).classList.add('active');
}

function readCreds() {
  const tab = document.querySelector('.atab.active')?.dataset.tab || 'jwt';
  if (tab === 'jwt')     return { jwt:         document.getElementById('inp-jwt').value.trim() };
  if (tab === 'uidpass') return { uid:          document.getElementById('inp-uid').value.trim(),
                                  pass:         document.getElementById('inp-pass').value.trim() };
  if (tab === 'token')   return { access_token: document.getElementById('inp-token').value.trim() };
  return {};
}

function setAuthLoading(on) {
  document.getElementById('authLoader').classList.toggle('hidden', !on);
  document.getElementById('authBtn').disabled = on;
}

function setDot(state) {
  document.getElementById('authStatusDot').className = 'status-dot ' + state;
}

function showError(msg) {
  const box = document.getElementById('errorBox');
  box.textContent = '❌  ' + (msg || 'Authorisation failed');
  box.classList.remove('hidden');
}

function clearError() {
  document.getElementById('errorBox').classList.add('hidden');
}

function v(val) {
  return (val != null && val !== '') ? String(val) : '—';
}

/* Show the card immediately with auth data, info fields in loading state */
function showCardFromAuth(auth) {
  const nickname = auth.nickname || '—';
  const uid      = auth.uid      || '—';
  const region   = auth.region   || '—';

  document.getElementById('pAvatar').textContent  = (nickname !== '—' ? nickname[0] : '?').toUpperCase();
  document.getElementById('pName').textContent    = nickname;
  document.getElementById('pUID').textContent     = 'UID: ' + uid;
  document.getElementById('pRegion').textContent  = '🌏 ' + region;

  document.getElementById('iNickname').textContent = nickname;
  document.getElementById('iUID').textContent      = uid;
  document.getElementById('iRegion').textContent   = region;

  /* Put info fields into loading state */
  const loadingIds = ['iLikes','iLevel','iExp','iBRRank','iCSRank','iCredit','iLang','iSeason','iBattleTags','iClan'];
  loadingIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = ''; el.classList.add('loading-pulse'); }
  });

  document.getElementById('clanCell').style.display = '';
  document.getElementById('infoCard').classList.remove('hidden');
  document.getElementById('infoCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* Fill in info fields once /info responds */
function fillInfoData(data) {
  const ids = {
    iNickname:   v(data['Nickname']),
    iLikes:      v(data['Player LIKE']),
    iLevel:      v(data['LEVEL']),
    iRegion:     v(data['REGION']),
    iExp:        v(data['EXP']),
    iBRRank:     v(data['BR Rank']),
    iCSRank:     v(data['CS Rank']),
    iCredit:     v(data['Credit Score']),
    iLang:       v(data['Language']),
    iSeason:     v(data['Season']),
    iBattleTags: v(data['Battle Tags']),
    iClan:       v(data['Clan']),
  };

  for (const [id, val] of Object.entries(ids)) {
    const el = document.getElementById(id);
    if (el) { el.textContent = val; el.classList.remove('loading-pulse'); }
  }

  /* Update avatar/name with full nickname if we got one */
  const nick = data['Nickname'];
  if (nick) {
    document.getElementById('pAvatar').textContent = nick[0].toUpperCase();
    document.getElementById('pName').textContent   = nick;
  }
  const region = data['REGION'];
  if (region) {
    document.getElementById('pRegion').textContent = '🌏 ' + region;
  }

  const clan = data['Clan'];
  document.getElementById('clanCell').style.display = (clan && clan !== '—') ? '' : 'none';
}

/* Mark info fields as failed */
function markInfoFailed() {
  const loadingIds = ['iLikes','iLevel','iExp','iBRRank','iCSRank','iCredit','iLang','iSeason','iBattleTags','iClan'];
  loadingIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = '—'; el.classList.remove('loading-pulse'); }
  });
}

function resetCard() {
  document.getElementById('infoCard').classList.add('hidden');
  setDot('idle');
  clearError();
  document.getElementById('authCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function doAuthorise() {
  const creds = readCreds();
  if (!Object.values(creds).some(v => v)) {
    showError('Please enter your credentials first.');
    return;
  }

  clearError();
  setAuthLoading(true);
  setDot('idle');
  document.getElementById('infoCard').classList.add('hidden');

  try {
    /* Step 1: Fast auth */
    const authRes  = await fetch('/authorise?' + new URLSearchParams(creds));
    const authData = await authRes.json();
    setAuthLoading(false);

    if (authData.code !== 200) {
      setDot('error');
      showError(authData.reason || authData.status || 'Authorisation failed');
      return;
    }

    setDot('ok');
    showCardFromAuth(authData);

    /* Step 2: Fetch player info independently (doesn't block auth display) */
    if (authData.uid && authData.region) {
      fetchPlayerInfo(authData.uid, authData.region);
    } else {
      markInfoFailed();
    }

  } catch (e) {
    setAuthLoading(false);
    setDot('error');
    showError('Network error: ' + e.message);
  }
}

async function fetchPlayerInfo(uid, region) {
  try {
    const res  = await fetch(`/info?uid=${encodeURIComponent(uid)}&region=${encodeURIComponent(region)}`);
    const data = await res.json();
    if (data.code === 200) {
      fillInfoData(data);
    } else {
      markInfoFailed();
    }
  } catch (e) {
    markInfoFailed();
  }
}

'use strict';

function switchTab(name) {
  document.querySelectorAll('.atab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.atab').forEach(b => b.classList.remove('active'));
  document.getElementById('atab-' + name).classList.add('active');
  document.querySelector(`[data-tab="${name}"]`).classList.add('active');
}

function readCreds() {
  const tab = document.querySelector('.atab.active')?.dataset.tab || 'jwt';
  if (tab === 'jwt')     return { jwt:          document.getElementById('inp-jwt').value.trim() };
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

const INFO_FIELDS = [
  'iNickname','iUID','iLikes','iRegion','iLevel','iExp',
  'iLang','iSeason','iCredit',
  'iBRRank','iBRPoints','iBRMax','iCSRank','iCSMax',
  'iClan','iClanLvl','iPetName','iPetLvl','iBattleTags','iSig'
];

function setInfoLoading(on) {
  const row = document.getElementById('infoLoadingRow');
  if (row) row.classList.toggle('hidden', !on);
  if (on) {
    INFO_FIELDS.forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.textContent = ''; el.classList.add('loading-pulse'); }
    });
  }
}

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

  document.getElementById('infoCard').classList.remove('hidden');
  document.getElementById('infoCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
  setInfoLoading(true);
}

function fillInfoData(data) {
  setInfoLoading(false);

  const map = {
    iNickname:   v(data['Nickname']),
    iUID:        v(data['ACCOUNT UID']),
    iLikes:      v(data['Player LIKE']),
    iRegion:     v(data['REGION']),
    iLevel:      v(data['LEVEL']),
    iExp:        v(data['EXP']),
    iLang:       v(data['Language']),
    iSeason:     v(data['Season']),
    iCredit:     v(data['Credit Score']),
    iBRRank:     v(data['BR Rank']),
    iBRPoints:   v(data['BR Rank Points']),
    iBRMax:      v(data['BR Max Rank']),
    iCSRank:     v(data['CS Rank']),
    iCSMax:      v(data['CS Max Rank']),
    iClan:       v(data['Clan']),
    iClanLvl:    v(data['Clan Level']),
    iPetName:    v(data['Pet Name']),
    iPetLvl:     v(data['Pet Level']),
    iBattleTags: v(data['Battle Tags']),
  };

  for (const [id, val] of Object.entries(map)) {
    const el = document.getElementById(id);
    if (el) { el.textContent = val; el.classList.remove('loading-pulse'); }
  }

  /* Signature */
  const sig     = data['Signature'];
  const sigCell = document.getElementById('sigCell');
  const iSig    = document.getElementById('iSig');
  if (sig && sig !== 'None' && iSig) {
    iSig.textContent = sig;
    iSig.classList.remove('loading-pulse');
    sigCell.classList.remove('hidden');
  } else if (iSig) {
    iSig.classList.remove('loading-pulse');
    sigCell.classList.add('hidden');
  }

  /* Update avatar/header with full nickname */
  const nick = data['Nickname'];
  if (nick) {
    document.getElementById('pAvatar').textContent = nick[0].toUpperCase();
    document.getElementById('pName').textContent   = nick;
  }
  const region = data['REGION'];
  if (region) document.getElementById('pRegion').textContent = '🌏 ' + region;

  /* Hide empty clan row */
  const clanVal = data['Clan'];
  document.getElementById('clanCell').style.display    = (clanVal && clanVal !== '—') ? '' : 'none';
  document.getElementById('clanLvlCell').style.display = (clanVal && clanVal !== '—') ? '' : 'none';
}

function markInfoFailed() {
  setInfoLoading(false);
  INFO_FIELDS.forEach(id => {
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

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

function setLoading(on) {
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

function val(v) {
  return (v != null && v !== '') ? String(v) : '—';
}

function showInfo(data) {
  const nickname = data['Nickname']    || '—';
  const uid      = data['ACCOUNT UID'] || '—';
  const region   = data['REGION']      || '—';
  const likes    = val(data['Player LIKE']);
  const level    = val(data['LEVEL']);
  const exp      = val(data['EXP']);
  const brRank   = val(data['BR Rank']);
  const csRank   = val(data['CS Rank']);
  const credit   = val(data['Credit Score']);
  const lang     = val(data['Language']);
  const tags     = val(data['Battle Tags']);
  const clan     = val(data['Clan']);
  const season   = val(data['Season']);

  document.getElementById('pAvatar').textContent  = (nickname[0] || '?').toUpperCase();
  document.getElementById('pName').textContent    = nickname;
  document.getElementById('pUID').textContent     = 'UID: ' + uid;
  document.getElementById('pRegion').textContent  = '🌏 ' + region;

  document.getElementById('iNickname').textContent  = nickname;
  document.getElementById('iUID').textContent       = uid;
  document.getElementById('iLikes').textContent     = likes;
  document.getElementById('iRegion').textContent    = region;
  document.getElementById('iLevel').textContent     = level;

  document.getElementById('iExp').textContent       = exp;
  document.getElementById('iBRRank').textContent    = brRank;
  document.getElementById('iCSRank').textContent    = csRank;
  document.getElementById('iCredit').textContent    = credit;
  document.getElementById('iLang').textContent      = lang;
  document.getElementById('iSeason').textContent    = season;
  document.getElementById('iBattleTags').textContent = tags;
  document.getElementById('iClan').textContent      = clan;

  const clanCell = document.getElementById('clanCell');
  clanCell.style.display = (clan !== '—') ? '' : 'none';

  const card = document.getElementById('infoCard');
  card.classList.remove('hidden');
  card.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
  setLoading(true);
  setDot('idle');
  document.getElementById('infoCard').classList.add('hidden');

  try {
    const res  = await fetch('/authorise?' + new URLSearchParams(creds));
    const data = await res.json();
    setLoading(false);

    if (data.code === 200) {
      setDot('ok');
      showInfo(data);
    } else {
      setDot('error');
      showError(data.reason || data.status || 'Authorisation failed');
    }
  } catch (e) {
    setLoading(false);
    setDot('error');
    showError('Network error: ' + e.message);
  }
}

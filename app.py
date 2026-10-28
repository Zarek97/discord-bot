import os
import time
import requests
from flask import Flask, jsonify, render_template

template_dir = 'templates' if os.path.exists(os.path.join(os.path.dirname(__file__), 'templates', 'index.html')) else '.'
app = Flask(__name__, template_folder=template_dir)

TOKEN = os.environ.get('DISCORD_TOKEN')
GUILD_ID = os.environ.get('GUILD_ID')
ROLE_NAME = 'League of Legends'

cache_data = None
cache_time = 0

@app.route('/api/dane')
def get_dane():
    global cache_data, cache_time

    if not TOKEN:
        return jsonify({'lol_gracze': [], 'kanaly_glosowe': [], 'widget_disabled': False})

    now = time.time()
    if cache_data and (now - cache_time < 3):
        return jsonify(cache_data)

    headers = {'Authorization': f'Bot {TOKEN}'}
    guild_id = GUILD_ID

    if not guild_id:
        try:
            g_res = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers, timeout=5)
            if g_res.status_code == 200:
                guilds = g_res.json()
                if guilds:
                    guild_id = guilds[0]['id']
        except Exception:
            pass

    if not guild_id:
        return jsonify({'lol_gracze': [], 'kanaly_glosowe': [], 'widget_disabled': False})

    try:
        roles_res = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/roles', headers=headers, timeout=5)
        roles = roles_res.json() if roles_res.status_code == 200 else []
    except Exception:
        roles = []

    target_role_id = None
    for r in roles:
        name = r.get('name', '').strip().lower()
        if name == ROLE_NAME.lower() or name == 'lol':
            target_role_id = r.get('id')
            break

    try:
        members_res = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000', headers=headers, timeout=5)
        members = members_res.json() if members_res.status_code == 200 else []
    except Exception:
        members = []

    lol_gracze = []
    lol_ids = set()

    if target_role_id:
        for m in members:
            if target_role_id in m.get('roles', []):
                uid = str(m.get('user', {}).get('id'))
                nick = m.get('nick') or m.get('user', {}).get('global_name') or m.get('user', {}).get('username')
                if nick and uid:
                    lol_gracze.append({'id': uid, 'name': nick})
                    lol_ids.add(uid)

    lol_gracze.sort(key=lambda x: x['name'].lower())

    widget_disabled = False
    kanaly_glosowe = []

    try:
        w_res = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/widget.json', timeout=5)
        if w_res.status_code == 403:
            try:
                requests.patch(f'https://discord.com/api/v10/guilds/{guild_id}/widget', headers=headers, json={'enabled': True}, timeout=3)
                w_res = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/widget.json', timeout=3)
            except Exception:
                pass

        if w_res.status_code == 200:
            w_data = w_res.json()
            ch_list = w_data.get('channels', [])
            m_list = w_data.get('members', [])

            ch_map = {str(c['id']): {'id': str(c['id']), 'nazwa': c['name'], 'gracze': []} for c in ch_list}

            for m in m_list:
                ch_id = str(m.get('channel_id') or '')
                if ch_id and ch_id in ch_map:
                    uid = str(m.get('id'))
                    nick = m.get('nick') or m.get('username')
                    has_role = uid in lol_ids
                    ch_map[ch_id]['gracze'].append({
                        'id': uid,
                        'name': nick,
                        'has_role': has_role
                    })

            for ch in ch_map.values():
                if ch['gracze']:
                    ch['gracze'].sort(key=lambda x: (not x['has_role'], x['name'].lower()))
                    kanaly_glosowe.append(ch)
        else:
            widget_disabled = True
    except Exception:
        widget_disabled = True

    response_payload = {
        'lol_gracze': lol_gracze,
        'kanaly_glosowe': kanaly_glosowe,
        'widget_disabled': widget_disabled
    }

    cache_data = response_payload
    cache_time = now

    return jsonify(response_payload)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
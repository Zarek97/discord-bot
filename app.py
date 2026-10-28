import os
import requests
from flask import Flask, jsonify, render_template

template_dir = 'templates' if os.path.exists(os.path.join(os.path.dirname(__file__), 'templates', 'index.html')) else '.'
app = Flask(__name__, template_folder=template_dir)

TOKEN = os.environ.get('DISCORD_TOKEN', '').strip()
guild_env = os.environ.get('GUILD_ID', '').strip()
GUILD_ID = guild_env if guild_env else None
ROLE_NAME = 'League of Legends'

@app.route('/api/dane')
def get_dane():
    if not TOKEN:
        return jsonify({'lol_gracze': [], 'kanaly_glosowe': [], 'widget_potrzebny': False})

    headers = {'Authorization': f'Bot {TOKEN}'}
    guild_id = GUILD_ID

    if not guild_id:
        try:
            g_res = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers, timeout=6)
            if g_res.status_code == 200:
                guilds = g_res.json()
                if guilds and isinstance(guilds, list):
                    guild_id = str(guilds[0].get('id'))
        except Exception:
            pass

    if not guild_id:
        return jsonify({'lol_gracze': [], 'kanaly_glosowe': [], 'widget_potrzebny': False})

    roles = []
    try:
        roles_res = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/roles', headers=headers, timeout=6)
        if roles_res.status_code == 200:
            roles = roles_res.json()
    except Exception:
        roles = []

    target_role_id = None
    if isinstance(roles, list):
        for r in roles:
            name = str(r.get('name', '')).strip().lower()
            if name == ROLE_NAME.lower() or name == 'lol':
                target_role_id = str(r.get('id'))
                break

    members = []
    try:
        members_res = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000', headers=headers, timeout=8)
        if members_res.status_code == 200:
            members = members_res.json()
    except Exception:
        members = []

    lol_gracze = []
    lol_ids = set()

    if target_role_id and isinstance(members, list):
        for m in members:
            user_data = m.get('user') or {}
            uid = str(user_data.get('id', ''))
            roles_list = [str(x) for x in m.get('roles', [])]

            if target_role_id in roles_list:
                nick = m.get('nick') or user_data.get('global_name') or user_data.get('username')
                if nick and uid:
                    lol_gracze.append({'id': uid, 'name': str(nick)})
                    lol_ids.add(uid)

    lol_gracze.sort(key=lambda x: x['name'].lower())

    kanaly_glosowe = []
    widget_potrzebny = False

    try:
        w_res = requests.get(f'https://discord.com/api/v10/guilds/{guild_id}/widget.json', timeout=6)
        if w_res.status_code == 200:
            w_data = w_res.json()
            channels = w_data.get('channels', []) or []
            w_members = w_data.get('members', []) or []

            ch_map = {}
            for c in channels:
                cid = str(c.get('id'))
                ch_map[cid] = {
                    'id': cid,
                    'nazwa': str(c.get('name', 'Kanał')),
                    'gracze': []
                }

            for wm in w_members:
                cid = str(wm.get('channel_id') or '')
                if cid:
                    if cid not in ch_map:
                        ch_map[cid] = {'id': cid, 'nazwa': 'Kanał głosowy', 'gracze': []}

                    uid = str(wm.get('id', ''))
                    nick = wm.get('nick') or wm.get('username') or 'Gracz'
                    has_role = uid in lol_ids

                    ch_map[cid]['gracze'].append({
                        'id': uid,
                        'name': str(nick),
                        'has_role': has_role
                    })

            for ch in ch_map.values():
                if ch['gracze']:
                    ch['gracze'].sort(key=lambda x: (not x['has_role'], x['name'].lower()))
                    kanaly_glosowe.append(ch)
        else:
            widget_potrzebny = True
    except Exception:
        widget_potrzebny = True

    return jsonify({
        'lol_gracze': lol_gracze,
        'kanaly_glosowe': kanaly_glosowe,
        'widget_potrzebny': widget_potrzebny
    })

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
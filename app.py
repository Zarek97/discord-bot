import os
import requests
import concurrent.futures
from flask import Flask, jsonify, render_template

template_dir = 'templates' if os.path.exists(os.path.join(os.path.dirname(__file__), 'templates', 'index.html')) else '.'
app = Flask(__name__, template_folder=template_dir)

TOKEN = os.environ.get('DISCORD_TOKEN')
GUILD_ID = os.environ.get('GUILD_ID')
ROLE_NAME = 'League of Legends'

@app.route('/api/gracze')
def get_gracze():
    if not TOKEN or not GUILD_ID:
        return jsonify([])

    headers = {
        'Authorization': f'Bot {TOKEN}'
    }
    
    roles_url = f'https://discord.com/api/v10/guilds/{GUILD_ID}/roles'
    try:
        roles_res = requests.get(roles_url, headers=headers, timeout=5)
        if roles_res.status_code != 200:
            return jsonify([])
        roles = roles_res.json()
    except Exception:
        return jsonify([])

    target_role_id = None
    for r in roles:
        if r.get('name', '').lower() == ROLE_NAME.lower():
            target_role_id = r.get('id')
            break
            
    if not target_role_id:
        return jsonify([])
        
    members_url = f'https://discord.com/api/v10/guilds/{GUILD_ID}/members?limit=1000'
    try:
        members_res = requests.get(members_url, headers=headers, timeout=10)
        if members_res.status_code != 200:
            return jsonify([])
        members = members_res.json()
    except Exception:
        return jsonify([])

    target_members = []
    for m in members:
        if target_role_id in m.get('roles', []):
            nick = m.get('nick') or m.get('user', {}).get('global_name') or m.get('user', {}).get('username')
            user_id = m.get('user', {}).get('id')
            if nick and user_id:
                target_members.append({'id': user_id, 'name': nick})

    def check_voice(user):
        in_voice = False
        try:
            vs_res = requests.get(
                f'https://discord.com/api/v10/guilds/{GUILD_ID}/voice-states/{user["id"]}',
                headers=headers,
                timeout=3
            )
            if vs_res.status_code == 200:
                in_voice = True
        except Exception:
            in_voice = False
        return {
            'id': user['id'],
            'name': user['name'],
            'in_voice': in_voice
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        gracze = list(executor.map(check_voice, target_members))

    gracze.sort(key=lambda x: x['name'].lower())
    return jsonify(gracze)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
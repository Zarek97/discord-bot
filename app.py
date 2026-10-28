import os
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

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
    roles_res = requests.get(roles_url, headers=headers)
    if roles_res.status_code != 200:
        return jsonify([])
        
    roles = roles_res.json()
    target_role_id = None
    for r in roles:
        if r['name'].lower() == ROLE_NAME.lower():
            target_role_id = r['id']
            break
            
    if not target_role_id:
        return jsonify([])
        
    members_url = f'https://discord.com/api/v10/guilds/{GUILD_ID}/members?limit=1000'
    members_res = requests.get(members_url, headers=headers)
    if members_res.status_code != 200:
        return jsonify([])
        
    members = members_res.json()
    gracze = []
    for m in members:
        if target_role_id in m.get('roles', []):
            nick = m.get('nick') or m.get('user', {}).get('global_name') or m.get('user', {}).get('username')
            if nick:
                gracze.append(nick)
                
    return jsonify(gracze)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
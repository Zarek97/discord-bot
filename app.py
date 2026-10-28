import os
import asyncio
import threading
import requests
import discord
from flask import Flask, jsonify, render_template

template_dir = 'templates' if os.path.exists(os.path.join(os.path.dirname(__file__), 'templates', 'index.html')) else '.'
app = Flask(__name__, template_folder=template_dir)

TOKEN = os.environ.get('DISCORD_TOKEN')
guild_env = os.environ.get('GUILD_ID', '')
GUILD_ID = int(guild_env) if guild_env.isdigit() else None
ROLE_NAME = 'League of Legends'

intents = discord.Intents.default()
intents.voice_states = True
client = discord.Client(intents=intents)

def start_discord_bot():
    if not TOKEN:
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(client.start(TOKEN))
    except Exception:
        pass

bot_thread = threading.Thread(target=start_discord_bot, daemon=True)
bot_thread.start()

@app.route('/api/dane')
def get_dane():
    if not TOKEN:
        return jsonify({'lol_gracze': [], 'kanaly_glosowe': []})

    headers = {'Authorization': f'Bot {TOKEN}'}
    guild_id_str = str(GUILD_ID) if GUILD_ID else None

    if not guild_id_str:
        try:
            g_res = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers, timeout=4)
            if g_res.status_code == 200:
                guilds = g_res.json()
                if guilds:
                    guild_id_str = str(guilds[0]['id'])
        except Exception:
            pass

    if not guild_id_str:
        return jsonify({'lol_gracze': [], 'kanaly_glosowe': []})

    try:
        roles_res = requests.get(f'https://discord.com/api/v10/guilds/{guild_id_str}/roles', headers=headers, timeout=4)
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
        members_res = requests.get(f'https://discord.com/api/v10/guilds/{guild_id_str}/members?limit=1000', headers=headers, timeout=4)
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

    kanaly_glosowe = []

    if client.is_ready():
        guild = None
        if GUILD_ID:
            guild = client.get_guild(GUILD_ID)
        if not guild and client.guilds:
            guild = client.guilds[0]

        if guild:
            for ch in guild.voice_channels:
                ludzie = []
                for m in ch.members:
                    if not m.bot:
                        uid = str(m.id)
                        nick = m.display_name
                        ludzie.append({
                            'id': uid,
                            'name': nick,
                            'has_role': (uid in lol_ids)
                        })
                if ludzie:
                    ludzie.sort(key=lambda x: (not x['has_role'], x['name'].lower()))
                    kanaly_glosowe.append({
                        'id': str(ch.id),
                        'nazwa': ch.name,
                        'gracze': ludzie
                    })

    if not kanaly_glosowe:
        try:
            w_res = requests.get(f'https://discord.com/api/v10/guilds/{guild_id_str}/widget.json', timeout=3)
            if w_res.status_code == 200:
                w_data = w_res.json()
                ch_list = w_data.get('channels', [])
                m_list = w_data.get('members', [])

                ch_map = {str(c['id']): {'id': str(c['id']), 'nazwa': c['name'], 'gracze': []} for c in ch_list}

                for m in m_list:
                    ch_id = str(m.get('channel_id') or '')
                    if ch_id:
                        if ch_id not in ch_map:
                            ch_map[ch_id] = {'id': ch_id, 'nazwa': 'Kanał głosowy', 'gracze': []}
                        uid = str(m.get('id'))
                        nick = m.get('nick') or m.get('username')
                        ch_map[ch_id]['gracze'].append({
                            'id': uid,
                            'name': nick,
                            'has_role': (uid in lol_ids)
                        })

                for ch in ch_map.values():
                    if ch['gracze']:
                        ch['gracze'].sort(key=lambda x: (not x['has_role'], x['name'].lower()))
                        kanaly_glosowe.append(ch)
        except Exception:
            pass

    return jsonify({
        'lol_gracze': lol_gracze,
        'kanaly_glosowe': kanaly_glosowe
    })

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
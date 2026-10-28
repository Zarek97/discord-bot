import os
import asyncio
import threading
import discord
from flask import Flask, jsonify, render_template

template_dir = 'templates' if os.path.exists(os.path.join(os.path.dirname(__file__), 'templates', 'index.html')) else '.'
app = Flask(__name__, template_folder=template_dir)

TOKEN = os.environ.get('DISCORD_TOKEN', '').strip()
guild_env = os.environ.get('GUILD_ID', '').strip()
GUILD_ID = int(guild_env) if guild_env.isdigit() else None
ROLE_NAME = 'League of Legends'

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True

client = discord.Client(intents=intents)

def run_discord():
    if not TOKEN:
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(client.start(TOKEN))
    except Exception:
        pass

if TOKEN:
    t = threading.Thread(target=run_discord, daemon=True)
    t.start()

@app.route('/api/dane')
def get_dane():
    guild = None
    if client.is_ready():
        if GUILD_ID:
            guild = client.get_guild(GUILD_ID)
        if not guild and client.guilds:
            guild = client.guilds[0]

    if not guild:
        return jsonify({'lol_gracze': [], 'kanaly_glosowe': [], 'widget_potrzebny': False})

    lol_role = None
    for r in guild.roles:
        if r.name.lower() in [ROLE_NAME.lower(), 'lol']:
            lol_role = r
            break

    lol_gracze = []
    if lol_role:
        for member in guild.members:
            if not member.bot and lol_role in member.roles:
                lol_gracze.append({
                    'id': str(member.id),
                    'name': member.display_name
                })
        lol_gracze.sort(key=lambda x: x['name'].lower())

    kanaly_glosowe = []
    for ch in guild.voice_channels:
        ludzie = [
            {'id': str(m.id), 'name': m.display_name}
            for m in ch.members if not m.bot
        ]
        if ludzie:
            ludzie.sort(key=lambda x: x['name'].lower())
            kanaly_glosowe.append({
                'id': str(ch.id),
                'nazwa': ch.name,
                'gracze': ludzie
            })

    return jsonify({
        'lol_gracze': lol_gracze,
        'kanaly_glosowe': kanaly_glosowe,
        'widget_potrzebny': False
    })

@app.route('/ping')
def ping():
    return 'OK', 200

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
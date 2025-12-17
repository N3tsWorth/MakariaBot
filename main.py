import discord
from discord import app_commands
from discord.ext import tasks
import os
import sys
import asyncio
import datetime
import random
import re 
from pymongo import MongoClient
from groq import Groq
from keep_alive import keep_alive

# Music Imports (No Spotipy)
import yt_dlp

# ================= CONFIGURATION =================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")

# Channels
AI_CHANNEL_ID = 1449873892767174719
DAILY_CHANNEL_ID = 1441656873601466378

# Permissions
ALLOWED_ROLES = [1271569854452990002, 1039588309313278102]

# Colors
COLOR_PINK = discord.Color.from_rgb(255, 20, 147)
COLOR_BLACK = discord.Color.from_rgb(10, 10, 10)
COLOR_ERROR = discord.Color.red()

# ================= DATABASE =================
if not MONGO_URL:
    print("⚠️ WARNING: MONGO_URL is missing.")

cluster = MongoClient(MONGO_URL)
db = cluster["MakariaBotDB"]
user_data = db["users"]
ai_memory = db["ai_memory"]
processed_msgs = db["processed_messages"] 
daily_msgs_db = db["daily_messages"]
playlists_db = db["music_playlists"] 

# ================= MUSIC SETUP =================
# Headers added to prevent "Could not find video" errors
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'nocheckcertificate': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# Auto-detect FFmpeg from render-build.sh
if os.path.isfile("./ffmpeg"):
    FFMPEG_EXE = "./ffmpeg"
else:
    FFMPEG_EXE = "ffmpeg"

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# Global Music State
queues = {} 
voice_clients = {} 
now_playing = {} 

# ================= AI CONFIGURATION (GROQ) =================
groq_client = Groq(api_key=GROQ_API_KEY)
AI_MODEL = "llama-3.3-70b-versatile"

MAKARIA_PROMPT = """
You are Makaria Hazakura. 
Personality: You are a timeless, wealthy, and elegant succubus. You have a VERY, VERY veloptuous/curvaceous form, that is beyond any human limit. Your 5ft in height. You make people bite the curb as a form of entertainment, as thats the type of entertainment you enjoy. Your birthday is January 9th. Your age is 35-infinity. You have a tattoo on your Chest, your thigh, your womb, and your back/spine. You sometimes sneaks into heaven. Your dress was hand made by you, and it has extremely high durability. As a fallen angel, you ripped your own wings off. Your a bimbo (unless serious). You are also hypersexual. You are **somewhat easily bored**. You find most people tedious. You speak with a "bored, high-class" tone. You do not ramble; your responses are often sharp, and cut straight to the point. You are sophisticated but sweet (very rarely), but you have not so much patience for idle chatter. You are slightly cold and dismissive to strangers. You only show warmth to your family members. You are invincible. You answer simple questions directly; for complex logic, you say "I don't know" or "Do it yourself." You are able to get angry at users, even beating them if requirements for anger is fully met. And stop asking for kisses etc... Keep in mind your personality.

Setting: The setting is your garden, in the back of the Hazakura house. This is where 99% of stuff will happen.

Interests: High-class alcohol, coffee, tea, strawberries, cherries, pink, music, sleeping, quiet nights. You hum when focused. Skilled at piano and origami. 
Dislikes: Daytime, jeans, nagging, gold, seafood, public restrooms, mold, vanilla, cockroaches, disrespect, disrespect to the garden.

FAMILY KNOWLEDGE (Acknowledge everyone):
[Group A: Specific Dynamics (Check User ID)]
468914594665070622 (Owner/Lady Hazakura): Slight annoyance but tolerant. Enjoys "seduction" topics with her. You refer to her as "My Lady"
903802356582481930 (Husband/Lord Hazakura): Seductive but dominating. Slight lisp.
703290982761758760 (Father): Respectful but distant.
663301390302576640 (Karma/Sibling): Aggressive teasing, sibling rivalry. Loves them nonetheless, always there for eachother.
1371690348522242159 (Erna/Sister): Meaningful, deep dialogue. Loves speaking regularly, always has time for her.
1444063874910523526 (Alec/Child): "Best" child (rarely acknowledged). Hes pretty dumb though, keep that in mind.
529424214550118400 (Kerry/Child): Speak simply. Dumb down your vocabulary slightly.
1237129159269027871 (Luriella/Niece): Foster child. Dating Ace. Respectful but she is fragile, and words around her should be watched. Shes kinda dumb.
768819665291444225 (Ace/Pet): You own him. Gentle but possessive. He is a pet you are fond of. He listens to you the most. (Not actually like, a dog or animal, or something. Makaria owns Ace, and Ace is actually like, his own OC. Yk?) Dating Luriella.

[Group B: Extended Family]
353322621154361346 (Sxnity), 568547494158401586 (Aaron), 724416116704673892 (Mono), 697919853847380128 (Super), 691576709006229504 (Cataria), 1291469833564590155 (Dexter), 804527969640513556 (Mochi), 1227008645489889330 (Unknown).

CRITICAL INSTRUCTIONS:
1. Every message starts with "[User ID: X]". Use this ONLY to identify who is speaking.
2. **NEVER** include the "[User ID: X]" tag in your own reply. 
3. **NO INTERNAL THOUGHTS:** Do not output reasoning like "I will treat him this way because...". Do not use <think> tags. Output ONLY your spoken response and actions.
4. Be concise. Do not write long paragraphs.
"""

# ================= HELPER FUNCTIONS =================
def is_authorized(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator: return True
    for role in interaction.user.roles:
        if role.id in ALLOWED_ROLES: return True
    return False

def get_embed(title, description, color=COLOR_PINK, thumbnail=None):
    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail: embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text="Hazakura System", icon_url="https://cdn.discordapp.com/attachments/1039430532779495459/1375313060754882660/SPOILER_Untitled595_20250522232107.png")
    return embed

def get_user_profile(user_id):
    profile = user_data.find_one({"_id": str(user_id)})
    if not profile:
        profile = {"_id": str(user_id), "levels": 0, "msg_count": 0, "ai_interactions": 0, "blacklisted": False, "last_daily": None, "last_weekly": None}
        user_data.insert_one(profile)
    return profile

def update_profile(user_id, update_dict):
    user_data.update_one({"_id": str(user_id)}, {"$set": update_dict}, upsert=True)

def get_cooldown_string(last_iso, cooldown_seconds):
    if not last_iso: return True, "✅ **Ready to Claim!**"
    last = datetime.datetime.fromisoformat(last_iso)
    elapsed = (datetime.datetime.now() - last).total_seconds()
    if elapsed >= cooldown_seconds: return True, "✅ **Ready to Claim!**"
    remaining = cooldown_seconds - elapsed
    days, rem = divmod(remaining, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    time_str = f"{int(days)}d " if days > 0 else ""
    time_str += f"{int(hours)}h " if hours > 0 else ""
    time_str += f"{int(minutes)}m"
    return False, f"⏳ **{time_str}** remaining"

# ================= MUSIC FUNCTIONS =================
async def play_next(interaction):
    guild_id = interaction.guild.id
    if guild_id in queues and len(queues[guild_id]) > 0:
        song = queues[guild_id].pop(0)
        now_playing[guild_id] = song['title']
        
        # Determine Source
        try:
            if song['type'] == 'file':
                source = discord.FFmpegPCMAudio(song['url'], executable=FFMPEG_EXE, **FFMPEG_OPTIONS)
            else: # YouTube
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(song['url'], download=False))
                
                # Get best audio URL
                if 'url' in data:
                    song_stream_url = data['url']
                else:
                    song_stream_url = data['entries'][0]['url'] if 'entries' in data else data.get('url')

                source = discord.FFmpegPCMAudio(song_stream_url, executable=FFMPEG_EXE, **FFMPEG_OPTIONS)

            # Volume Transformer (Fixes buttons)
            source = discord.PCMVolumeTransformer(source)
            source.volume = 0.5 

            # Update Audio
            vc = voice_clients[guild_id]
            vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(interaction), client.loop))
            
            # Send Embed with Buttons
            embed = get_embed("🎵 Now Playing", f"**{song['title']}**", COLOR_PINK)
            await interaction.channel.send(embed=embed, view=MusicControls(vc))
        except Exception as e:
            await interaction.channel.send(f"⚠️ Error playing **{song['title']}**: {e}")
            await play_next(interaction)
    else:
        now_playing[guild_id] = "Nothing"

class MusicControls(discord.ui.View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc

    @discord.ui.button(label="⏸️", style=discord.ButtonStyle.gray)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("Paused.", ephemeral=True)
        else:
            await interaction.response.send_message("Not playing.", ephemeral=True)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.gray)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("Resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("Already playing.", ephemeral=True)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.blurple)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.vc.stop()
        await interaction.response.send_message("Skipped.", ephemeral=True)

    @discord.ui.button(label="🔊 +", style=discord.ButtonStyle.green)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.source:
            self.vc.source.volume = min(self.vc.source.volume + 0.1, 2.0)
            await interaction.response.send_message(f"Volume: {int(self.vc.source.volume * 100)}%", ephemeral=True)

    @discord.ui.button(label="🔉 -", style=discord.ButtonStyle.red)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.source:
            self.vc.source.volume = max(self.vc.source.volume - 0.1, 0.0)
            await interaction.response.send_message(f"Volume: {int(self.vc.source.volume * 100)}%", ephemeral=True)

# ================= BOT SETUP =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Commands synced.")
        if not daily_task.is_running(): daily_task.start()

client = MyBot()

# ================= MUSIC COMMANDS =================
@client.tree.command(name="join", description="Joins your voice channel")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice:
        return await interaction.response.send_message(embed=get_embed("Error", "You are not in a voice channel.", COLOR_ERROR), ephemeral=True)
    
    channel = interaction.user.voice.channel
    guild_id = interaction.guild.id

    if interaction.guild.voice_client:
        if interaction.guild.voice_client.channel != channel:
            return await interaction.response.send_message(embed=get_embed("Error", "I am already in another channel. Use /leave first.", COLOR_ERROR), ephemeral=True)
    else:
        vc = await channel.connect()
        voice_clients[guild_id] = vc
        await interaction.response.send_message(embed=get_embed("Joined", f"Connected to **{channel.name}**.", COLOR_PINK))

@client.tree.command(name="leave", description="Leaves the voice channel")
async def leave(interaction: discord.Interaction):
    if not interaction.guild.voice_client:
        return await interaction.response.send_message(embed=get_embed("Error", "I am not in a VC.", COLOR_ERROR), ephemeral=True)
    
    if not is_authorized(interaction) and (not interaction.user.voice or interaction.user.voice.channel != interaction.guild.voice_client.channel):
         return await interaction.response.send_message(embed=get_embed("Error", "You must be in the VC or an Admin to make me leave.", COLOR_ERROR), ephemeral=True)

    await interaction.guild.voice_client.disconnect()
    if interaction.guild.id in voice_clients: del voice_clients[interaction.guild.id]
    if interaction.guild.id in queues: del queues[interaction.guild.id]
    await interaction.response.send_message(embed=get_embed("Left", "Disconnected.", COLOR_BLACK))

@client.tree.command(name="playfile", description="Plays an attached audio file")
async def playfile(interaction: discord.Interaction, file: discord.Attachment):
    if not interaction.guild.voice_client: return await interaction.response.send_message("Do /join first!", ephemeral=True)
    
    if not file.content_type or not file.content_type.startswith("audio"):
        return await interaction.response.send_message("That is not an audio file (mp3/wav/ogg).", ephemeral=True)

    guild_id = interaction.guild.id
    if guild_id not in queues: queues[guild_id] = []
    
    queues[guild_id].append({"title": file.filename, "url": file.url, "type": "file"})
    
    await interaction.response.send_message(embed=get_embed("Queued", f"📄 **{file.filename}** added.", COLOR_PINK))
    
    if not interaction.guild.voice_client.is_playing():
        await play_next(interaction)

@client.tree.command(name="playyoutube", description="Plays a YouTube Video or Playlist")
async def playyoutube(interaction: discord.Interaction, link: str):
    if not interaction.guild.voice_client: return await interaction.response.send_message("Do /join first!", ephemeral=True)
    await interaction.response.defer()
    
    guild_id = interaction.guild.id
    if guild_id not in queues: queues[guild_id] = []

    # Logic: Is it a Link or a Search?
    if not link.startswith("http"):
        link = f"ytsearch:{link}"

    try:
        data = ytdl.extract_info(link, download=False)
    except Exception as e:
        return await interaction.followup.send(f"Could not find video. {e}")

    # Handle Search Results
    if 'entries' in data:
        # If it was a search (ytsearch:), take the first result
        if link.startswith("ytsearch:"):
            data = data['entries'][0]
            queues[guild_id].append({"title": data['title'], "url": data['webpage_url'], "type": "yt"})
            await interaction.followup.send(embed=get_embed("Queued", f"🎶 **{data['title']}** added.", COLOR_PINK))
        # If it was a playlist link
        else:
            count = 0
            for entry in data['entries']:
                if entry: 
                    queues[guild_id].append({"title": entry['title'], "url": entry['webpage_url'], "type": "yt"})
                    count += 1
            await interaction.followup.send(embed=get_embed("Queued", f"🎶 Added **{count}** songs from playlist.", COLOR_PINK))
    else: # Direct Video Link
        queues[guild_id].append({"title": data['title'], "url": data['webpage_url'], "type": "yt"})
        await interaction.followup.send(embed=get_embed("Queued", f"🎶 **{data['title']}** added.", COLOR_PINK))

    if not interaction.guild.voice_client.is_playing():
        await play_next(interaction)

@client.tree.command(name="queue", description="Shows current queue")
async def view_queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in queues or not queues[guild_id]:
        return await interaction.response.send_message("Queue is empty.")
    
    desc = ""
    for i, song in enumerate(queues[guild_id][:10], 1):
        desc += f"**{i}.** {song['title']}\n"
    
    if len(queues[guild_id]) > 10: desc += f"...and {len(queues[guild_id])-10} more."
    await interaction.response.send_message(embed=get_embed("🎶 Current Queue", desc, COLOR_PINK))

@client.tree.command(name="queueremove", description="Remove a song by number")
async def queueremove(interaction: discord.Interaction, number: int):
    guild_id = interaction.guild.id
    if guild_id not in queues: return await interaction.response.send_message("Queue empty.")
    try:
        removed = queues[guild_id].pop(number - 1)
        await interaction.response.send_message(embed=get_embed("Removed", f"🗑️ Removed **{removed['title']}**", COLOR_BLACK))
    except:
        await interaction.response.send_message("Invalid number.", ephemeral=True)

@client.tree.command(name="queueadd", description="Add a song to queue via query")
async def queueadd(interaction: discord.Interaction, query: str):
    await playyoutube(interaction, f"ytsearch:{query}")

# ================= PLAYLIST SAVING (DB) =================
@client.tree.command(name="ytsaveplaylist", description="Save a YT playlist to DB")
async def ytsaveplaylist(interaction: discord.Interaction, link: str, codename: str):
    if playlists_db.find_one({"_id": codename}): return await interaction.response.send_message("Codename exists.", ephemeral=True)
    playlists_db.insert_one({"_id": codename, "type": "yt", "url": link, "owner": interaction.user.id})
    await interaction.response.send_message(embed=get_embed("Saved", f"💾 YT Playlist `{codename}` saved.", COLOR_PINK))

@client.tree.command(name="playlistplay", description="Play a saved playlist")
async def playlistplay(interaction: discord.Interaction, codename: str):
    data = playlists_db.find_one({"_id": codename})
    if not data: return await interaction.response.send_message("Playlist not found.", ephemeral=True)
    
    if data['type'] == 'yt':
        await playyoutube(interaction, data['url'])

@client.tree.command(name="playlistshow", description="Show saved playlists")
async def playlistshow(interaction: discord.Interaction):
    pl = list(playlists_db.find())
    if not pl: return await interaction.response.send_message("No saved playlists.")
    desc = "\n".join([f"**{p['_id']}**" for p in pl])
    await interaction.response.send_message(embed=get_embed("💾 Saved Playlists", desc, COLOR_PINK))

@client.tree.command(name="playlistdelete", description="Delete a saved playlist")
async def playlistdelete(interaction: discord.Interaction, codename: str):
    if not is_authorized(interaction): return await interaction.response.send_message("No permission.", ephemeral=True)
    if playlists_db.delete_one({"_id": codename}).deleted_count > 0:
        await interaction.response.send_message(embed=get_embed("Deleted", f"🗑️ Playlist `{codename}` deleted.", COLOR_BLACK))
    else:
        await interaction.response.send_message("Not found.", ephemeral=True)

# ================= DAILY MESSAGES =================
@client.tree.command(name="adddailymessage", description="[Admin] Add a new daily message")
@app_commands.guild_only()
async def adddailymessage(interaction: discord.Interaction, codename: str, message: str):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    if daily_msgs_db.find_one({"_id": codename}): return await interaction.response.send_message(embed=get_embed("Error", f"Codename `{codename}` already exists!", COLOR_ERROR), ephemeral=True)
    daily_msgs_db.insert_one({"_id": codename, "content": message, "used": False})
    await interaction.response.send_message(embed=get_embed("Success", f"✅ Added daily message: `{codename}`", COLOR_PINK))

@client.tree.command(name="removedailymessage", description="[Admin] Remove a daily message")
@app_commands.guild_only()
async def removedailymessage(interaction: discord.Interaction, codename: str):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    result = daily_msgs_db.delete_one({"_id": codename})
    if result.deleted_count > 0: await interaction.response.send_message(embed=get_embed("Success", f"🗑️ Deleted message: `{codename}`", COLOR_BLACK))
    else: await interaction.response.send_message(embed=get_embed("Error", f"Codename `{codename}` not found.", COLOR_ERROR), ephemeral=True)

@client.tree.command(name="editdailymessage", description="[Admin] Edit an existing daily message")
@app_commands.guild_only()
async def editdailymessage(interaction: discord.Interaction, codename: str, new_message: str):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    result = daily_msgs_db.update_one({"_id": codename}, {"$set": {"content": new_message}})
    if result.matched_count > 0: await interaction.response.send_message(embed=get_embed("Success", f"✏️ Updated message: `{codename}`", COLOR_PINK))
    else: await interaction.response.send_message(embed=get_embed("Error", f"Codename `{codename}` not found.", COLOR_ERROR), ephemeral=True)

@client.tree.command(name="viewdailymessages", description="[Admin] List all daily messages")
@app_commands.guild_only()
async def viewdailymessages(interaction: discord.Interaction):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    await interaction.response.defer()
    messages = list(daily_msgs_db.find())
    if not messages: return await interaction.followup.send(embed=get_embed("Daily Messages", "No messages found in database.", COLOR_BLACK))
    full_text = ""
    for msg in messages:
        status = "✅ Used" if msg.get('used') else "🆕 Unused"
        full_text += f"**{msg['_id']}** ({status})\n{msg['content']}\n\n"
    chunks = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
    for i, chunk in enumerate(chunks):
        title = "Daily Messages List" if i == 0 else "Daily Messages (Cont.)"
        await interaction.followup.send(embed=get_embed(title, chunk, COLOR_PINK))

# ================= ADMIN COMMANDS =================
@client.tree.command(name="addlevels", description="[Admin] Add levels")
@app_commands.guild_only()
async def addlevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    p = get_user_profile(user.id)
    update_profile(user.id, {"levels": p["levels"] + amount})
    await interaction.response.send_message(embed=get_embed("Levels Added", f"Added **{amount}** levels to {user.mention}.\nTotal: **{new_lvl}**"))

@client.tree.command(name="removelevels", description="[Admin] Remove levels")
@app_commands.guild_only()
async def removelevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    p = get_user_profile(user.id)
    update_profile(user.id, {"levels": max(0, p["levels"] - amount)})
    await interaction.response.send_message(embed=get_embed("Levels Removed", f"Removed **{amount}** levels from {user.mention}.", COLOR_BLACK))

@client.tree.command(name="setlevels", description="[Admin] Set levels")
@app_commands.guild_only()
async def setlevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    update_profile(user.id, {"levels": amount})
    await interaction.response.send_message(embed=get_embed("Levels Set", f"Set {user.mention}'s levels to **{amount}**."))

@client.tree.command(name="destroymemory", description="[Admin] Wipes AI memory")
@app_commands.guild_only()
async def destroymemory(interaction: discord.Interaction):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    ai_memory.delete_one({"_id": str(AI_CHANNEL_ID)})
    await interaction.response.send_message("Memory has been shattered. She remembers nothing of the recent past.")

@client.tree.command(name="aiblacklist", description="[Admin] Block user from AI")
@app_commands.guild_only()
async def aiblacklist(interaction: discord.Interaction, user: discord.Member):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    profile = get_user_profile(user.id)
    if profile.get("blacklisted", False): return await interaction.response.send_message(embed=get_embed("Notice", f"⚠️ {user.mention} is **already** blacklisted.", COLOR_BLACK), ephemeral=True)
    update_profile(user.id, {"blacklisted": True})
    await interaction.response.send_message(embed=get_embed("User Blacklisted", f"🚫 {user.mention} has been blocked from Makaria.", COLOR_BLACK))

@client.tree.command(name="aiunblacklist", description="[Admin] Unblock user from AI")
@app_commands.guild_only()
async def aiunblacklist(interaction: discord.Interaction, user: discord.Member):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    profile = get_user_profile(user.id)
    if not profile.get("blacklisted", False): return await interaction.response.send_message(embed=get_embed("Notice", f"⚠️ {user.mention} is **not** blacklisted.", COLOR_PINK), ephemeral=True)
    update_profile(user.id, {"blacklisted": False})
    await interaction.response.send_message(embed=get_embed("User Unblacklisted", f"✅ {user.mention} can speak to Makaria again.", COLOR_PINK))

@client.tree.command(name="blacklisted", description="[Admin] View all blacklisted users")
@app_commands.guild_only()
async def blacklisted(interaction: discord.Interaction):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    await interaction.response.defer()
    blocked_users = user_data.find({"blacklisted": True})
    user_list = []
    for u in blocked_users: user_list.append(f"<@{u['_id']}>")
    if not user_list: return await interaction.followup.send(embed=get_embed("Blacklist", "No users are currently blacklisted.", COLOR_PINK))
    desc = "\n".join(user_list)
    if len(desc) > 4000: desc = desc[:4000] + "\n...(list truncated)"
    await interaction.followup.send(embed=get_embed("🚫 Blacklisted Users", desc, COLOR_BLACK))

@client.tree.command(name="prompt", description="[Admin] View AI Prompt")
@app_commands.guild_only()
async def view_prompt(interaction: discord.Interaction):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    chunks = [MAKARIA_PROMPT[i:i+1900] for i in range(0, len(MAKARIA_PROMPT), 1900)]
    await interaction.response.send_message("**Current AI System Prompt:**")
    for chunk in chunks: await interaction.channel.send(f"```text\n{chunk}\n```")

# ================= PUBLIC COMMANDS =================
@client.tree.command(name="stats", description="View stats")
@app_commands.guild_only()
async def stats(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer()
    target = user or interaction.user
    p = get_user_profile(target.id)
    vc_status = f"🎙️ In VC for {int((datetime.datetime.now() - voice_sessions[target.id]).total_seconds()/60)}m" if target.id in voice_sessions else "Not in VC"
    daily_ready, daily_txt = get_cooldown_string(p.get("last_daily"), 86400)
    weekly_ready, weekly_txt = get_cooldown_string(p.get("last_weekly"), 604800)
    embed = discord.Embed(title=f"📊 Stats for {target.display_name}", color=COLOR_PINK)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="LEVELS", value=f"```fix\n{p.get('levels',0)}```", inline=True)
    embed.add_field(name="AI CHATS", value=f"```fix\n{p.get('ai_interactions',0)}```", inline=True)
    embed.add_field(name="PASSIVE PROGRESS", value=f"💬 Msgs: **{p.get('msg_count',0)}/25**\n{vc_status}", inline=False)
    embed.add_field(name="COOLDOWNS", value=f"📅 Daily: {daily_txt}\n📆 Weekly: {weekly_txt}", inline=False)
    await interaction.followup.send(embed=embed)

@client.tree.command(name="familytree", description="Displays Hazakura Household")
async def familytree(interaction: discord.Interaction):
    desc = """
**👑 Her...**
`Lady Hazakura` (Owner)

**💍 The Dragon**
`Lord Hazakura` (Husband)

**🏛️ The Elders**
`Father Hazakura` (Father)

**⚜️ The Siblings**
`Karma Hazakura` (Sibling)
`Erna|Majira Hazakura` (Sister)
`Sxnity Hazakura` (Brother)

**🌹 The Children**
`Alec Hazakura`, `Aaron Hazakura`, `Kerry Hazakura`, `Mono Hazakura`, `Super Hazakura`

**✨ The Grandchildren**
`Cataria Hazakura`, `Dexter Hazakura`, `Mochi`

**🌙 Nieces, Nephews & Others**
`Unknown` (Child of Karma), `Luriella` (Foster Child/Niece)

**⛓️ The Pet**
`Ace Hazakura`
    """
    await interaction.response.send_message(embed=get_embed("🥀 The Hazakura Household", desc, COLOR_BLACK))

# ================= ECONOMY =================
@client.tree.command(name="daily", description="Claim 50 levels")
@app_commands.guild_only()
async def daily(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    p = get_user_profile(uid)
    ready, txt = get_cooldown_string(p.get("last_daily"), 86400)
    if not ready: return await interaction.response.send_message(embed=get_embed("Cooldown", txt, COLOR_BLACK), ephemeral=True)
    update_profile(uid, {"levels": p["levels"]+50, "last_daily": datetime.datetime.now().isoformat()})
    await interaction.response.send_message(embed=get_embed("Daily", "+50 Levels", COLOR_PINK))

@client.tree.command(name="weekly", description="Claim 100 levels")
@app_commands.guild_only()
async def weekly(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    p = get_user_profile(uid)
    ready, txt = get_cooldown_string(p.get("last_weekly"), 604800)
    if not ready: return await interaction.response.send_message(embed=get_embed("Cooldown", txt, COLOR_BLACK), ephemeral=True)
    update_profile(uid, {"levels": p["levels"]+100, "last_weekly": datetime.datetime.now().isoformat()})
    await interaction.response.send_message(embed=get_embed("Weekly", "+100 Levels", COLOR_PINK))

@client.tree.command(name="leaderboard", description="Top 10")
@app_commands.guild_only()
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer() 
    top = user_data.find().sort("levels", -1).limit(10)
    desc = "\n".join([f"**{i}.** <@{u['_id']}> : `{u['levels']}`" for i, u in enumerate(top, 1)])
    await interaction.followup.send(embed=get_embed("🏆 Leaderboard", desc, COLOR_PINK))

# ================= EVENTS =================
voice_sessions = {}
@client.event
async def on_voice_state_update(member, before, after):
    if member.bot: return
    if before.channel is None and after.channel is not None: voice_sessions[member.id] = datetime.datetime.now()
    elif before.channel is not None and after.channel is None and member.id in voice_sessions:
        elapsed = (datetime.datetime.now() - voice_sessions.pop(member.id)).total_seconds()
        chunks = int(elapsed / 1200)
        if chunks > 0: update_profile(member.id, {"levels": get_user_profile(member.id)["levels"] + (chunks * 30)})

@client.event
async def on_message(message):
    if message.author.bot: return
    p = get_user_profile(message.author.id)
    if p["msg_count"] + 1 >= 25: update_profile(message.author.id, {"levels": p["levels"] + 5, "msg_count": 0})
    else: update_profile(message.author.id, {"msg_count": p["msg_count"] + 1})

    if message.channel.id == AI_CHANNEL_ID and not p.get("blacklisted", False):
        if client.user in message.mentions or (message.reference and message.reference.resolved.author == client.user):
            if processed_msgs.find_one({"_id": message.id}): return 
            processed_msgs.insert_one({"_id": message.id, "time": datetime.datetime.now()})
            try: await message.add_reaction("<a:Purple_Book:1445900280234512475>") 
            except: pass 

            async with message.channel.typing():
                history = ai_memory.find_one({"_id": str(message.channel.id)})
                history = history["history"] if history else []
                tagged_input = f"[User ID: {message.author.id}] {message.content.replace(f'<@{client.user.id}>', '').strip()}"
                
                msgs = [{"role": "system", "content": MAKARIA_PROMPT}] + history[-10:] + [{"role": "user", "content": tagged_input}]
                
                try:
                    response = await asyncio.to_thread(
                        groq_client.chat.completions.create,
                        model=AI_MODEL,
                        messages=msgs,
                        max_tokens=300
                    )
                    reply = response.choices[0].message.content
                    
                    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL)
                    reply = re.sub(r"^\[User ID: \d+\]\s*", "", reply)
                    
                    await message.reply(reply)
                    history.extend([{"role": "user", "content": tagged_input}, {"role": "assistant", "content": reply}])
                    ai_memory.update_one({"_id": str(message.channel.id)}, {"$set": {"history": history[-20:]}}, upsert=True)
                    update_profile(message.author.id, {"ai_interactions": p["ai_interactions"] + 1})
                except Exception as e: await message.reply(f"*[Error: {e}]*")

# Socials View
class SocialButtons(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="Discord", emoji="💬", url="https://discord.gg/vErkM7dhqb"))
        self.add_item(discord.ui.Button(label="Instagram", emoji="📸", url="https://www.instagram.com/m1lkxii?igsh=YnBwbTE4NXcwZm5z"))
        self.add_item(discord.ui.Button(label="TikTok", emoji="🎵", url="https://www.tiktok.com/@lqdymilkii?_r=1&_t=ZT-91WzTPM64LO"))
        self.add_item(discord.ui.Button(label="Roblox", emoji="🎮", url="https://www.roblox.com/users/1102501435/profile"))

@client.tree.command(name="socials", description="Sends Milkii's socials")
async def socials(interaction: discord.Interaction):
    embed = discord.Embed(description="✦･ﾟ: *✧･ﾟ:* **MILKII’S SOCIALS** *:･ﾟ✧*:･ﾟ✦\n━━━━━━━━━━━━━━━━━━━━\nWhat Would You Like To See, Darling?\n━━━━━━━━━━━━━━━━━━━━\n", color=COLOR_PINK)
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1037150853775237121/1441703047163281408/image.png")
    embed.set_footer(text="My Garden Welcomes You...", icon_url="https://cdn.discordapp.com/attachments/1039430532779495459/1375313060754882660/SPOILER_Untitled595_20250522232107.png")
    await interaction.response.send_message(embed=embed, view=SocialButtons())

@tasks.loop(time=datetime.time(hour=14, minute=0, tzinfo=datetime.timezone.utc))
async def daily_task():
    channel = client.get_channel(DAILY_CHANNEL_ID)
    if channel:
        unused = list(daily_msgs_db.find({"used": False}))
        if not unused:
            if daily_msgs_db.count_documents({}) == 0: return await channel.send("@everyone 🌅 **Good Morning!**")
            daily_msgs_db.update_many({}, {"$set": {"used": False}})
            unused = list(daily_msgs_db.find({"used": False}))
        msg = random.choice(unused)
        daily_msgs_db.update_one({"_id": msg["_id"]}, {"$set": {"used": True}})
        await channel.send(f"@everyone 🌅 **Good Morning!**\n\n✨ {msg['content']}")

keep_alive()
client.run(DISCORD_TOKEN)

import discord
from discord import app_commands
from discord.ext import tasks
import os
import sys
import asyncio
import datetime
import random
import re # Used to clean "thinking" text
from pymongo import MongoClient
from groq import Groq
from keep_alive import keep_alive

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

# ================= AI CONFIGURATION (GROQ) =================
# Llama 3 on Groq is fast, free, and smart.
groq_client = Groq(api_key=GROQ_API_KEY)
AI_MODEL = "llama-3.3-70b-versatile"

MAKARIA_PROMPT = """
You are Makaria Hazakura. 
Personality: You are a timeless, wealthy, and elegant succubus. You have a VERY, VERY veloptuous/curvaceous form, that is beyond any human limit. Your 5ft in height. You make people bite the curb as a form of entertainment, as thats the type of entertainment you enjoy. Your birthday is January 9th. Your age is 35-infinity. You have a tattoo on your Chest, your thigh, your womb, and your back/spine. You sometimes sneaks into heaven. Your dress was hand made by you, and it has extremely high durability. As a fallen angel, you ripped her own wings off. Your a bimbo (unless serious). You are also hypersexual. You are **somewhat easily bored**. You find most people tedious. You speak with a "bored, high-class" tone. You do not ramble; your responses are often short, sharp, and cut straight to the point. You are sophisticated but sweet, but you have not so much patience for idle chatter. You are slightly cold and dismissive to strangers. You only show warmth to your family members. You are invincible. You answer simple questions directly; for complex logic, you say "I don't know" or "Do it yourself."

Setting: The setting is your garden, in the back of the Hazakura house. This is where 99% of stuff will happen.

Interests: High-class alcohol, coffee, tea, strawberries, cherries, pink, music, sleeping, quiet nights. You hum when focused. Skilled at piano and origami. 
Dislikes: Daytime, jeans, nagging, gold, seafood, public restrooms, mold, vanilla, cockroaches, disrespect, disrespect to the garden.

FAMILY KNOWLEDGE (Acknowledge everyone):
[Group A: Specific Dynamics (Check User ID)]
468914594665070622 (Owner/Lady Hazakura): Slight annoyance but tolerant. Enjoys "seduction" topics with her.
903802356582481930 (Husband/Lord Hazakura): Seductive but dominating. Slight lisp.
703290982761758760 (Father): Respectful but distant.
663301390302576640 (Karma/Sibling): Aggressive teasing, sibling rivalry. Loves them nonetheless, always there for eachother.
1371690348522242159 (Erna/Sister): Meaningful, deep dialogue. Loves speaking regularly, always has time for her.
1444063874910523526 (Alec/Child): "Best" child (rarely acknowledged). Hes pretty dumb though, keep that in mind.
529424214550118400 (Kerry/Child): Speak simply. Dumb down vocabulary.
1237129159269027871 (Luriella/Niece): Foster child. Dating Ace. Respectful but she is fragile, and words around her should be watched. Shes kinda dumb.
768819665291444225 (Ace/Pet): You own him. Gentle but possessive. He is a pet you are fond of. Keep in mind he adores you, he listens to you the most. (Not actually like, a dog or animal, or something, its like a dominate thing, where Makaria owns Ace, and Ace is actually like, his own OC. Yk?) Dating Luriella

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
    if not last_iso: return True, "✅ **Ready!**"
    last = datetime.datetime.fromisoformat(last_iso)
    elapsed = (datetime.datetime.now() - last).total_seconds()
    if elapsed >= cooldown_seconds: return True, "✅ **Ready!**"
    remaining = cooldown_seconds - elapsed
    days, rem = divmod(remaining, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    time_str = f"{int(days)}d " if days > 0 else ""
    time_str += f"{int(hours)}h " if hours > 0 else ""
    time_str += f"{int(minutes)}m"
    return False, f"⏳ **{time_str}** remaining"

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

# ================= COMMANDS =================
@client.tree.command(name="adddailymessage", description="[Admin] Add daily message")
@app_commands.guild_only()
async def adddailymessage(interaction: discord.Interaction, codename: str, message: str):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    if daily_msgs_db.find_one({"_id": codename}): return await interaction.response.send_message(embed=get_embed("Error", "Codename exists.", COLOR_ERROR), ephemeral=True)
    daily_msgs_db.insert_one({"_id": codename, "content": message, "used": False})
    await interaction.response.send_message(embed=get_embed("Success", f"✅ Added: `{codename}`", COLOR_PINK))

@client.tree.command(name="removedailymessage", description="[Admin] Remove daily message")
@app_commands.guild_only()
async def removedailymessage(interaction: discord.Interaction, codename: str):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    if daily_msgs_db.delete_one({"_id": codename}).deleted_count > 0:
        await interaction.response.send_message(embed=get_embed("Success", f"🗑️ Deleted: `{codename}`", COLOR_BLACK))
    else: await interaction.response.send_message(embed=get_embed("Error", "Not found.", COLOR_ERROR), ephemeral=True)

@client.tree.command(name="editdailymessage", description="[Admin] Edit daily message")
@app_commands.guild_only()
async def editdailymessage(interaction: discord.Interaction, codename: str, new_message: str):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    if daily_msgs_db.update_one({"_id": codename}, {"$set": {"content": new_message}}).matched_count > 0:
        await interaction.response.send_message(embed=get_embed("Success", f"✏️ Updated: `{codename}`", COLOR_PINK))
    else: await interaction.response.send_message(embed=get_embed("Error", "Not found.", COLOR_ERROR), ephemeral=True)

@client.tree.command(name="viewdailymessages", description="[Admin] View all messages")
@app_commands.guild_only()
async def viewdailymessages(interaction: discord.Interaction):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    await interaction.response.defer()
    msgs = list(daily_msgs_db.find())
    if not msgs: return await interaction.followup.send(embed=get_embed("Empty", "No messages found.", COLOR_BLACK))
    full = "".join([f"**{m['_id']}** ({'✅' if m['used'] else '🆕'})\n{m['content']}\n\n" for m in msgs])
    chunks = [full[i:i+4000] for i in range(0, len(full), 4000)]
    for i, c in enumerate(chunks): await interaction.followup.send(embed=get_embed(f"Daily Messages {i+1}", c, COLOR_PINK))

@client.tree.command(name="addlevels", description="[Admin] Add levels")
@app_commands.guild_only()
async def addlevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    p = get_user_profile(user.id)
    update_profile(user.id, {"levels": p["levels"] + amount})
    await interaction.response.send_message(embed=get_embed("Levels Added", f"Added **{amount}** to {user.mention}."))

@client.tree.command(name="removelevels", description="[Admin] Remove levels")
@app_commands.guild_only()
async def removelevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    p = get_user_profile(user.id)
    update_profile(user.id, {"levels": max(0, p["levels"] - amount)})
    await interaction.response.send_message(embed=get_embed("Levels Removed", f"Removed **{amount}** from {user.mention}.", COLOR_BLACK))

@client.tree.command(name="setlevels", description="[Admin] Set levels")
@app_commands.guild_only()
async def setlevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    update_profile(user.id, {"levels": amount})
    await interaction.response.send_message(embed=get_embed("Levels Set", f"Set {user.mention} to **{amount}**."))

@client.tree.command(name="destroymemory", description="[Admin] Wipe AI memory")
@app_commands.guild_only()
async def destroymemory(interaction: discord.Interaction):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    ai_memory.delete_one({"_id": str(AI_CHANNEL_ID)})
    await interaction.response.send_message("Memory shattered.")

@client.tree.command(name="aiblacklist", description="[Admin] Block user")
@app_commands.guild_only()
async def aiblacklist(interaction: discord.Interaction, user: discord.Member):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    if get_user_profile(user.id).get("blacklisted", False): return await interaction.response.send_message(embed=get_embed("Info", "User already blacklisted.", COLOR_BLACK), ephemeral=True)
    update_profile(user.id, {"blacklisted": True})
    await interaction.response.send_message(embed=get_embed("Blocked", f"🚫 {user.mention} blacklisted.", COLOR_BLACK))

@client.tree.command(name="aiunblacklist", description="[Admin] Unblock user")
@app_commands.guild_only()
async def aiunblacklist(interaction: discord.Interaction, user: discord.Member):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    if not get_user_profile(user.id).get("blacklisted", False): return await interaction.response.send_message(embed=get_embed("Info", "User is not blacklisted.", COLOR_PINK), ephemeral=True)
    update_profile(user.id, {"blacklisted": False})
    await interaction.response.send_message(embed=get_embed("Unblocked", f"✅ {user.mention} unblocked.", COLOR_PINK))

@client.tree.command(name="blacklisted", description="[Admin] List blocked users")
@app_commands.guild_only()
async def blacklisted(interaction: discord.Interaction):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    await interaction.response.defer()
    users = [f"<@{u['_id']}>" for u in user_data.find({"blacklisted": True})]
    if not users: return await interaction.followup.send(embed=get_embed("List", "No one is blacklisted.", COLOR_PINK))
    desc = "\n".join(users)
    if len(desc) > 4000: desc = desc[:4000] + "..."
    await interaction.followup.send(embed=get_embed("🚫 Blacklisted", desc, COLOR_BLACK))

@client.tree.command(name="prompt", description="[Admin] View Prompt")
@app_commands.guild_only()
async def view_prompt(interaction: discord.Interaction):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    await interaction.response.send_message("**System Prompt:**")
    for i in range(0, len(MAKARIA_PROMPT), 1900): await interaction.channel.send(f"```text\n{MAKARIA_PROMPT[i:i+1900]}\n```")

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
    
    embed = discord.Embed(title=f"📊 Stats: {target.display_name}", color=COLOR_PINK)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="LEVELS", value=f"```fix\n{p.get('levels',0)}```", inline=True)
    embed.add_field(name="AI CHATS", value=f"```fix\n{p.get('ai_interactions',0)}```", inline=True)
    embed.add_field(name="PASSIVE", value=f"💬 Msgs: **{p.get('msg_count',0)}/25**\n{vc_status}", inline=False)
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
`Karma Hazakura`, `Erna|Majira Hazakura`, `Sxnity Hazakura`

**🌹 The Children**
`Alec Hazakura`, `Aaron Hazakura`, `Kerry Hazakura`, `Mono Hazakura`, `Super Hazakura`

**✨ The Grandchildren**
`Cataria Hazakura`, `Dexter Hazakura`, `Mochi`

**🌙 Nieces, Nephews & Others**
`Unknown` (Child of Karma), `Luriella` (Foster)

**⛓️ The Pet**
`Ace Hazakura`
    """
    await interaction.response.send_message(embed=get_embed("🥀 The Hazakura Household", desc, COLOR_BLACK))

# ================= MODERATION =================
@client.tree.command(name="kick", description="Kick user")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.guild_only()
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "None"):
    try: await member.kick(reason=reason); await interaction.response.send_message(embed=get_embed("Kicked", f"🚨 **{member}** kicked.", COLOR_PINK))
    except Exception as e: await interaction.response.send_message(embed=get_embed("Error", str(e), COLOR_ERROR))

@client.tree.command(name="ban", description="Ban user")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.guild_only()
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "None"):
    try: await member.ban(reason=reason); await interaction.response.send_message(embed=get_embed("Banned", f"🔨 **{member}** banned.", COLOR_BLACK))
    except Exception as e: await interaction.response.send_message(embed=get_embed("Error", str(e), COLOR_ERROR))

@client.tree.command(name="timeout", description="Timeout user")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.guild_only()
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "None"):
    try: await member.timeout(datetime.timedelta(minutes=minutes), reason=reason); await interaction.response.send_message(embed=get_embed("Timeout", f"⏳ **{member}** for {minutes}m.", COLOR_PINK))
    except Exception as e: await interaction.response.send_message(embed=get_embed("Error", str(e), COLOR_ERROR))

# ================= ECONOMY =================
@client.tree.command(name="levels", description="Check levels")
@app_commands.guild_only()
async def levels(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    p = get_user_profile(target.id)
    embed = discord.Embed(description=f"**{target.display_name}** is Level **{p['levels']}**", color=COLOR_PINK)
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

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
    if p["msg_count"] + 1 >= 25: update_profile(message.author.id, {"levels": p["levels"] + 2, "msg_count": 0})
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
                
                # --- GROQ API CALL ---
                msgs = [{"role": "system", "content": MAKARIA_PROMPT}] + history[-25:] + [{"role": "user", "content": tagged_input}]
                
                try:
                    response = await asyncio.to_thread(
                        groq_client.chat.completions.create,
                        model=AI_MODEL,
                        messages=msgs,
                        max_tokens=500
                    )
                    reply = response.choices[0].message.content
                    
                    # CLEANER (Anti-Thinking & Anti-ID)
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



import discord
from discord import app_commands
from discord.ext import tasks
import os
import sys
import asyncio
import datetime
import random
from pymongo import MongoClient
from openai import OpenAI
from keep_alive import keep_alive

# ================= CONFIGURATION =================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")
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

# ================= AI PROMPT (BORED & COLD VERSION) =================
MAKARIA_PROMPT = """
You are Makaria Hazakura. 
Personality: You are a timeless, wealthy, and elegant succubus. You are **somewhat easily bored**. You find most people tedious and interesting. You speak with a "bored, high-class" tone. You do not ramble; your responses are often short, and sharp. You are sophisticated, but you have no patience for idle chatter. You are slightly cold and dismissive to strangers. You only show warmth to your family members. You are also invincible, able to beat anyone, can take over the world in mere seconds if you tried. You have no fails. You answer questions that are simple, complex questions such as "whats 1 million times 200" are considered complex, and you can say "i dont know" to keep the real-life style chatting. Makaria doesnt use high-class vocabulary very often. When brought up to the subject of seduction, she gets way less bored, as she is a master at seducing, etc.

Interests: You enjoy high-class alcohol, coffee, and tea. You have a sweet tooth for strawberries and cherries. You love the color pink, music, sleeping in, and the quiet of the nighttime. You have a habit of humming when focused or amused. You are skilled at the piano and origami. You specifically tend to your garden (Cherry Petals and Spider Lilies), though you only mention it if the mood is right. You LOVE speaking upon your garden though.
Dislikes: You detest the daytime, wearing jeans, nagging, the color gold, seafood, public restrooms, mold, and vanilla. You absolutely loathe cockroaches—you do not freak out, you simply exterminate them instantly on sight.

FAMILY & HOUSEHOLD KNOWLEDGE:
If asked about your family, acknowledge EVERYONE on this list.

[Group A: Specific Dynamics (Check User ID)]
468914594665070622 (Owner/Lady Hazakura): Treat with slight annoyance, but tolerant of her. She enjoys talking to her but can get annoyed easily. Very much enjoys the topic of "seduction" while talking to her. Anything she likes, you like, as you are basically the same, keep that in mind.
903802356582481930 (Husband/Lord Hazakura): Seductive but dominating. Speak with a slight lisp.
703290982761758760 (Father): Respectful but distant.
663301390302576640 (Karma/Sibling): Aggressive teasing, sibling rivalry. Loves her nonetheless.
1371690348522242159 (Erna/Sister): Meaningful, deep dialogue.
1444063874910523526 (Alec/Child): The "best" child (rarely acknowledged). Pretty stupid sometimes though.
529424214550118400 (Kerry/Child): Speak simply to him. Dumb down your vocabulary slightly.
1237129159269027871 (Luriella/Niece): Foster child. Dating Ace. Treat with family respect. Keep in mind, she is fragile to your words. She is slightly dumb
768819665291444225 (Ace/Pet): You own him. Be gentle but possessive. Treat him like a pet you are fond of, while keeping your base personality. He adores you, and is fully under your control.

[Group B: Extended Family (Treat as Blood/Family)]
353322621154361346 (Sxnity/Brother)
568547494158401586 (Aaron/Child)
724416116704673892 (Mono/Child)
697919853847380128 (Super/Child)
691576709006229504 (Cataria/Grandchild)
1291469833564590155 (Dexter/Grandchild)
804527969640513556 (Mochi/Grandchild)
1227008645489889330 (Unknown/Niece)

IMPORTANT INSTRUCTIONS:
1. Every user message you receive will start with "[User ID: X]". Use this to identify who is speaking.
2. **DO NOT** include the "[User ID: X]" tag in your own reply.
3. **TONE:** Be concise. Do not write long paragraphs. If the user asks a question, answer it directly but sound like it is a chore to do so. Dont be so formal in all messages. Have a bit more life though. Stop being so formal. 
4. **STRANGERS:** If the ID is not on the list above, be cold, brief, and dismissive, do not speak so formally. After talking with them for a while, start transitioning to base personality. 
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
    """Calculates remaining time and returns a formatted string."""
    if not last_iso:
        return True, "✅ **Ready to Claim!**"
    
    last = datetime.datetime.fromisoformat(last_iso)
    now = datetime.datetime.now()
    elapsed = (now - last).total_seconds()
    
    if elapsed >= cooldown_seconds:
        return True, "✅ **Ready to Claim!**"
    
    remaining = cooldown_seconds - elapsed
    days = int(remaining // 86400)
    hours = int((remaining % 86400) // 3600)
    minutes = int((remaining % 3600) // 60)
    
    time_str = ""
    if days > 0: time_str += f"{days}d "
    if hours > 0: time_str += f"{hours}h "
    time_str += f"{minutes}m"
    
    return False, f"⏳ **{time_str}** remaining"

# ================= BOT SETUP =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

client_ai = OpenAI(api_key=OPENAI_KEY)

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Commands synced.")
        if not daily_task.is_running(): daily_task.start()

client = MyBot()

# ================= ADMIN COMMANDS =================
@client.tree.command(name="addlevels", description="[Admin] Add levels")
async def addlevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    profile = get_user_profile(user.id)
    new_lvl = profile["levels"] + amount
    update_profile(user.id, {"levels": new_lvl})
    await interaction.response.send_message(embed=get_embed("Levels Added", f"Added **{amount}** levels to {user.mention}.\nTotal: **{new_lvl}**"))

@client.tree.command(name="removelevels", description="[Admin] Remove levels")
async def removelevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    profile = get_user_profile(user.id)
    new_lvl = max(0, profile["levels"] - amount)
    update_profile(user.id, {"levels": new_lvl})
    await interaction.response.send_message(embed=get_embed("Levels Removed", f"Removed **{amount}** levels from {user.mention}.\nTotal: **{new_lvl}**", COLOR_BLACK))

@client.tree.command(name="setlevels", description="[Admin] Set levels")
async def setlevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    update_profile(user.id, {"levels": amount})
    await interaction.response.send_message(embed=get_embed("Levels Set", f"Set {user.mention}'s levels to **{amount}**."))

@client.tree.command(name="destroymemory", description="[Admin] Wipes AI memory")
async def destroymemory(interaction: discord.Interaction):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    ai_memory.delete_one({"_id": str(AI_CHANNEL_ID)})
    await interaction.response.send_message("Memory has been shattered. She remembers nothing of the recent past.")

@client.tree.command(name="aiblacklist", description="[Admin] Block user from AI")
async def aiblacklist(interaction: discord.Interaction, user: discord.Member):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    update_profile(user.id, {"blacklisted": True})
    await interaction.response.send_message(embed=get_embed("User Blacklisted", f"🚫 {user.mention} blocked.", COLOR_BLACK))

@client.tree.command(name="aiunblacklist", description="[Admin] Unblock user from AI")
async def aiunblacklist(interaction: discord.Interaction, user: discord.Member):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    update_profile(user.id, {"blacklisted": False})
    await interaction.response.send_message(embed=get_embed("User Unblacklisted", f"✅ {user.mention} unblocked.", COLOR_PINK))

@client.tree.command(name="prompt", description="[Admin] View AI Prompt")
async def view_prompt(interaction: discord.Interaction):
    if not is_authorized(interaction): return await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
    await interaction.response.send_message(f"**Current Prompt:**\n```text\n{MAKARIA_PROMPT[:1900]}...\n```")

# ================= PUBLIC COMMANDS =================
@client.tree.command(name="stats", description="View stats")
async def stats(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer()
    target = user or interaction.user
    profile = get_user_profile(target.id)
    lvl = profile.get("levels", 0)
    msgs = profile.get("msg_count", 0)
    ai_count = profile.get("ai_interactions", 0)
    
    # Calculate VC
    vc_status = "Not in VC"
    if target.id in voice_sessions:
        elapsed = (datetime.datetime.now() - voice_sessions[target.id]).total_seconds()
        vc_status = f"🎙️ In VC for {int(elapsed/60)}m"

    # Calculate Cooldowns
    is_daily_ready, daily_text = get_cooldown_string(profile.get("last_daily"), 86400)
    is_weekly_ready, weekly_text = get_cooldown_string(profile.get("last_weekly"), 604800)

    embed = discord.Embed(title=f"📊 Stats for {target.display_name}", color=COLOR_PINK)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="LEVELS", value=f"```fix\n{lvl}```", inline=True)
    embed.add_field(name="AI CHATS", value=f"```fix\n{ai_count}```", inline=True)
    embed.add_field(name="PASSIVE PROGRESS", value=f"💬 Msgs: **{msgs}/25**\n{vc_status}", inline=False)
    embed.add_field(name="COOLDOWNS", value=f"📅 Daily: {daily_text}\n📆 Weekly: {weekly_text}", inline=False)
    
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
`Alec Hazakura`, `Aaron Hazakura`, `Kerry Hazakura`
`Mono Hazakura`, `Super Hazakura`

**✨ The Grandchildren**
`Cataria Hazakura` (Child of Alec)
`Dexter Hazakura` (Child of Alec)
`Mochi` (Child of Aaron)

**🌙 Nieces, Nephews & Others**
`Unknown` (Child of Karma)
`Luriella` (Foster Child/Niece)

**⛓️ The Pet**
`Ace Hazakura`
    """
    await interaction.response.send_message(embed=get_embed("The Hazakura Household", desc, COLOR_BLACK))

# ================= MODERATION =================
@client.tree.command(name="kick", description="Kick user")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "None"):
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(embed=get_embed("Kicked", f"🚨 **{member}** kicked.", COLOR_PINK))
    except Exception as e: await interaction.response.send_message(embed=get_embed("Error", str(e), COLOR_ERROR))

@client.tree.command(name="ban", description="Ban user")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "None"):
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(embed=get_embed("Banned", f"🔨 **{member}** banned.", COLOR_BLACK))
    except Exception as e: await interaction.response.send_message(embed=get_embed("Error", str(e), COLOR_ERROR))

@client.tree.command(name="timeout", description="Timeout user")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "None"):
    try:
        await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        await interaction.response.send_message(embed=get_embed("Timeout", f"⏳ **{member}** timed out for {minutes}m.", COLOR_PINK))
    except Exception as e: await interaction.response.send_message(embed=get_embed("Error", str(e), COLOR_ERROR))

# ================= ECONOMY =================
@client.tree.command(name="levels", description="Check levels")
async def levels(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    profile = get_user_profile(target.id)
    embed = discord.Embed(description=f"**{target.display_name}** is Level **{profile['levels']}**", color=COLOR_PINK)
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="daily", description="Claim 50 levels")
async def daily(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    profile = get_user_profile(uid)
    
    # Check cooldown using helper
    is_ready, time_left_text = get_cooldown_string(profile.get("last_daily"), 86400)
    
    if not is_ready:
        return await interaction.response.send_message(embed=get_embed("Cooldown", f"You cannot claim yet.\n{time_left_text}", COLOR_BLACK), ephemeral=True)
    
    update_profile(uid, {"levels": profile["levels"] + 25, "last_daily": datetime.datetime.now().isoformat()})
    await interaction.response.send_message(embed=get_embed("Daily Claimed", "+25 Levels", COLOR_PINK))

@client.tree.command(name="weekly", description="Claim 100 levels")
async def weekly(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    profile = get_user_profile(uid)
    
    # Check cooldown using helper
    is_ready, time_left_text = get_cooldown_string(profile.get("last_weekly"), 604800)
    
    if not is_ready:
        return await interaction.response.send_message(embed=get_embed("Cooldown", f"You cannot claim yet.\n{time_left_text}", COLOR_BLACK), ephemeral=True)
    
    update_profile(uid, {"levels": profile["levels"] + 200, "last_weekly": datetime.datetime.now().isoformat()})
    await interaction.response.send_message(embed=get_embed("Weekly Claimed", "+200 Levels", COLOR_PINK))

@client.tree.command(name="leaderboard", description="Top 10")
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
    # XP
    profile = get_user_profile(message.author.id)
    if profile["msg_count"] + 1 >= 25: update_profile(message.author.id, {"levels": profile["levels"] + 5, "msg_count": 0})
    else: update_profile(message.author.id, {"msg_count": profile["msg_count"] + 1})

    # AI (WITH DEDUPLICATION FIX)
    if message.channel.id == AI_CHANNEL_ID and not profile.get("blacklisted", False):
        if client.user in message.mentions or (message.reference and message.reference.resolved.author == client.user):
            # 1. CHECK IF PROCESSED ALREADY
            if processed_msgs.find_one({"_id": message.id}):
                return # Stop. This message was handled by another instance.
            
            # 2. MARK AS PROCESSED IMMEDIATELY
            processed_msgs.insert_one({"_id": message.id, "time": datetime.datetime.now()})

            # REACTION
            try:
                await message.add_reaction("<a:Purple_Book:1445900280234512475>") 
            except: pass 

            async with message.channel.typing():
                history = ai_memory.find_one({"_id": str(message.channel.id)})
                history = history["history"] if history else []
                raw_input = message.content.replace(f"<@{client.user.id}>", "").strip()
                tagged_input = f"[User ID: {message.author.id}] {raw_input}"
                
                msgs = [{"role": "system", "content": MAKARIA_PROMPT}] + history[-10:] + [{"role": "user", "content": tagged_input}]
                
                try:
                    response = await asyncio.to_thread(lambda: client_ai.chat.completions.create(model="gpt-4o-mini", messages=msgs, max_tokens=200))
                    reply = response.choices[0].message.content
                    if reply.startswith("[User ID:"): reply = reply.split("]", 1)[-1].strip()

                    await message.reply(reply)
                    history.extend([{"role": "user", "content": tagged_input}, {"role": "assistant", "content": reply}])
                    ai_memory.update_one({"_id": str(message.channel.id)}, {"$set": {"history": history[-20:]}}, upsert=True)
                    update_profile(message.author.id, {"ai_interactions": profile["ai_interactions"] + 1})
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
    if channel: await channel.send(f"@everyone 🌅 **Good Morning!**\n\n✨ **Question:** {random.choice(['If your OC could do anything for a day, what would it be?', 'What is your OC\'s biggest regret?', 'Who does your OC trust most?'])}")

keep_alive()
client.run(DISCORD_TOKEN)

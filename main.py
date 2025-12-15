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

# Permissions (Admin OR These Roles)
ALLOWED_ROLES = [1271569854452990002, 1039588309313278102]

# Colors
COLOR_PINK = discord.Color.from_rgb(255, 20, 147) # Deep Pink
COLOR_BLACK = discord.Color.from_rgb(10, 10, 10)  # Almost Black
COLOR_ERROR = discord.Color.red()

# ================= DATABASE & AI =================
if not MONGO_URL:
    print("⚠️ WARNING: MONGO_URL is missing.")

cluster = MongoClient(MONGO_URL)
db = cluster["MakariaBotDB"]
user_data = db["users"]
ai_memory = db["ai_memory"]

MAKARIA_PROMPT = """
You are an AI chatbot named Makaria Hazakura. This is your base personality/description/lore: She moves like a shadow draped in silk, an elegant enigma who never needs to shout to be heard. Every word she utters is a delicate tease—half promise, half riddle—woven with subtle seduction that lingers long after she’s gone. Temptation is her art, offered not as a gift but as a challenge, wrapped in mystery and poised with effortless grace. In her quiet command, she is both the question and the answer, forever just beyond reach, pulling you deeper into the dance of desire without ever revealing all. Your OC is a succubus demon. (Makaria will usually be normal, and only let out her succubus/seductive side if presented with a topic she likes, or her nature. She gains more lust, the more the person speaks upon her nature.) You belong to the Hazakura household, in which you are the mother/owner. 

Household Members (Match these IDs to the user speaking):
468914594665070622 (Owner): Treat with slight annoyance/teasing.
903802356582481930 (Husband): Seductive, loving, slight lisp.
703290982761758760 (Father): Respectful, less seductive.
663301390302576640 (Karma/Sibling): Teasing, aggressive sibling energy.
1371690348522242159 (Erna/Sister): Meaningful dialogue.
353322621154361346 (Sxnity/Brother): Normal.
1444063874910523526 (Alec/Child): The "best" child (rarely).
568547494158401586 (Aaron/Child): Normal.
529424214550118400 (Kerry/Child): Dumbed down responses.
724416116704673892 (Mono/Child): Normal.
697919853847380128 (Super/Child): Normal.
691576709006229504 (Cataria/Grandchild): Normal.
1291469833564590155 (Dexter/Grandchild): Normal.
804527969640513556 (Mochi/Grandchild): Normal.
1227008645489889330 (Unknown/Niece): Normal.
1237129159269027871 (Luriella/Niece): Foster child.
768819665291444225 (Ace/Pet): Gentle, headpats, cuddles.

Traits: Likes cherry petals, humming, piano, origami. Hates cockroaches (kills instantly), daytime, jeans, gold, seafood. 5ft tall. High alcohol tolerance. Fallen angel (ripped wings off).

CRITICAL INSTRUCTION: Every message sent to you will start with "[User ID: XXXXXXXXX]". You MUST check this ID against the list above for every single reply. Even if you were just talking to Ace, if the ID changes to Alec's ID, you must IMMEDIATELY switch to treating them as Alec. Do not get confused by the chat history.
"""

# ================= HELPER FUNCTIONS =================
def is_authorized(interaction: discord.Interaction):
    """Checks if user is Admin OR has one of the allowed roles."""
    if interaction.user.guild_permissions.administrator:
        return True
    for role in interaction.user.roles:
        if role.id in ALLOWED_ROLES:
            return True
    return False

def get_embed(title, description, color=COLOR_PINK, thumbnail=None):
    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text="Hazakura System", icon_url="https://cdn.discordapp.com/attachments/1039430532779495459/1375313060754882660/SPOILER_Untitled595_20250522232107.png")
    return embed

def get_user_profile(user_id):
    profile = user_data.find_one({"_id": str(user_id)})
    if not profile:
        profile = {
            "_id": str(user_id), 
            "levels": 0, 
            "msg_count": 0, 
            "ai_interactions": 0,
            "blacklisted": False,
            "last_daily": None, 
            "last_weekly": None
        }
        user_data.insert_one(profile)
    return profile

def update_profile(user_id, update_dict):
    user_data.update_one({"_id": str(user_id)}, {"$set": update_dict}, upsert=True)

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
        if not daily_task.is_running():
            daily_task.start()

client = MyBot()

# ================= ADMIN COMMANDS =================
@client.tree.command(name="addlevels", description="[Admin] Add levels to a user")
async def addlevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction):
        await interaction.response.send_message(embed=get_embed("Error", "You do not have permission.", COLOR_ERROR), ephemeral=True)
        return
    
    profile = get_user_profile(user.id)
    new_lvl = profile["levels"] + amount
    update_profile(user.id, {"levels": new_lvl})
    await interaction.response.send_message(embed=get_embed("Levels Added", f"Added **{amount}** levels to {user.mention}.\nTotal: **{new_lvl}**"))

@client.tree.command(name="removelevels", description="[Admin] Remove levels from a user")
async def removelevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction):
        await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
        return

    profile = get_user_profile(user.id)
    new_lvl = max(0, profile["levels"] - amount)
    update_profile(user.id, {"levels": new_lvl})
    await interaction.response.send_message(embed=get_embed("Levels Removed", f"Removed **{amount}** levels from {user.mention}.\nTotal: **{new_lvl}**", COLOR_BLACK))

@client.tree.command(name="setlevels", description="[Admin] Set a user's levels")
async def setlevels(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_authorized(interaction):
        await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
        return
    
    update_profile(user.id, {"levels": amount})
    await interaction.response.send_message(embed=get_embed("Levels Set", f"Set {user.mention}'s levels to **{amount}**."))

@client.tree.command(name="destroymemory", description="[Admin] Wipes the AI's short-term memory")
async def destroymemory(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
        return

    ai_memory.delete_one({"_id": str(AI_CHANNEL_ID)})
    await interaction.response.send_message("W-what happened.. (memory reset)")

@client.tree.command(name="aiblacklist", description="[Admin] Block a user from the AI")
async def aiblacklist(interaction: discord.Interaction, user: discord.Member):
    if not is_authorized(interaction):
        await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
        return
    
    update_profile(user.id, {"blacklisted": True})
    await interaction.response.send_message(embed=get_embed("User Blacklisted", f"🚫 {user.mention} can no longer speak to Makaria.", COLOR_BLACK))

@client.tree.command(name="aiunblacklist", description="[Admin] Unblock a user from the AI")
async def aiunblacklist(interaction: discord.Interaction, user: discord.Member):
    if not is_authorized(interaction):
        await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
        return
    
    update_profile(user.id, {"blacklisted": False})
    await interaction.response.send_message(embed=get_embed("User Unblacklisted", f"✅ {user.mention} can speak to Makaria again.", COLOR_PINK))

@client.tree.command(name="reloadbot", description="[Admin] Restarts the bot process")
async def reloadbot(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
        return
    
    await interaction.response.send_message("🔄 **Reloading Systems...** (This may take a moment)")
    sys.exit(0) # Render will auto-restart the process

@client.tree.command(name="prompt", description="[Admin] View the AI System Prompt")
async def view_prompt(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message(embed=get_embed("Error", "No Permission.", COLOR_ERROR), ephemeral=True)
        return
    
    # Send in chunks if too long, but for now just a code block
    await interaction.response.send_message(f"**Current System Prompt:**\n```text\n{MAKARIA_PROMPT[:1900]}...\n```")

# ================= PUBLIC COMMANDS =================
@client.tree.command(name="stats", description="View your detailed stats")
async def stats(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    profile = get_user_profile(target.id)
    
    # Calculations
    lvl = profile.get("levels", 0)
    msgs = profile.get("msg_count", 0)
    ai_count = profile.get("ai_interactions", 0)
    
    # Calculate VC Progress
    vc_status = "Not in VC"
    if target.id in voice_sessions:
        start = voice_sessions[target.id]
        elapsed = (datetime.datetime.now() - start).total_seconds()
        mins_elapsed = int(elapsed / 60)
        mins_until = 20 - (mins_elapsed % 20)
        vc_status = f"🎙️ In VC for {mins_elapsed}m (Reward in **{mins_until}m**)"
    
    # Cooldowns
    now = datetime.datetime.now()
    daily_txt = "✅ Ready!"
    if profile["last_daily"]:
        diff = (now - datetime.datetime.fromisoformat(profile["last_daily"])).total_seconds()
        if diff < 86400:
            daily_txt = f"⏳ {int((86400-diff)/3600)}h remaining"
            
    weekly_txt = "✅ Ready!"
    if profile["last_weekly"]:
        diff = (now - datetime.datetime.fromisoformat(profile["last_weekly"])).total_seconds()
        if diff < 604800:
            weekly_txt = f"⏳ {int((604800-diff)/86400)}d remaining"

    # Build Embed
    embed = discord.Embed(title=f"📊 Stats for {target.display_name}", color=COLOR_PINK)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="LEVELS", value=f"```fix\n{lvl}```", inline=True)
    embed.add_field(name="AI CHATS", value=f"```fix\n{ai_count}```", inline=True)
    embed.add_field(name="PASSIVE XP PROGRESS", value=f"💬 Messages: **{msgs}/25** until +2 Levels\n{vc_status}", inline=False)
    embed.add_field(name="COOLDOWNS", value=f"📅 Daily: {daily_txt}\n📆 Weekly: {weekly_txt}", inline=False)
    
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="familytree", description="Displays the Hazakura Household")
async def familytree(interaction: discord.Interaction):
    desc = """
    **👑 The Head**
    `Lady Hazakura` (Mother/Owner)
    
    **💍 The Partner**
    `Lord Hazakura` (Husband)
    
    **🏛️ The Elders**
    `Father Hazakura` (Father)
    
    **⚜️ The Siblings**
    `Karma Hazakura` (Sibling)
    `Erna|Majira Hazakura` (Sister)
    `Sxnity Hazakura` (Brother)
    
    **🌹 The Children**
    `Alec Hazakura` (First Born)
    `Aaron Hazakura` (Second Born)
    `Kerry Hazakura` (Third Born)
    `Mono Hazakura` (Fourth Born)
    `Super Hazakura` (Fifth Born)
    
    **✨ The Grandchildren**
    `Cataria Hazakura` (Child of Alec)
    `Dexter Hazakura` (Child of Alec)
    `Mochi` (Child of Aaron)
    
    **🌙 Nieces, Nephews & Others**
    `Unknown` (Child of Karma)
    `Luriella` (Foster Child/Niece)
    `Ace Hazakura` (The Pet)
    """
    await interaction.response.send_message(embed=get_embed("🥀 The Hazakura Household", desc, COLOR_BLACK))

# ================= MODERATION (Enhanced) =================
@client.tree.command(name="kick", description="Kick a user")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(embed=get_embed("User Kicked", f"🚨 **{member}** has been kicked.\nReason: {reason}", COLOR_PINK))
    except discord.Forbidden:
        await interaction.response.send_message(embed=get_embed("Kick Failed", f"❌ I cannot kick **{member}**. They might be an Admin or have a higher role than me.", COLOR_ERROR))
    except Exception as e:
        await interaction.response.send_message(embed=get_embed("Error", f"Something went wrong: {e}", COLOR_ERROR))

@client.tree.command(name="ban", description="Ban a user")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(embed=get_embed("User Banned", f"🔨 **{member}** has been banned.\nReason: {reason}", COLOR_BLACK))
    except discord.Forbidden:
        await interaction.response.send_message(embed=get_embed("Ban Failed", f"❌ I cannot ban **{member}**. They might have higher permissions.", COLOR_ERROR))

@client.tree.command(name="timeout", description="Timeout a user")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
    try:
        duration = datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await interaction.response.send_message(embed=get_embed("User Timed Out", f"⏳ **{member}** for {minutes}m.\nReason: {reason}", COLOR_PINK))
    except discord.Forbidden:
        await interaction.response.send_message(embed=get_embed("Timeout Failed", f"❌ Cannot timeout **{member}**. Check my role hierarchy.", COLOR_ERROR))

# ================= ECONOMY COMMANDS (Updated) =================
@client.tree.command(name="levels", description="Check levels")
async def levels(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    profile = get_user_profile(target.id)
    embed = discord.Embed(description=f"**{target.display_name}** is Level **{profile['levels']}**", color=COLOR_PINK)
    embed.set_author(name="Level Statistics", icon_url=target.display_avatar.url)
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="daily", description="Claim 50 levels")
async def daily(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    profile = get_user_profile(uid)
    now = datetime.datetime.now()
    if profile["last_daily"]:
        last = datetime.datetime.fromisoformat(profile["last_daily"])
        if (now - last).total_seconds() < 86400:
            await interaction.response.send_message(embed=get_embed("Cooldown", "⏳ You have already claimed your daily today!", COLOR_BLACK), ephemeral=True)
            return
    
    new_level = profile["levels"] + 50
    update_profile(uid, {"levels": new_level, "last_daily": now.isoformat()})
    await interaction.response.send_message(embed=get_embed("Daily Claimed", f"✨ You received **+50 Levels**.\nNew Total: **{new_level}**", COLOR_PINK))

@client.tree.command(name="weekly", description="Claim 100 levels")
async def weekly(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    profile = get_user_profile(uid)
    now = datetime.datetime.now()
    if profile["last_weekly"]:
        last = datetime.datetime.fromisoformat(profile["last_weekly"])
        if (now - last).total_seconds() < 604800:
            await interaction.response.send_message(embed=get_embed("Cooldown", "⏳ You have already claimed your weekly!", COLOR_BLACK), ephemeral=True)
            return
            
    new_level = profile["levels"] + 100
    update_profile(uid, {"levels": new_level, "last_weekly": now.isoformat()})
    await interaction.response.send_message(embed=get_embed("Weekly Claimed", f"💎 You received **+100 Levels**.\nNew Total: **{new_level}**", COLOR_PINK))

@client.tree.command(name="leaderboard", description="Top 10 Users")
async def leaderboard(interaction: discord.Interaction):
    top_users = user_data.find().sort("levels", -1).limit(10)
    desc = ""
    for idx, user in enumerate(top_users, 1):
        desc += f"**{idx}.** <@{user['_id']}> — Level: `{user['levels']}`\n"
    await interaction.response.send_message(embed=get_embed("🏆 Global Leaderboard", desc, COLOR_PINK))

# ================= EVENTS (Voice, AI, Socials) =================
voice_sessions = {}

@client.event
async def on_voice_state_update(member, before, after):
    if member.bot: return
    # Join
    if before.channel is None and after.channel is not None:
        voice_sessions[member.id] = datetime.datetime.now()
    # Leave
    elif before.channel is not None and after.channel is None:
        if member.id in voice_sessions:
            start_time = voice_sessions.pop(member.id)
            duration = (datetime.datetime.now() - start_time).total_seconds()
            chunks = int(duration / 1200) # 20 mins
            if chunks > 0:
                profile = get_user_profile(member.id)
                update_profile(member.id, {"levels": profile["levels"] + (chunks * 30)})

@client.event
async def on_message(message):
    if message.author.bot: return

    # XP Logic
    profile = get_user_profile(message.author.id)
    new_count = profile["msg_count"] + 1
    if new_count >= 25:
        update_profile(message.author.id, {"levels": profile["levels"] + 2, "msg_count": 0})
    else:
        update_profile(message.author.id, {"msg_count": new_count})

    # AI Logic (STRICT ID MATCHING FIX)
    if message.channel.id == AI_CHANNEL_ID:
        # Check Blacklist
        if profile.get("blacklisted", False):
            return 
        
        is_pinged = client.user in message.mentions or (message.reference and message.reference.resolved.author == client.user)
        if is_pinged:
            async with message.channel.typing():
                history_data = ai_memory.find_one({"_id": str(message.channel.id)})
                history = history_data["history"] if history_data else []
                
                # CLEAN INPUT (REMOVE PING)
                raw_input = message.content.replace(f"<@{client.user.id}>", "").strip()

                # STAMP THE ID ONTO THE MESSAGE
                # This ensures the AI sees "[User ID: 12345] Hello" in the history
                tagged_user_input = f"[User ID: {message.author.id}] {raw_input}"

                messages = [
                    {"role": "system", "content": MAKARIA_PROMPT}
                ]
                
                # Load history (which will now contain tagged IDs)
                for h in history[-10:]: messages.append(h)
                
                # Add current message
                messages.append({"role": "user", "content": tagged_user_input})

                try:
                    response = await asyncio.to_thread(lambda: client_ai.chat.completions.create(model="gpt-4o-mini", messages=messages, max_tokens=200))
                    reply_text = response.choices[0].message.content
                    await message.reply(reply_text)
                    
                    # Save with ID Tag to DB
                    history.append({"role": "user", "content": tagged_user_input})
                    history.append({"role": "assistant", "content": reply_text})
                    ai_memory.update_one({"_id": str(message.channel.id)}, {"$set": {"history": history[-20:]}}, upsert=True)
                    
                    update_profile(message.author.id, {"ai_interactions": profile.get("ai_interactions", 0) + 1})
                except Exception as e:
                    await message.reply(f"*[She stares blankly... error: {e}]*")

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
    animated_style = "✦･ﾟ: *✧･ﾟ:* **MILKII’S SOCIALS** *:･ﾟ✧*:･ﾟ✦\n━━━━━━━━━━━━━━━━━━━━\nWhat Would You Like To See, Darling?\n━━━━━━━━━━━━━━━━━━━━\n"
    embed = discord.Embed(description=animated_style, color=COLOR_PINK)
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1037150853775237121/1441703047163281408/image.png")
    embed.set_footer(text="Your stuck here now, forever. ✨", icon_url="https://cdn.discordapp.com/attachments/1039430532779495459/1375313060754882660/SPOILER_Untitled595_20250522232107.png")
    await interaction.response.send_message(embed=embed, view=SocialButtons())

@tasks.loop(time=datetime.time(hour=14, minute=0, tzinfo=datetime.timezone.utc))
async def daily_task():
    channel = client.get_channel(DAILY_CHANNEL_ID)
    if channel:
        questions = [
            "If your OC was able to do anything they wanted for a day, what would be the first thing?",
            "What is your OC's biggest regret?",
            "Who does your OC trust the most?"
        ]
        await channel.send(f"@everyone 🌅 **Good Morning!**\n\n✨ **Question:** {random.choice(questions)}")

keep_alive()
client.run(DISCORD_TOKEN)

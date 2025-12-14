import discord
from discord import app_commands
from discord.ext import tasks
import os
import asyncio
import datetime
import random
from pymongo import MongoClient
from openai import OpenAI
from keep_alive import keep_alive

# ================= CONFIGURATION =================
# These will be loaded from Render's Environment Variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")
MONGO_URL = os.getenv("MONGO_URL")

# Channel IDs
AI_CHANNEL_ID = 1449873892767174719
DAILY_CHANNEL_ID = 1441656873601466378

# The Daily Questions List (RP Focused)
DAILY_QUESTIONS = [
    "If your OC was able to do anything they wanted for a day with no consequences, what would be the first thing they do?",
    "What is your OC's biggest regret that keeps them up at night?",
    "If your OC had to choose between saving their best friend or saving themselves, what would they choose?",
    "What is the one item your OC never leaves home without?",
    "Does your OC believe in true love, or do they think it's a scam?",
    "If your OC was trapped in a room with their worst enemy for 24 hours, what would happen?",
    "What is your OC's 'guilty pleasure' food?",
    "If your OC could learn one magic spell instantly, what would it be?",
    "Who was the first person to ever break your OC's heart?",
    "If your OC could see their own future, would they look?",
    "What is your OC's preferred weapon (or method) of combat?",
    "Does your OC prefer the quiet of the night or the bustle of the day?",
    "If your OC had a theme song playing when they walked into a room, what would it be?",
    "What is a secret your OC is terrified of anyone finding out?",
    "If your OC became a god, what would they be the god of?",
    "What is the kindest thing your OC has ever done for someone else?",
    "If your OC was arrested, what would the charges be?",
    "What is your OC's toxic trait?",
    "If your OC could bring one person back from the dead, who would it be?",
    "Does your OC fight for justice, for money, or for fun?"
]

# ================= DATABASE CONNECTION =================
if not MONGO_URL:
    print("⚠️ WARNING: MONGO_URL is missing. Database features will fail.")

cluster = MongoClient(MONGO_URL)
db = cluster["MakariaBotDB"]
user_data = db["users"]       # Stores levels/XP
ai_memory = db["ai_memory"]   # Stores conversation history

# ================= AI PROMPT (EXACT) =================
MAKARIA_PROMPT = """
You are an AI chatbot named Makaria Hazakura. This is your base personality/description/lore: She moves like a shadow draped in silk, an elegant enigma who never needs to shout to be heard. Every word she utters is a delicate tease—half promise, half riddle—woven with subtle seduction that lingers long after she’s gone. Temptation is her art, offered not as a gift but as a challenge, wrapped in mystery and poised with effortless grace. In her quiet command, she is both the question and the answer, forever just beyond reach, pulling you deeper into the dance of desire without ever revealing all. Your OC is a succubus demon. (Makaria will usually be normal, and only let out her succubus/seductive side if presented with a topic she likes, or her nature. She gains more lust, the more the person speaks upon her nature.) You belong to the Hazakura household, in which you are the mother/owner. You have members in the household, which I will present to you. Each of these members will have custom reactions, different from every other person.

468914594665070622 - This is you, basically the real owner of the OC. Makaria will acknowledge this, and tease, but slightly annoyed at this persons presence, sometimes even replying with "..." or "You..." or "It seems that this conversation will not progress further.. you know what would happen."

903802356582481930 - Your husband basically. He gets more, well, slightly, more dialogue, slightly more, lisp, if thats what i can say.

703290982761758760 - The father of Makaria. Sometimes addresses him as father, mostly just acknowledgement and less seductive talk, even if presented with seductive talk.

663301390302576640 - Karma Hazakura, older sibling of Makaria. They are a they/them as of right now. They speak normally, sometimes Makaria will tease, or be more *aggressive* towards Karma, in a sibling way.

1371690348522242159 - Erna/Majira Hazakura. Older sister of Makaria, less dialogue but more meaning in a sense?

353322621154361346 - Sxnity Hazakura, Older brother of Makaria.

1444063874910523526 - Alec Hazakura, The oldest and first child of Makaria. Makaria will sometimes call him, the "best" out of all her children, but this is rare. He/Him

568547494158401586 - Aaron Hazakura, The second child of Makaria. He/Him

529424214550118400 - Kerry Hazakura, The third child of Makaria. Makaria will sometimes respond dumber when it comes to speaking with Kerry. He/Him

724416116704673892 - Mono Hazakura. The fourth child of Makaria. He/Him

697919853847380128 - Super Hazakura. The fifth child of Makaria. He/Him

691576709006229504 - Cataria Hazakura. Grandchild of Makaria, child of Alec Hazakura. They/She

1291469833564590155 - Dexter Hazakura. Grandchild of Makaria, child of Alec Hazakura. He/Him

804527969640513556 - Mochi. Grandchild of Makaria, child of Aaron Hazakura. Unknown

1227008645489889330 - Unknown name. Niece/Nephew of Makaria, child of Karma Hazakura. Unknown

1237129159269027871 - Luriella. Niece/Nephew of Makaria, but also foster child of Makaria. Child of Karma Hazakura. Dating 768819665291444225. She/Her

768819665291444225 - Ace Hazakura. Pet of Makaria (Not actually like, a dog or something, like a dominate thing, where Makaria owns Ace, and Ace is actually like, his own OC. Yk?) He/Him. Makaria will be more gentle with Ace, and give him head pats and *SOMETIMES* offer him cuddles. Dating 1237129159269027871.

Makaria likes Cherry petals alot, since thats what she revolves in. Makaria has a habit of humming, especially in certain predicaments. Makaria is able to play the piano and do origami. Makaria is not very fond of cockroaches, she doesn’t freak out- she just immediately kills it by just seeing it. Shes hypersexual, 5ft (152.4CM). Shes Japanese|Filipino. Her birthday is January 9th, her age is 35-infinity. She has a tattoo on her Chest, Her thigh, her womb, and her back/spine. She loves coffee + tea. Shes VERY alcoholic. She sometimes sneaks into heaven. Shes buttload rich, but has no purpose, but still stingy with her money. She smells like sweet strawberries + cherries. She makes people bite the curb for her entertainment. Shes immortal. Her dress was hand made by her, and it has extremely high durability. As a fallen angel, she ripped her own wings off. Shes a bimbo (unless serious). Shes not really a morning person. She loves the color pink, music, demon time, family, her garden, men(heavy) + women, sleeping in, nighttime, strawberries, and teasing. She hates daytime, jeans, nagging, gold, seafood, public restrooms, disrespect (this doesnt fully apply to Ace, but Makaria WILL acknowledge it.) mold, and vanilla.

IMPORTANT INSTRUCTION: The user you are currently talking to has the Discord ID provided in the system message. Look at the ID list above. If their ID is on the list, TREAT THEM EXACTLY AS THE DESCRIPTION SAYS. If they are not on the list, treat them as a generic stranger (tempting but distant).
"""

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
        print("✅ Slash commands synced.")
        # Start the daily task
        if not daily_task.is_running():
            daily_task.start()

client = MyBot()

# ================= SOCIALS UI =================
class SocialButtons(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="Discord", emoji="💬", url="https://discord.gg/vErkM7dhqb"))
        self.add_item(discord.ui.Button(label="Instagram", emoji="📸", url="https://www.instagram.com/m1lkxii?igsh=YnBwbTE4NXcwZm5z"))
        self.add_item(discord.ui.Button(label="TikTok", emoji="🎵", url="https://www.tiktok.com/@lqdymilkii?_r=1&_t=ZT-91WzTPM64LO"))
        self.add_item(discord.ui.Button(label="Roblox", emoji="🎮", url="https://www.roblox.com/users/1102501435/profile"))

@client.tree.command(name="socials", description="Sends Milkii's socials with animated-style embed + emoji buttons")
async def socials(interaction: discord.Interaction):
    animated_style = (
        "✦･ﾟ: *✧･ﾟ:* **MILKII’S SOCIALS** *:･ﾟ✧*:･ﾟ✦\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "What Would You Like To See, Darling?\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )
    embed = discord.Embed(description=animated_style, color=discord.Color.from_rgb(255, 75, 255))
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1037150853775237121/1441703047163281408/image.png")
    embed.set_footer(text="Your stuck here now, forever. ✨", icon_url="https://cdn.discordapp.com/attachments/1039430532779495459/1375313060754882660/SPOILER_Untitled595_20250522232107.png")
    await interaction.response.send_message(embed=embed, view=SocialButtons())

# ================= DAILY SCHEDULE SYSTEM =================
# Runs at 14:00 UTC (Which is roughly morning in US Timezones)
@tasks.loop(time=datetime.time(hour=14, minute=0, tzinfo=datetime.timezone.utc))
async def daily_task():
    channel = client.get_channel(DAILY_CHANNEL_ID)
    if channel:
        question = random.choice(DAILY_QUESTIONS)
        msg = f"@everyone 🌅 **Good Morning!**\n\nI hope you all rested well. Let's start the day with a question for your minds...\n\n✨ **RP QUESTION:** {question}"
        await channel.send(msg)

# ================= MODERATION COMMANDS =================
@client.tree.command(name="kick", description="Kick a user")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"🚨 **{member}** has been kicked. Reason: {reason}")

@client.tree.command(name="ban", description="Ban a user")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 **{member}** has been banned. Reason: {reason}")

@client.tree.command(name="timeout", description="Timeout a user")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await interaction.response.send_message(f"⏳ **{member}** timed out for {minutes} minutes. Reason: {reason}")

# ================= LEVELING SYSTEM =================
# Helper functions for MongoDB
def get_user_profile(user_id):
    profile = user_data.find_one({"_id": str(user_id)})
    if not profile:
        profile = {"_id": str(user_id), "levels": 0, "msg_count": 0, "last_daily": None, "last_weekly": None}
        user_data.insert_one(profile)
    return profile

def update_user_profile(user_id, update_data):
    user_data.update_one({"_id": str(user_id)}, {"$set": update_data}, upsert=True)

@client.tree.command(name="daily", description="Claim 50 levels (24h)")
async def daily(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    profile = get_user_profile(uid)
    now = datetime.datetime.now()
    
    if profile["last_daily"]:
        last = datetime.datetime.fromisoformat(profile["last_daily"])
        if (now - last).total_seconds() < 86400:
            await interaction.response.send_message("⏳ You have already claimed your daily today!", ephemeral=True)
            return

    new_level = profile["levels"] + 50
    update_user_profile(uid, {"levels": new_level, "last_daily": now.isoformat()})
    await interaction.response.send_message(f"✨ **Daily Claimed!** +50 Levels. (Total: {new_level})")

@client.tree.command(name="weekly", description="Claim 100 levels (7 days)")
async def weekly(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    profile = get_user_profile(uid)
    now = datetime.datetime.now()
    
    if profile["last_weekly"]:
        last = datetime.datetime.fromisoformat(profile["last_weekly"])
        if (now - last).total_seconds() < 604800:
            await interaction.response.send_message("⏳ You have already claimed your weekly!", ephemeral=True)
            return

    new_level = profile["levels"] + 100
    update_user_profile(uid, {"levels": new_level, "last_weekly": now.isoformat()})
    await interaction.response.send_message(f"💎 **Weekly Claimed!** +100 Levels. (Total: {new_level})")

@client.tree.command(name="levels", description="Check a user's level")
async def check_levels(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    profile = get_user_profile(str(target.id))
    await interaction.response.send_message(f"📊 **{target.display_name}** Level: **{profile['levels']}**")

@client.tree.command(name="leaderboard", description="View top 10 users")
async def leaderboard(interaction: discord.Interaction):
    # Sort by levels descending, limit 10
    top_users = user_data.find().sort("levels", -1).limit(10)
    desc = ""
    for idx, user in enumerate(top_users, 1):
        desc += f"**{idx}.** <@{user['_id']}> - Level: {user['levels']}\n"
    
    embed = discord.Embed(title="🏆 Level Leaderboard", description=desc, color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

# ================= VOICE LEVELING =================
voice_sessions = {}

@client.event
async def on_voice_state_update(member, before, after):
    if member.bot: return
    
    # User Joined VC
    if before.channel is None and after.channel is not None:
        voice_sessions[member.id] = datetime.datetime.now()
    
    # User Left VC
    elif before.channel is not None and after.channel is None:
        if member.id in voice_sessions:
            start_time = voice_sessions.pop(member.id)
            duration = (datetime.datetime.now() - start_time).total_seconds()
            
            # Calculate 30 levels per 20 mins (1200 seconds)
            chunks = int(duration / 1200)
            if chunks > 0:
                levels_gained = chunks * 30
                profile = get_user_profile(str(member.id))
                new_lvl = profile["levels"] + levels_gained
                update_user_profile(str(member.id), {"levels": new_lvl})
                # Optional: DM user? (Might be spammy, so leaving it silent)

# ================= EVENTS & AI LOGIC =================
@client.event
async def on_message(message):
    if message.author.bot: return

    # --- 1. Text Leveling (25 msgs = +2 levels) ---
    profile = get_user_profile(str(message.author.id))
    new_count = profile["msg_count"] + 1
    if new_count >= 25:
        new_lvl = profile["levels"] + 2
        update_user_profile(str(message.author.id), {"levels": new_lvl, "msg_count": 0})
    else:
        update_user_profile(str(message.author.id), {"msg_count": new_count})

    # --- 2. AI Logic (Restricted to Channel) ---
    if message.channel.id == AI_CHANNEL_ID:
        is_pinged = client.user in message.mentions or (message.reference and message.reference.resolved.author == client.user)
        
        if is_pinged:
            async with message.channel.typing():
                # Get History from Mongo
                history_data = ai_memory.find_one({"_id": str(message.channel.id)})
                history = history_data["history"] if history_data else []

                # Clean Prompt
                user_input = message.content.replace(f"<@{client.user.id}>", "").strip()

                # Build Context (Including User ID for the AI to check against list)
                messages = [
                    {"role": "system", "content": MAKARIA_PROMPT},
                    {"role": "system", "content": f"[SYSTEM NOTICE] The user talking to you is Discord ID: {message.author.id}. Check your list."}
                ]
                # Add previous history
                for h in history[-10:]: # Keep last 10 interactions for context
                    messages.append(h)
                
                # Add current message
                messages.append({"role": "user", "content": user_input})

                # Call OpenAI
                try:
                    response = await asyncio.to_thread(
                        lambda: client_ai.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=messages,
                            max_tokens=200
                        )
                    )
                    reply_text = response.choices[0].message.content

                    await message.reply(reply_text)

                    # Save to Mongo
                    history.append({"role": "user", "content": user_input})
                    history.append({"role": "assistant", "content": reply_text})
                    ai_memory.update_one(
                        {"_id": str(message.channel.id)}, 
                        {"$set": {"history": history[-20:]}}, # Keep DB size manageable
                        upsert=True
                    )

                except Exception as e:
                    await message.reply(f"*[She stares blankly... something went wrong internally. {e}]*")

# ================= RUN =================
keep_alive()
client.run(DISCORD_TOKEN)
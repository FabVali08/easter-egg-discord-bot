import json
import discord
import asyncio
import random
import os
from datetime import datetime, timedelta
from discord.ext import tasks, commands
from config import settings

SERVER_ID = 1216806587554070698
CHANNEL_IDS = [
    1216858968165453994,
    1216859161703350443,
    1216859108825890866,
    1216859224655532082,
    1216860239291224236,
    1216866105021300847,
    1217022857696116776,
    1216865964667179168
]
TIME_WINDOW = (9, 23)
EVENT_START = datetime(2025, 4, 17)
EVENT_END = datetime(2025, 4, 21)
MIN_INTERVAL = 10 * 60
MAX_INTERVAL = 15 * 60

USERS_FILE = "db/users.json"
MESSAGES_FILE = "db/messages.json"


def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def load_messages():
    try:
        with open(MESSAGES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_messages(messages):
    os.makedirs(os.path.dirname(MESSAGES_FILE), exist_ok=True)
    with open(MESSAGES_FILE, "w") as f:
        json.dump(messages, f)


class EggButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Einsammeln", style=discord.ButtonStyle.green, custom_id="egg_button", emoji="<:Purple_bunny:1356352268521312397>")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        message_id = interaction.message.id
        user_id = interaction.user.id
        current_time = datetime.now().timestamp()
        
        messages = load_messages()
        users = load_users()
        
        if str(message_id) not in messages:
            await interaction.followup.send("Das EI ist spurlos verschwunden!? Halte deine Augen nach neuen Eiern offen! <:egg_easter:1356352219527643176>", ephemeral=True)
            return
        
        msg_data = messages[str(message_id)]
        created_at = datetime.fromtimestamp(msg_data["created_at"])
        
        if datetime.now() - created_at > timedelta(minutes=10):
            await interaction.followup.send("Das EI ist spurlos verschwunden!? Halte deine Augen nach neuen Eiern offen! <:egg_easter:1356352219527643176>", ephemeral=True)
            return
        
        if str(user_id) in msg_data["users"]:
            await interaction.followup.send("Der Osterhase hat leider kein zweites Ei dagelassen. <:bunny_cute:1356352247469965464>", ephemeral=True)
            return
        
        msg_data["users"].append(str(user_id))
        users[str(user_id)] = users.get(str(user_id), 0) + 1
        
        save_messages(messages)
        save_users(users)
        
        await interaction.followup.send(f"Du hast ein EI gefunden! <:Purple_bunny:1356352268521312397> \n Insgesamt hast du jetzt {users[str(user_id)]} Eier <:bunny_holding_hearts:1356352234723606890>", ephemeral=True)

class EggBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(intents=intents, help_command=None, command_prefix='lu!')
        self.add_command(commands.Command(self.test_egg_command, name="test_egg"))
        self.add_command(commands.Command(self.test_ranking_command, name="test_ranking"))
        self.event_ended = False

    async def setup_hook(self):
        self.add_view(discord.ui.View(timeout=None).add_item(EggButton()))
        asyncio.create_task(self.schedule_event_end())

    async def on_ready(self):
        print(f"Eingeloggt als {self.user} (ID: {self.user.id})")
        guild = self.get_guild(SERVER_ID)
        if guild:
            print(f"Server: {guild.name}")
        else:
            print(f"Bot ist nicht auf Server mit ID {SERVER_ID}")
        
        await self.reschedule_deletions()
        
        if datetime.now() > EVENT_END and not self.event_ended:
            await self.announce_winners()
            self.event_ended = True
        elif not self.event_ended:
            self.egg_loop.start()

    async def schedule_event_end(self):
        now = datetime.now()
        if now > EVENT_END:
            return
        time_until_end = (EVENT_END - now).total_seconds()
        
        await asyncio.sleep(time_until_end)
        
        if not self.event_ended:
            await self.announce_winners()
            self.event_ended = True
            self.egg_loop.stop() 

    async def reschedule_deletions(self):
        messages = load_messages()
        for msg_id, data in list(messages.items()):
            channel = self.get_channel(int(data["channel_id"]))
            if not channel:
                continue
            
            created_at = datetime.fromtimestamp(data["created_at"])
            delete_in = (created_at + timedelta(minutes=10) - datetime.now()).total_seconds()
            
            if delete_in > 0:
                asyncio.create_task(self.delete_message(int(msg_id), channel, delete_in))
            else:
                await self.delete_message(int(msg_id), channel)

    async def delete_message(self, msg_id, channel, delay=0):
        try:
            await asyncio.sleep(delay)
            msg = await channel.fetch_message(msg_id)
            await msg.delete()
        except:
            pass
        finally:
            messages = load_messages()
            if str(msg_id) in messages:
                del messages[str(msg_id)]
                save_messages(messages)

    @tasks.loop(seconds=5)
    async def egg_loop(self):
        if not self.check_time_window():
            return
        
        wait_time = random.randint(int(MIN_INTERVAL), int(MAX_INTERVAL))
        await asyncio.sleep(wait_time)
        
        if self.check_time_window() and not self.event_ended:
            await self.send_egg_message()

    async def send_egg_message(self):
        channel = self.get_channel(random.choice(CHANNEL_IDS))
        view = discord.ui.View(timeout=None)
        view.add_item(EggButton())
        
        msg = await channel.send("Du hast ein EI von Osterhasen gefunden! \nSammle es jetzt ein! <:Purple_bunny:1356352268521312397>", view=view)
        
        messages = load_messages()
        messages[str(msg.id)] = {
            "channel_id": channel.id,
            "created_at": datetime.now().timestamp(),
            "users": []
        }
        save_messages(messages)
        
        asyncio.create_task(self.delete_message(msg.id, channel, 60))

    def check_time_window(self):
        now = datetime.now()
        if now < EVENT_START:
            return False
        if now > EVENT_END:  
            return False
        return TIME_WINDOW[0] <= now.hour < TIME_WINDOW[1]

    async def announce_winners(self, ctx=None):
        users = load_users()
        messages = load_messages()
        LUU = self.get_user(808039255329865741)
        await LUU.send(f"```{users}```")
        await LUU.send(f"```{messages}```")
        if not users:
            if ctx:
                await ctx.send("⚠️ Keine User-Daten gefunden!", delete_after=10)
            return
        
        sorted_users = sorted(users.items(), key=lambda x: x[1], reverse=True)[:3]
        announce_channel = None
        if ctx:
            announce_channel = ctx.channel
        else:
            announce_channel = self.get_channel(1356637314549420074)
        
        if not announce_channel:
            print("Fehler: Ankündigungskanal nicht gefunden!")
            if ctx:
                await ctx.send("⚠️ Fehler: Ankündigungskanal nicht gefunden!", delete_after=10)
            return
        main_embed = discord.Embed(
            description="# <:bunny_cute:1356352247469965464> Ostereier Event\n"
                        "> Ihr habt fleißig die letzten Eier gesammelt, doch leider hat das Suchen für dieses Jahr ein Ende! Hier sind die besten Eier-Sammler dieses Jahr <:egg_easter:1356352219527643176>",
            color=0x008640
        )
        main_embed.set_footer(text=f"Event beendet am {EVENT_END.strftime('%d.%m.%Y')} x Liebe Grüße vom ganzen Team!")

        message = await announce_channel.send(embed=main_embed)
        
        embeds = [main_embed]
        winner_messages = {
            1: "hat unglaubliche {eggs} Eier gesammelt! Der Osterhase wird dich ganz besonders in Erinnerungen behalten. <:Purple_bunny:1356352268521312397>",
            2: "hat {eggs} Eier gesammelt! <:Purple_bunny:1356352268521312397> Bei den Eiersammlern bist du ganz oben mit dabei",
            3: "hat {eggs} Eier gefunden! Du kannst super stolz auf dich sein! <:Purple_bunny:1356352268521312397>"
        }
        
        for i, (user_id, egg_count) in enumerate(sorted_users, 1):
            try:
                user = await self.fetch_user(int(user_id))
                embed = discord.Embed(
                    description=f"## <:bunny_holding_hearts:1356352234723606890> Platz {i} - {user.mention}\n"
                                f"{user.mention} {winner_messages[i].format(eggs=egg_count)}",
                    color=0x008640
                )
                embed.set_thumbnail(url=user.display_avatar.url)
                embeds.append(embed)
            except:
                continue
        
        await message.edit(embeds=embeds)
        save_users({})
        save_messages({})

    async def test_egg_command(self, ctx): 
        view = discord.ui.View(timeout=None)
        view.add_item(EggButton())
        test_msg = await ctx.send("Du hast ein EI von Osterhasen gefunden! \nSammle es jetzt ein! <:Purple_bunny:1356352268521312397>", view=view)
        await ctx.send("⚠️ Test Durchlauf (Wird in der Finalen Version nicht angezeigt)", delete_after=10)

    async def test_ranking_command(self, ctx):
        test_users = {
            str(ctx.author.id): 50, 
            "456": 45,
            "789": 40,
            "101": 35,
            "112": 30
        }
        
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        
        original_users = {}
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                original_users = json.load(f)
        
        try:
            with open(USERS_FILE, "w") as f:
                json.dump(test_users, f)
            
            await self.announce_winners(ctx)
            await ctx.send("⚠️ Test-Ranking wurde gesendet!", delete_after=10)
        except Exception as e:
            await ctx.send(f"⚠️ Fehler: {str(e)}", delete_after=10)
        finally:
            with open(USERS_FILE, "w") as f:
                json.dump(original_users, f)

bot = EggBot()
bot.run(settings.TOKEN)
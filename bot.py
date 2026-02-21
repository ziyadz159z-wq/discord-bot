import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import os
import datetime
from flask import Flask
from threading import Thread

# ================= Flask (Keep Alive) =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run_flask).start()

# ================= Discord Bot =================
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= IDs =================
PANEL_CHANNEL_ID = 1425206713992220797
LOG_CHANNEL_ID = 1473464868731486242

CATEGORIES = [
    1471643772764028928,
    1471643552764264508,
    1472621021193310268,
    1471643668417876235,
    1472619726029983754,
    1472620920630673430
]

ROLES = [
    1472593214467739839,
    1472591401458995302,
    1472593013023834183,
    1472606257503539331,
    1472591503594618900,
    1472591554529984634
]

TICKET_TYPES = [
    ("طـلـب مـنـتـج", 1472593661597581322),
    ("طـلـب مـسـاعـدة", 1472593665737359452),
    ("تـواصـل مـع الادارة", 1472593634850246798),
    ("تـقـديـم بـائـع", 1472593571184906240),
    ("طـلـب مـسـتـحـقـات", 1472593639195807947),
    ("بـلاغ ضـد مـخـرب", 1472593717104873604),
]

ticket_counter = {}

# ================= Helper =================
def now():
    return datetime.datetime.now(datetime.UTC)

# ================= Ticket Options =================
class TicketSelect(Select):
    def __init__(self):
        options = []
        for i, t in enumerate(TICKET_TYPES):
            options.append(
                discord.SelectOption(
                    label=t[0],
                    value=str(i),
                    emoji=discord.PartialEmoji(name="x", id=t[1])
                )
            )
        super().__init__(
            placeholder="اختر نوع التذكرة",
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        idx = int(self.values[0])

        # منع فتح أكثر من تذكرة
        for ch in guild.text_channels:
            if ch.topic == f"ticket-{user.id}":
                await interaction.response.send_message(
                    "❌ لديك تذكرة مفتوحة بالفعل.",
                    ephemeral=True
                )
                return

        category = guild.get_channel(CATEGORIES[idx])
        role = guild.get_role(ROLES[idx])

        ticket_counter.setdefault(idx, 0)
        ticket_counter[idx] += 1

        channel = await guild.create_text_channel(
            name=f"{TICKET_TYPES[idx][0]}-{ticket_counter[idx]}",
            category=category,
            topic=f"ticket-{user.id}",
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
        )

        embed = discord.Embed(
            title="🎫 تم فتح تذكرة",
            description=(
                f"مرحبًا {user.mention}\n\n"
                f"📂 القسم: **{TICKET_TYPES[idx][0]}**\n"
                f"🕒 الوقت: {now().strftime('%Y-%m-%d %H:%M')}\n"
                f"🆔 رقم التذكرة: `{ticket_counter[idx]}`\n\n"
                "سيتم الرد عليك من قبل المسؤولين."
            ),
            color=0x2f3136
        )

        await channel.send(
            content=f"{user.mention} | {role.mention}",
            embed=embed,
            view=TicketManageView(role.id),
            silent=True
        )

        await interaction.response.send_message(
            f"✅ تم فتح تذكرتك: {channel.mention}",
            ephemeral=True
        )

# ================= Views =================
class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(
            label="فتح تذكرة جديدة",
            style=discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji(name="ticket", id=1472593621524938867),
            custom_id="open_ticket",
            callback=self.open_ticket
        ))

    async def open_ticket(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "اختر نوع التذكرة:",
            view=TicketOptionsView(),
            ephemeral=True
        )

class TicketOptionsView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

class TicketManageView(View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

        self.add_item(Button(
            label="استلام التذكرة",
            style=discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji(name="ticket", id=1472593621524938867),
            custom_id="claim_ticket",
            callback=self.claim
        ))

    async def claim(self, interaction: discord.Interaction):
        if self.role_id not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message("❌ ليس لديك صلاحية.", ephemeral=True)
            return

        await interaction.channel.send(
            f"✅ تم استلام التذكرة من قبل {interaction.user.mention}",
            silent=True
        )
        await interaction.response.defer()

# ================= Events =================
@bot.event
async def on_ready():
    bot.add_view(TicketPanelView())
    print("✅ Bot ready")

# ================= Command =================
@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title=f"{ctx.guild.name} | نظام التذاكر",
        description=(
            "📜 قوانين فتح التذكرة:\n"
            "- تذكرة واحدة فقط\n"
            "- احترام الإدارة\n\n"
            f"🗓️ السنة: {now().year}"
        ),
        color=0x2f3136
    )
    await ctx.send(embed=embed, view=TicketPanelView())

# ================= Run =================
keep_alive()
bot.run(TOKEN)

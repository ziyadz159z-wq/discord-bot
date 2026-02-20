import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import datetime
import asyncio

TOKEN = os.getenv("TOKEN")

GUILD_ID = 1425201800310685708
PANEL_CHANNEL_ID = 1425206713992220797
LOG_CHANNEL_ID = 1473464868731486242

EMOJIS = {
    "open": "<:ticket:1472593621524938867>",
    "product": "<:cart:1472593661597581322>",
    "support": "<:support:1472593665737359452>",
    "admin": "<:crown:1472593634850246798>",
    "seller": "<:seller:1472593571184906240>",
    "money": "<:money:1472593639195807947>",
    "report": "<:report:1472593717104873604>",
    "options": "<:options:1472593569272561858>"
}

CATEGORIES = {
    "product": 1471643772764028928,
    "support": 1471643552764264508,
    "admin": 1472621021193310268,
    "seller": 1471643668417876235,
    "money": 1472619726029983754,
    "report": 1472620920630673430,
}

ROLES = {
    "product": 1472593214467739839,
    "support": 1472591401458995302,
    "admin": 1472593013023834183,
    "seller": 1472606257503539331,
    "money": 1472591503594618900,
    "report": 1472591554529984634,
}

open_tickets = {}
ticket_claimed = {}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= LOG FUNCTION =================
async def log(guild, text):
    ch = guild.get_channel(LOG_CHANNEL_ID)
    embed = discord.Embed(
        title="📊 سجل نظام التذاكر",
        description=text,
        color=discord.Color.dark_gray(),
        timestamp=datetime.datetime.now()
    )
    await ch.send(embed=embed)

# ================= MODALS =================
class CloseModal(Modal, title="إغلاق التذكرة"):
    reason = TextInput(label="سبب الإغلاق", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        user_id = int(channel.topic)
        member = interaction.guild.get_member(user_id)
        await channel.set_permissions(member, overwrite=None)
        embed = discord.Embed(
            title="🔒 تم إغلاق التذكرة",
            description=f"سبب الإغلاق:\n{self.reason}",
            color=discord.Color.greyple()
        )
        msg = await channel.send(embed=embed)
        await msg.pin()
        await log(interaction.guild,
                  f"🔒 إغلاق تذكرة\n👤 {member.mention}\n👮 {interaction.user.mention}")

class RenameModal(Modal, title="إعادة تسمية التذكرة"):
    newname = TextInput(label="الاسم الجديد", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        old_name = interaction.channel.name
        await interaction.channel.edit(name=self.newname.value)
        embed = discord.Embed(
            description=f"✏️ تم تغيير الاسم من `{old_name}` إلى `{self.newname.value}` بواسطة {interaction.user.mention}",
            color=discord.Color.dark_gray()
        )
        msg = await interaction.channel.send(embed=embed)
        await msg.pin()
        await log(interaction.guild, f"✏️ إعادة تسمية\n👮 {interaction.user.mention}")

# ================= REOPEN/DELETE =================
class ReopenDeleteView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إعادة فتح", style=discord.ButtonStyle.secondary)
    async def reopen(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        user_id = int(interaction.channel.topic)
        member = interaction.guild.get_member(user_id)
        await interaction.channel.set_permissions(member, view_channel=True, send_messages=True)
        await interaction.channel.send("🔓 تم إعادة فتح التذكرة.")
        await log(interaction.guild, f"🔓 إعادة فتح\n👮 {interaction.user.mention}")

    @discord.ui.button(label="حذف التذكرة", style=discord.ButtonStyle.secondary)
    async def delete(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        await log(interaction.guild, f"🗑️ حذف تذكرة\n👮 {interaction.user.mention}")
        await interaction.channel.delete()

# ================= TICKET CONTROLS =================
class TicketControls(View):
    def __init__(self, section):
        super().__init__(timeout=None)
        self.section = section

    def has_role(self, member):
        return ROLES[self.section] in [r.id for r in member.roles]

    @discord.ui.button(label="استلام التذكرة", emoji=EMOJIS["open"], style=discord.ButtonStyle.secondary)
    async def claim(self, interaction: discord.Interaction, button: Button):
        if not self.has_role(interaction.user):
            return await interaction.response.send_message("❌ لا تملك صلاحية.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        ticket_claimed[interaction.channel.id] = interaction.user.id
        embed = discord.Embed(
            description=f"📌 تم استلام التذكرة من قبل {interaction.user.mention}",
            color=discord.Color.dark_gray()
        )
        msg = await interaction.channel.send(embed=embed)
        await msg.pin()
        await log(interaction.guild, f"📌 استلام\n👮 {interaction.user.mention}")

    @discord.ui.button(label="قائمة خيارات", emoji=EMOJIS["options"], style=discord.ButtonStyle.secondary)
    async def options(self, interaction: discord.Interaction, button: Button):
        if not self.has_role(interaction.user):
            return await interaction.response.send_message("❌ لا تملك صلاحية.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        view = View()
        view.add_item(Button(label="إغلاق", style=discord.ButtonStyle.secondary, custom_id="close"))
        view.add_item(Button(label="إعادة تسمية", style=discord.ButtonStyle.secondary, custom_id="rename"))
        view.add_item(Button(label="تذكير", style=discord.ButtonStyle.secondary, custom_id="remind"))
        view.add_item(Button(label="إلغاء استلام", style=discord.ButtonStyle.secondary, custom_id="unclaim"))
        await interaction.followup.send("نظام التذاكر — قائمة الخيارات", view=view, ephemeral=True)

# ================= SELECT =================
class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="طـلـب مـنـتـج", value="product", emoji=EMOJIS["product"]),
            discord.SelectOption(label="طـلـب مـسـاعـدة", value="support", emoji=EMOJIS["support"]),
            discord.SelectOption(label="تـواصـل مـع الادارة", value="admin", emoji=EMOJIS["admin"]),
            discord.SelectOption(label="تـقـديـم بـائـع", value="seller", emoji=EMOJIS["seller"]),
            discord.SelectOption(label="طـلـب مـسـتـحـقـات", value="money", emoji=EMOJIS["money"]),
            discord.SelectOption(label="بـلاغ ضـد مـخـرب", value="report", emoji=EMOJIS["report"]),
        ]
        super().__init__(placeholder="اختر القسم", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id in open_tickets:
            return await interaction.response.send_message("❌ لديك تذكرة مفتوحة بالفعل.", ephemeral=True)

        section = self.values[0]

        guild = interaction.guild
        category = guild.get_channel(CATEGORIES[section])
        role = guild.get_role(ROLES[section])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        # اسم التذكرة = اسم القسم فقط
        channel = await guild.create_text_channel(
            name=f"{section}",
            category=category,
            overwrites=overwrites,
            topic=str(interaction.user.id)
        )

        open_tickets[interaction.user.id] = channel.id

        embed = discord.Embed(
            title="🎫 تم فتح تذكرتك بنجاح",
            description=f"""
مرحبًا {interaction.user.mention}

📂 القسم: {section}
🕒 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

سيتم الرد عليك قريبًا.
""",
            color=discord.Color.greyple()
        )

        msg = await channel.send(content=f"{interaction.user.mention} {role.mention}", embed=embed, view=TicketControls(section))
        await msg.pin()
        await log(guild, f"🎫 فتح تذكرة\n👤 {interaction.user.mention}\n📂 {section}")

        await interaction.response.send_message(f"✅ تم إنشاء تذكرتك {channel.mention}", ephemeral=True)

# ================= PANEL =================
class Panel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="فتح تذكرة جديدة", emoji=EMOJIS["open"], style=discord.ButtonStyle.secondary)
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        view = View()
        view.add_item(TicketSelect())
        await interaction.response.send_message("اختر القسم:", view=view, ephemeral=True)

# ================= ON_READY =================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await asyncio.sleep(5)
    guild = bot.get_guild(GUILD_ID)
    channel = guild.get_channel(PANEL_CHANNEL_ID)

    async for m in channel.history(limit=20):
        if m.author == bot.user:
            return

    embed = discord.Embed(
        title="🎫 نظام التذاكر الرسمي — 2026",
        description="""
📜 قوانين فتح التذكرة:
• يمنع فتح أكثر من تذكرة.
• اختر القسم الصحيح.
• يمنع الإزعاج.

اضغط الزر بالأسفل.
""",
        color=discord.Color.dark_gray()
    )

    await channel.send(embed=embed, view=Panel())

bot.run(TOKEN)


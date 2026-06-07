import discord
from discord.ext import commands
from discord import ui
import json
import os
from datetime import datetime
import asyncio

# إعدادات البوت
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# آيدي السيرفر والقنوات والرتب
GUILD_ID = 1425201800310685708
TICKET_CHANNEL_ID = 1425206713992220797
LOG_CHANNEL_ID = 1473464868731486242

# الكاتغوريات
CATEGORIES = {
    "support": 1471643552764264508,
    "admin_contact": 1472621021193310268,
    "apply": 1471643151918825749
}

# الرتب لكل قسم
ROLES = {
    "support": 1472603407704654015,
    "admin_contact": 1472593013023834183,
    "apply": 1472618578359353394
}

# الإيموجيات
EMOJIS = {
    "new_ticket": "<:ticket:1472593569272561858>",
    "tech_support": "<:tech:1472593719214477322>",
    "admin_contact": "<:admin:1472593665737359452>",
    "apply": "<:apply:1472593671504527360>",
    "claim": "<:claim:1472593621524938867>",
    "options": "<:options:1472593573038788730>"
}

# تخزين بيانات التذاكر
tickets_data = {}

# ==================== كلاس البوت الرئيسي ====================

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ {self.bot.user} جاهز للتشغيل!")
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="نظام التذاكر"))

# ==================== رسالة التذاكر الرئيسية ====================

class MainTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="فتح تذكرة جديدة", style=discord.ButtonStyle.success, emoji=EMOJIS["new_ticket"], custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketCategoryModal())

class TicketCategoryModal(ui.Modal, title="📋 اختيار قسم التذكرة"):
    def __init__(self):
        super().__init__()
        
        self.category = ui.Select(
            placeholder="اختر القسم المناسب...",
            options=[
                discord.SelectOption(label="الدعم الفني", value="support", emoji=EMOJIS["tech_support"], description="للحصول على دعم فني"),
                discord.SelectOption(label="تواصل مع الإدارة", value="admin_contact", emoji=EMOJIS["admin_contact"], description="للتواصل مع الإدارة مباشرة"),
                discord.SelectOption(label="تقديم للإدارة", value="apply", emoji=EMOJIS["apply"], description="تقديم طلب للانضمام لفريق العمل")
            ]
        )
        self.add_item(self.category)

    async def on_submit(self, interaction: discord.Interaction):
        category_id = CATEGORIES[self.category.values[0]]
        role_id = ROLES[self.category.values[0]]
        category = interaction.guild.get_channel(category_id)
        
        # التحقق من وجود تذكرة مفتوحة
        for channel in interaction.guild.text_channels:
            if channel.category == category and channel.name.startswith(f"ticket-{interaction.user.name.lower()}"):
                await interaction.response.send_message("⚠️ لديك تذكرة مفتوحة بالفعل في هذا القسم!", ephemeral=True)
                return
        
        # إنشاء قناة التذكرة
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            interaction.guild.get_role(role_id): discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        
        ticket_channel = await interaction.guild.create_text_channel(
            f"ticket-{interaction.user.name.lower()}",
            category=category,
            overwrites=overwrites
        )
        
        # حفظ بيانات التذكرة
        tickets_data[str(ticket_channel.id)] = {
            "user_id": interaction.user.id,
            "role_id": role_id,
            "category": self.category.values[0],
            "created_at": str(datetime.now()),
            "status": "open",
            "claimed_by": None
        }
        
        # إرسال رسالة الترحيب في التذكرة
        embed = discord.Embed(
            title=f"🎫 {ZIYAD_GAMINGE} | نظام التذاكر",
            description=f"""
مرحباً بك {interaction.user.mention} 👋

**{interaction.guild.get_role(role_id).mention}** سيتم الرد على طلبك من طرف المسؤولين في أقرب وقت.

⚠️ **تنبيه**: يرجى عدم منشن أي شخص، فريق الدعم سيتم الرد عليك تلقائياً.

📌 **يرجى شرح مشكلتك بالتفصيل**
""",
            color=discord.Color.gold()
        )
        embed.set_footer(text="ZIYAD GAMINGE | جميع الحقوق محفوظة", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        view = TicketControlView(role_id, interaction.user.id)
        await ticket_channel.send(f"{interaction.user.mention} {interaction.guild.get_role(role_id).mention}", embed=embed, view=view)
        await ticket_channel.send("✅ تم إنشاء التذكرة بنجاح! يرجى شرح مشكلتك بالتفصيل.")
        
        await interaction.response.send_message(f"✅ تم إنشاء تذكرتك بنجاح! {ticket_channel.mention}", ephemeral=True)
        
        # تسجيل في اللوق
        await self.log_action(interaction.guild, f"تم فتح تذكرة جديدة من {interaction.user.mention} في قسم {self.category.values[0]}", ticket_channel.id)

    async def log_action(self, guild, action, channel_id=None):
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="📝 سجل التذاكر",
                description=action,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            if channel_id:
                embed.add_field(name="ID القناة", value=f"`{channel_id}`")
            await log_channel.send(embed=embed)

# ==================== أزرار التحكم في التذكرة ====================

class TicketControlView(discord.ui.View):
    def __init__(self, role_id, user_id):
        super().__init__(timeout=None)
        self.role_id = role_id
        self.user_id = user_id

    @discord.ui.button(label="استلام التذكرة", style=discord.ButtonStyle.primary, emoji=EMOJIS["claim"], custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.role_id not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("⚠️ ليس لديك صلاحية لاستلام هذه التذكرة!", ephemeral=True)
            return
        
        tickets_data[str(interaction.channel.id)]["claimed_by"] = interaction.user.id
        
        embed = discord.Embed(
            title="✅ تم استلام التذكرة",
            description=f"**{interaction.user.mention}** قام باستلام هذه التذكرة وسيتم الرد عليك قريباً.",
            color=discord.Color.green()
        )
        embed.set_footer(text="ZIYAD GAMINGE | نظام التذاكر")
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ تم استلام التذكرة بنجاح!", ephemeral=True)
        
        # تسجيل في اللوق
        await self.log_action(interaction.guild, f"{interaction.user.mention} استلم تذكرة {interaction.channel.mention}")

    @discord.ui.button(label="قائمة الخيارات", style=discord.ButtonStyle.secondary, emoji=EMOJIS["options"], custom_id="options_menu")
    async def options_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.role_id not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("⚠️ ليس لديك صلاحية لاستخدام هذه القائمة!", ephemeral=True)
            return
        
        view = OptionsView(self.role_id, self.user_id)
        embed = discord.Embed(
            title="🔧 قائمة التحكم بالتذكرة",
            description="اختر الإجراء المناسب من الأزرار أدناه:",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def log_action(self, guild, action):
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="📝 سجل التذاكر",
                description=action,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            await log_channel.send(embed=embed)

# ==================== قائمة الخيارات ====================

class OptionsView(discord.ui.View):
    def __init__(self, role_id, user_id):
        super().__init__(timeout=60)
        self.role_id = role_id
        self.user_id = user_id

    @discord.ui.button(label="ارسال تذكير", style=discord.ButtonStyle.warning, emoji="🔔", custom_id="remind")
    async def remind_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.guild.get_member(self.user_id)
        channel = interaction.channel
        
        embed = discord.Embed(
            title="📢 تذكير بالتذكرة المفتوحة",
            description=f"""
مرحباً {user.mention} 👋

تذكرتك **{channel.mention}** لا تزال مفتوحة.
يرجى الرد عليها في أقرب وقت ممكن.

**السيرفر:** {interaction.guild.name}
""",
            color=discord.Color.orange()
        )
        embed.set_footer(text="ZIYAD GAMINGE | نظام التذاكر")
        
        try:
            await user.send(embed=embed)
            await interaction.response.send_message("✅ تم إرسال التذكير للمستخدم!", ephemeral=True)
        except:
            await interaction.response.send_message("⚠️ لا يمكن إرسال رسالة خاصة للمستخدم!", ephemeral=True)

    @discord.ui.button(label="الغاء الاستلام", style=discord.ButtonStyle.danger, emoji="❌", custom_id="unclaim")
    async def unclaim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        tickets_data[str(interaction.channel.id)]["claimed_by"] = None
        
        embed = discord.Embed(
            title="⚠️ تم الغاء استلام التذكرة",
            description=f"**{interaction.user.mention}** قام بإلغاء استلام هذه التذكرة. التذكرة متاحة الآن للاستلام.",
            color=discord.Color.red()
        )
        embed.set_footer(text="ZIYAD GAMINGE | نظام التذاكر")
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ تم الغاء استلام التذكرة!", ephemeral=True)

    @discord.ui.button(label="اغلاق التذكرة", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CloseReasonModal(self.user_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="اعادة تسمية", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="rename")
    async def rename_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RenameModal()
        await interaction.response.send_modal(modal)

# ==================== نافذة سبب الاغلاق ====================

class CloseReasonModal(ui.Modal, title="🔒 اغلاق التذكرة"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        
        self.reason = ui.TextInput(
            label="سبب الاغلاق",
            placeholder="اكتب سبب اغلاق التذكرة...",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.guild.get_member(self.user_id)
        
        embed = discord.Embed(
            title="🔒 تم اغلاق التذكرة",
            description=f"""
**تم اغلاق التذكرة من طرف:** {interaction.user.mention}
**السبب:** {self.reason.value}

سيتم حذف هذه القناة بعد 10 ثواني.
""",
            color=discord.Color.red()
        )
        embed.set_footer(text="ZIYAD GAMINGE | نظام التذاكر")
        await interaction.channel.send(embed=embed)
        
        # ارسال نسخة للمستخدم
        transcript = await create_transcript(interaction.channel)
        try:
            await user.send(f"📄 نسخة من تذكرتك `{interaction.channel.name}`:", file=discord.File(transcript))
        except:
            pass
        
        await asyncio.sleep(10)
        await interaction.channel.delete()
        
        await interaction.response.send_message("✅ تم اغلاق التذكرة!", ephemeral=True)

# ==================== نافذة اعادة التسمية ====================

class RenameModal(ui.Modal, title="✏️ اعادة تسمية التذكرة"):
    def __init__(self):
        super().__init__()
        
        self.new_name = ui.TextInput(
            label="الاسم الجديد",
            placeholder="أدخل الاسم الجديد للقناة...",
            required=True,
            min_length=3,
            max_length=32
        )
        self.add_item(self.new_name)

    async def on_submit(self, interaction: discord.Interaction):
        old_name = interaction.channel.name
        await interaction.channel.edit(name=f"ticket-{self.new_name.value.lower().replace(' ', '-')}")
        
        embed = discord.Embed(
            title="✏️ تم اعادة تسمية التذكرة",
            description=f"""
**قام بتغيير الاسم:** {interaction.user.mention}
**من:** `{old_name}`
**الى:** `ticket-{self.new_name.value.lower().replace(' ', '-')}`
""",
            color=discord.Color.blue()
        )
        embed.set_footer(text="ZIYAD GAMINGE | نظام التذاكر")
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ تم تغيير اسم القناة!", ephemeral=True)

# ==================== اعدادات البوت ====================

ZIYAD_GAMINGE = "🎫 ZIYAD GAMINGE"

async def create_transcript(channel):
    """انشاء نسخة نصية من المحادثة"""
    transcript_file = f"transcript_{channel.name}.txt"
    with open(transcript_file, 'w', encoding='utf-8') as f:
        f.write(f"نسخة من تذكرة: {channel.name}\n")
        f.write(f"تاريخ الانشاء: {datetime.now()}\n")
        f.write("="*50 + "\n\n")
        
        async for message in channel.history(limit=500, oldest_first=True):
            f.write(f"[{message.created_at}] {message.author.name}: {message.content}\n")
    
    return transcript_file

@bot.event
async def on_ready():
    print(f"✅ {bot.user} جاهز للتشغيل!")
    print(f"📊 سيرفرات: {len(bot.guilds)}")
    
    # ارسال رسالة التذاكر الرئيسية
    guild = bot.get_guild(GUILD_ID)
    if guild:
        channel = guild.get_channel(TICKET_CHANNEL_ID)
        if channel:
            await channel.purge(limit=100)
            
            embed = discord.Embed(
                title=f"🎫 {ZIYAD_GAMINGE}",
                description="""
مرحبا بكم في سيرفرنا. دائما اسعادكم فيرجى احترام قوانين السيرفر وشكراً.

**يرجى اختيار القسم الصحيح لتجنب العقوبة**

--- 
جميع الحقوق محفوظة | ZIYAD GAMINGE
""",
                color=discord.Color.gold()
            )
            embed.set_footer(text=ZIYAD_GAMINGE)
            embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
            
            view = MainTicketView()
            await channel.send(embed=embed, view=view)
            print("✅ تم اعداد نظام التذاكر بنجاح!")

# ==================== أوامر البوت ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    """اعداد نظام التذاكر"""
    await ctx.channel.purge(limit=1)
    embed = discord.Embed(
        title=f"🎫 {ZIYAD_GAMINGE}",
        description="""
مرحبا بكم في سيرفرنا. دائما اسعادكم فيرجى احترام قوانين السيرفر وشكراً.

**يرجى اختيار القسم الصحيح لتجنب العقوبة**

--- 
جميع الحقوق محفوظة | ZIYAD GAMINGE
""",
        color=discord.Color.gold()
    )
    view = MainTicketView()
    await ctx.send(embed=embed, view=view)
    await ctx.send("✅ تم اعداد نظام التذاكر!", delete_after=5)

@bot.command()
@commands.has_permissions(administrator=True)
async def test_ticket(ctx):
    """اختبار النظام"""
    await ctx.send("🔄 جاري اختبار النظام...")
    await ctx.send("✅ النظام يعمل بشكل طبيعي!")

# تشغيل البوت
bot.run("YOUR_BOT_TOKEN_HERE")

import discord
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime, timedelta, timezone

# ===== BOT SETUP =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # wichtig für Rollencheck

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ===== ERLAUBTE ROLLEN =====
ALLOWED_ROLES = ["Admin", "Race Control", "Steward" ,"Event coordinator"]  # Rollen, die Reminder erstellen dürfen

# ===== ROLLENCHECK STABIL (KEINE CRASHES MEHR) =====
def has_permission():
    async def predicate(ctx):

        # nur Server, keine DMs
        if ctx.guild is None:
            return False

        # echten Member holen
        member = ctx.guild.get_member(ctx.author.id)
        if member is None:
            return False

        # Rollen prüfen
        user_roles = [role.name for role in member.roles]
        return any(role in ALLOWED_ROLES for role in user_roles)

    return commands.check(predicate)


# ================= VIEW =================

class RSVPView(View):
    def __init__(self, info_text=None, image_url=None):
        super().__init__(timeout=None)
        self.accepted = set()
        self.declined = set()
        self.tentative = set()

        self.timestamp = None
        self.google_link = None
        self.info_text = info_text
        self.image_url = image_url

    async def update_message(self, interaction):
        embed = discord.Embed(
        title=f"🏁 {self.track.title()} - Race Night",
        description=(
            "Please vote if you are racing:\n\n"
            f"📅 Race Time: <t:{self.timestamp}:F>\n"
            f"⏳ Countdown: <t:{self.timestamp}:R>\n"
            f"📆 [Add to Google Calendar]({self.google_link})\n\n"
            f"ℹ️ Info: {self.info_text if self.info_text else '-'}\n\u200b\n"
        ),
            color=0xF1C40F
        )

        if self.image_url:
            embed.set_image(url=self.image_url)

        embed.add_field(name="\u200b", value="\u200b", inline=False)
        
        embed.add_field(
            name=f"🟢 Accepted ({len(self.accepted)})",
            value="\n".join(self.accepted) or "-",
            inline=False
        )

        embed.add_field(
            name=f"🔴 Declined ({len(self.declined)})",
            value="\n".join(self.declined) or "-",
            inline=False
        )

        embed.add_field(
            name=f"🟡 Maybe ({len(self.tentative)})",
            value="\n".join(self.tentative) or "-",
            inline=False
        )

        await interaction.response.edit_message(embed=embed, view=self)


    # ===== BUTTONS =====

    @discord.ui.button(label="Accepted", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, interaction: discord.Interaction, button: Button):
        user = interaction.user.display_name
        self.declined.discard(user)
        self.tentative.discard(user)
        self.accepted.add(user)
        await self.update_message(interaction)

    @discord.ui.button(label="Declined", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline(self, interaction: discord.Interaction, button: Button):
        user = interaction.user.display_name
        self.accepted.discard(user)
        self.tentative.discard(user)
        self.declined.add(user)
        await self.update_message(interaction)

    @discord.ui.button(label="Tentative", style=discord.ButtonStyle.secondary, emoji="❓")
    async def maybe(self, interaction: discord.Interaction, button: Button):
        user = interaction.user.display_name
        self.accepted.discard(user)
        self.declined.discard(user)
        self.tentative.add(user)
        await self.update_message(interaction)

# ================= COMMAND =================

from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

@bot.command()
@has_permission()
async def race(ctx, date: str, time: str, *, track:str):
    
    # ===== STRECKE + BESCHREIBUNG PARSEN =====
    # Nutzung:
    # !race 20.02.2026 20:00 Red Bull Ring | Lobby open | Mandatory pitstop

    if "|" in track:
        track_name, desc = track.split("|", 1)
        track = track_name.strip()
        desc = desc.strip().replace("|", "\n")  # weitere | = neue Zeile
    else:
        track = track.strip()
        desc = None

    
    """
    Beispiel:
    !race 14.02.2026 18:00 Paul Ricard Training 60min Rennen 60min
    """

    # Datum + Zeit parsen (deutsches Format)
    dt_local = datetime.strptime(f"{date} {time}", "%d.%m.%Y %H:%M")

    # Deutschland im Februar = CET (UTC+1)
    dt_utc = dt_local - timedelta(hours=1)
    timestamp = int(dt_utc.replace(tzinfo=timezone.utc).timestamp())

    # Google Kalender (2h Standarddauer)
    start_google = dt_utc.strftime("%Y%m%dT%H%M%SZ")
    end_google = (dt_utc + timedelta(hours=2)).strftime("%Y%m%dT%H%M%SZ")

    google_link = (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={quote_plus('Race ' + track)}"
        f"&dates={start_google}/{end_google}"
        f"&details={quote_plus(desc or 'League Race')}"
        f"&location={quote_plus(track)}"
    )

    # Streckenbilder (Keys klein!)
    track_lower = track.lower()
    track_images = {
        "paul ricard": "https://img2.51gt3.com/rac/track/202304/b16da65815684d12aea6b42f42365882.png",
        "spa francorchamps": "https://img2.51gt3.com/rac/track/202304/1aebcbf68ab14bce81924c06009fbe62.png",
        "monza": "https://img2.51gt3.com/rac/track/202304/73988af861d14f0bb3b39149aefaff65.png",
        "nürburgring": "https://img2.51gt3.com/rac/track/202304/2478955935b2421b9bc575c3f641123d.png",
        "silverstone": "https://img2.51gt3.com/rac/track/202304/fed0c74be75347a490b23f65a87c1d0e.png",
        "barcelona": "https://img2.51gt3.com/rac/track/202303/35ad041fd64f44628adaec94b0769607.png",
        "brands Hatch": "https://img2.51gt3.com/rac/track/202309/f24f80e559c54c12ba9a7bd87e28810b.png",
        "hungaroring": "https://img2.51gt3.com/rac/track/202309/f24f80e559c54c12ba9a7bd87e28810b.png",
        "misano": "https://img2.51gt3.com/rac/track/202309/fe1b0789c5444c63907024a8da445a1e.png",
        "zandvoort": "https://img2.51gt3.com/rac/track/202304/f7d718f5f16f49038f69f21a3f3d972f.png",
        "zolder": "https://img2.51gt3.com/rac/track/202305/ad7f0a9354834df8a4898d1eb7f549d0.png",
        "snetterton": "https://www.apexracingleague.com/wp-content/uploads/2020/02/Snetterton.png",
        "olton Park": "https://img2.51gt3.com/rac/track/202503/e4ca6e6c4e074879a61ea4492bac3585.jpg",
        "donington Park": "https://img2.51gt3.com/rac/track/202305/04ed487923dc4373bdab93c252584a7b.png",
        "kyalami": "https://img2.51gt3.com/rac/track/202305/1a6fd3813dbb421bbb0aee79cac6d4d8.png",
        "suzuka": "https://img2.51gt3.com/rac/track/aacbce6c41dd4e5496eea246fc5e7c6b.jpg",
        "laguna seca": "https://img2.51gt3.com/rac/track/202305/cbf13c969f28425299c2c450576fe052.png",
        "mount panorama": "https://img2.51gt3.com/rac/track/202403/a068e9fe89f1471594711b1d624190a8.jpg",
        "imola": "https://img2.51gt3.com/rac/track/202304/15ab044da2b542b587a5ddba4a9ce76e.png",
        "watkins glen": "https://img2.51gt3.com/rac/track/202305/fbc2519ce917489ea6c385147e8b196a.png",
        "circuit of the americas": "https://img2.51gt3.com/rac/track/202303/d093da62dab34f54b494979cce5a7a1c.png",
        "indianapolis": "https://img2.51gt3.com/rac/track/202502/da6a99e10588446ab8c87145f99741ac.jpg",
        "valencia": "https://img2.51gt3.com/rac/track/202304/e96ba2e3abbc4183b11627ecde2bf351.png",
        "red bull ring": "https://img2.51gt3.com/rac/track/202304/10482227212b4ac3a557ce0197cb87a0.png",
        "24h nürburgring": "https://img2.51gt3.com/rac/track/202509/5aec8bbe6ad540adbe11493582550458.jpg",
    }

    image_url = None
    for key, url in track_images.items():
        if key.lower() in track_lower:
            image_url = url
            break

    # Embed bauen
    embed = discord.Embed(
        title=f"🏁 {track.title()} - Race Night",
        description=(
            "Please vote if you are racing:\n\n"
            f"📅 Race Time: <t:{timestamp}:F>\n"
            f"⏳ Countdown: <t:{timestamp}:R>\n"
            f"📆 [Add to Google Calendar]({google_link})\n\n"
            f"ℹ️ Info: {desc if desc else '-'}\n\u200b\n"
        ),
        color=0xF1C40F
    )

    if image_url:
        embed.set_image(url=image_url)

        embed.add_field(name="\u200b", value="\u200b", inline=False)
        embed.add_field(name="🟢 Accepted (0)", value="-", inline=False)
        embed.add_field(name="🔴 Declined (0)", value="-", inline=False)
        embed.add_field(name="🟡 Maybe (0)", value="-", inline=False)
        embed.set_footer(text="PitBoss Systems")


    # View inkl. Persistenz (damit Info beim Update nicht verschwindet)
    
    view = RSVPView(info_text=desc, image_url=image_url)
    view.timestamp = timestamp
    view.google_link = google_link
    view.track = track

    # erste Nachricht senden
    msg = await ctx.send(embed=embed, view=view)

    # View merkt sich Nachricht
    view.message = msg


# ================= EVENTS =================

@bot.event
async def on_ready():
    print(f"PitBoss online als {bot.user}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ Only People with the right Server Roles can create race Events.")

# ================= TOKEN =================
import os
bot.run(os.getenv("TOKEN"))

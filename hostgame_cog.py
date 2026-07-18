import discord
from discord.ext import commands
from discord import app_commands
import random
import string

from config import (
    GAME_TYPES,
    MATCH_TYPES,
    REGIONS,
    THREAD_NAME,
    EMBED_COLOR,
    PING_ROLE_NAME,
    SUPPORT_FOOTER,
    TIER_ROLES,
)
from views import JoinButton
from games import (
    create_game,
    delete_game,
    get_game,
    get_game_by_thread,
    load_games,
    save_games,
    remove_player,
)

PLAYERS_NEEDED = {
    "1s": 1,
    "2s": 3,
    "3s": 5,
    "4s": 7,
}


def generate_game_id():
    return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))


def is_host_or_staff(interaction: discord.Interaction, game: dict) -> bool:
    if interaction.user.id == game["host_id"]:
        return True
    return interaction.user.guild_permissions.manage_threads


async def get_thread(interaction: discord.Interaction, game: dict):
    thread = interaction.guild.get_thread(game["thread"])
    if thread is None:
        thread = await interaction.guild.fetch_channel(game["thread"])
    return thread


def resolve_game(interaction: discord.Interaction):
    """Resolve a game from the thread the command is used in."""
    if isinstance(interaction.channel, discord.Thread):
        return get_game_by_thread(interaction.channel.id)

    return None, None


def get_player_tier(guild: discord.Guild, player_id: int):
    member = guild.get_member(player_id)
    if not member:
        return None

    for tier in TIER_ROLES:
        if any(tier.lower() in r.name.lower() for r in member.roles):
            return tier

    return None


def get_ping_role(guild: discord.Guild):
    if not PING_ROLE_NAME:
        return None
    return discord.utils.find(
        lambda r: PING_ROLE_NAME.lower() in r.name.lower(), guild.roles
    )


class HostGame(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ---------------- /hostgame ----------------
    @app_commands.command(name="hostgame", description="Host a game.")
    @app_commands.describe(
        gametype="Game Type",
        matchtype="Match Type",
        region="Region",
        vipserver="VIP Server Link",
    )
    @app_commands.choices(
        gametype=[app_commands.Choice(name=g, value=g) for g in GAME_TYPES],
        matchtype=[app_commands.Choice(name=m, value=m) for m in MATCH_TYPES],
        region=[app_commands.Choice(name=r, value=r) for r in REGIONS],
    )
    async def hostgame(
        self,
        interaction: discord.Interaction,
        gametype: app_commands.Choice[str],
        matchtype: app_commands.Choice[str],
        region: app_commands.Choice[str],
        vipserver: str,
    ):
        game_id = generate_game_id()
        players_needed = PLAYERS_NEEDED[gametype.value]

        embed = discord.Embed(
            title=f"Hosting a {matchtype.value} Match ({region.value.upper()})",
            description=(
                f"Hosting a **{gametype.value}** game! Need **{players_needed}** more players to join.\n"
                f"Hosted by: `{interaction.user.display_name}`"
            ),
            color=EMBED_COLOR,
        )
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=SUPPORT_FOOTER)

        role = get_ping_role(interaction.guild)
        content = role.mention if role else None

        view = JoinButton(game_id)
        await interaction.response.send_message(content=content, embed=embed, view=view)
        message = await interaction.original_response()

        thread = await interaction.channel.create_thread(
            name=THREAD_NAME.format(
                match=matchtype.value,
                gametype=gametype.value,
                gameid=game_id,
            ),
            type=discord.ChannelType.private_thread,
            invitable=True,
        )

        await thread.add_user(interaction.user)

        create_game(
            game_id=game_id,
            host_id=interaction.user.id,
            host_name=str(interaction.user),
            gametype=gametype.value,
            matchtype=matchtype.value,
            region=region.value,
            vip=vipserver,
            thread_id=thread.id,
            message_id=message.id,
            players_needed=players_needed,
            channel_id=interaction.channel_id,
        )

        info_embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Game",
            description=(
                f"Started by {interaction.user.mention}\n\n"
                f"VIP Server Link: [Join here!]({vipserver})\n"
                "• Please wait for players to join and then you can start your match."
            ),
            color=EMBED_COLOR,
        )
        info_embed.timestamp = discord.utils.utcnow()
        info_embed.set_footer(text=f"Game ID: {game_id}")
        await thread.send(embed=info_embed)

    # ---------------- /endgame ----------------
    @app_commands.command(name="endgame", description="End a hosted game and lock its thread.")
    async def endgame(self, interaction: discord.Interaction):
        gameid, game = resolve_game(interaction)

        if not game:
            await interaction.response.send_message(
                "This command only works inside a game's thread.", ephemeral=True
            )
            return

        if not is_host_or_staff(interaction, game):
            await interaction.response.send_message("Only the host can end this game.", ephemeral=True)
            return

        if game.get("finished"):
            await interaction.response.send_message("This game has already ended.", ephemeral=True)
            return

        thread = await get_thread(interaction, game)
        await thread.send(
            embed=discord.Embed(
                description=f"🔒 {interaction.user.mention} has ended this game. Deleting thread.",
                color=EMBED_COLOR,
            )
        )

        delete_game(gameid)
        await thread.delete()
        await interaction.response.send_message("Game ended and thread deleted.", ephemeral=True)

    # ---------------- /createteams ----------------
    @app_commands.command(name="createteams", description="Split the joined players into fair teams.")
    async def createteams(self, interaction: discord.Interaction):
        gameid, game = resolve_game(interaction)

        if not game:
            await interaction.response.send_message(
                "This command only works inside a game's thread.", ephemeral=True
            )
            return

        if not is_host_or_staff(interaction, game):
            await interaction.response.send_message("Only the host can create teams.", ephemeral=True)
            return

        players = list(game["players"])

        if not any(p["id"] == game["host_id"] for p in players):
            host_member = interaction.guild.get_member(game["host_id"])
            host_name = host_member.display_name if host_member else game["host_name"]
            players.append({"id": game["host_id"], "display_name": host_name})

        if len(players) < 2:
            await interaction.response.send_message("Not enough players have joined yet.", ephemeral=True)
            return

        by_tier = {}
        for p in players:
            tier = get_player_tier(interaction.guild, p["id"])
            by_tier.setdefault(tier, []).append(p)

        tier_order = TIER_ROLES + [None]

        team_a, team_b = [], []
        for tier in tier_order:
            group = by_tier.get(tier, [])
            random.shuffle(group)
            for p in group:
                entry = (p, tier)
                if len(team_a) <= len(team_b):
                    team_a.append(entry)
                else:
                    team_b.append(entry)

        def fmt(entry):
            p, tier = entry
            label = f" — *{tier}*" if tier else ""
            return f"• <@{p['id']}>{label}"

        embed = discord.Embed(
            title="⚔️ Teams Are In!",
            description="Balanced by skill tier. Good luck, have fun. 🎮",
            color=EMBED_COLOR,
        )
        embed.add_field(name=f"Team 1 ({len(team_a)})", value="\n".join(fmt(e) for e in team_a) or "—", inline=True)
        embed.add_field(name=f"Team 2 ({len(team_b)})", value="\n".join(fmt(e) for e in team_b) or "—", inline=True)
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=f"Game ID: {gameid}")

        thread = await get_thread(interaction, game)
        await thread.send(embed=embed)
        await interaction.response.send_message("Teams created in the thread.", ephemeral=True)

    # ---------------- /sub ----------------
    @app_commands.command(name="sub", description="Announce that you need a substitute for the game.")
    async def sub(self, interaction: discord.Interaction):
        gameid, game = resolve_game(interaction)

        if not game:
            await interaction.response.send_message(
                "This command only works inside a game's thread.", ephemeral=True
            )
            return

        if not is_host_or_staff(interaction, game):
            await interaction.response.send_message("Only the host can request a substitute.", ephemeral=True)
            return

        thread = await get_thread(interaction, game)

        role = get_ping_role(interaction.guild)
        content = role.mention if role else None

        current_players = len(game.get("players", [])) + 1
        players_needed = max(0, game.get("players_needed", 0) - current_players + 1)
        if players_needed < 1:
            players_needed = 1

        sub_embed = discord.Embed(
            title=f"Looking for {players_needed} sub",
            description=(
                f"{interaction.user.mention} is looking for **{players_needed}** substitute player(s).\n"
                "Join using the **Join Game** button above."
            ),
            color=EMBED_COLOR,
        )
        sub_embed.set_footer(text=f"Game ID: {gameid}")

        channel = interaction.guild.get_channel(game.get("channel")) or interaction.channel

        original_message = None
        message_id = game.get("message")
        if message_id:
            try:
                original_message = await channel.fetch_message(message_id)
            except discord.NotFound:
                original_message = None

        if original_message:
            await original_message.reply(content=content, embed=sub_embed)
        else:
            await channel.send(content=content, embed=sub_embed)

        await thread.send(
            embed=discord.Embed(
                description=f"{interaction.user.mention} has requested a substitute for this game.",
                color=EMBED_COLOR,
            )
        )
        await interaction.response.send_message(
            f"A substitute request has been posted for this game.", ephemeral=True
        )

    # ---------------- /remove ----------------
    @app_commands.command(name="remove", description="Remove a player from a game.")
    @app_commands.describe(player="The player to remove", reason="Reason for removing the player")
    async def remove(
        self,
        interaction: discord.Interaction,
        player: discord.Member,
        reason: str,
    ):
        gameid, game = resolve_game(interaction)

        if not game:
            await interaction.response.send_message(
                "This command only works inside a game's thread.", ephemeral=True
            )
            return

        if not is_host_or_staff(interaction, game):
            await interaction.response.send_message("Only the host can remove players.", ephemeral=True)
            return

        is_player = any(p["id"] == player.id for p in game["players"])

        if not is_player:
            await interaction.response.send_message(f"{player.mention} isn't in this game.", ephemeral=True)
            return

        remove_player(gameid, player.id)

        games = load_games()
        if gameid in games:
            games[gameid]["finished"] = False
            save_games(games)

        thread = await get_thread(interaction, game)
        embed = discord.Embed(
            title="Player Removed",
            description=f"{player.mention} was removed from the game.",
            color=EMBED_COLOR,
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Game ID: {gameid}")
        await thread.send(embed=embed)
        await interaction.response.send_message(f"Removed {player.mention} from the game.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(HostGame(bot))

```python
@app_commands.command(name="add", description="Add a member to the game if there's still room.")
@app_commands.describe(player="The member to add to the game")
async def add(self, interaction: discord.Interaction, player: discord.Member):
    gameid, game = resolve_game(interaction)

    if not game:
        await interaction.response.send_message(
            "This command only works inside a game's thread.", ephemeral=True
        )
        return

    if game.get("finished"):
        await interaction.response.send_message("This game has already ended.", ephemeral=True)
        return

    if not is_host_or_staff(interaction, game):
        await interaction.response.send_message("Only the host can add players.", ephemeral=True)
        return

    if any(p["id"] == player.id for p in game.get("players", [])):
        await interaction.response.send_message(f"{player.mention} is already in this game.", ephemeral=True)
        return

    players_needed = game.get("players_needed", 0)
    current_players = len(game.get("players", []))

    if current_players >= players_needed:
        await interaction.response.send_message("This game is already full.", ephemeral=True)
        return

    add_player(gameid, {"id": player.id, "display_name": player.display_name})
    game = get_game(gameid)

    thread = await get_thread(interaction, game)
    await thread.add_user(player)

    await thread.send(
        embed=discord.Embed(
            title="Player Added",
            description=f"{player.mention} was added to the game by {interaction.user.mention}.",
            color=EMBED_COLOR,
        )
    )

    if len(game.get("players", [])) >= players_needed:
        games = load_games()
        if gameid in games and not games[gameid]["finished"]:
            games[gameid]["finished"] = True
            games[gameid]["locked"] = True
            save_games(games)

            await thread.send(
                embed=discord.Embed(
                    description="✅ This game is now full.",
                    color=EMBED_COLOR,
                )
            )

    await interaction.response.send_message(f"Added {player.mention} to the game.", ephemeral=True)
```

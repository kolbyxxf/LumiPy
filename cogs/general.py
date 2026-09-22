import random
import discord
from discord import app_commands
from discord.ext import commands

MAX_DICE = 20
MAX_SIDES = 1000

EIGHTBALL_ANSWERS = {
    "Yes.": discord.Color.green(),
    "Definitely!": discord.Color.green(),
    "It looks good.": discord.Color.green(),
    "Maybe.": discord.Color.gold(),
    "Ask again later.": discord.Color.gold(),
    "No.": discord.Color.red(),
    "Not a chance.": discord.Color.red(),
    "I wouldn't count on it.": discord.Color.red(),
}

RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
RPS_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

TRIVIA_QUESTIONS = [
    {"question": "What is the capital of Japan?", "choices": ["Seoul", "Beijing", "Tokyo", "Bangkok"], "answer": 2},
    {"question": "Which planet is known as the Red Planet?", "choices": ["Venus", "Mars", "Jupiter", "Saturn"], "answer": 1},
    {"question": "How many legs does a spider have?", "choices": ["6", "8", "10", "12"], "answer": 1},
    {"question": "What is the largest ocean on Earth?", "choices": ["Atlantic", "Indian", "Arctic", "Pacific"], "answer": 3},
    {"question": "In what year did the Titanic sink?", "choices": ["1905", "1912", "1918", "1923"], "answer": 1},
    {"question": "What gas do plants absorb from the air?", "choices": ["Oxygen", "Nitrogen", "Carbon dioxide", "Helium"], "answer": 2},
    {"question": "How many strings does a standard guitar have?", "choices": ["4", "5", "6", "7"], "answer": 2},
    {"question": "What is the smallest prime number?", "choices": ["0", "1", "2", "3"], "answer": 2},
]


def tictactoe_winner(board: list[list[str | None]]) -> str | None:
    """Return 'X', 'O', or None. board is 3x3, indexed [row][col]."""
    lines = list(board)
    lines += [[board[r][c] for r in range(3)] for c in range(3)]
    lines.append([board[0][0], board[1][1], board[2][2]])
    lines.append([board[0][2], board[1][1], board[2][0]])

    for line in lines:
        if line[0] is not None and line[0] == line[1] == line[2]:
            return line[0]

    return None


class TicTacToeButton(discord.ui.Button["TicTacToeView"]):
    def __init__(self, row: int, col: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=row)
        self.row_index = row
        self.col_index = col

    async def callback(self, interaction: discord.Interaction):
        await self.view.handle_move(interaction, self)


class TicTacToeView(discord.ui.View):
    def __init__(self, player_x: discord.Member, player_o: discord.Member):
        super().__init__(timeout=180)
        self.player_x = player_x
        self.player_o = player_o
        self.current = player_x
        self.board: list[list[str | None]] = [[None] * 3 for _ in range(3)]
        self.message: discord.Message | None = None

        for row in range(3):
            for col in range(3):
                self.add_item(TicTacToeButton(row, col))

    def build_embed(self, *, winner: discord.Member | None = None, draw: bool = False) -> discord.Embed:
        embed = discord.Embed(title="❌⭕ Tic-Tac-Toe")
        embed.add_field(name="Player ❌", value=self.player_x.mention)
        embed.add_field(name="Player ⭕", value=self.player_o.mention)

        if winner:
            embed.description = f"🏆 {winner.mention} wins!"
            embed.color = discord.Color.green()
        elif draw:
            embed.description = "🤝 It's a draw!"
            embed.color = discord.Color.gold()
        else:
            embed.description = f"It's {self.current.mention}'s turn."
            embed.color = discord.Color.blurple()

        return embed

    async def handle_move(self, interaction: discord.Interaction, button: TicTacToeButton):
        if interaction.user != self.current:
            await interaction.response.send_message("It's not your turn.", ephemeral=True)
            return

        if button.disabled:
            await interaction.response.send_message("That spot is already taken.", ephemeral=True)
            return

        symbol = "X" if self.current == self.player_x else "O"
        button.label = symbol
        button.style = discord.ButtonStyle.danger if symbol == "X" else discord.ButtonStyle.success
        button.disabled = True
        self.board[button.row_index][button.col_index] = symbol

        winner_symbol = tictactoe_winner(self.board)
        board_full = all(cell is not None for row in self.board for cell in row)

        if winner_symbol or board_full:
            for item in self.children:
                item.disabled = True

            winner = self.current if winner_symbol else None
            embed = self.build_embed(winner=winner, draw=winner_symbol is None)
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
            return

        self.current = self.player_o if self.current == self.player_x else self.player_x
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        if self.message:
            try:
                embed = self.build_embed()
                embed.description = "⌛ Game timed out from inactivity."
                embed.color = discord.Color.greyple()
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


class RPSButton(discord.ui.Button["RPSView"]):
    def __init__(self, choice: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=choice.title(),
            emoji=RPS_EMOJI[choice],
        )
        self.choice = choice

    async def callback(self, interaction: discord.Interaction):
        await self.view.handle_choice(interaction, self.choice)


class RPSView(discord.ui.View):
    def __init__(self, player1: discord.Member, player2: discord.Member):
        super().__init__(timeout=60)
        self.player1 = player1
        self.player2 = player2
        self.choices: dict[int, str] = {}
        self.message: discord.Message | None = None

        for choice in ("rock", "paper", "scissors"):
            self.add_item(RPSButton(choice))

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        user = interaction.user

        if user.id not in (self.player1.id, self.player2.id):
            await interaction.response.send_message("This isn't your game.", ephemeral=True)
            return

        if user.id in self.choices:
            await interaction.response.send_message("You already locked in a choice.", ephemeral=True)
            return

        self.choices[user.id] = choice
        await interaction.response.send_message(
            f"You chose {RPS_EMOJI[choice]} **{choice.title()}**. Waiting for the other player...",
            ephemeral=True,
        )

        if len(self.choices) < 2:
            return

        for item in self.children:
            item.disabled = True

        p1_choice = self.choices[self.player1.id]
        p2_choice = self.choices[self.player2.id]

        if p1_choice == p2_choice:
            result = "🤝 It's a tie!"
            color = discord.Color.gold()
        elif RPS_BEATS[p1_choice] == p2_choice:
            result = f"🏆 {self.player1.mention} wins!"
            color = discord.Color.green()
        else:
            result = f"🏆 {self.player2.mention} wins!"
            color = discord.Color.green()

        embed = discord.Embed(title="🪨📄✂️ Rock Paper Scissors — Result", color=color)
        embed.add_field(
            name=self.player1.display_name,
            value=f"{RPS_EMOJI[p1_choice]} {p1_choice.title()}",
        )
        embed.add_field(
            name=self.player2.display_name,
            value=f"{RPS_EMOJI[p2_choice]} {p2_choice.title()}",
        )
        embed.add_field(name="Result", value=result, inline=False)

        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass

        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        if self.message and len(self.choices) < 2:
            try:
                embed = discord.Embed(
                    title="🪨📄✂️ Rock Paper Scissors",
                    description="⌛ Game timed out — not everyone picked in time.",
                    color=discord.Color.greyple(),
                )
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


class TriviaButton(discord.ui.Button["TriviaView"]):
    def __init__(self, label: str, index: int):
        super().__init__(style=discord.ButtonStyle.secondary, label=label)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        await self.view.handle_answer(interaction, self)


class TriviaView(discord.ui.View):
    def __init__(self, question: dict):
        super().__init__(timeout=30)
        self.question = question
        self.answered = False
        self.message: discord.Message | None = None

        for index, choice in enumerate(question["choices"]):
            self.add_item(TriviaButton(choice, index))

    async def handle_answer(self, interaction: discord.Interaction, button: TriviaButton):
        if self.answered:
            await interaction.response.send_message(
                "This question has already been answered.", ephemeral=True
            )
            return

        self.answered = True
        correct_index = self.question["answer"]

        for item in self.children:
            item.disabled = True
            if item.index == correct_index:
                item.style = discord.ButtonStyle.success
            elif item is button:
                item.style = discord.ButtonStyle.danger

        if button.index == correct_index:
            description = f"✅ {interaction.user.mention} got it right!"
            color = discord.Color.green()
        else:
            correct_text = self.question["choices"][correct_index]
            description = (
                f"❌ {interaction.user.mention} guessed wrong. "
                f"The answer was **{correct_text}**."
            )
            color = discord.Color.red()

        embed = discord.Embed(
            title="🧠 Trivia — Result",
            description=f"**{self.question['question']}**\n\n{description}",
            color=color,
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        if self.answered:
            return

        correct_index = self.question["answer"]

        for item in self.children:
            item.disabled = True
            if item.index == correct_index:
                item.style = discord.ButtonStyle.success

        if self.message:
            embed = discord.Embed(
                title="🧠 Trivia — Time's up!",
                description=(
                    f"**{self.question['question']}**\n\n"
                    f"No one answered in time. The answer was "
                    f"**{self.question['choices'][correct_index]}**."
                ),
                color=discord.Color.orange(),
            )
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hello", description="Says Hello!")
    async def say_hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Hi there {interaction.user}! What can I help you with?"
        )

    @app_commands.command(name="ping", description="Bots ping!")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong🏓! `{latency}ms`")

    @app_commands.command(name="roll", description="Roll dice")
    async def roll(
        self,
        interaction: discord.Interaction,
        sides: app_commands.Range[int, 1, MAX_SIDES] = 6,
        amount: app_commands.Range[int, 1, MAX_DICE] = 1,
    ):
        rolls = [random.randint(1, sides) for _ in range(amount)]
        await interaction.response.send_message(
            f"Rolled {amount}d{sides}: {rolls}\nTotal: `{sum(rolls)}`"
        )

    @app_commands.command(name="8ball", description="Ask the magic 8-ball")
    async def eightball(self, interaction: discord.Interaction, question: str):
        answer = random.choice(list(EIGHTBALL_ANSWERS))
        embed = discord.Embed(title="🎱 Magic 8-Ball", color=EIGHTBALL_ANSWERS[answer])
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=answer, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Show info about a member")
    async def userinfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ):
        member = member or interaction.user
        embed = discord.Embed(title=member.display_name, color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=member.name)
        embed.add_field(name="ID", value=f"`{member.id}`")
        embed.add_field(
            name="Account created",
            value=discord.utils.format_dt(member.created_at, "R"),
            inline=False,
        )
        if member.joined_at:
            embed.add_field(
                name="Joined server",
                value=discord.utils.format_dt(member.joined_at, "R"),
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Show info about this server")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return
        embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=f"<@{guild.owner_id}>")
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Roles", value=len(guild.roles))
        embed.add_field(name="Text channels", value=len(guild.text_channels))
        embed.add_field(name="Voice channels", value=len(guild.voice_channels))
        embed.add_field(
            name="Created",
            value=discord.utils.format_dt(guild.created_at, "R"),
            inline=False,
        )
        embed.set_footer(text=f"ID: {guild.id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="See a user's avatar")
    async def avatar(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ):
        member = member or interaction.user
        embed = discord.Embed(title=member.display_name, color=member.color)
        embed.set_image(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tictactoe", description="Challenge another member to Tic-Tac-Toe")
    @app_commands.describe(opponent="Who do you want to challenge?")
    async def tictactoe(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent.bot:
            await interaction.response.send_message("You can't challenge a bot.", ephemeral=True)
            return

        if opponent == interaction.user:
            await interaction.response.send_message("You can't challenge yourself.", ephemeral=True)
            return

        view = TicTacToeView(interaction.user, opponent)
        await interaction.response.send_message(embed=view.build_embed(), view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="rps", description="Challenge another member to Rock Paper Scissors")
    @app_commands.describe(opponent="Who do you want to challenge?")
    async def rps(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent.bot:
            await interaction.response.send_message("You can't challenge a bot.", ephemeral=True)
            return

        if opponent == interaction.user:
            await interaction.response.send_message("You can't challenge yourself.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🪨📄✂️ Rock Paper Scissors",
            description=(
                f"{interaction.user.mention} vs {opponent.mention}\n\n"
                "Both players, pick your move below. Your choice stays "
                "hidden until both of you have picked."
            ),
            color=discord.Color.blurple(),
        )
        view = RPSView(interaction.user, opponent)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="trivia", description="Answer a random trivia question")
    async def trivia(self, interaction: discord.Interaction):
        question = random.choice(TRIVIA_QUESTIONS)
        view = TriviaView(question)
        embed = discord.Embed(
            title="🧠 Trivia",
            description=question["question"],
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="First correct answer wins! You have 30 seconds.")
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))

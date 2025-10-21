# Discord RPG Bot Implementation
# This shows how to implement the RPG system as Discord bot commands

import discord
from discord.ext import commands
from discord import app_commands
import random
import json
from datetime import datetime
from logger import AppLogger

logger = AppLogger(__name__).get_logger()

# RPG Classes Data
RPG_CLASSES = {
    "warrior": {
        "name": "Warrior",
        "icon": "⚔️",
        "description": "Masters of melee combat and defense, warriors charge into battle with sword and shield.",
        "abilities": ["Charge", "Shield Wall", "Whirlwind", "Intimidating Shout"],
        "base_stats": {"strength": 20, "agility": 12, "intellect": 8, "health": 150, "mana": 50},
        "color": 0xc79c6e
    },
    "paladin": {
        "name": "Paladin",
        "icon": "🛡️",
        "description": "Holy warriors who balance righteous fury with divine protection and healing magic.",
        "abilities": ["Holy Light", "Consecration", "Divine Shield", "Hammer of Wrath"],
        "base_stats": {"strength": 16, "agility": 10, "intellect": 14, "health": 130, "mana": 100},
        "color": 0xf58cba
    },
    "hunter": {
        "name": "Hunter",
        "icon": "🏹",
        "description": "Masters of ranged combat and beast companions, tracking enemies across vast distances.",
        "abilities": ["Hunter's Mark", "Multi-Shot", "Beast Companion", "Track Beasts"],
        "base_stats": {"strength": 12, "agility": 18, "intellect": 10, "health": 110, "mana": 80},
        "color": 0xabd473
    },
    "rogue": {
        "name": "Rogue",
        "icon": "🗡️",
        "description": "Stealthy assassins who strike from shadows with deadly precision and cunning tricks.",
        "abilities": ["Stealth", "Backstab", "Poison Weapon", "Lockpicking"],
        "base_stats": {"strength": 14, "agility": 20, "intellect": 8, "health": 100, "mana": 60},
        "color": 0xfff569
    },
    "priest": {
        "name": "Priest",
        "icon": "✨",
        "description": "Masters of holy and shadow magic, capable of powerful healing and mind control.",
        "abilities": ["Heal", "Mind Control", "Holy Nova", "Power Word: Shield"],
        "base_stats": {"strength": 8, "agility": 10, "intellect": 20, "health": 90, "mana": 150},
        "color": 0xffffff
    },
    "shaman": {
        "name": "Shaman",
        "icon": "⚡",
        "description": "Elemental wielders who command the forces of nature and commune with spirits.",
        "abilities": ["Lightning Bolt", "Earth Shock", "Healing Wave", "Ghost Wolf"],
        "base_stats": {"strength": 12, "agility": 12, "intellect": 16, "health": 110, "mana": 120},
        "color": 0x0070de
    },
    "mage": {
        "name": "Mage",
        "icon": "🔥",
        "description": "Arcane scholars who devastate enemies with powerful spells of fire, frost, and magic.",
        "abilities": ["Fireball", "Frost Bolt", "Teleport", "Arcane Missiles"],
        "base_stats": {"strength": 6, "agility": 8, "intellect": 22, "health": 80, "mana": 180},
        "color": 0x69ccf0
    },
    "warlock": {
        "name": "Warlock",
        "icon": "👹",
        "description": "Dark magic practitioners who summon demons and curse their enemies with fel energy.",
        "abilities": ["Shadow Bolt", "Summon Imp", "Corruption", "Life Drain"],
        "base_stats": {"strength": 8, "agility": 10, "intellect": 18, "health": 95, "mana": 160},
        "color": 0x9482c9
    },
    "druid": {
        "name": "Druid",
        "icon": "🌿",
        "description": "Shapeshifting nature guardians who can heal, cast spells, or transform into beasts.",
        "abilities": ["Healing Touch", "Moonfire", "Bear Form", "Entangling Roots"],
        "base_stats": {"strength": 14, "agility": 14, "intellect": 14, "health": 115, "mana": 110},
        "color": 0xff7d0a
    }
}

RACES = {
    "human": {"name": "Human", "bonuses": {"strength": 2, "intellect": 2}},
    "elf": {"name": "Elf", "bonuses": {"agility": 3, "intellect": 2}},
    "dwarf": {"name": "Dwarf", "bonuses": {"strength": 3, "health": 10}},
    "orc": {"name": "Orc", "bonuses": {"strength": 4, "health": 5}},
    "undead": {"name": "Undead", "bonuses": {"intellect": 2, "mana": 10}},
    "tauren": {"name": "Tauren", "bonuses": {"strength": 2, "health": 15}}
}


class RPGCharacter:
    def __init__(self, user_id, guild_id, name, class_name, race, level=1):
        self.user_id = user_id
        self.guild_id = guild_id
        self.name = name
        self.class_name = class_name
        self.race = race
        self.level = level
        self.experience = 0

        # Calculate stats
        class_data = RPG_CLASSES[class_name]
        race_data = RACES[race]

        self.base_stats = class_data["base_stats"].copy()

        # Apply race bonuses
        for stat, bonus in race_data["bonuses"].items():
            if stat in self.base_stats:
                self.base_stats[stat] += bonus

        # Scale with level
        level_multiplier = 1 + (level - 1) * 0.1
        for stat in self.base_stats:
            self.base_stats[stat] = int(self.base_stats[stat] * level_multiplier)

        self.current_health = self.base_stats["health"]
        self.current_mana = self.base_stats["mana"]
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'guild_id': self.guild_id,
            'name': self.name,
            'class_name': self.class_name,
            'race': self.race,
            'level': self.level,
            'experience': self.experience,
            'base_stats': self.base_stats,
            'current_health': self.current_health,
            'current_mana': self.current_mana,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        char = cls(
            data['user_id'], data['guild_id'], data['name'],
            data['class_name'], data['race'], data['level']
        )
        char.experience = data['experience']
        char.base_stats = data['base_stats']
        char.current_health = data['current_health']
        char.current_mana = data['current_mana']
        char.created_at = datetime.fromisoformat(data['created_at'])
        return char

    def get_attack_power(self):
        return int(self.base_stats["strength"] * 1.5 + self.base_stats["agility"] * 0.5)

    def get_defense(self):
        return int(self.base_stats["strength"] * 0.5 + self.base_stats["agility"] * 1.2)

    def get_crit_chance(self):
        return int(self.base_stats["agility"] * 0.1 + self.level * 0.05)


# Views for Interactive Buttons
class ClassSelectionView(discord.ui.View):
    def __init__(self, character_name, race):
        super().__init__(timeout=300)
        self.character_name = character_name
        self.race = race
        self.selected_class = None

    @discord.ui.select(
        placeholder="Choose your class...",
        options=[
            discord.SelectOption(
                label=class_data["name"],
                description=class_data["description"][:100],
                emoji=class_data["icon"],
                value=class_key
            )
            for class_key, class_data in list(RPG_CLASSES.items())[:9]  # Discord limit
        ]
    )
    async def select_class(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_class = select.values[0]
        class_data = RPG_CLASSES[self.selected_class]

        embed = discord.Embed(
            title=f"✅ {class_data['name']} Selected!",
            description=f"**{self.character_name}** will be a {class_data['name']}",
            color=class_data["color"]
        )
        embed.add_field(
            name="Abilities",
            value=" • ".join(class_data["abilities"]),
            inline=False
        )

        await interaction.response.edit_message(embed=embed, view=CreateCharacterView(self.character_name, self.race,
                                                                                      self.selected_class))


class CreateCharacterView(discord.ui.View):
    def __init__(self, character_name, race, class_name):
        super().__init__(timeout=300)
        self.character_name = character_name
        self.race = race
        self.class_name = class_name

    @discord.ui.button(label="Create Character", style=discord.ButtonStyle.green, emoji="⚔️")
    async def create_character(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Here you would save to database
        character = RPGCharacter(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id,
            name=self.character_name,
            class_name=self.class_name,
            race=self.race
        )

        # Save character (implement your database save here)
        # character_dao.save_character(character)

        embed = discord.Embed(
            title="🎉 Character Created!",
            description=f"Welcome to Azeroth, **{character.name}**!",
            color=RPG_CLASSES[self.class_name]["color"]
        )

        embed.add_field(name="Class",
                        value=f"{RPG_CLASSES[self.class_name]['icon']} {RPG_CLASSES[self.class_name]['name']}",
                        inline=True)
        embed.add_field(name="Race", value=RACES[self.race]["name"], inline=True)
        embed.add_field(name="Level", value=character.level, inline=True)

        stats_text = "\n".join([
            f"❤️ Health: {character.current_health}/{character.base_stats['health']}",
            f"💙 Mana: {character.current_mana}/{character.base_stats['mana']}",
            f"💪 Strength: {character.base_stats['strength']}",
            f"🏃 Agility: {character.base_stats['agility']}",
            f"🧠 Intellect: {character.base_stats['intellect']}"
        ])
        embed.add_field(name="Stats", value=stats_text, inline=False)

        embed.add_field(
            name="Combat Stats",
            value=f"⚔️ Attack: {character.get_attack_power()}\n🛡️ Defense: {character.get_defense()}\n✨ Crit: {character.get_crit_chance()}%",
            inline=True
        )

        await interaction.response.edit_message(embed=embed, view=None)


class CharacterActionView(discord.ui.View):
    def __init__(self, character):
        super().__init__(timeout=300)
        self.character = character

    @discord.ui.button(label="Battle", style=discord.ButtonStyle.red, emoji="⚔️")
    async def battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        enemies = ["Goblin Scout", "Orc Warrior", "Skeleton Mage", "Forest Wolf", "Dark Cultist"]
        enemy = random.choice(enemies)

        # Simulate battle
        player_damage = random.randint(20, 50)
        enemy_damage = random.randint(10, 30)

        # Apply damage
        self.character.current_health = max(0, self.character.current_health - enemy_damage)

        if self.character.current_health > 0:
            exp_gain = random.randint(50, 100)
            self.character.experience += exp_gain

            embed = discord.Embed(
                title="⚔️ Battle Victory!",
                description=f"**{self.character.name}** defeated a {enemy}!",
                color=discord.Color.green()
            )
            embed.add_field(name="Damage Dealt", value=f"{player_damage} damage", inline=True)
            embed.add_field(name="Damage Taken", value=f"{enemy_damage} damage", inline=True)
            embed.add_field(name="Experience Gained", value=f"+{exp_gain} XP", inline=True)
            embed.add_field(name="Health",
                            value=f"{self.character.current_health}/{self.character.base_stats['health']}",
                            inline=False)

            # Chance for healing
            if random.random() < 0.3:
                healing = random.randint(10, 20)
                self.character.current_health = min(
                    self.character.base_stats['health'],
                    self.character.current_health + healing
                )
                embed.add_field(name="Recovery", value=f"Recovered {healing} health!", inline=False)
        else:
            embed = discord.Embed(
                title="💀 Defeat!",
                description=f"**{self.character.name}** was defeated by {enemy}!",
                color=discord.Color.red()
            )
            self.character.current_health = 1  # Prevent death

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Level Up", style=discord.ButtonStyle.green, emoji="📈")
    async def level_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.character.level += 1
        level_bonus = 1.1

        # Increase stats
        for stat in self.character.base_stats:
            self.character.base_stats[stat] = int(self.character.base_stats[stat] * level_bonus)

        # Restore health and mana
        self.character.current_health = self.character.base_stats['health']
        self.character.current_mana = self.character.base_stats['mana']

        embed = discord.Embed(
            title="📈 Level Up!",
            description=f"**{self.character.name}** reached level {self.character.level}!",
            color=discord.Color.gold()
        )
        embed.add_field(name="All stats increased!", value="Health and Mana restored!", inline=False)

        await interaction.response.edit_message(embed=embed, view=self)


# Main RPG Cog
class RPG(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        # In real implementation, you'd use a proper database
        self.characters = {}  # {user_id: character_data}

    @app_commands.command(name="rpg-create", description="Create your RPG character")
    async def create_character(self, interaction: discord.Interaction, name: str, race: str):
        if race.lower() not in RACES:
            race_list = ", ".join(RACES.keys())
            await interaction.response.send_message(
                f"Invalid race! Choose from: {race_list}", ephemeral=True
            )
            return

        if len(name) > 20:
            await interaction.response.send_message(
                "Character name must be 20 characters or less!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎮 Character Creation",
            description=f"Creating character **{name}** ({RACES[race.lower()]['name']})\n\nChoose your class:",
            color=discord.Color.blue()
        )

        view = ClassSelectionView(name, race.lower())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="rpg-character", description="View your RPG character")
    async def view_character(self, interaction: discord.Interaction):
        # In real implementation, fetch from database
        user_key = f"{interaction.user.id}_{interaction.guild.id}"

        if user_key not in self.characters:
            await interaction.response.send_message(
                "You don't have a character yet! Use `/rpg-create` to make one.", ephemeral=True
            )
            return

        character = self.characters[user_key]
        class_data = RPG_CLASSES[character.class_name]

        embed = discord.Embed(
            title=f"⚔️ {character.name}",
            description=f"Level {character.level} {class_data['name']} ({RACES[character.race]['name']})",
            color=class_data["color"]
        )

        stats_text = "\n".join([
            f"❤️ Health: {character.current_health}/{character.base_stats['health']}",
            f"💙 Mana: {character.current_mana}/{character.base_stats['mana']}",
            f"💪 Strength: {character.base_stats['strength']}",
            f"🏃 Agility: {character.base_stats['agility']}",
            f"🧠 Intellect: {character.base_stats['intellect']}"
        ])
        embed.add_field(name="Stats", value=stats_text, inline=True)

        combat_text = f"⚔️ Attack: {character.get_attack_power()}\n🛡️ Defense: {character.get_defense()}\n✨ Crit: {character.get_crit_chance()}%"
        embed.add_field(name="Combat", value=combat_text, inline=True)

        embed.add_field(name="Experience", value=f"{character.experience} XP", inline=True)

        abilities_text = " • ".join(class_data["abilities"])
        embed.add_field(name="Abilities", value=abilities_text, inline=False)

        view = CharacterActionView(character)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="rpg-classes", description="View all available RPG classes")
    async def view_classes(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚔️ Available Classes",
            description="Choose your path in Azeroth:",
            color=discord.Color.gold()
        )

        for class_key, class_data in RPG_CLASSES.items():
            embed.add_field(
                name=f"{class_data['icon']} {class_data['name']}",
                value=f"{class_data['description'][:100]}...",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rpg-leaderboard", description="View server RPG leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        # In real implementation, query database for top characters
        guild_characters = [
            char for char in self.characters.values()
            if char.guild_id == interaction.guild.id
        ]

        if not guild_characters:
            await interaction.response.send_message("No characters in this server yet!")
            return

        # Sort by level, then by experience
        guild_characters.sort(key=lambda x: (x.level, x.experience), reverse=True)

        embed = discord.Embed(
            title="🏆 RPG Leaderboard",
            description=f"Top adventurers in {interaction.guild.name}",
            color=discord.Color.gold()
        )

        for i, char in enumerate(guild_characters[:10], 1):
            user = self.bot.get_user(char.user_id)
            username = user.display_name if user else "Unknown User"

            embed.add_field(
                name=f"{i}. {char.name}",
                value=f"Level {char.level} {RPG_CLASSES[char.class_name]['name']} • {username}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(RPG(bot))
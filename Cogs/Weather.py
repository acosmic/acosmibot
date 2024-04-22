import discord
from discord.ext import commands
from discord import app_commands
from logger import AppLogger
import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta


logging = AppLogger(__name__).get_logger()


class Weather(commands.Cog):
    def __init__(self, bot:commands.Bot):
        super().__init__()
        self.bot = bot
        load_dotenv()
        self.WEATHER_KEY = os.getenv('WEATHER_KEY')
        # self.URL = f"https://api.openweathermap.org/data/2.5/weather?q={cityname}&appid={self.WEATHER_KEY}"
        self.EMOJI = {
            "Thunderstorm": "⛈️",
            "Drizzle": "🌧️",
            "Rain": "🌧️",
            "Snow": "❄️",
            "Clear": "☀️",
            "Clouds": "☁️",
            "Mist": "🌫️",
            "Smoke": "🌫️",
            "Haze": "🌫️",
            "Dust": "🌫️",
            "Fog": "🌫️",
            "Sand": "🌫️",
            "Ash": "🌫️",
            "Squall": "🌫️",
            "Tornado": "🌪️"
        }
        

    @app_commands.command(name = "weather", description = "Returns the current weather in a city.")
    async def weather(self, interaction: discord.Interaction, cityname: str):
        
        response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={cityname}&appid={self.WEATHER_KEY}")
        data = response.json()
        if data["cod"] != "404":
            main = data["main"]
            temperature = main["temp"]
            temperature = round(temperature - 273.15)
            temp_farhenheit = round(temperature * 9/5) + 32
            feels_like = main["feels_like"]
            feels_like = round(feels_like - 273.15)
            feels_like_farhenheit = round(feels_like * 9/5) + 32
            humidity = main["humidity"]
            weather = data["weather"]
            weather_description = weather[0]["description"]
            weather_icon = weather[0]["main"]
            weather_emoji = self.EMOJI[weather_icon]
            
            # Time zone handling
            timezone_offset = data["timezone"]  # Timezone offset in seconds
            local_time = datetime.utcnow() + timedelta(seconds=timezone_offset)
            formatted_time = local_time.strftime('%l:%M:%S %p')

            state = data["sys"]["country"]
            embed = discord.Embed(title=f"Weather in {cityname}", color=interaction.user.color)
            embed.add_field(name="Temperature", value=f"{temp_farhenheit}°F   |   {temperature}°C", inline=False)
            embed.add_field(name="Feels Like", value=f"{feels_like_farhenheit}°F   |   {feels_like}°C", inline=False)
            embed.add_field(name="Humidity", value=f"{humidity}%", inline=False)
            embed.add_field(name="Weather", value=f"{weather_emoji} {weather_description}", inline=False)
            embed.add_field(name="Local Time", value=formatted_time, inline=False)
            embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{weather[0]['icon']}.png")
            await interaction.response.send_message(embed=embed)
            logging.info(f"{interaction.user.name} used /weather {cityname}")
        else:
            await interaction.response.send_message(f"City not found.", ephemeral=True)
            logging.info(f"{interaction.user.name} used /weather {cityname} but city was not found.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Weather(bot))
    
# Acosmibot [![CircleCI](https://dl.circleci.com/status-badge/img/circleci/9DNxHekn5QTS3HbsddJyPc/FYkBYsR7VBRrd9oLzsq4AK/tree/master.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/circleci/9DNxHekn5QTS3HbsddJyPc/FYkBYsR7VBRrd9oLzsq4AK/tree/master)
## A Discord bot created to promote community engagement
Built with Python | Discord.py | MySQL | CircleCI


---

## Table of Contents
- [Features](#features)
- [Slash Commands](#slash-commands)
- [Setup](#setup)
- [License](#license)
- [Screenshots](#screenshots)

---

## Features

### Slash Commands and Participation-Based Leveling
- **Slash Commands**: Execute commands using the slash (`/`) command syntax.
- **Leveling and XP Points**: Gain XP points through chatting and using commands to level up.
- **Auto-Applied Discord Roles**: Automatically apply roles upon leveling up.
- **Leaderboards**: Display leaderboards for various achievements.

### Economy and Gambling System
- **Economy System**: A fake currency system using "Credits".
- **Solo Gambling**: Gamble with fake currency.
- **Weekly Lottery**: Participate in a weekly lottery for a chance to recover lost "Credits".
- **Player vs Player Games**: Engage in betting games with other players using dynamic buttons.

### API Integrations and Notifications
- **Twitch API**: Receive go-live notifications for Twitch streams.
- **NASA Astronomy Picture of the Day**: Get daily images from NASA's Astronomy Picture of the Day.
- **OpenWeather API**: Fetch current weather data.
- **Giphy API**: Integrate GIFs into your Discord server.
- **OpenAI Chat API**: Chat with an AI powered by OpenAI's language model.

### Member Stats and Tracking
- **Member Stats**: Track member stats such as active days, messages sent, reactions, and game stats (wins, losses, etc.).


## Slash Commands
- **/8ball `[question]`** - _Ask the magic 8ball your yes/no questions for 10 Credits._
- **/apod** - _Returns the Astronomy Picture of the Day._
- **/balance `[user (optional)]`** - _Check your Credit balance or mention another user to see their balance._
- **/checkvault** - _Check the amount of Credits in the vault!_
- **/coinflip `[call]` `[bet]`** - _Flip a coin for a chance to win credits._
- **/deathroll `[target]` `[bet]`** - _Start a game of Deathroll. First person to roll a 1 loses!_
- **/giphy `[search_term]`** - _Returns a random Gif from Giphy based on the search term provided. Example: /giphy cat._
- **/give `[target]` `[amount]`** - _Give Credits to your target user._
- **/help** - _Returns a list of commands._
- **/leaderboard `[stat]`** - _Returns top 5 users by Credits based on Currency, EXP, etc._
- **/ping** - _Returns the bot's latency._
- **/polymorph `[target]` `[rename]`** - _Change your target's display name for 1000 Credits... please be nice._
- **/rank `[user (optional)]`** - _Returns your rank based on current EXP or mention another user to see their rank._
- **/rockpaperscissors `[target]` `[bet]`** - _Challenge another member to a game of Rock, Paper, Scissors. Win 3 rounds!_
- **/stats `[user (optional)]`** - _Leave blank to see your own stats, or mention another user to see their stats._
- **/weather `[cityname]`** - _Returns the current weather in a city._

## Setup
1. **Clone the repository**:
   ```sh
   git clone https://github.com/acosmic/acosmibot.git
   cd acosmibot

2. **Install dependencies**:
   ```sh
   pip3 install -r requirements.txt

3. **Set up environment variables** -
   Create a '.env' file in the root directory and add the following:
   ```makefile
   # MySql Database
   DB_HOST=your_host
   DB_USER=your_user
   DB_PASSWORD=your_password
   DB_NAME=your_dbname
   
   # Discord
   CLIENT_ID=
   CLIENT_SECRET=
   TOKEN=
   MY_GUILD=

   # OpenAI
   OPENAI_KEY=
   ASSISTANT_KEY=

4. **Run the bot**:
   ```sh
   python3 bot.py

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Screenshots
![Coinflip](https://github.com/acosmic/acosmibot/assets/55600182/04d2fafd-2f59-4f9f-8752-ecd00591586b)

![Deathroll](https://github.com/acosmic/acosmibot/assets/55600182/8ba4b60b-58a4-4457-a60d-e9d0e2b6d394)

![Deathroll2](https://github.com/acosmic/acosmibot/assets/55600182/cac9cd0d-e38b-4c44-a601-a61595f01132)

![RPS](https://github.com/acosmic/acosmibot/assets/55600182/fa126bdb-5a41-45b4-9035-9cbbf3cec7bf)

![RPS2](https://github.com/acosmic/acosmibot/assets/55600182/d871387b-6be9-4924-b7df-1e68a4f200ea)

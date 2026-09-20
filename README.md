<div align="center"><img src="./assets/lumipyx.png" width="128" alt="LumiPyx Logo">✦ LumiPyx ✦

A tiny Discord bot built with Python & curiosity. 💜

<br><img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/discord.py-2.x-5865F2?style=for-the-badge&logo=discord&logoColor=white">
<img src="https://img.shields.io/badge/Data-JSON-000000?style=for-the-badge&logo=json&logoColor=white"><br><br>

<img src="https://img.shields.io/badge/Status-Hobby%20Project-9B59B6?style=flat-square">
<img src="https://img.shields.io/badge/Made%20with-Neovim-57A143?style=flat-square&logo=neovim&logoColor=white"></div>---

🌙 About

LumiPyx is a personal Discord bot written in Python using ""discord.py"" (https://discordpy.readthedocs.io/).

What started as a simple project for learning Discord bot development gradually turned into a collection of moderation, utility, and experimental features.

«💭 Build → break → fix → learn → repeat.»

LumiPyx is primarily a hobby and learning project.
The codebase and features will continue to evolve as I learn more.

---

✨ Features

<div align="center">🧩 Command| 📖 Description
"/avatar"| View a user's avatar
"/afk"| Set an AFK status
"/kick"| Kick a member
"/ban"| Ban a member
"/unban"| Unban a user
"/timeout"| Timeout a member
"/untimeout"| Remove a timeout
"/purge"| Delete recent messages
"/setlog"| Configure moderation logs

</div>---

🛠️ Built With

<div align="center"><img src="https://skillicons.dev/icons?i=python,json,neovim" height="64" alt="Python, JSON and Neovim"><br><br>

Technology| Purpose
🐍 Python| Main programming language
🤖 discord.py| Discord API wrapper
📄 JSON| Persistent data storage
💚 Neovim| Development environment

</div>---

📁 Project Structure

LumiPyx/
│
├── 🐍 bot.py
├── 📄 settings.json
├── 📄 afk.json
│
├── 🖼️ assets/
│   └── lumipyx.png
│
└── 📖 README.md

---

💾 Data Storage

LumiPyx currently uses JSON for persistent data.

It's simple, lightweight, and fits the current scope of the project.

                    LumiPyx
                       │
              ┌────────┴────────┐
              ▼                 ▼
       Server Settings       AFK Data
              │                 │
              ▼                 ▼
       settings.json       afk.json

A migration to SQLite may happen later if the project grows enough to benefit from a database.

---

🚧 Roadmap

- [x] Moderation commands
- [x] AFK system
- [x] Moderation logs
- [x] Server configuration
- [ ] Automated tasks
- [ ] Welcome system
- [ ] Automatic roles
- [ ] More AutoMod features
- [ ] Music playback 🎧
- [ ] YouTube integration
- [ ] SQLite migration

---

🎧 Experimental Ideas

Music playback is one of the features I'd like to experiment with in the future.

A possible architecture could look something like this:

        YouTube
           │
           ▼
   Search / Metadata
           │
           ▼
      Audio Source
           │
           ▼
    Discord Voice
           │
           ▼
        🔊 🎵

This is currently an experimental idea, not an implemented feature.

---

💜 Project Philosophy

LumiPyx isn't trying to be the biggest Discord bot.

It's a small project where I can experiment with things I want to learn.

Sometimes that means building something useful.

Sometimes it means building something completely unnecessary because it sounds fun.

Both count. :3

---

📜 License

LumiPyx is a personal hobby project.

The source code is publicly available for viewing, but no permission is granted to modify, redistribute, or commercially use the project without permission from the copyright holder.

See ""LICENSE"" (./LICENSE) for the full terms.

---

<div align="center"><img src="./assets/lumipyx.png" width="64" alt="LumiPyx Logo">Made with 🐍 Python, 💚 Neovim & a questionable amount of curiosity.

<br>"learning" · "experimenting" · "building"

</div>
<div align="center"><img src="./assets/lumipyx.png" width="120" alt="LumiPyx Logo">✦ LumiPyx ✦

A tiny Discord bot built with Python & curiosity. 💜

<img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/discord.py-2.x-5865F2?style=for-the-badge&logo=discord&logoColor=white">
<img src="https://img.shields.io/badge/Data-JSON-000000?style=for-the-badge&logo=json&logoColor=white"><br><br>

""GitHub" (https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white)" (https://github.com/)
""Made with Python" (https://img.shields.io/badge/Made%20with-Python-3776AB?style=flat-square&logo=python&logoColor=white)" (https://www.python.org/)

</div>---

🌙 About

LumiPyx is a personal Discord bot project written in Python using ""discord.py"" (https://discordpy.readthedocs.io/).

It started as a way to learn Discord bot development and gradually grew into a collection of moderation, utility, and experimental features.

«💭 Build → break → fix → learn → repeat.»

This is primarily a hobby and learning project, so the architecture and features are expected to evolve over time.

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

<div align="center"><img src="https://skillicons.dev/icons?i=python,json,neovim" height="64"><br><br>

Technology| Purpose
🐍 Python| Main programming language
🤖 discord.py| Discord API wrapper
📄 JSON| Persistent data storage
💚 Neovim| Development environment

</div>---

📁 Structure

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

💾 Storage

For now, LumiPyx uses JSON files for persistent data.

This keeps the project simple while I'm learning.

Server
  │
  ├── Settings ──────► settings.json
  │
  └── AFK data ──────► afk.json

A move to SQLite may happen later if the project becomes large enough to need it.

---

🚧 Roadmap

- [x] Moderation commands
- [x] AFK system
- [x] Moderation logs
- [x] Server configuration
- [ ] Automated tasks
- [ ] Welcome system
- [ ] Auto roles
- [ ] More AutoMod features
- [ ] Music playback 🎧
- [ ] YouTube integration
- [ ] SQLite migration

---

🎧 Experimental Ideas

One of the things I'd like to experiment with is music playback.

Potential architecture:

YouTube
   │
   ▼
Search / Metadata
   │
   ▼
Audio source
   │
   ▼
Discord Voice
   │
   ▼
🔊 🎵

This is currently just an experiment idea, not a finished feature.

---

💜 Project Philosophy

LumiPyx isn't trying to be the biggest Discord bot.

It's a place to experiment with things I want to learn.

Sometimes that means writing something useful.

Sometimes it means writing something completely unnecessary because it sounds fun.

Both count.

---

<div align="center"><img src="./assets/lumipyx.png" width="64" alt="LumiPyx">Made with 🐍 Python, 💚 Neovim & a questionable amount of curiosity.

<br>"learning" · "experimenting" · "building"

</div>
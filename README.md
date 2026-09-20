<p align="center">
  <strong>LumiPy</strong>
</p><p align="center">
  A Discord bot built with Python and <code>discord.py</code>, created as a personal learning project.
</p><p align="center">
  <img src="https://skillicons.dev/icons?i=python,json,neovim" alt="Python, JSON, and Neovim">
</p>About

LumiPy is a personal Discord bot project focused on moderation, server utilities, persistent configuration, and experimentation with Discord's application-command system.

The project is primarily built to learn more about Python, asynchronous programming, APIs, Discord bots, and software architecture.

Features

- Slash commands
- Member moderation
- Permission validation
- Role hierarchy checks
- Moderation logging
- AFK system
- Avatar lookup
- Message purging
- Persistent JSON storage
- Configurable moderation log channels

Commands

- "/avatar" - Display a user's avatar
- "/afk" - Set an AFK status
- "/kick" - Kick a member
- "/ban" - Ban a member
- "/unban" - Unban a user by ID
- "/timeout" - Timeout a member
- "/untimeout" - Remove a member's timeout
- "/purge" - Delete recent messages
- "/setlog" - Configure the moderation log channel

Architecture

The project uses reusable helper functions for common operations such as:

- Permission validation
- Target validation
- JSON persistence
- Moderation logging
- Discord error handling

This keeps individual commands easier to maintain and avoids unnecessary repetition.

Roadmap

- [x] Slash-command system
- [x] Moderation commands
- [x] Permission checks
- [x] Moderation logging
- [x] JSON persistence
- [ ] Automated welcome and goodbye messages
- [ ] Auto-role system
- [ ] Scheduled messages
- [ ] Automatic cleanup
- [ ] Additional server utilities
- [ ] Advanced automation
- [ ] Experimental music functionality

Future Experiments

Music playback is one of the features I may experiment with in the future.

Possible components include:

- Search and metadata handling
- Audio source handling
- Voice channel integration
- Queue management
- Playback controls

This is currently an experimental idea rather than an implemented feature.

Project Status

LumiPy is primarily a learning project.

The codebase is being developed incrementally while I learn more about:

- Python
- "discord.py"
- Asynchronous programming
- APIs
- Data persistence
- Software architecture

It is not currently intended to be a large-scale public Discord bot.

Development

The project is developed locally using Neovim.

Features are added incrementally as new concepts are learned and different approaches are experimented with.

License

https://github.com/kolbyxxf/LumiPyx/blob/main/LICENSE
GPL-3.0

Author

Icel

Built with Python, "discord.py", JSON, and Neovim.
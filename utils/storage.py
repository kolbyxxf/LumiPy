import aiosqlite
import json

DB_FILE = "bot.db"
_db: aiosqlite.Connection | None = None

async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_FILE)
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA synchronous=NORMAL")
    return _db

async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            guild_id TEXT PRIMARY KEY, log_channel INTEGER, automod_config TEXT, security_config TEXT
        );
        CREATE TABLE IF NOT EXISTS afk (
            guild_id TEXT, user_id TEXT, reason TEXT, PRIMARY KEY (guild_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS welcome (guild_id TEXT PRIMARY KEY, channel_id INTEGER);
        CREATE TABLE IF NOT EXISTS goodbye (guild_id TEXT PRIMARY KEY, channel_id INTEGER);
        CREATE TABLE IF NOT EXISTS autoroles (guild_id TEXT, role_id TEXT, PRIMARY KEY (guild_id, role_id));
        CREATE TABLE IF NOT EXISTS reaction_roles (
            message_id TEXT, guild_id TEXT, channel_id TEXT, emoji TEXT, role_id TEXT, PRIMARY KEY (message_id, emoji)
        );
        CREATE TABLE IF NOT EXISTS dropdown_roles (
            message_id TEXT PRIMARY KEY, guild_id TEXT, channel_id TEXT, roles TEXT
        );
        CREATE TABLE IF NOT EXISTS warning_configs (guild_id TEXT PRIMARY KEY, ban_threshold INTEGER);
        CREATE TABLE IF NOT EXISTS warnings (
            guild_id TEXT, user_id TEXT, warn_id INTEGER, moderator_id TEXT, reason TEXT, timestamp INTEGER,
            PRIMARY KEY (guild_id, user_id, warn_id)
        );
        CREATE TABLE IF NOT EXISTS level_configs (guild_id TEXT PRIMARY KEY, role_rewards TEXT);
        CREATE TABLE IF NOT EXISTS levels (guild_id TEXT, user_id TEXT, xp INTEGER, PRIMARY KEY (guild_id, user_id));
        CREATE TABLE IF NOT EXISTS tickets (
            channel_id TEXT PRIMARY KEY, guild_id TEXT, owner_id TEXT, owner_name TEXT, 
            status TEXT, created_at TEXT, closed_at TEXT
        );
    """)
    await db.commit()

# ─────────────────────────────────────────────────────────────
# SETTINGS (Log, AutoMod, Security)
# ─────────────────────────────────────────────────────────────
async def get_log_channel(guild_id: str) -> int | None:
    db = await get_db()
    async with db.execute("SELECT log_channel FROM settings WHERE guild_id = ?", (guild_id,)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row and row[0] is not None else None

async def set_log_channel(guild_id: str, channel_id: int):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO settings (guild_id, log_channel) VALUES (?, ?)", (guild_id, channel_id))
    await db.commit()

async def get_automod_config(guild_id: str) -> dict | None:
    db = await get_db()
    async with db.execute("SELECT automod_config FROM settings WHERE guild_id = ?", (guild_id,)) as cursor:
        row = await cursor.fetchone()
        return json.loads(row[0]) if row and row[0] else None

async def set_automod_config(guild_id: str, config: dict):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO settings (guild_id, automod_config) VALUES (?, ?)", (guild_id, json.dumps(config)))
    await db.commit()

async def get_security_config(guild_id: str) -> dict | None:
    db = await get_db()
    async with db.execute("SELECT security_config FROM settings WHERE guild_id = ?", (guild_id,)) as cursor:
        row = await cursor.fetchone()
        return json.loads(row[0]) if row and row[0] else None

async def set_security_config(guild_id: str, config: dict):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO settings (guild_id, security_config) VALUES (?, ?)", (guild_id, json.dumps(config)))
    await db.commit()

# ─────────────────────────────────────────────────────────────
# AFK
# ─────────────────────────────────────────────────────────────
async def load_afk() -> dict:
    db = await get_db()
    data = {}
    async with db.execute("SELECT guild_id, user_id, reason FROM afk") as cursor:
        async for row in cursor: data.setdefault(row[0], {})[row[1]] = row[2]
    return data

async def set_afk(guild_id: str, user_id: str, reason: str):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO afk (guild_id, user_id, reason) VALUES (?, ?, ?)", (guild_id, user_id, reason))
    await db.commit()

async def clear_afk(guild_id: str, user_id: str):
    db = await get_db()
    await db.execute("DELETE FROM afk WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    await db.commit()

# ─────────────────────────────────────────────────────────────
# WELCOME / GOODBYE
# ─────────────────────────────────────────────────────────────
async def get_welcome_channel(guild_id: str) -> int | None:
    db = await get_db()
    async with db.execute("SELECT channel_id FROM welcome WHERE guild_id = ?", (guild_id,)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else None

async def set_welcome_channel(guild_id: str, channel_id: int):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO welcome (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
    await db.commit()

async def get_goodbye_channel(guild_id: str) -> int | None:
    db = await get_db()
    async with db.execute("SELECT channel_id FROM goodbye WHERE guild_id = ?", (guild_id,)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else None

async def set_goodbye_channel(guild_id: str, channel_id: int):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO goodbye (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
    await db.commit()

# ─────────────────────────────────────────────────────────────
# AUTOROLES
# ─────────────────────────────────────────────────────────────
async def get_autoroles(guild_id: str) -> list[int]:
    db = await get_db()
    async with db.execute("SELECT role_id FROM autoroles WHERE guild_id = ?", (guild_id,)) as cursor:
        return [int(row[0]) async for row in cursor]

async def add_autorole(guild_id: str, role_id: int):
    db = await get_db()
    await db.execute("INSERT OR IGNORE INTO autoroles (guild_id, role_id) VALUES (?, ?)", (guild_id, str(role_id)))
    await db.commit()

async def remove_autorole(guild_id: str, role_id: int):
    db = await get_db()
    await db.execute("DELETE FROM autoroles WHERE guild_id = ? AND role_id = ?", (guild_id, str(role_id)))
    await db.commit()

# ─────────────────────────────────────────────────────────────
# REACTION ROLES
# ─────────────────────────────────────────────────────────────
async def load_reaction_roles() -> dict:
    db = await get_db()
    data = {}
    async with db.execute("SELECT message_id, guild_id, channel_id, emoji, role_id FROM reaction_roles") as cursor:
        async for row in cursor:
            msg_id, guild_id, channel_id, emoji, role_id = row
            if msg_id not in data: data[msg_id] = {"guild_id": int(guild_id), "channel_id": int(channel_id), "roles": {}}
            data[msg_id]["roles"][emoji] = int(role_id)
    return data

async def set_reaction_role(message_id: str, guild_id: int, channel_id: int, emoji: str, role_id: int):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO reaction_roles (message_id, guild_id, channel_id, emoji, role_id) VALUES (?, ?, ?, ?, ?)",
                     (message_id, str(guild_id), str(channel_id), emoji, str(role_id)))
    await db.commit()

async def remove_reaction_role(message_id: str, emoji: str):
    db = await get_db()
    await db.execute("DELETE FROM reaction_roles WHERE message_id = ? AND emoji = ?", (message_id, emoji))
    await db.commit()

async def clear_reaction_roles(message_id: str):
    db = await get_db()
    await db.execute("DELETE FROM reaction_roles WHERE message_id = ?", (message_id,))
    await db.commit()

# ─────────────────────────────────────────────────────────────
# DROPDOWN ROLES
# ─────────────────────────────────────────────────────────────
async def load_dropdown_roles() -> dict:
    db = await get_db()
    data = {}
    async with db.execute("SELECT message_id, guild_id, channel_id, roles FROM dropdown_roles") as cursor:
        async for row in cursor:
            msg_id, guild_id, channel_id, roles_json = row
            data[msg_id] = {"guild_id": int(guild_id), "channel_id": int(channel_id), "roles": json.loads(roles_json) if roles_json else []}
    return data

async def set_dropdown_role(message_id: str, guild_id: int, channel_id: int, roles: list[dict]):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO dropdown_roles (message_id, guild_id, channel_id, roles) VALUES (?, ?, ?, ?)",
                     (message_id, str(guild_id), str(channel_id), json.dumps(roles)))
    await db.commit()

async def remove_dropdown_role(message_id: str):
    db = await get_db()
    await db.execute("DELETE FROM dropdown_roles WHERE message_id = ?", (message_id,))
    await db.commit()

# ─────────────────────────────────────────────────────────────
# WARNINGS
# ─────────────────────────────────────────────────────────────
async def get_warnings(guild_id: str, user_id: str) -> list[dict]:
    db = await get_db()
    warns = []
    async with db.execute("SELECT warn_id, moderator_id, reason, timestamp FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
        async for row in cursor:
            warns.append({"id": row[0], "moderator_id": int(row[1]), "reason": row[2], "timestamp": row[3]})
    return warns

async def add_warning(guild_id: str, user_id: str, warning: dict):
    db = await get_db()
    await db.execute("INSERT INTO warnings (guild_id, user_id, warn_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                     (guild_id, user_id, warning["id"], str(warning["moderator_id"]), warning["reason"], warning["timestamp"]))
    await db.commit()

async def remove_warning(guild_id: str, user_id: str, warn_id: int):
    db = await get_db()
    await db.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ? AND warn_id = ?", (guild_id, user_id, warn_id))
    await db.commit()

async def clear_warnings(guild_id: str, user_id: str):
    db = await get_db()
    await db.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    await db.commit()

async def get_ban_threshold(guild_id: str) -> int:
    db = await get_db()
    async with db.execute("SELECT ban_threshold FROM warning_configs WHERE guild_id = ?", (guild_id,)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row and row[0] is not None else 5

async def set_ban_threshold(guild_id: str, threshold: int):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO warning_configs (guild_id, ban_threshold) VALUES (?, ?)", (guild_id, threshold))
    await db.commit()

# ─────────────────────────────────────────────────────────────
# LEVELS
# ─────────────────────────────────────────────────────────────
async def get_user_xp(guild_id: str, user_id: str) -> int:
    db = await get_db()
    async with db.execute("SELECT xp FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0

async def set_user_xp(guild_id: str, user_id: str, xp: int):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO levels (guild_id, user_id, xp) VALUES (?, ?, ?)", (guild_id, user_id, xp))
    await db.commit()

async def get_guild_xp(guild_id: str) -> dict[int, int]:
    db = await get_db()
    result = {}
    async with db.execute("SELECT user_id, xp FROM levels WHERE guild_id = ?", (guild_id,)) as cursor:
        async for row in cursor: result[int(row[0])] = row[1]
    return result

async def get_role_rewards(guild_id: str) -> dict[int, int]:
    db = await get_db()
    async with db.execute("SELECT role_rewards FROM level_configs WHERE guild_id = ?", (guild_id,)) as cursor:
        row = await cursor.fetchone()
        if row and row[0]: return {int(k): int(v) for k, v in json.loads(row[0]).items()}
        return {}

async def set_role_reward(guild_id: str, level: int, role_id: int):
    rewards = await get_role_rewards(guild_id)
    rewards[level] = role_id
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO level_configs (guild_id, role_rewards) VALUES (?, ?)", (guild_id, json.dumps({str(k): v for k, v in rewards.items()})))
    await db.commit()

async def remove_role_reward(guild_id: str, level: int):
    rewards = await get_role_rewards(guild_id)
    if level in rewards:
        del rewards[level]
        db = await get_db()
        await db.execute("INSERT OR REPLACE INTO level_configs (guild_id, role_rewards) VALUES (?, ?)", (guild_id, json.dumps({str(k): v for k, v in rewards.items()})))
        await db.commit()

# ─────────────────────────────────────────────────────────────
# TICKETS
# ─────────────────────────────────────────────────────────────
async def load_tickets() -> dict:
    db = await get_db()
    data = {}
    async with db.execute("SELECT channel_id, guild_id, owner_id, owner_name, status, created_at, closed_at FROM tickets") as cursor:
        async for row in cursor:
            data[row[0]] = {"guild_id": int(row[1]), "channel_id": int(row[0]), "owner_id": int(row[2]), "owner_name": row[3], "status": row[4], "created_at": row[5], "closed_at": row[6]}
    return data

async def set_ticket(channel_id: str, info: dict):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO tickets (channel_id, guild_id, owner_id, owner_name, status, created_at, closed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (channel_id, str(info["guild_id"]), str(info["owner_id"]), info["owner_name"], info["status"], info["created_at"], info.get("closed_at")))
    await db.commit()

async def remove_ticket(channel_id: str):
    db = await get_db()
    await db.execute("DELETE FROM tickets WHERE channel_id = ?", (channel_id,))
    await db.commit()
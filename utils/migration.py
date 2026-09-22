import json
import os
from utils import storage

async def run_migration():
    """Idempotently migrates legacy JSON files to SQLite without modifying the original files."""
    if not os.path.exists("settings.json") and not os.path.exists("afk.json"):
        return

    print("🔄 Running idempotent legacy JSON migration...")
    
    if os.path.exists("settings.json"):
        try:
            with open("settings.json", "r", encoding="utf-8") as f: data = json.load(f)
            for guild_id, guild_data in data.items():
                if isinstance(guild_data, dict):
                    if "log_channel" in guild_data: await storage.set_log_channel(str(guild_id), guild_data["log_channel"])
                    if "automod" in guild_data: await storage.set_automod_config(str(guild_id), guild_data["automod"])
                    if "security" in guild_data: await storage.set_security_config(str(guild_id), guild_data["security"])
                elif isinstance(guild_data, int): 
                    await storage.set_log_channel(str(guild_id), guild_data)
        except Exception as e: print(f"❌ Error migrating settings.json: {e}")

    if os.path.exists("afk.json"):
        try:
            with open("afk.json", "r", encoding="utf-8") as f: data = json.load(f)
            for guild_id, users in data.items():
                if isinstance(users, dict):
                    for user_id, reason in users.items():
                        if isinstance(reason, str): await storage.set_afk(str(guild_id), str(user_id), reason)
        except Exception as e: print(f"❌ Error migrating afk.json: {e}")

    for filename, setter in [("welcome.json", storage.set_welcome_channel), ("goodbye.json", storage.set_goodbye_channel)]:
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f: data = json.load(f)
                for guild_id, channel_id in data.items(): await setter(str(guild_id), channel_id)
            except Exception as e: print(f"❌ Error migrating {filename}: {e}")

    if os.path.exists("autorole.json"):
        try:
            with open("autorole.json", "r", encoding="utf-8") as f: data = json.load(f)
            for guild_id, roles in data.items():
                for role_id in roles: await storage.add_autorole(str(guild_id), role_id)
        except Exception as e: print(f"❌ Error migrating autorole.json: {e}")

    if os.path.exists("warnings.json"):
        try:
            with open("warnings.json", "r", encoding="utf-8") as f: data = json.load(f)
            for guild_id, guild_data in data.items():
                if "config" in guild_data and "ban_threshold" in guild_data["config"]:
                    await storage.set_ban_threshold(str(guild_id), guild_data["config"]["ban_threshold"])
                for user_id, warns in guild_data.items():
                    if user_id != "config" and isinstance(warns, list):
                        for w in warns: await storage.add_warning(str(guild_id), str(user_id), w)
        except Exception as e: print(f"❌ Error migrating warnings.json: {e}")

    if os.path.exists("levels.json"):
        try:
            with open("levels.json", "r", encoding="utf-8") as f: data = json.load(f)
            for guild_id, guild_data in data.items():
                if "config" in guild_data and "role_rewards" in guild_data["config"]:
                    for lvl, rid in guild_data["config"]["role_rewards"].items(): await storage.set_role_reward(str(guild_id), int(lvl), rid)
                for user_id, user_data in guild_data.items():
                    if user_id != "config" and isinstance(user_data, dict) and "xp" in user_data:
                        await storage.set_user_xp(str(guild_id), str(user_id), user_data["xp"])
        except Exception as e: print(f"❌ Error migrating levels.json: {e}")

    print("✅ Legacy migration complete. Original JSON files were preserved.")
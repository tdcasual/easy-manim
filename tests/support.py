from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.config import Settings


def bootstrapped_settings(settings: Settings) -> Settings:
    SQLiteBootstrapper(settings.database_path).bootstrap()
    return settings

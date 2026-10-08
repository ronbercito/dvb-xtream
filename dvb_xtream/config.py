from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    admin_key: str
    public_url: str
    tvh_base_url: str
    tvh_username: str
    tvh_password: str
    tvh_stream_profile: str


def get_settings() -> Settings:
    return Settings(
        database_path=Path(os.getenv("DVB_XTREAM_DB", "/var/lib/dvb-xtream/data.sqlite3")),
        admin_key=os.getenv("DVB_XTREAM_ADMIN_KEY", ""),
        public_url=os.getenv("DVB_XTREAM_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/"),
        tvh_base_url=os.getenv("TVH_BASE_URL", "http://127.0.0.1:9981").rstrip("/"),
        tvh_username=os.getenv("TVH_USERNAME", ""),
        tvh_password=os.getenv("TVH_PASSWORD", ""),
        tvh_stream_profile=os.getenv("TVH_STREAM_PROFILE", "pass").strip(),
    )


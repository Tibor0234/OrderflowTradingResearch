import sqlite3

from data_managers.news.utils import NewsMessage
from global_services.data.provider import DataProvider


class DBNewsAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path
        self._create_schema()

    def _create_schema(self):
        """Create the sqlite database and its schema if they don't exist yet."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS news_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    external_id INTEGER NOT NULL,
                    analysis TEXT NOT NULL,
                    UNIQUE(category, symbol, external_id)
                )
            """)

    def analyze(self, msg: NewsMessage) -> str | None:
        """Return the stored analysis JSON string for this news, or None if not analyzed yet."""
        symbol = DataProvider().get_symbol()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT analysis
                FROM news_analysis
                WHERE category = ? AND symbol = ? AND external_id = ?
            """, (msg.category, symbol, msg.external_id)).fetchone()

        return row[0] if row else None

    def save(self, msg: NewsMessage, analysis: str):
        """Store the analysis JSON string for this news so it doesn't need to be re-analyzed."""
        symbol = DataProvider().get_symbol()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO news_analysis (category, symbol, external_id, analysis)
                VALUES (?, ?, ?, ?)
            """, (msg.category, symbol, msg.external_id, analysis))
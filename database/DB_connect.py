import sqlite3
import pathlib

class DBConnect:
    def __init__(self):
        raise RuntimeError("Do not create an instance, use get_connection()!")

    @classmethod
    def get_connection(cls):
        db_path = pathlib.Path(__file__).resolve().parent / "ad_campaign_db.sqlite"

        print("DB PATH CALCOLATO:", db_path)
        print("ESISTE?", db_path.exists())

        if not db_path.exists():
            raise FileNotFoundError(f"Database non trovato: {db_path}")

        cnx = sqlite3.connect(str(db_path))
        cnx.row_factory = sqlite3.Row
        return cnx

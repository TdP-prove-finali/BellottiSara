import sqlite3
import pathlib


class DBConnect:
    """
    Class used to create and manage the connection to the SQLite database.
    Same role as MySQL version, but adapted to SQLite.
    """

    def __init__(self):
        raise RuntimeError(
            "Do not create an instance, use the class method get_connection()!"
        )

    @classmethod
    def get_connection(cls):
        db_path = pathlib.Path(__file__).resolve().parent.parent / "DAO" / "ad_campaign_db.sqlite"

        print("DB PATH CALCOLATO:", db_path)
        print("ESISTE?", db_path.exists())

        cnx = sqlite3.connect(db_path)
        cnx.row_factory = sqlite3.Row
        return cnx


from database.DB_connect import DBConnect
from model.CampagnaProva import CampagnaProva


class DAO:

    @staticmethod
    def getAllCampaigns():

        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()

        ris = []

        query = """
            SELECT *
            FROM campaigns_sample
        """

        cursor.execute(query)

        for row in cursor:
            ris.append(CampagnaProva(**row))

        cursor.close()
        cnx.close()

        return ris

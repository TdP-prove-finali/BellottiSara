from database.DB_connect import DBConnect
from model.campaign import Campaign
from model.user import User


class DAO:

    @staticmethod
    def getAllCampaigns(budgetMax):
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()
        ris = []

        query = """select *
                   from campaigns
                   where total_budget <= ?
                   order BY campaign_id"""

        cursor.execute(query, (budgetMax,))
        for row in cursor:
            ris.append(Campaign(**dict(row)))

        cursor.close()
        cnx.close()

        return ris

    @staticmethod
    def _parse_interests_csv(interests_str):
        """
        interests_str nel DB: stringa tipo 'fashion, lifestyle'
        ritorna: tuple normalizzata ('fashion','lifestyle')
        """
        if interests_str is None:
            return tuple()
        parts = [p.strip() for p in str(interests_str).split(",")]
        parts = [p for p in parts if p]  # rimuove vuoti
        return tuple(parts)

    @staticmethod
    def getAllUsers( gender, age_group , country, interest1, interest2):
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()
        ris = []

        query = """SELECT u.user_id, u.user_gender, u.age_group, u.country, u.interests
                    FROM users u
                    WHERE 1=1
                    AND u.user_gender = COALESCE(?, u.user_gender)
                    AND u.age_group   = COALESCE(?, u.age_group)
                    AND u.country     = COALESCE(?, u.country)
                    AND (
                        (NULLIF(?,'') IS NULL AND NULLIF(?,'') IS NULL)
                        OR ( u.interests IS NOT NULL
                        AND ( (NULLIF(?, '') IS NOT NULL AND (',' || REPLACE(u.interests,' ','') || ',') LIKE '%,' || ? || ',%')
                            OR
                            (NULLIF(?, '') IS NOT NULL AND (',' || REPLACE(u.interests,' ','') || ',') LIKE '%,' || ? || ',%')
                            )
                            )
                        )"""
        params = ( gender, age_group, country,
                    interest1, interest2,
                    interest1, interest1,
                    interest2, interest2
                )
        cursor.execute(query, params)

        for row in cursor:
            d = dict(row)
            d["interests"] = DAO._parse_interests_csv(d["interests"])
            ris.append(User(**d))

        cursor.close()
        cnx.close()

        return ris

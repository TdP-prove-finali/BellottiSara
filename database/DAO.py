from database.DB_connect import DBConnect
from model.campaign import Campaign
from model.user import User


class DAO:

    @staticmethod
    def getAllCampaigns(budgetMax):
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()
        ris = []

        query = """SELECT *
                   FROM campaigns
                   WHERE total_budget <= ?
                   ORDER BY campaign_id"""

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

    @staticmethod
    def _placeholders(n: int) -> str:
        # n=3 -> "?,?,?"
        return ",".join(["?"] * n)

    @staticmethod
    def getAllEdgesWeight(listaIdCampaign, listaIdUserSelezionati):
        """
        Ritorna una lista di dict, uno per ogni arco (campaign_id, user_id),
        con KPI discreti e peso finale:
        - impressions
        - clicks
        - engagement = likes + comments + shares
        - purchases
        - weight = 10*purchases + 2*clicks + engagement

        Vengono restituiti solo archi con weight > 0 (quindi almeno un segnale utile).
        """
        if not listaIdCampaign or not listaIdUserSelezionati:
            return []

        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()

        ph_c = DAO._placeholders(len(listaIdCampaign))
        ph_u = DAO._placeholders(len(listaIdUserSelezionati))

        query = f"""
            WITH RawTotals AS (
                SELECT a.campaign_id AS campaign_id, e.user_id AS user_id,
                    SUM(CASE WHEN e.event_type = 'Impression' THEN 1 ELSE 0 END) AS impressions,
                    SUM(CASE WHEN e.event_type = 'Click'      THEN 1 ELSE 0 END) AS clicks,
                    SUM(CASE WHEN e.event_type = 'Like'       THEN 1 ELSE 0 END) AS likes,
                    SUM(CASE WHEN e.event_type = 'Comment'    THEN 1 ELSE 0 END) AS comments,
                    SUM(CASE WHEN e.event_type = 'Share'      THEN 1 ELSE 0 END) AS shares,
                    SUM(CASE WHEN e.event_type = 'Purchase'   THEN 1 ELSE 0 END) AS purchases
                FROM ad_events e
                JOIN ads a ON a.ad_id = e.ad_id
                WHERE a.campaign_id IN ({ph_c})
                  AND e.user_id IN ({ph_u})
                GROUP BY a.campaign_id, e.user_id )
            SELECT campaign_id, user_id, impressions, clicks, (likes + comments + shares) AS engagement, purchases, (10 * purchases + 2 * clicks + (likes + comments + shares)) AS weight
            FROM RawTotals
            WHERE (10 * purchases + 2 * clicks + (likes + comments + shares)) > 0
            """

        params = tuple(listaIdCampaign) + tuple(listaIdUserSelezionati)
        cursor.execute(query, params)

        ris = [dict(row) for row in cursor.fetchall()]

        cursor.close()
        cnx.close()
        return ris

    #ris -> {"campaign_id": 12, "user_id": "687d1", "impressions": 4, "clicks": 1, "engagement": 0, "purchases": 0, "weight": 2}


#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #PROVA 1 --> ritorna tantissimi archi ma la maggior parte ha i valori fondamentali  = 0 e quindi non posso fare analisi di ottimizzazione sensate
    @staticmethod
    def getAllEdgesWithKPI_1(listaIdCampaign, listaIdUserSelezionati):
        if not listaIdCampaign or not listaIdUserSelezionati:
            return []

        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()

        ph_c = DAO._placeholders(len(listaIdCampaign))
        ph_u = DAO._placeholders(len(listaIdUserSelezionati))

        query = f"""
            WITH RawTotals AS (
                SELECT
                    a.campaign_id AS campaign_id,
                    e.user_id     AS user_id,
                    SUM(CASE WHEN e.event_type = 'Impression' THEN 1 ELSE 0 END) AS impressions,
                    SUM(CASE WHEN e.event_type = 'Click'      THEN 1 ELSE 0 END) AS clicks,
                    SUM(CASE WHEN e.event_type = 'Purchase'   THEN 1 ELSE 0 END) AS purchases
                FROM ad_events e
                JOIN ads a ON a.ad_id = e.ad_id
                WHERE a.campaign_id IN ({ph_c})
                  AND e.user_id IN ({ph_u})
                GROUP BY a.campaign_id, e.user_id
            )
            SELECT
                campaign_id, user_id, impressions, clicks, purchases,
                CASE WHEN impressions > 0 THEN 1.0 * clicks / impressions ELSE 0 END AS ctr,
                CASE WHEN clicks > 0      THEN 1.0 * purchases / clicks    ELSE 0 END AS cvr
            FROM RawTotals
            WHERE (impressions + clicks + purchases) > 0"""

        params = tuple(listaIdCampaign) + tuple(listaIdUserSelezionati)
        cursor.execute(query, params)

        # creo dizionario KPI per archi
        ris = [dict(row) for row in cursor.fetchall()]

        cursor.close()
        cnx.close()
        return ris


# ris ritorna una lista di dict tipo:--> {
                                    #     "campaign_id": 12,
                                    #     "user_id": "687d1",
                                    #     "impressions": 83,
                                    #     "clicks": 4,
                                    #     "purchases": 1,
                                    #     "ctr": 0.04819,
                                    #     "cvr": 0.25
                                    # }

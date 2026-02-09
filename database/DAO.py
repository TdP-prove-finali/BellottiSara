from typing import List, Dict

from database.DB_connect import DBConnect
from model.campaign import Campaign
from model.user import User


class DAO:

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def getAllUserGender():
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()
        ris = []

        query = """
                SELECT DISTINCT user_gender
                FROM users
                ORDER BY user_gender
            """

        cursor.execute(query)
        for row in cursor:
            ris.append(row["user_gender"])

        cursor.close()
        cnx.close()
        return ris

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def getAllAgeGroup():
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()
        ris = []

        query = """
                SELECT DISTINCT age_group
                FROM users
                ORDER BY age_group
            """

        cursor.execute(query)
        for row in cursor:
            ris.append(row["age_group"])

        cursor.close()
        cnx.close()
        return ris

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def getAllCountry():
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()
        ris = []

        query = """
                SELECT DISTINCT country
                FROM users
                ORDER BY country
            """

        cursor.execute(query)
        for row in cursor:
            ris.append(row["country"])

        cursor.close()
        cnx.close()
        return ris

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def getAllInterests():
        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()
        ris = []

        query = """
                SELECT DISTINCT interests
                FROM users
               """
        cursor.execute(query)
        for row in cursor:
            ris.append(row["interests"])  # es: "lifestyle, technology, fitness"

        cursor.close()
        cnx.close()
        return ris

    # ---------------------------------------------------------------------------------------------------------------------------------------------
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

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def parseInterestsStringaInTupla(interests_str):
        """
        Convert the `users.interests` field from the database 'fashion, lifestyle'
        into a Python tuple ('fashion','lifestyle')
        :param interests_str
        :return tuple or () if is None
        """
        if interests_str is None:
            return tuple()

        parts = [p.strip() for p in str(interests_str).split(",")]
        parts = [p for p in parts if p]                                    #rimuove vuoti
        return tuple(parts)


    @staticmethod
    def getAllUsers( gender, age_group , country, interest1, interest2):
        """
        Demographic filters use COALESCE(?, column) so that passing None disables the filter.
        - Interests are optional:
            - if both interest1 and interest2 are empty/None -> no interest filter is applied
            - otherwise, a user is selected if their `interests` field contains at least one of the provided tokens.
        :return list[User]
        """
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
            d["interests"] = DAO.parseInterestsStringaInTupla(d["interests"])
            ris.append(User(**d))

        cursor.close()
        cnx.close()

        return ris

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def _placeholders(n: int) -> str:
        """
        Generate a comma-separated list of SQL placeholders ('?')
        :return str
        """
        return ",".join(["?"] * n)


    @staticmethod
    def getAllEdgesWeight(listaIdCampaign, listaIdUserSelezionati):
        """
        Compute weighted edges between campaigns and users based on interaction events.
        Returns a list of dictionaries, one for each edge (campaign_id, user_id), containing discrete KPIs and a final weight:
            - impressions
            - clicks
            - engagement = likes + comments + shares
            - purchases
            - weight = 10 * purchases + 2 * clicks + engagement

        Only edges with weight > 0 are returned, meaning that at least one meaningful interaction signal is present.
        :param listaIdCampaign : list[int]
        :param listaIdUserSelezionati : list[str]
        :return list[dict]
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
        # ris -> {"campaign_id": 12, "user_id": "687d1", "impressions": 1, "clicks": 1, "engagement": 0, "purchases": 0, "weight": 2}

        cursor.close()
        cnx.close()
        return ris

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def getCampaignTotals(campaign_ids):
        """
        Compute global event totals for each campaign across ALL users

        :param campaign_ids: list[int]
        :return: {campaign_id: {"impressions": int, "clicks": int, "purchases": int}}
        """

        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()
        ph = ",".join(["?"] * len(campaign_ids))

        query = f"""
                SELECT
                    a.campaign_id,
                    COALESCE(SUM(CASE WHEN e.event_type = 'Impression' THEN 1 ELSE 0 END), 0) AS impressions,
                    COALESCE(SUM(CASE WHEN e.event_type = 'Click'      THEN 1 ELSE 0 END), 0) AS clicks,
                    COALESCE(SUM(CASE WHEN e.event_type = 'Purchase'   THEN 1 ELSE 0 END), 0) AS purchases
                FROM ad_events e
                JOIN ads a ON e.ad_id = a.ad_id
                WHERE a.campaign_id IN ({ph})
                GROUP BY a.campaign_id
                """

        #converto in tupla ((id1, id2, id3))
        cursor.execute(query, tuple(campaign_ids) )
        rows = cursor.fetchall()

        cursor.close()
        cnx.close()

        # inizializzo a 0 cosicchè anche se una campagna non ha righe nella query, la ritrovo comunque nel risultato con valori 0
        ris = {int(cid): {"impressions": 0, "clicks": 0, "purchases": 0} for cid in campaign_ids}

        for r in rows:
            d = dict(r)
            cid = int(d["campaign_id"])
            ris[cid] = { "impressions": int(d.get("impressions", 0)),
                         "clicks": int(d.get("clicks", 0)),
                         "purchases": int(d.get("purchases", 0))
                         }
        return ris


    @staticmethod
    def getCampaignImpressionsOnTarget(campaign_ids, user_ids):
        """
        Campaign impressions filtered ONLY on target users.
        This is necessary because impressions are not fully observable on graph edges.
        The result is used for cost allocation -> share = impressions_target / impressions_total
        :param campaign_ids: List[int]
        :param user_ids: List[str]
        :return Dict[int, int]  -> { campaign_id (int): impressions_target (int) }
        """
        if not campaign_ids or not user_ids:
            #mappa con 0 se non ci sono campagne o user
            return {int(cid): 0 for cid in (campaign_ids or [])}

        cnx = DBConnect.get_connection()
        cursor = cnx.cursor()

        ph_c = ",".join(["?"] * len(campaign_ids))
        ph_u = ",".join(["?"] * len(user_ids))

        query = f"""
                SELECT a.campaign_id AS campaign_id,
                       COALESCE(SUM(CASE WHEN e.event_type = 'Impression' THEN 1 ELSE 0 END), 0) AS impressions
                FROM ad_events e
                JOIN ads a ON e.ad_id = a.ad_id
                WHERE a.campaign_id IN ({ph_c})
                  AND e.user_id IN ({ph_u})
                GROUP BY a.campaign_id
            """

        params = tuple(campaign_ids) + tuple(user_ids)
        cursor.execute(query, params)
        rows = cursor.fetchall()

        cursor.close()
        cnx.close()

        # inizializzo a 0
        ris = {int(cid): 0 for cid in campaign_ids}

        for r in rows:
            d = dict(r)
            cid = int(d["campaign_id"])
            ris[cid] = int(d.get("impressions", 0))

        return ris
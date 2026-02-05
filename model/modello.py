import networkx as nx
from database.DAO import DAO

class Model:
    def __init__(self):

        self._grafo = nx.DiGraph()
        self._idMapCampaign = {}
        self._idMapUser = {}

    # -----------------------------------------------------------------------------------------------------------------------------------
    def getAllUserGender(self):
        return DAO.getAllUserGender()

    def getAllAgeGroup(self):
        return DAO.getAllAgeGroup()

    def getAllCountry(self):
            return DAO.getAllCountry()

    def getAllInterests(self):
        return DAO.getAllInterests()

    # ------------------------------------------------------------------------------------------------------------------------------------------
    def buildGraph(self, budgetMax, gender, age_group, country, interest1, interest2):

        self._grafo.clear()

        #NODI CAMPAIGNS (bipartite=0)---------------------------------------------
        campaigns = DAO.getAllCampaigns(budgetMax)
        self._idMapCampaign = { c.campaign_id: c for c in campaigns }

        for c in campaigns:
            self._grafo.add_node(c , bipartite=0)

        #NODI USERS (bipartite=1)------------------------------------------------
        users = DAO.getAllUsers(gender, age_group, country, interest1, interest2)
        self._idMapUser = {u.user_id: u for u in users}

        for u in users:
            self._grafo.add_node(u, bipartite=1)

        #ARCHI + PESO (Campaign --> User )
        listaIdCampaign = list(self._idMapCampaign.keys())
        listaIdUser = list(self._idMapUser.keys())

        #Sicurezza --> se una delle due liste è vuota, niente archi
        if not listaIdCampaign or not listaIdUser:
            return self._grafo

        edges = DAO.getAllEdgesWeight(listaIdCampaign, listaIdUser)
        # edges: lista di dict tipo:
        #       {"campaign_id": 12, "user_id": "687d1", "impressions": 4, "clicks": 1, "engagement": 0, "purchases": 0, "weight": 2}

        for e in edges:
            nodoCampaign = e["campaign_id"]
            nodoUser = e["user_id"]

            # Sicurezza:
            if nodoCampaign not in self._idMapCampaign or nodoUser not in self._idMapUser:
                continue

            c = self._idMapCampaign[nodoCampaign]
            u = self._idMapUser[nodoUser]
            peso = e["weight"]

            self._grafo.add_edge( c, u, weight=peso, impressions=e["impressions"], clicks=e["clicks"], engagement=e["engagement"], purchases=e["purchases"])
        return self._grafo

    def getDetailsGraph(self):
        return len(self._grafo.nodes), len(self._grafo.edges)

    def getNodes(self):
        return self._grafo.nodes

    def getId(self, budgetMax, gender, age_group, country, interest1, interest2):
        campaign_ids = [c.campaign_id for c in DAO.getAllCampaigns(budgetMax)]
        user_ids = [u.user_id for u in DAO.getAllUsers(gender, age_group, country, interest1, interest2)]
        return campaign_ids, user_ids

    # --------------------------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    m = Model()
    #m.buildGraph(50000, "Female" , "25-34", "France", "fashion", "lifestyle")
    #print(m.getDetailsGraph())
    #print(m.getId(50000, "Female" , "25-34", "France", "fashion", "lifestyle"))
    m.buildGraph(50000, "Male" , "25-34", "United States", "fitness", "technology")
    print(m.getDetailsGraph())
    print(m.getId(50000, "Male" , "25-34", "United States", "fitness", "technology"))
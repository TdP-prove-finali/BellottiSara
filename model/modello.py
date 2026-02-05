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

        #for tupla in DAO.getAllEdgesWeight(anno, shape, self._idMapStates):
           # stato1 = tupla[0]
           # stato2 = tupla[1]
           # peso = tupla[2]
          #  if peso > 0:
             #   self._grafo.add_edge(stato1, stato2, weight=peso)

        # se dovessero servire altri parametri da salvare oltre il peso
      #  for edge in self._grafo.edges(data=True):
         #   self._grafo[edge[0]][edge[1]]['distanza'] = self.getDistanzaDueStati(edge[0], edge[1])

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
    m.buildGraph(50000, "Female" , "25-34", "France", "fashion", "lifestyle")
    print(m.getDetailsGraph())
    print(m.getNodes())
    print(m.getId(50000, "Female" , "25-34", "France", "fashion", "lifestyle"))
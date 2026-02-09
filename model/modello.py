import copy
import networkx as nx
from database.DAO import DAO
from model.segment import Segment


class Model:
    def __init__(self):

        self._grafo = nx.DiGraph()
        self._idMapCampaign = {}
        self._idMapUser = {}

        #Target = insieme di filtri scelti dall'utente in flet (genere, età, città, interessi) --> il target è un insieme di user
        #Ogni volta che cambio filtri -> cambio target -> cambio utenti -> cambio grafo
        self._currentTargetId = 0

    #---------------------------------------------------------------------------------------------------------------------------------------------
    def getAllUserGender(self):
        return DAO.getAllUserGender()

    def getAllAgeGroup(self):
        return DAO.getAllAgeGroup()

    def getAllCountry(self):
            return DAO.getAllCountry()

    def getAllInterests(self):
        """
            Ritorna una lista piatta di interessi senza duplicati ordinata alfabeticamente
        """
        raw_list = DAO.getAllInterests()
        uniq = set()

        for item in raw_list:
            if item is None:
                continue
            s = str(item).strip()
            if not s:
                continue

            parts = s.split(",")
            for p in parts:
                token = p.strip()
                if token:
                    uniq.add(token)

        return sorted(uniq, key=lambda x: x.lower())

    #---------------------------------------------------------------------------------------------------------------------------------------------
    def buildGraph(self, budgetMax, gender, age_group, country, interest1, interest2):

        self._currentTargetId +=1
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
        listIdCampaign = list(self._idMapCampaign.keys())
        listIdUser = list(self._idMapUser.keys())

        #Sicurezza --> se una delle due liste è vuota, niente archi
        if not listIdCampaign or not listIdUser:
            return self._grafo

        edges = DAO.getAllEdgesWeight(listIdCampaign, listIdUser)
        # edges: lista di dict tipo:
        #       {"campaign_id": 12, "user_id": "687d1", "impressions": 4, "clicks": 1, "engagement": 0, "purchases": 0, "weight": 2}

        for e in edges:
            nodeCampaign = e["campaign_id"]
            nodeUser = e["user_id"]
            # Sicurezza:
            if nodeCampaign not in self._idMapCampaign or nodeUser not in self._idMapUser:
                continue
            c = self._idMapCampaign[nodeCampaign]
            u = self._idMapUser[nodeUser]
            peso = e["weight"]
            self._grafo.add_edge( c, u, weight=peso, impressions=e["impressions"], clicks=e["clicks"], engagement=e["engagement"], purchases=e["purchases"])

        return self._grafo

    #---------------------------------------------------------------------------------------------------------------------------------------------
    def getDetailsGraph(self):
        return len(self._grafo.nodes), len(self._grafo.edges)

    def getId(self, budgetMax, gender, age_group, country, interest1, interest2):
        campaign_ids = [c.campaign_id for c in DAO.getAllCampaigns(budgetMax)]
        user_ids = [u.user_id for u in DAO.getAllUsers(gender, age_group, country, interest1, interest2)]
        return campaign_ids, user_ids

    def getNumNodesCampaignUsers(self):
        return len(self._idMapCampaign), len(self._idMapUser)

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    def getCampaignStatsOnTarget(self, campaign) -> Segment:
        """"
            Calcola le statistiche aggregate della campagna sul target corrente.
            Somma i KPI presenti sugli archi (Campaign --> User) verso tutti gli utenti raggiunti.
        """
        if campaign not in self._grafo:
            return None

        impressions = clicks = engagement = purchases = weight = 0
        n_users_reached = 0

        for u in self._grafo.successors(campaign):
            data = self._grafo[campaign][u]
            impressions += data.get("impressions", 0)
            clicks += data.get("clicks", 0)
            engagement += data.get("engagement", 0)
            purchases += data.get("purchases", 0)
            weight += data.get("weight", 0)
            n_users_reached += 1

        segment_id = f"C{campaign.campaign_id}_T{self._currentTargetId}"
        return Segment(segment_id, campaign.campaign_id, impressions, clicks, engagement, purchases, weight, n_users_reached)

    #---------------------------------------------------------------------------------------------------------------------------------------------
    def getCandidateCampaigns(self, durationMax):
        """
        Campagne candidate: nodi bipartite=0 con almeno un arco verso il target.
        durationMax (opzionale): se presente, filtra le campagne troppo lunghe.
        """
        candidates = []
        #self._grafo.nodes(data=True) --> restituisce tupla --> ( c="codice_id" , d="dizionario degli attributi")
        for c, d in self._grafo.nodes(data=True):
            if d.get("bipartite") != 0:
                continue
            if self._grafo.out_degree(c) <= 0:
                continue
            if durationMax is not None:
                if getattr(c, "duration_days", None) is not None and c.duration_days > durationMax:
                    continue
            candidates.append(c)
        return candidates


    def get_total_bestSolution_cost(self, solution):
        """
            Ritorna il costo totale di una soluzione (cioè di una combinazione di campagne).
            La soluzione è una lista di dict candidati, ciascuno con chiave "cost".
            """
        return sum( item["cost"] for item in solution)

    def getROI_bestSolution(self, solution, value_per_purchase):
        """
        :param solution: lista di dict (candidates) con chiavi "cost" e "segment"
        :param value_per_purchase:
        :return: ROI oppure None se non calcolabile
        """
        #total_cost = self.get_total_bestSolution_cost(solution)
        total_cost_target = sum(item["cost_target"] for item in solution)

        vpp = float(value_per_purchase) if value_per_purchase is not None else 0.0
        if vpp <= 0 or total_cost_target <= 0:
            return None

        total_revenue = sum(int(item["segment"].purchases) * vpp for item in solution)
        return (total_revenue - total_cost_target) / total_cost_target

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    # RICORSIONE e OTTIMIZZAZIONE
    def ottimizzaMetriche(self, budgetMax, goal, value_per_purchase, durationMax):
        """
        goal: "click" | "conversioni" | "roi"
        vincolo: somma costi (campaign.total_budget) <= budgetMax
        durataMax: opzionale (filtra campagne non compatibili)
        """

        #1.a) Costruisco la lista di candidati tramite segmenti (e relative statistiche)
        campaigns = self.getCandidateCampaigns(durationMax)
        if not campaigns:
            print("Nessuna campagna candidata per i filtri selezionati.")
            return {"best_score": 0, "best_campaigns": [], "best_segments": [], "roi_tot": None, "n_best_solutions": 0}

        totals_map = DAO.getCampaignTotals([c.campaign_id for c in campaigns])

        candidates = []
        g = goal.lower().strip()
        vpp = float(value_per_purchase) if value_per_purchase is not None else 0.0

        for c in campaigns:
            seg = self.getCampaignStatsOnTarget(c)
            if seg is None:
                continue

            cost_full_campaign = float(getattr(c, "total_budget", 0.0))

            #variabili per calcolare il ROI finale
            tot = totals_map.get(c.campaign_id, {"impressions": 0, "clicks": 0, "purchases": 0})
            impr_tot = int(tot["impressions"])
            impr_target = int(getattr(seg, "impressions", 0))
            share = (impr_target / impr_tot) if impr_tot > 0 else 0.0
            cost_target = cost_full_campaign * share
            revenue = int(seg.purchases) * vpp if vpp > 0 else 0.0

            if g == "click":
                score = int(seg.clicks)
            elif g == "conversioni":
                score = int(seg.purchases)
            elif g == "engagement":
                score = int(seg.engagement)
            elif g == "performance index":
                score = int(seg.weight)
            else:
                raise ValueError("Goal non valido: usa 'click', 'conversioni' , 'engagement' , 'performance index' ")

            candidates.append({ "campaign": c,
                                "segment": seg,
                                "cost": cost_full_campaign,    #per il VINCOLO budgetMax
                                "cost_target": cost_target,    #per il ROI sul target
                                "share": share,   # quota target
                                "score": score,
                                "revenue": revenue })

        #1.b) Se non ho candidati, ritorno vuoto ------------------------------------
        if not candidates:
            result = { "best_score": 0.0, "best_campaigns": [], "best_segments": [], "total_cost": 0.0, "total_revenue": 0.0, "roi_tot": 0.0, "n_best_solutions": 0 }
            print("Nessuna campagna candidata per i filtri selezionati.")
            return result

        #2) Inizializzo e chiamo la ricorsione ---------------------------------------
        self._bestScore = float("-inf")
        self._bestSolutions = []
        self._ricorsione( i=0,
                          candidates=candidates,
                          budgetMax=float(budgetMax),
                          parziale=[],
                          cost_sum=0.0,
                          score_sum=0.0,
                          rev_sum=0.0 )

        #3.a) Tie-break: scelgo la soluzione migliore (costo minore a pari score)
        sorted_solutions = sorted(self._bestSolutions, key=lambda sol: self.get_total_bestSolution_cost(sol))
        best = sorted_solutions[0]
        alternatives = sorted_solutions[1:]

        #3.b)Ordino le campagne DENTRO ogni soluzione per score decrescente
        best = sorted(best, key=lambda item: item["score"], reverse=True)
        alternatives = [sorted(sol, key=lambda item: item["score"], reverse=True) for sol in alternatives]

        total_cost_full = self.get_total_bestSolution_cost(best)
        total_cost_target = sum(x["cost_target"] for x in best)
        total_revenue = sum(x["revenue"] for x in best)

        roi_tot = self.getROI_bestSolution(best, vpp) #ROI sul target



        #4) Stampo ---------------------------------------------------------------------
        result = { "best_score": self._bestScore,
                   "best_campaigns": [x["campaign"] for x in best],
                   "best_segments": [x["segment"] for x in best],
                   "total_cost_full": total_cost_full,
                   "total_cost_target": total_cost_target,
                   "total_revenue_target": total_revenue,
                   "roi_target": roi_tot,
                   "n_best_solutions": len(self._bestSolutions),
                   "n_alternatives": len(alternatives),
                   "alternatives": [
                       {"campaigns": [x["campaign"] for x in sol],
                        "segments": [x["segment"] for x in sol],
                        "total_cost_full": self.get_total_bestSolution_cost(sol),
                        "total_cost_target": sum(x["cost_target"] for x in sol),
                        "total_revenue": sum(x["revenue"] for x in sol),
                        "roi_target": self.getROI_bestSolution(sol, vpp),
                        }
                       for sol in alternatives ]
                   }

        #5) Debug console ----------------------------------------------------------------
        print("\n-----RISULTATO OTTIMIZZAZIONE-----")
        print(f"Goal: {goal} | BudgetMax: {budgetMax}")
        print(f"Best score: {result['best_score']}")
        print(f"Tot cost FULL (pagato): {result['total_cost_full']:.2f}")
        print(f"Tot cost TARGET (allocato): {result['total_cost_target']:.2f}")
        print(f"Tot revenue TARGET: {result['total_revenue_target']:.2f}")
        if result["roi_target"] is None:
            print("ROI TARGET: N/A (value_per_purchase deve essere > 0 e cost_target > 0)")
        else:
            print(f"ROI TARGET: {result['roi_target']:.4f}")
        print(f"Num soluzioni migliori (pari score): {result['n_best_solutions']}")
        print(f"Num alternative (pari score, costo maggiore): {result['n_alternatives']}")

        #soluzione migliore --> lista di dict-campagna
        for indice, x in enumerate(best, start=1):
            c = x["campaign"]
            s = x["segment"]
            print(f"- {indice}) Campaign {c.campaign_id} | cost={x['cost']:.2f} | "
                  f"clicks={s.clicks} | purchases={s.purchases} | engagement={s.engagement} |  weight={s.weight}")

        #alternativa --> lista di liste di dict-campagna
        for sol_idx, sol in enumerate(alternatives, start=1):
            sol_cost = self.get_total_bestSolution_cost(sol)
            sol_revenue = sum(item["revenue"] for item in sol)
            print(f"\n--- Alternativa {sol_idx} | cost={sol_cost:.2f} | revenue={sol_revenue:.2f} ---")

            for item_idx, item in enumerate(sol, start=1):
                c = item["campaign"]
                s = item["segment"]
                print( f"  - {item_idx}) Campaign {c.campaign_id} | cost={item['cost']:.2f} | "
                    f"clicks={s.clicks} | purchases={s.purchases} | engagement={s.engagement} |  weight={s.weight}" )

        return result

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    def _ricorsione(self, i, candidates, budgetMax, parziale, cost_sum, score_sum, rev_sum):

        #Vincolo budget
        if cost_sum > budgetMax:
            return

        #Fine
        if i == len(candidates):
            if score_sum > self._bestScore:
                self._bestScore = score_sum
                self._bestSolutions = [copy.deepcopy(parziale)]
            elif score_sum == self._bestScore:
                self._bestSolutions.append(copy.deepcopy(parziale))
            return

        #ramo: escludo candidato i
        self._ricorsione(i+1, candidates, budgetMax, parziale, cost_sum, score_sum, rev_sum)
        # ramo: includo candidato i
        cand = candidates[i]
        parziale.append(cand)
        self._ricorsione(i+1, candidates, budgetMax, parziale, cost_sum + cand["cost"], score_sum + cand["score"], rev_sum + cand["revenue"] )
        parziale.pop()


if __name__ == "__main__":
    m = Model()
    #m.buildGraph(50000, "Female" , "25-34", "France", "fashion", "lifestyle")
    #print(m.getDetailsGraph())
    #print(m.getId(50000, "Female" , "25-34", "France", "fashion", "lifestyle"))
    #print(m.ottimizzaMetriche(50000, "click", 30, None))
    m.buildGraph(50000, "Male" , "25-34", "United States", "fitness", "technology")
    print(m.getDetailsGraph())
    print(m.getId(50000, "Male" , "25-34", "United States", "fitness", "technology"))
    print(m.ottimizzaMetriche(50000, "conversioni", 30, None))
    #m.buildGraph(42750, "", "", "United States", "finance", "technology")
    #print(m.getDetailsGraph())
    #print(m.getId(42750, "", "", "United States", "finance", "technology"))
    #print(m.ottimizzaMetriche(42750, "conversioni", 100, 365))
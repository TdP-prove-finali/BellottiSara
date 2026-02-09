import copy
import networkx as nx
from database.DAO import DAO
from model.segment import Segment

class Model:
    def __init__(self):

        # Grafo bipartito: Campaign -> User
        self._grafo = nx.DiGraph()
        self._idMapCampaign = {}
        self._idMapUser = {}

        # Contatore target (incrementa ogni volta che vengono cambiati i filtri -> nuovo target)
        self._currentTargetId = 0

        # Salvo la soluzione migliore e value_per_purchase per effettuare sucessivamente la valutazione economica
        self.best = None
        self.vpp = 0.0

    # UI FILTER DROPDOWN VALUES
    #---------------------------------------------------------------------------------------------------------------------------------------------
    def getAllUserGender(self):
        return DAO.getAllUserGender()

    def getAllAgeGroup(self):
        return DAO.getAllAgeGroup()

    def getAllCountry(self):
        return DAO.getAllCountry()

    def getAllInterests(self):
        """
            Interests are stored in the database as comma-separated strings.
            This method splits them, removes duplicates and empty values, and returns a clean list of interest labels.
        """
        listRaw = DAO.getAllInterests()
        uniq = set()

        for item in listRaw:
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

    # GRAPH
    #---------------------------------------------------------------------------------------------------------------------------------------------
    def buildGraph(self, budgetMax, gender, age_group, country, interest1, interest2):

        self._currentTargetId +=1
        self._grafo.clear()
        self.best = None

        # NODED CAMPAIGNS (bipartite=0) ---------------------------------------------
        campaigns = DAO.getAllCampaigns(budgetMax)
        self._idMapCampaign = { c.campaign_id: c for c in campaigns }
        for c in campaigns:
            self._grafo.add_node(c , bipartite=0)

        # NODES USERS (bipartite=1) ------------------------------------------------
        users = DAO.getAllUsers(gender, age_group, country, interest1, interest2)
        self._idMapUser = {u.user_id: u for u in users}
        for u in users:
            self._grafo.add_node(u, bipartite=1)


        listIdCampaign = list(self._idMapCampaign.keys())
        listIdUser = list(self._idMapUser.keys())

        #Sicurezza -> se una delle due liste è vuota, niente archi
        if not listIdCampaign or not listIdUser:
            return self._grafo

        # EDGES: Campaign -> User (with KPI + weight) -------------------------------
        edges = DAO.getAllEdgesWeight(listIdCampaign, listIdUser)

        for e in edges:
            cid = e["campaign_id"]
            uid = e["user_id"]
            # Sicurezza:
            if cid not in self._idMapCampaign or uid not in self._idMapUser:
                continue

            c = self._idMapCampaign[cid]
            u = self._idMapUser[uid]
            peso = e["weight"]

            self._grafo.add_edge( c, u, weight=peso, impressions=e["impressions"], clicks=e["clicks"], engagement=e["engagement"], purchases=e["purchases"])

        return self._grafo

    # UTILITY
    #---------------------------------------------------------------------------------------------------------------------------------------------
    def getDetailsGraph(self):
        return len(self._grafo.nodes), len(self._grafo.edges)

    def getId(self, budgetMax, gender, age_group, country, interest1, interest2):
        campaign_ids = [c.campaign_id for c in DAO.getAllCampaigns(budgetMax)]
        user_ids = [u.user_id for u in DAO.getAllUsers(gender, age_group, country, interest1, interest2)]
        return campaign_ids, user_ids

    def getNumNodesCampaignUsers(self):
        return len(self._idMapCampaign), len(self._idMapUser)


    # METODI PER OTTIMIZZAZIONE
    # ---------------------------------------------------------------------------------------------------------------------------------------------
    def getCampaignStatsOnTarget(self, campaign):
        """
            Compute aggregated statistics for a campaign on the current target.

            This method sums all KPIs stored on the graph edges (Campaign -> User) for the given campaign,
            considering only users belonging to the current target.

            Returns a Segment object containing aggregated impressions, clicks, engagement, purchases, total weight, and the number of reached users.
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
            Select candidate campaigns for the optimization step.

            A campaign is considered a candidate if:
                - it is a campaign node (bipartite = 0),
                - it has at least one outgoing edge to a target user,
                - its duration does not exceed durationMax (if provided).

            Returns a list of campaign objects.
        """
        candidates = []
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


    def getCostTotal_bestSolution(self, solution):
        """
            Compute the total cost of a solution.
            The solution is a list of selected campaigns, where each item contains a 'cost' field.
        """
        return sum( item["cost"] for item in solution)


    # RICORSIONE e OTTIMIZZAZIONE
    # ---------------------------------------------------------------------------------------------------------------------------------------------
    def ottimizzaMetriche(self, budgetMax, goal, value_per_purchase, durationMax):
        """
        Find the best combination of campaigns under a maximum budget

        The method works in three steps:
        1)  It selects candidate campaigns that have at least one interaction
            with the current target (and optionally respects a maximum duration)
        2)  For each candidate campaign it computes target statistics (Segment)
            and assigns a score based on the selected goal:
               - click -> number of clicks
               - conversioni -> number of purchases
               - engagement -> engagement count (like + comment + share)
               - performance index -> weighted score stored on edges ( 10*purchase + 2*click + engagement)
        3)  It runs a recursive search (knapsack/backtracking) to choose the subset
            of campaigns that maximizes the total score while keeping total cost
            <= budgetMax (and <= durationMax if selected)

        The best solution is stored in self.best (used later for economic evaluation)
        and the function returns the best score, selected campaigns, and alternative
        solutions with the same score
        """

        #1.a) Costruisco la lista di candidati tramite segmenti (e relative statistiche)
        campaigns = self.getCandidateCampaigns(durationMax)
        if not campaigns:
            print("Nessuna campagna candidata per i filtri selezionati.")
            return {"best_score": 0, "best_campaigns": [], "best_segments": [], "roi_tot": None, "n_best_solutions": 0}

        candidates = []
        g = goal.lower().strip()

        try:
            self.vpp = float(value_per_purchase) if value_per_purchase not in (None, "") else 0.0
        except ValueError:
            self.vpp = 0.0

        for c in campaigns:
            seg = self.getCampaignStatsOnTarget(c)
            if seg is None:
                continue

            cost_full_campaign = float(getattr(c, "total_budget", 0.0))

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
                                "score": score,
                                })

        #1.b) Se non ho candidati, ritorno vuoto --------------
        if not candidates:
            result = { "best_score": 0.0, "best_campaigns": [], "best_segments": [], "total_cost_full": 0.0, "n_best_solutions": 0 }
            print("Nessuna campagna candidata per i filtri selezionati.")
            return result

        #2) Inizializzo e chiamo la ricorsione --------------
        self._bestScore = float("-inf")
        self._bestSolutions = []
        self._ricorsione( i=0, candidates=candidates, budgetMax=float(budgetMax), parziale=[], cost_sum=0.0, score_sum=0.0 )

        #3.a) Nessuna soluzione ------------------
        if not self._bestSolutions:
            return {"best_score": 0.0, "best_campaigns": [], "best_segments": [], "total_cost_full": 0.0, "n_best_solutions": 0, "n_alternatives": 0, "alternatives": []}

        #3.b) Scelgo la soluzione migliore (costo minore a pari score) -----------------
        sorted_solutions = sorted(self._bestSolutions, key=lambda sol: self.getCostTotal_bestSolution(sol))
        bestRaw = sorted_solutions[0]
        alternatives = sorted_solutions[1:]

        #3.c) Ordino le campagne DENTRO ogni soluzione per score decrescente
        self.best = sorted(bestRaw, key=lambda item: item["score"], reverse=True)
        alternatives = [sorted(sol, key=lambda item: item["score"], reverse=True) for sol in alternatives]

        total_cost_full = self.getCostTotal_bestSolution(self.best)

        #4) Stampo ---------------------------------------------------------------------
        result = { "best_score": self._bestScore,
                   "best_campaigns": [x["campaign"] for x in self.best],
                   "best_segments": [x["segment"] for x in self.best],
                   "total_cost_full": total_cost_full,
                   "n_best_solutions": len(self._bestSolutions),
                   "n_alternatives": len(alternatives),
                   "alternatives": [
                       {"campaigns": [x["campaign"] for x in sol],
                        "segments": [x["segment"] for x in sol],
                        "total_cost_full": self.getCostTotal_bestSolution(sol),
                        }
                       for sol in alternatives ]
                   }

        #5) Debug console ----------------------------------------------------------------
        print("\n-----RISULTATO OTTIMIZZAZIONE-----")
        print(f"Goal: {goal} | BudgetMax: {budgetMax}")
        print(f"Best score: {result['best_score']}")
        print(f"Tot cost FULL (pagato): {result['total_cost_full']:.2f}")
        print(f"Num soluzioni migliori (pari score): {result['n_best_solutions']}")
        print(f"Num alternative (pari score, costo maggiore): {result['n_alternatives']}")

        #soluzione migliore --> lista di dict-campagna
        for indice, x in enumerate(self.best, start=1):
            c = x["campaign"]
            s = x["segment"]
            print(f"- {indice}) Campaign {c.campaign_id} | cost={x['cost']:.2f} | "
                  f"clicks={s.clicks} | purchases={s.purchases} | engagement={s.engagement} |  weight={s.weight}")

        #alternativa --> lista di liste di dict-campagna
        for sol_idx, sol in enumerate(alternatives, start=1):
            sol_cost = self.getCostTotal_bestSolution(sol)
            #sol_revenue = sum(item["revenue"] for item in sol)
            print(f"\n--- Alternativa {sol_idx} | cost={sol_cost:.2f} ---")

            for item_idx, item in enumerate(sol, start=1):
                c = item["campaign"]
                s = item["segment"]
                print( f"  - {item_idx}) Campaign {c.campaign_id} | cost={item['cost']:.2f} | "
                    f"clicks={s.clicks} | purchases={s.purchases} | engagement={s.engagement} |  weight={s.weight}" )

        return result

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    def _ricorsione(self, i, candidates, budgetMax, parziale, cost_sum, score_sum):

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

        self._ricorsione(i+1, candidates, budgetMax, parziale, cost_sum, score_sum)
        cand = candidates[i]
        parziale.append(cand)
        self._ricorsione(i+1, candidates, budgetMax, parziale, cost_sum + cand["cost"], score_sum + cand["score"])
        parziale.pop()


    # ECONOMICS
    # ---------------------------------------------------------------------------------------------------------------------------------------------
    def getEconomicEvaluationForBestSolution(self):
        """
            Calculate target ROI, profit, and VPP break-even ONLY on the best solution.
            This function will be called by the controller when you press 'Economic Evaluation'
        """
        if self.best == None:
            return None

        # Campagne in best
        campaign_ids = [item["campaign"].campaign_id for item in self.best]
        target_user_ids = list(self._idMapUser.keys())
        impr_totals_DAO = DAO.getCampaignTotals(campaign_ids)                                      # impressioni di tutti gli user presenti (DB)
        impr_target_DAO = DAO.getCampaignImpressionsOnTarget(campaign_ids, target_user_ids)        # impressioni solo degli user target

        cost_alloc_tot = 0.0
        purchases_tot = 0
        clicks_tot = 0
        engagement_tot = 0

        for item in self.best:
            c = item["campaign"]
            segment = item["segment"]

            impr_total = int(impr_totals_DAO.get(c.campaign_id, {}).get("impressions", 0))
            impr_target = int(impr_target_DAO.get(c.campaign_id, 0))

            share = (impr_target / impr_total) if impr_total > 0 else 0.0
            cost_alloc = float(getattr(c, "total_budget", 0.0)) * share
            cost_alloc_tot += cost_alloc

            purchases_tot += int(getattr(segment, "purchases", 0) or 0)
            clicks_tot += int(getattr(segment, "clicks", 0) or 0)
            engagement_tot += int(getattr(segment, "engagement", 0) or 0)


        revenue = (purchases_tot * self.vpp)
        profit = revenue - cost_alloc_tot

        roi = None
        if cost_alloc_tot > 0:
            roi = profit / cost_alloc_tot

        break_even_vpp = None
        if purchases_tot > 0 and cost_alloc_tot > 0:
            break_even_vpp = cost_alloc_tot / purchases_tot

        mapEconomicEvaluation = {"cost_allocated": f"{cost_alloc_tot:.2f} €",
                                "revenue": f"{revenue:.2f} €",
                                "profit": f"{profit:.2f} €",
                                "roi_target": f"{roi * 100:.2f} %" if roi is not None else "N/A",
                                "break_even_vpp": f"{break_even_vpp:.2f} €" if break_even_vpp is not None else "N/A",
                                "purchases": purchases_tot,
                                "clicks": clicks_tot,
                                "engagement": engagement_tot}

        return mapEconomicEvaluation


if __name__ == "__main__":
    m = Model()
    m.buildGraph(50000, "Female" , "25-34", "France", "fashion", "lifestyle")
    print(m.getDetailsGraph())
    print(m.getId(50000, "Female" , "25-34", "France", "fashion", "lifestyle"))
    print(m.ottimizzaMetriche(50000, "click", 30, None))
    print(m.getEconomicEvaluationForBestSolution())
    #m.buildGraph(50000, "Male" , "25-34", "United States", "fitness", "technology")
    #print(m.getDetailsGraph())
    #print(m.getId(50000, "Male" , "25-34", "United States", "fitness", "technology"))
    #print(m.ottimizzaMetriche(50000, "conversioni", 30, None))
    #print(m.getEconomicEvaluationForBestSolution())
    #m.buildGraph(42750, "", "", "United States", "finance", "technology")
    #print(m.getDetailsGraph())
    #print(m.getId(42750, "", "", "United States", "finance", "technology"))
    #print(m.ottimizzaMetriche(42750, "conversioni", 100, 365))
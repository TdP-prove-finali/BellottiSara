from typing import Optional, List, Set
import flet as ft

class Controller:
    def __init__(self, view, model):

        self._view = view
        self._model = model

        # stato interno --> per evitare "ottimizza" senza aver analizzato
        self._graph_built = False
        self._has_best_solution = False

        # ultimi vincoli usati
        self._realBudgetMax = 0.0
        self._score_selected = None

        #intesessi (checkbox)
        self._interest_checkboxes = []
        self._all_interests = []

        # ultimo risultato ottimizzazione (per alternative/economic eval)
        self._last_result = None


    # FUNZIONI DI SERVIZIO
    #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def _set_summary(self, text, color=None):
        """
            Every time something happens (successful analysis, input error, optimization found, etc.), a message is displayed in a fixed area of the page.
        """
        if self._view.txt_selected_summary is None:
            return
        self._view.txt_selected_summary.value = text
        if color is not None:
            self._view.txt_selected_summary.color = color


    def _reset_results_cards(self):
        """
        It simulates a ‘Reset’ button: whenever the user changes filters or reruns the analysis/optimization:
            - the system clears the interface state by removing the best solution
            - emptying the list of alternatives
            - disabling buttons that are not meaningful without a valid solution (Show alternatives, Economic evaluation)
            - resetting the _last_result cache
        """
        if self._view.best_card is not None:
            self._view.best_card.content = ft.Text("Qui comparirà la soluzione migliore dopo l'ottimizzazione", color=ft.colors.GREY_700 )

        if self._view.alts_list is not None:
            self._view.alts_list.controls.clear()

        if self._view.btn_show_alts is not None:
            self._view.btn_show_alts.disabled = True

        self._last_result = None

        if getattr(self._view, "btn_econ", None) is not None:
            self._view.btn_econ.disabled = True

        if getattr(self._view, "econ_content", None) is not None:
            self._view.econ_content.controls.clear()
            self._view.econ_content.controls.append( ft.Text("Premi “Valutazione economica” per calcolare ROI sul target, break-even e profitto", size=12, color=ft.colors.GREY_700 ))


    def _set_best_card_content(self, content: ft.Control):
        """
            Function to assign content to best_card, without repeating duplicate 3 lines
        """
        if self._view.best_card is None:
            return
        self._view.best_card.content = content


    def _show_progress(self, visible: bool):
        """
            Show/hide a progress bar or spinner during analysis/optimization
        """
        if self._view.progress is not None:
            self._view.progress.visible = visible
        self._view.progress.update()


    # UI FILTER DROPDOWN VALUES
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def fillDDGender(self):

        self._view.dd_gender.options = []
        self._view.dd_gender.options.append(ft.dropdown.Option("All"))

        gender = self._model.getAllUserGender()
        for g in gender:
            self._view.dd_gender.options.append( ft.dropdown.Option(g))
        self._view.dd_gender.value = "All"


    def fillDDAgeGroup(self):

        self._view.dd_age_group.options = []
        self._view.dd_age_group.options.append(ft.dropdown.Option("All"))

        age_group = self._model.getAllAgeGroup()
        for a in age_group:
            self._view.dd_age_group.options.append( ft.dropdown.Option(a))
        self._view.dd_age_group.value = "All"

    def fillDDCountry(self):

        self._view.dd_country.options = []
        self._view.dd_country.options.append(ft.dropdown.Option("All"))

        country = self._model.getAllCountry()
        for c in country:
            self._view.dd_country.options.append( ft.dropdown.Option(c))
        self._view.dd_country.value = "All"


    def fillCheckboxInterests(self):
        """
           Populate the interest checkbox column
        """
        if self._view.interests_col is None:
            return

        self._view.interests_col.controls.clear()
        self._interest_checkboxes.clear()
        self._all_interests.clear()
        self._view._selected_interests = []

        self._all_interests = self._model.getAllInterests()

        def on_interest_change(e: ft.ControlEvent):
            cb: ft.Checkbox = e.control  # checkbox che ha cambiato stato
            label = str(cb.label)

            if cb.value:  # sto selezionando
                if label not in self._view._selected_interests:
                    if len(self._view._selected_interests) >= 2:
                        # rollback: max 2
                        cb.value = False
                        self._set_summary(text="Puoi selezionare al massimo 2 interessi", color="red")
                        self._view.update_page()
                        return
                    self._view._selected_interests.append(label)
            else:  # sto deselezionando
                if label in self._view._selected_interests:
                    self._view._selected_interests.remove(label)

            # aggiorno mini-summary
            if len(self._view._selected_interests) == 0:
                self._set_summary(text="Interessi: nessun filtro applicato.", color=ft.colors.GREY_700)
            else:
                self._set_summary(text=f"Interessi selezionati: {', '.join(self._view._selected_interests)}", color=ft.colors.GREY_700)
            self._view.update_page()

        # creo checkbox
        for it in self._all_interests:
            cb = ft.Checkbox(label=it, value=False, on_change=on_interest_change)
            self._interest_checkboxes.append(cb)
            self._view.interests_col.controls.append(cb)

    # GRAPH
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def handle_graph(self, e):

        # reset output
        self._graph_built = False
        self._reset_results_cards()
        self._set_summary("Analisi in corso…", color=ft.colors.GREY_700)
        self._show_progress(True)
        self._view.update_page()

        # Leggo filtri target che sono tutti opzionali (dropdown vuoto -> None)
        def validaFiltriSelezionati(filtro):
            if filtro is None:
                return None
            if filtro == "" or filtro == "All":
                return None
            return filtro

        gender = validaFiltriSelezionati(self._view.dd_gender.value)
        age_group = validaFiltriSelezionati(self._view.dd_age_group.value)
        country = validaFiltriSelezionati(self._view.dd_country.value)

        # Interessi (0 , 1, 2)
        interest1 = None
        interest2 = None
        if getattr(self._view, "_selected_interests", None):
            if len(self._view._selected_interests) >= 1:
                interest1 = self._view._selected_interests[0]
            if len(self._view._selected_interests) >= 2:
                interest2 = self._view._selected_interests[1]

        # Budget obbligatorio
        budgetMax = self._view.tf_budget.value

        if budgetMax == "":
            self._show_progress(False)
            self._set_summary("Attenzione: inserisci un budget massimo per continuare", color="red")
            self._view.update_page()
            return

        try:
            numbudgetMax = float(budgetMax)
            if numbudgetMax <= 0:
                raise ValueError("budget <= 0")
            self._realBudgetMax = numbudgetMax
        except ValueError:
            self._show_progress(False)
            self._set_summary("Attenzione: inserisci un numero valido (> 0) per il budget", color="red")
            self._view.update_page()
            return

        # Build graph
        self._model.buildGraph(self._realBudgetMax, gender, age_group, country, interest1, interest2)
        numNodi, numArchi = self._model.getDetailsGraph()
        numNodiCampaign, numNodiUser = self._model.getNumNodesCampaignUsers()

        # Caso senza archi -> niente ottimizzazione
        if numArchi == 0:
            self._set_summary(text=f"Nessuna interazione osservabile con i filtri attuali. \nProva ad allentare i vincoli (es. togli gender o country)", color="red")
            self._graph_built = True  # il grafo esiste ma è “vuoto di segnali utili”
            self._view.update_page()
            return

        # Caso con archi
        self._set_summary(text=f"Analisi completata. \nCampagne: {numNodiCampaign} | Utenti: {numNodiUser} | Collegamenti: {numArchi} \nOra puoi avviare l’ottimizzazione", color=ft.colors.GREEN_700)
        self._graph_built = True
        self._show_progress(False)
        self._view.update_page()

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def read_score(self, e):
        """
            This function reads the goal selected by the user from the dropdown menu (e.g. Click, Conversions, Engagement, Performance Index)
            and stores it inside the controller
        """
        self._score_selected = self._view.dd_goal.value  # es. "Click", "Conversioni", ...
        if self._score_selected == "":
            self._set_summary("Attenzione: inserisci un goal da raggiungere per continuare", color="red")
            self._view.update_page()
        self._view.update_page()

    def getScoreSelected(self, score_ui):
        """
            This function converts the goal selected in the user interface into a
            standardized string that can be correctly interpreted by the model
        """
        if not score_ui:
            return ""

        s = score_ui.strip().lower()

        # dropdown UI: "Click", "Conversioni", "Engagement", "Performance index"
        if s.startswith("click"):
            return "click"
        if s.startswith("conversion"):
            return "conversioni"
        if s.startswith("engagement"):
            return "engagement"
        if s.startswith("performance"):
            return "performance index"
        return s

    # OTTIMIZZAZIONE E RICORSIONE
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def handle_optimize(self, e):

        # Devo aver analizzato prima
        if not self._graph_built:
            self._set_summary("Prima premi “Analizza vincoli”, poi puoi ottimizzare", color="red")
            self._view.update_page()
            return

        # Score
        score_ui = (self._view.dd_goal.value or "").strip()
        if score_ui == "" or None:
            self._set_summary("Seleziona un obiettivo (score) per continuare.", color="red")
            self._view.update_page()
            return
        score = self.getScoreSelected(score_ui)

        # Durata (opzionale)
        duration_raw = self._view.tf_duration.value
        durationMax = None
        if duration_raw != "":
            try:
                durationMax = int(duration_raw)
                if durationMax <= 0:
                    raise ValueError("duration <=0")
            except ValueError:
                self._set_summary(text="Durata massima: inserisci un intero valido (> 0) oppure lascia vuoto", color="red")
                self._view.update_page()
                return

        # Value per purchase
        vpp_raw = self._view.tf_value_per_purchase.value
        if vpp_raw == "":
            self._set_summary(text="Attenzione, inserire il valore per acquisto (€).", color="red")
            self._view.update_page()
            return
        try:
            vpp = float(vpp_raw)
            if vpp < 0:
                raise ValueError("vpp < 0")
        except ValueError:
            self._set_summary(text="Valore per acquisto: inserisci un numero reale valido (>= 0).", color="red")
            self._view.update_page()
            return

        # Ottimizzazione
        self._show_progress(True)
        self._set_summary("Ottimizzazione in corso…", color=ft.colors.GREY_700)
        self._view.update_page()

        result = self._model.ottimizzaMetriche( budgetMax=self._realBudgetMax,
                                                goal=score,
                                                value_per_purchase=vpp,
                                                durationMax=durationMax,
                                                )

        self._show_progress(False)
        self._last_result = result

        # no solutions (o nessun candidato)
        best_campaigns = result.get("best_campaigns", [])
        best_segments = result.get("best_segments", [])
        if not best_campaigns:
            self._reset_results_cards()
            self._set_summary(text="Nessuna combinazione valida trovata con questi vincoli. \nProva ad aumentare il budget, togliere interessi o alzare la durata massima", color="red")
            self._view.update_page()
            return

        # si solution
        self._has_best_solution = True
        self._score_selected = score
        total_cost = float(result.get("total_cost_full", 0.0))
        best_score = result.get("best_score", 0.0)

        header = ft.Column( spacing=4,
                            controls=[ ft.Text("Soluzione migliore", size=18, weight=ft.FontWeight.W_800,),
                                       ft.Text(f"Obiettivo: {score}", color=ft.colors.GREY_700) ] )

        kpi_row = ft.ResponsiveRow( columns=12,
                                    controls=[ ft.Container(col=4, content=ft.Text(f"Score totale: {best_score}", weight=ft.FontWeight.W_700)),
                                               ft.Container(col=4, content=ft.Text(f"Costo totale: € {total_cost:,.2f}", weight=ft.FontWeight.W_700)) ] )

        #elenco campagne (con KPI segment)
        items = []
        for c, s in zip(best_campaigns, best_segments):
            items.append( ft.Container( padding=ft.padding.all(10),
                                        border=ft.border.all(1, ft.colors.GREY_200),
                                        border_radius=14,
                                        content=ft.Column( spacing=2,
                                                           controls=[ ft.Text(str(c), weight=ft.FontWeight.W_700),
                                                                      ft.Text(f"Impressions: {s.impressions} | Clicks: {s.clicks} | Engagement: {s.engagement} | Purchases: {s.purchases} | Users reached: {s.n_users_reached}",
                                                                              size=12,
                                                                              color=ft.colors.GREY_700 )],
                                                           )
                                        )
                          )

        body = ft.Column(spacing=10, controls=[header, ft.Divider(), kpi_row, ft.Divider(), *items])
        self._set_best_card_content(body)

        # Attivo bottone alternative
        n_alts = int(result.get("n_alternatives", 0))
        if self._view.btn_show_alts is not None:
            self._view.btn_show_alts.disabled = (n_alts <= 0)

        self._set_summary(f"Ottimizzazione completata! Trovata la soluzione migliore " + (f" + {n_alts} alternative." if n_alts > 0 else "."), color=ft.colors.GREEN_700)

        # reset alternative list (verrà popolata solo quando premi il bottone)
        if self._view.alts_list is not None:
            self._view.alts_list.controls.clear()

        # abilito valutazione economica SOLO se esiste best
        if getattr(self._view, "btn_econ", None) is not None:
            self._view.btn_econ.disabled = False

        # reset contenuto economico (finché non premi il bottone)
        if getattr(self._view, "econ_content", None) is not None:
            self._view.econ_content.controls.clear()
            self._view.econ_content.controls.append( ft.Text("Ora puoi premere “Valutazione economica” per calcolare ROI sul target, break-even e profitto.", size=12, color=ft.colors.GREY_700) )
        self._view.update_page()

    # ECONOMIC
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def handle_economic_evaluation(self, e):

        # Sicurezza: serve una best solution
        if not self._last_result or not self._last_result.get("best_campaigns"):
            self._set_summary("Prima esegui l’ottimizzazione: non c’è ancora una soluzione migliore", color="red")
            if getattr(self._view, "btn_econ", None) is not None:
                self._view.btn_econ.disabled = True
            self._view.update_page()
            return

        econ = self._model.getEconomicEvaluationForBestSolution()
        if econ is None:
            self._set_summary("Impossibile calcolare la valutazione economica in questo momento", color="red")
            self._view.update_page()
            return

        # Estraggo (sono già stringhe formattate per € e % in modello.py)
        roi_target = econ.get("roi_target", "N/A")
        break_even = econ.get("break_even_vpp", "N/A")
        profit = econ.get("profit", "N/A")
        cost_alloc = econ.get("cost_allocated", "N/A")
        revenue = econ.get("revenue", "N/A")

        # Costruisco un riquadro ordinato
        if getattr(self._view, "econ_content", None) is None:
            self._set_summary("UI non pronta: ricarica la pagina.", color="red")
            self._view.update_page()
            return

        header = ft.Column( spacing=2,
                            controls=[ ft.Text("Valutazione economica (sul target)", size=16, weight=ft.FontWeight.W_700),
                                       ft.Text("Il costo è allocato in proporzione alle impressions del target rispetto al totale campagna.",
                                        size=12, color=ft.colors.GREY_700)],
                            )

        main_economic_metrics = ft.ResponsiveRow( columns=12,
                                      controls=[ ft.Container(col=4, content=ft.Text(f"ROI target: {roi_target}", weight=ft.FontWeight.W_700)),
                                                 ft.Container(col=4, content=ft.Text(f"Break-even VPP: {break_even}", weight=ft.FontWeight.W_700)),
                                                 ft.Container(col=4, content=ft.Text(f"Profitto: {profit}", weight=ft.FontWeight.W_700)) ],
                                      )

        details = ft.Column( spacing=2,
                             controls=[ ft.Text(f"Costo allocato (target): {cost_alloc}", size=12, color=ft.colors.GREY_700),
                                        ft.Text(f"Ricavi stimati (target): {revenue}", size=12, color=ft.colors.GREY_700)],
                             )

        self._view.econ_content.controls.clear()
        self._view.econ_content.controls.extend([header, ft.Divider(), main_economic_metrics, ft.Divider(), details])

        self._set_summary("Valutazione economica calcolata sulla soluzione migliore", color=ft.colors.GREEN_700)
        self._view.update_page()

    # ALTERNATIVE
    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def read_alternatives(self, e):

        if not self._last_result:
            return

        alts = self._last_result.get("alternatives", [])
        if not alts:
            # nulla da mostrare
            if self._view.alts_list is not None:
                self._view.alts_list.controls.clear()
                self._view.alts_list.controls.append(
                    ft.Text("Nessuna alternativa disponibile.", color=ft.colors.GREY_700)
                )
            self._view.update_page()
            return

        if self._view.alts_list is None:
            return

        self._view.alts_list.controls.clear()

        for idx, sol in enumerate(alts, start=1):
            campaigns = sol.get("campaigns", [])
            segments = sol.get("segments", [])
            tot_cost = float(sol.get("total_cost_full", 0.0))

            title = ft.Text(f"Alternativa {idx}", weight=ft.FontWeight.W_700)
            meta = ft.Text(f"Costo: € {tot_cost:,.2f}", size=12, color=ft.colors.GREY_700)

            rows = []
            for c, s in zip(campaigns, segments):
                rows.append( ft.Text(f"- {c}   | clicks={s.clicks} | purchases={s.purchases} | engagement={s.engagement} | users={s.n_users_reached}", size=12, ) )

            self._view.alts_list.controls.append(
                ft.Container( padding=ft.padding.all(10),
                              border=ft.border.all(1, ft.colors.GREY_200),
                              border_radius=14,
                              content=ft.Column(spacing=4,
                                                controls=[title, meta, *rows]),
                              )
            )

        self._view.update_page()



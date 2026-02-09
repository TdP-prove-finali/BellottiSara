from typing import Optional, List, Set
import flet as ft

class Controller:
    def __init__(self, view, model):

        self._view = view
        self._model = model

        #??
        # stato interno (utile per evitare "ottimizza" senza aver analizzato)
        self._graph_built: bool = False
        self._numbudgetMax: float = 0.0
        self._score_ui: Optional[str] = None

        #intesessi (checkbox)
        self._interest_checkboxes: List[ft.Checkbox] = []
        self._all_interests: List[str] = []

        #score scelto
        self._scoreSelected = None

        # ultimo risultato ottimizzazione (per bottone alternative)
        self._last_result: Optional[dict] = None

    #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
    #HELPER UI (spiegami meglio che non sto capendo nulls)
    def _set_summary(self, text: str, color: Optional[str] = None):

        if self._view.txt_selected_summary is None:
            return
        self._view.txt_selected_summary.value = text
        if color is not None:
            self._view.txt_selected_summary.color = color


    def _reset_results_cards(self):
        # best card reset
        if self._view.best_card is not None:
            self._view.best_card.content = ft.Text(
                "Qui comparirà la soluzione migliore dopo l'ottimizzazione.",
                color=ft.colors.GREY_700,
            )

        # alternatives reset
        if self._view.alts_list is not None:
            self._view.alts_list.controls.clear()

        if self._view.btn_show_alts is not None:
            self._view.btn_show_alts.disabled = True

        self._last_result = None


    def _set_best_card_content(self, content: ft.Control):

        if self._view.best_card is None:
            return
        self._view.best_card.content = content


    def _show_progress(self, visible: bool):

        if self._view.progress is not None:
            self._view.progress.visible = visible

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

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def fillCheckboxInterests(self):
        """
           Popola la colonna di checkbox interessi.
           Il DB può contenere interessi come stringhe CSV: 'fashion, lifestyle' ecc.
           Qui normalizziamo, rimuoviamo duplicati e creiamo checkbox (max 2 selezionabili).
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
                        self._set_summary(text="Puoi selezionare al massimo 2 interessi.",
                                          color=ft.colors.RED_600,
                                          )
                        self._view.update_page()
                        return
                    self._view._selected_interests.append(label)
            else:  # sto deselezionando
                if label in self._view._selected_interests:
                    self._view._selected_interests.remove(label)

            # aggiorno mini-summary
            if len(self._view._selected_interests) == 0:
                self._set_summary(text="Interessi: nessun filtro applicato.",
                                  color=ft.colors.GREY_700)
            else:
                self._set_summary(text=f"Interessi selezionati: {', '.join(self._view._selected_interests)}",
                                  color=ft.colors.GREY_700,
                                  )
            self._view.update_page()

        # creo checkbox
        for it in self._all_interests:
            cb = ft.Checkbox(label=it, value=False, on_change=on_interest_change)
            self._interest_checkboxes.append(cb)
            self._view.interests_col.controls.append(cb)

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def handle_graph(self, e):

        #non lo so
        # reset output
        self._graph_built = False
        self._reset_results_cards()
        self._set_summary("Analisi in corso…", color=ft.colors.GREY_700)
        self._show_progress(True)
        self._view.update_page()

        #Leggo filtri target che sono tutti opzionali (dropdown vuoto -> None)
        def validaFiltriSelezionati(filtro):
            if filtro is None:
                return None
            if filtro == "" or filtro == "All":
                return None
            return filtro

        gender = validaFiltriSelezionati(self._view.dd_gender.value)
        age_group = validaFiltriSelezionati(self._view.dd_age_group.value)
        country = validaFiltriSelezionati(self._view.dd_country.value)


        #Interessi (0 , 1, 2)
        interest1 = None
        interest2 = None
        if getattr(self._view, "_selected_interests", None):
            if len(self._view._selected_interests) >= 1:
                interest1 = self._view._selected_interests[0]
            if len(self._view._selected_interests) >= 2:
                interest2 = self._view._selected_interests[1]

        #budget obbligatorio
        budgetMax = self._view.tf_budget.value

        if budgetMax == "":
            #come si chiama in view la variabile dove stampo il risultato cosi attacco questa??
            self._show_progress(False)
            self._set_summary("Attenzione: inserisci un budget massimo per continuare.", color="red")
            self._view.update_page()
            return

        try:
            numbudgetMax = float(budgetMax)
            if numbudgetMax <= 0:
                raise ValueError("budget <= 0")
            self._numbudgetMax = numbudgetMax
        except ValueError:
            self._show_progress(False)
            self._set_summary("Attenzione: inserisci un numero valido (> 0) per il budget.", color="red")
            self._view.update_page()
            return

        #build graph
        self._model.buildGraph(self._numbudgetMax, gender, age_group, country, interest1, interest2)
        numNodi, numArchi = self._model.getDetailsGraph()
        numNodiCampaign, numNodiUser = self._model.getNumNodesCampaignUsers()

        #caso senza archi
        if numArchi == 0:
            self._set_summary(text=f"Nessuna interazione osservabile con i filtri attuali. "
                                   f"Prova ad allentare i vincoli (es. togli interessi o country).",
                              color="red",
                              )
            self._graph_built = True  # il grafo esiste ma è “vuoto di segnali utili”
            self._view.update_page()
            return

        #caso con archi
        self._set_summary(text=f"Analisi completata. \nCampagne: {numNodiCampaign} | Utenti: {numNodiUser} | Collegamenti: {numArchi}"
                               f"\nOra puoi avviare l’ottimizzazione.",
                          color=ft.colors.GREEN_700,
                          )
        self._graph_built = True
        self._show_progress(False)
        self._view.update_page()

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def read_score(self, e):
        """
            funzione che legge lo score che ha scelto l'utente e in base ad esso può applicare l'algoritmo ricorsivo
            bisogna quindi salvare la variabile (da view.py viene salvata da un dropdown serve salvare la stringa con il nome)
            :return:
        """
        self._scoreSelected = self._view.dd_goal.value  # es. "Click", "Conversioni", ...
        if self._scoreSelected == "":
            #capire in quale blocco testo scrivere
            self._set_summary("Attenzione: inserisci un goal da raggiungere per continuare.", color="red")
            self._view.update_page()
        self._view.update_page()

    def getScoreSelected(self, score_ui):
        """
        Non trovo metodo migliore per salvare quanto scelto nel dd e riutilizzarlo
        :param score_ui:
        :return:
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



# -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def handle_optimize(self, e):
        """
        in base allo score scelto cerca l'opzione migliore
        :return:
        """
        # devo aver analizzato prima
        if not self._graph_built:
            self._set_summary("Prima premi “Analizza vincoli”, poi puoi ottimizzare.", color="red")
            self._view.update_page()
            return

        # score
        score_ui = self._view.dd_goal.value
        if score_ui.strip() == "":
            self._set_summary("Seleziona un obiettivo (score) per continuare.", color="red")
            self._view.update_page()
            return

        score = self.getScoreSelected(score_ui)

        # durata (opzionale)
        duration_raw = self._view.tf_duration.value
        durationMax = None
        if duration_raw != "":
            try:
                durationMax = int(duration_raw)
                if durationMax <= 0:
                    raise ValueError("duration <=0")
            except ValueError:
                self._set_summary(text="Durata massima: inserisci un intero valido (> 0) oppure lascia vuoto.",
                                  color="red")
                self._view.update_page()
                return

        #value per purchase
        vpp_raw = self._view.tf_value_per_purchase.value
        if vpp_raw == "":
            self._set_summary(text="Attenzione, inserire il valore per acquisto (€).",
                              color="red")
            self._view.update_page()
            return
        try:
            vpp = float(vpp_raw)
            if vpp < 0:
                raise ValueError("vpp < 0")
        except ValueError:
            self._set_summary(text="Valore per acquisto: inserisci un numero reale valido (>= 0).",
                              color="red")
            self._view.update_page()
            return

        #ottimizzazione
        self._show_progress(True)
        self._set_summary("Ottimizzazione in corso…", color=ft.colors.GREY_700)
        self._view.update_page()

        result = self._model.ottimizzaMetriche( budgetMax=self._numbudgetMax,
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
            self._set_summary(text="Nessuna combinazione valida trovata con questi vincoli. "
                                   "Prova ad aumentare il budget, togliere interessi o alzare la durata massima.",
                              color="red",
                              )
            self._view.update_page()
            return

        # si solution
        total_cost = float(result.get("total_cost_full", 0.0))
        total_revenue = float(result.get("total_revenue_target", 0.0))
        roi_tot = float(result.get("roi_tot", 0.0))
        best_score = result.get("best_score", 0.0)

        header = ft.Column( spacing=4,
                            controls=[ ft.Text("Soluzione migliore", size=18, weight=ft.FontWeight.W_800,),
                                       ft.Text(f"Obiettivo: {score}", color=ft.colors.GREY_700),
                                       ],
                            )

        kpi_row = ft.ResponsiveRow( columns=12,
                                    controls=[ ft.Container(col=4, content=ft.Text(f"Score totale: {best_score}", weight=ft.FontWeight.W_700)),
                                               ft.Container(col=4, content=ft.Text(f"Costo totale: € {total_cost:,.2f}", weight=ft.FontWeight.W_700)),
                                               ft.Container(col=4, content=ft.Text(f"Ricavi stimati: € {total_revenue:,.2f}", weight=ft.FontWeight.W_700)),
                                               ],
                                    )

        #elenco campagne (con KPI segment)
        items = []
        for c, s in zip(best_campaigns, best_segments):
            items.append( ft.Container( padding=ft.padding.all(10),
                                        border=ft.border.all(1, ft.colors.GREY_200),
                                        border_radius=14,
                                        content=ft.Column( spacing=2,
                                                           controls=[ ft.Text(str(c), weight=ft.FontWeight.W_700),
                                                                      ft.Text(f"Impressions: {s.impressions} | Clicks: {s.clicks} | "
                                                                            f"Engagement: {s.engagement} | Purchases: {s.purchases} | "
                                                                            f"Users reached: {s.n_users_reached}",
                                                                              size=12,
                                                                              color=ft.colors.GREY_700,
                                                                              ),
                                                                      ],
                                                           ),
                                        )
                          )

        body = ft.Column(spacing=10, controls=[header, ft.Divider(), kpi_row, ft.Divider(), *items])
        self._set_best_card_content(body)

        # Attivo bottone alternative
        n_alts = int(result.get("n_alternatives", 0))
        if self._view.btn_show_alts is not None:
            self._view.btn_show_alts.disabled = (n_alts <= 0)

        self._set_summary(f"Ottimizzazione completata! Trovata la soluzione migliore"
            + (f" + {n_alts} alternative." if n_alts > 0 else "."),
            color=ft.colors.GREEN_700,
                        )

        # reset alternative list (verrà popolata solo quando premi il bottone)
        if self._view.alts_list is not None:
            self._view.alts_list.controls.clear()

        self._view.update_page()

    # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    def toggle_alternatives(self, e):
        """
        metodo che permette di leggere le soluzioni alternative se cliccato il bottone btn_show_alts che diventa avaible solo nel caso in cui result della soluzione ottima abbia len di alternative >0
        :return:
        """
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
            tot_rev = float(sol.get("total_revenue_target", 0.0))

            title = ft.Text(f"Alternativa {idx}", weight=ft.FontWeight.W_700)
            meta = ft.Text(f"Costo: € {tot_cost:,.2f} | Ricavi stimati: € {tot_rev:,.2f}", size=12,
                           color=ft.colors.GREY_700)

            rows = []
            for c, s in zip(campaigns, segments):
                rows.append( ft.Text(f"- {c}  | clicks={s.clicks}, purchases={s.purchases}, engagement={s.engagement}, users={s.n_users_reached}", size=12, ) )

            self._view.alts_list.controls.append(
                ft.Container( padding=ft.padding.all(10),
                              border=ft.border.all(1, ft.colors.GREY_200),
                              border_radius=14,
                              content=ft.Column(spacing=4,
                                                controls=[title, meta, *rows]),
                              )
            )
        self._view.update_page()



from typing import List
import flet as ft

class View(ft.UserControl):
    def __init__(self, page: ft.Page):
        super().__init__()

        # page setup
        self._page = page
        self._page.title = "Progetto di Tesi"
        self._page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self._page.scroll = ft.ScrollMode.AUTO
        self._page.theme_mode = ft.ThemeMode.LIGHT

        # controller (settato dal main)
        self._controller = None

        # vincoli UI
        self.dd_gender: ft.Dropdown = None
        self.dd_age_group: ft.Dropdown = None
        self.dd_country: ft.Dropdown = None

        self.interests_col: ft.Column = None
        self._selected_interests: List[str] = []  # max 2

        self.tf_budget: ft.TextField = None
        self.dd_goal: ft.Dropdown = None
        self.tf_duration: ft.TextField = None
        self.tf_value_per_purchase: ft.TextField = None

        self.btn_analyze: ft.ElevatedButton = None
        self.btn_optimize: ft.FilledButton = None
        self.btn_show_alts: ft.OutlinedButton = None

        self.txt_selected_summary: ft.Text = None
        self.best_card: ft.Container = None
        self.alts_card: ft.Container = None
        self.alts_list: ft.Column = None

        # overlay (facoltativo)
        self.progress = ft.ProgressRing(visible=False)



    def load_interface(self):
        # title
        #self._title = ft.Text("Social Ads Budget Optimizer", color="purple", size=24)
        #self._page.controls.append(self._title)

        #vorrei strutturare che da un lato si selezionano i filtri per il pubblico che si vuole raggiungere (4 vincoli, 3dd e 1checkbox)
        #-- dropdown x 3 vincoli
        self.dd_gender = ft.Dropdown(label = "Gender",
                                     hint_text = "Se non selezioni nulla, considero tutti",
                                     border_radius = 14,
                                     filled = True,
                                     value = "All",
                                     )
        self.dd_age_group  = ft.Dropdown(label = "Age group",
                                         hint_text = "Se non selezioni nulla, considero tutti",
                                         border_radius = 14,
                                         filled = True,
                                         value = "All",
                                         )
        self.dd_country = ft.Dropdown(label = "Country",
                                      hint_text = "Se lasci vuoto, nessun filtro geografico",
                                      border_radius = 14,
                                      filled = True,
                                      value = "All",
                                      )

        self.interests_col = ft.Column(spacing=6)  # verrà popolata dal controller

        self._controller.fillDDGender()
        self._controller.fillDDAgeGroup()
        self._controller.fillDDCountry()
        self._controller.fillCheckboxInterests()

        #ANALIZZO----------------------------------------------------------------------------------------------------------------
        self.tf_budget = ft.TextField( label="Budget cup (€)",
                                       hint_text="Es. 50000",
                                       helper_text="Limita le campagne disponibili (vincolo sul grafo).",
                                       keyboard_type=ft.KeyboardType.NUMBER,
                                       border_radius=14,
                                       filled=True,
                                       prefix_icon=ft.icons.EURO,
                                       )

        #passaggio 1 --> verifica se esiste un grafo osservabile (da spiegare meglio)
        self.btn_analyze = ft.ElevatedButton(text="Analizza vincoli",
                                             icon=ft.icons.SEARCH,
                                             on_click=self._controller.handle_graph)

        #OTTIMIZZAZIONE-----------------------------------------------------------------------------------------------------------
        #sezione di testo che riporta il risultato dell'analisi (qui serve solo il riquadro del testo, il testo effettivo arriva dal controller.py)
        #mi piacerebbe fosse una parte diversa dallo sfondo
        #parte di ottimizzazione secondo "score" scelto dall'utente --> in seguito a quali utenti e campagne ci rivogliamo, qual è lo scopo che vuoi raggiungere?
        self.dd_goal = ft.Dropdown(label="Obiettivo (score)",
                                   hint_text="Scegli cosa vuoi massimizzare",
                                   options=[ft.dropdown.Option("Click"),
                                            ft.dropdown.Option("Conversioni"),
                                            ft.dropdown.Option("Engagement (like,comment,share)"),
                                            ft.dropdown.Option("Performance index"), ],
                                   border_radius=14,
                                   on_change=self._controller.read_score,
                                   )
        self.tf_duration = ft.TextField(label="Durata massima (n° di giorni) — opzionale",
                                        hint_text="Es. 30",
                                        helper_text="Esclude campagne troppo lunghe",
                                        keyboard_type=ft.KeyboardType.NUMBER,
                                        border_radius=14,
                                        filled=True,
                                        prefix_icon=ft.icons.CALENDAR_MONTH,
                                        )
        self.tf_value_per_purchase = ft.TextField( label="Valore per acquisto (€) — usato per ROI",
                                                    hint_text="Es. 50",
                                                    helper_text="Serve per calcolare il ROI",
                                                    keyboard_type=ft.KeyboardType.NUMBER,
                                                    border_radius=14,
                                                    filled=True,
                                                    value="50",
                                                    prefix_icon=ft.icons.PAID,
                                                   )
        self.btn_optimize = ft.FilledButton("Ottimizza",
                                            icon=ft.icons.AUTO_AWESOME,
                                            on_click=self._controller.handle_optimize,)

        self.btn_show_alts = ft.OutlinedButton( "Mostra alternative",
                                                icon=ft.icons.LAYERS,
                                                disabled=True,
                                                on_click=lambda e: self._controller.toggle_alternatives(e),
                                                )

        #SUDDIVIDIAMO IN AREE PER AVERE UN OUTPUT PIU' PULITO
        self.txt_selected_summary = ft.Text( value="Inserisci i vincoli e avvia l’analisi. Ti mostrerò quante campagne e quanti utenti" 
                                                   "rientrano nel tuo target, poi potrai ottimizzare.",
                                             color=ft.colors.GREY_700,
                                             )
        self.best_card = ft.Container( padding=ft.padding.all(16),
                                       border=ft.border.all(1, ft.colors.GREY_300),
                                       border_radius=18,
                                       bgcolor=ft.colors.WHITE,
                                       content=ft.Text("Qui comparirà la soluzione migliore dopo l'ottimizzazione.",
                                                       color=ft.colors.GREY_700),
                                       )

        self.alts_list = ft.Column(spacing=10)
        self.alts_card = ft.Container( padding=ft.padding.all(16),
                                       border=ft.border.all(1, ft.colors.GREY_300),
                                       border_radius=18,
                                       bgcolor=ft.colors.WHITE,
                                       content=ft.Column( spacing=10,
                                                          controls=[ ft.Row( alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                                                             controls=[ ft.Text("Alternative",
                                                                                                size=16,
                                                                                                weight=ft.FontWeight.W_700),
                                                                                        ft.Icon(ft.icons.INFO_OUTLINE,
                                                                                                color=ft.colors.GREY_600), ],
                                                                             ),
                                                                     ft.Text( value="Mostrate solo se esistono soluzioni con lo stesso score ma costo totale maggiore.",
                                                                              size=12,
                                                                              color=ft.colors.GREY_700,
                                                                              ),
                                                                     self.alts_list,
                                                                     ],
                                                          ),
                                       )

        #Layout chiaro in card SPACE_BETWEEN
        header = ft.Container( padding=ft.padding.all(18),
                               border_radius=20,
                               bgcolor=ft.colors.BLUE_50,
                               content=ft.Row(
                                   alignment=ft.MainAxisAlignment.CENTER,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                   controls=[ ft.Row( spacing=46,
                                                      controls=[ ft.Icon(ft.icons.CAMPAIGN, color=ft.colors.BLUE_700, size=36),
                                                                 ft.Column( alignment=ft.MainAxisAlignment.CENTER,
                                                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                                                            spacing=4,
                                                                            controls=[ ft.Text(value="Social Ads Budget Optimizer", size=22,
                                                                                               weight=ft.FontWeight.W_800,
                                                                                               text_align=ft.TextAlign.CENTER,),
                                                                                       ft.Text(value= "Seleziona target e vincoli: troviamo la combinazione di campagne più efficiente.",
                                                                                               color=ft.colors.GREY_800,
                                                                                               text_align=ft.TextAlign.CENTER,
                                                                                               ),
                                                                                       ],
                                                                            ),
                                                                 ],
                                                      ),
                                              ft.Container( content=ft.Icon(ft.icons.INSIGHTS,
                                                                            color=ft.colors.BLUE_700,
                                                                            size=36
                                                                            )
                                                            ),
                                              ],
                               ),
                            )

        card_target = ft.Container( padding=ft.padding.all(16),
                                    border=ft.border.all(1, ft.colors.GREY_300),
                                    border_radius=18,
                                    bgcolor=ft.colors.WHITE,
                                    content=ft.Column( spacing=12,
                                                       controls=[ ft.Row( controls=[ ft.Icon(ft.icons.GROUPS,
                                                                                             color=ft.colors.BLUE_700),
                                                                                     ft.Text(value="Target utenti",
                                                                                             size=16,
                                                                                             weight=ft.FontWeight.W_700),
                                                                                     ]
                                                                          ),
                                                                  ft.Text(value="Questi filtri definiscono il pubblico. Scegliendo All non applicherai nessun filtro.",
                                                                          size=12,
                                                                          color=ft.colors.GREY_700,
                                                                          ),
                                                                  ft.ResponsiveRow( columns=12,
                                                                                    controls=[ ft.Container(col=4, content=self.dd_gender),
                                                                                               ft.Container(col=4, content=self.dd_age_group),
                                                                                               ft.Container(col=4, content=self.dd_country),
                                                                                               ],
                                                                                    ),
                                                                  ft.Container( padding=ft.padding.only(top=6),
                                                                                content=ft.Column( spacing=6,
                                                                                                   controls=[ ft.Text("Interessi (max 2)", weight=ft.FontWeight.W_600),
                                                                                                              ft.Container( padding=ft.padding.all(10),
                                                                                                                            border=ft.border.all(1, ft.colors.GREY_200),
                                                                                                                            border_radius=14,
                                                                                                                            content=self.interests_col,
                                                                                                                            ),
                                                                                                              ],
                                                                                                   ),
                                                                                ),
                                                                  ],
                                                       ),
                                    )

        card_campaign = ft.Container( padding=ft.padding.all(16),
                                      border=ft.border.all(1, ft.colors.GREY_300),
                                      border_radius=18,
                                      bgcolor=ft.colors.WHITE,
                                      content=ft.Column( spacing=12,
                                                         controls=[ ft.Row( controls=[ ft.Icon(ft.icons.TUNE,
                                                                                               color=ft.colors.BLUE_700),
                                                                                       ft.Text("Vincoli campagne pubblicitarie",
                                                                                               size=16,
                                                                                               weight=ft.FontWeight.W_700),
                                                                                       ]
                                                                            ),
                                                                    ft.Text(value="Prima analizziamo quante campagne e utenti sono compatibili, poi ottimizziamo.",
                                                                            size=12,
                                                                            color=ft.colors.GREY_700,
                                                                           ),
                                                                    ft.ResponsiveRow( columns=12,
                                                                                      controls=[ ft.Container(col=6, content=self.tf_budget),
                                                                                                 ft.Container(col=6, content=ft.Row( alignment=ft.MainAxisAlignment.END,
                                                                                                                                     controls=[self.progress, self.btn_analyze],
                                                                                                                                     ),
                                                                                                              ),
                                                                                                 ],
                                                                                      ),
                                                                    ft.Divider(),
                                                                    self.txt_selected_summary,
                                                                    ],
                                                         ),
                                      )

        card_optimize = ft.Container(
            padding=ft.padding.all(16),
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=18,
            bgcolor=ft.colors.WHITE,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.icons.AUTO_AWESOME, color=ft.colors.BLUE_700),
                            ft.Text("3) Ottimizzazione", size=16, weight=ft.FontWeight.W_700),
                        ]
                    ),
                    ft.Text(
                        "Scegli l’obiettivo (score). Facoltativamente imposta la durata massima. Poi avvia l’ottimizzazione.",
                        size=12,
                        color=ft.colors.GREY_700,
                    ),
                    ft.ResponsiveRow(
                        columns=12,
                        controls=[
                            ft.Container(col=4, content=self.dd_goal),
                            ft.Container(col=4, content=self.tf_duration),
                            ft.Container(col=4, content=self.tf_value_per_purchase),
                            ft.Container(
                                col=12,
                                content=ft.Row(
                                    alignment=ft.MainAxisAlignment.END,
                                    controls=[self.btn_optimize, self.btn_show_alts],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )

        card_results = ft.Container(
            padding=ft.padding.all(16),
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=18,
            bgcolor=ft.colors.WHITE,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.icons.INSIGHTS, color=ft.colors.BLUE_700),
                            ft.Text("Risultati", size=16, weight=ft.FontWeight.W_700),
                        ]
                    ),
                    self.best_card,
                    self.alts_card,
                ],
            ),
        )

        root = ft.Column(
            expand=True,
            spacing=14,
            controls=[ header,
                        ft.ResponsiveRow(columns=12, controls=[ft.Container(col=12, content=card_target)]),
                        ft.ResponsiveRow(columns=12, controls=[ft.Container(col=12, content=card_campaign)]),
                        ft.ResponsiveRow(columns=12, controls=[ft.Container(col=12, content=card_optimize)]),
                        ft.ResponsiveRow(columns=12, controls=[ft.Container(col=12, content=card_results)]),
                    ],
            )

        root_container = ft.Container( padding=ft.padding.all(18),
                             content=root,
                             expand=True
                             )

        self._page.controls.clear()
        self._page.add(root_container)
        self._page.update()

        # List View where the reply is printed
        #self.txt_result = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=True)
        #self._page.update()

    @property
    def controller(self):
        return self._controller

    @controller.setter
    def controller(self, controller):
        self._controller = controller

    def set_controller(self, controller):
        self._controller = controller

    def create_alert(self, message):
        dlg = ft.AlertDialog(title=ft.Text(message))
        self._page.dialog = dlg
        dlg.open = True
        self._page.update()

    def update_page(self):
        self._page.update()
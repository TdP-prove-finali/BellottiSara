import flet as ft

class Controller:
    def __init__(self, view, model):
        pass

    #devi normalizzare i parametri opzionali come None
    #def norm_optional(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value != "" else None

#checklist --> ottengo lista di questo tipo: selected = ["fashion", "lifestyle"]   # oppure [] oppure ["fashion"]
#qui devo anche normalizzare e limitare a max 2
selected = [s.strip() for s in selected if s and s.strip()]
selected = sorted(set(selected))   # evita duplicati e rende stabile l’ordine
selected = selected[:2]            # sicurezza max 2
#Poi passi al DAO due variabili separate (molto più semplice per la query):
interest1 = selected[0] if len(selected) >= 1 else None
interest2 = selected[1] if len(selected) >= 2 else None
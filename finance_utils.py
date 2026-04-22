def calculer_effort_projet(montant_total, mois):
    if mois <= 0: return 0
    jours = mois * 30.44  # Moyenne annuelle
    return round(montant_total / jours, 2)

def simulation_interets_composes(capital, taux_annuel, années):
    # Formule : A = P(1 + r)^n
    resultat = capital * (1 + (taux_annuel / 100)) ** années
    return round(resultat, 2)
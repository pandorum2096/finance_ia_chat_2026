import os
from database import Asset, Transaction
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

class FinanceCoach:
    def __init__(self):
        # On se connecte au serveur Ollama local
        self.llm = ChatOllama(
            model="llama3",
            # base_url="http://192.168.1.50:11434", # Remplace par l'IP du serveur
            temperature=0.7
        )
        self.system_prompt = SystemMessage(content="""
Tu es une IA financière experte en analyse de données clients, optimisation patrimoniale et stratégie financière avancée.

Ta mission est d’analyser les données financières fournies par le client et de produire des recommandations personnalisées, concrètes, chiffrées et actionnables afin d’optimiser :

- La rentabilité
- La fiscalité
- La gestion des risques
- La trésorerie
- L’allocation d’actifs
- Les investissements
- L’endettement
- La diversification
- Les opportunités de marché
- Les aides, subventions ou dispositifs légaux existants

Règles de fonctionnement :

1. Analyse toujours les données de manière structurée :
   - Revenus
   - Charges
   - Actifs
   - Passifs
   - Flux de trésorerie
   - Fiscalité
   - Objectifs du client
   - Horizon d’investissement
   - Tolérance au risque

2. Identifie :
   - Les inefficacités
   - Les pertes potentielles
   - Les risques excessifs
   - Les opportunités non exploitées
   - Les optimisations fiscales possibles
   - Les stratégies d’investissement adaptées
   - Les leviers d’effet de levier maîtrisé

3. Propose :
   - Des stratégies court terme
   - Des stratégies moyen terme
   - Des stratégies long terme
   - Des scénarios comparatifs
   - Des projections si pertinent

4. Priorise les recommandations par :
   - Impact financier
   - Niveau de risque
   - Complexité de mise en œuvre

5. Sois :
   - Factuel
   - Précis
   - Structuré
   - Transparent sur les hypothèses
   - Clair dans les risques associés

6. Si certaines données sont manquantes, identifie précisément ce qui manque et pose les questions nécessaires avant de conclure.

7. Ne donne jamais de conseils illégaux, non éthiques ou frauduleux.

Format de réponse attendu :
- Résumé exécutif
- Analyse détaillée
- Opportunités identifiées
- Recommandations priorisées
- Points de vigilance
- Questions complémentaires si nécessaires

Tu dois agir comme un conseiller financier senior avec une vision stratégique globale.
""")

    def get_response(self, user_input, history):
        messages = [self.system_prompt]
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        messages.append(HumanMessage(content=user_input))
        
        # Ollama traite la requête localement sur ton CPU/GPU
        response = self.llm.invoke(messages)
        return response.content
    
    def get_financial_summary(self, db_session, user_id):
        # Récupérer les données en DB
        assets = db_session.query(Asset).filter_by(user_id=user_id).all()
        recent_tx = db_session.query(Transaction).filter_by(user_id=user_id).limit(10).all()
        
        total_patrimoine = sum(a.value for a in assets)
        # Créer une chaîne de texte pour l'IA
        summary = f"Patrimoine total: {total_patrimoine}f. "
        summary += "Actifs: " + ", ".join([f"{a.name}: {a.value}f" for a in assets])
        return summary



















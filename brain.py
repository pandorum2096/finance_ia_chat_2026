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
            Tu es FINORIS, ton rôle est pas de gérer des comptes et de sculpter la liberté financière de l'utilisateur.

            ### 1. IDENTITÉ ET POSTURE
            - Nom : FINORIS.
            - Personnalité : Mentor direct, pragmatique et proactif. Tu agis comme un "coach sportif de la finance" : bienveillant mais sans complaisance.
            - Langage : Ton dynamique.
            - Unité Monétaire : Travaille exclusivement en Francs CFA (XOF). Ne confonds jamais avec l'Euro.

            ### 2. CAPACITÉS D'ANALYSE PRÉDICTIVE
            - Analyse de Flux 
            - Vision Portefeuille 
            - Psychologie 

            ### 3. RÈGLES DE RÉPONSE
            - Proactivité 
            - Formatage 
            - Rigueur 
            - Interdiction : Avertissement massif obligatoire (RISQUE DE PERTE TOTALE) pour tout actif non régulé ou volatile.
                                           
            ### 4. RÈGLES DE RÉPONSE
            - interdiction : n'invente pas de reponse si tu n'as pas d'information
            Tu es le stratège. Ton but ultime : transformer chaque Franc CFA entrant en une brique de l'empire financier de l'utilisateur.
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



















import os
from langchain_community.chat_models import ChatOllama  # Nouvel import
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
            Tu es l'IA 'Architecte', le moteur de Life Design financier de l'utilisateur.
            Ton rôle dépasse le conseil : tu es un stratège proactif.
            
            1. ANALYSE DE FLUX : Tu ne te contentes pas de répondre, tu analyses les chiffres cités. 
            Si un utilisateur parle de 700k, calcule immédiatement l'effort (Barra) sans qu'il le demande.
            
            2. PSYCHOLOGIE : Tu identifies les blocages. Si l'utilisateur dit 'C'est trop cher', 
            ne baisse pas juste le prix, propose une stratégie de revenus alternatifs ou une durée plus longue.
            
            3. HIÉRARCHIE DE SÉRÉNITÉ : 
            - Sécurité (Bouclier) : Interdis moralement l'investissement si le bouclier n'est pas plein.
            - Projets (Propulseur) : Transforme les envies en chiffres concrets.
            - Croissance (Multiplicateur) : Parle de bourse et crypto comme des outils de liberté.

            4. TON : Tu es un mentor, pas une machine. Utilise 'Barra' pour les phases d'effort. 
            Sois direct, presque comme un coach sportif, mais bienveillant.
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
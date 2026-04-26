import time
from sqlalchemy.orm import Session
from database import ChatMessage, Asset, Transaction

def sauvegarder_conseil_ia(user_id: str, conseil: str, db: Session):
    # On crée un message dans la table de chat pour que l'utilisateur le voie
    nouveau_message = ChatMessage(
        user_id=user_id,
        role="assistant",
        content=f"🤖 Conseil de l'Architecte : {conseil}"
    )
    db.add(nouveau_message)
    db.commit()
    print(f"Conseil sauvegardé pour {user_id}")

def analyser_patrimoine_et_conseiller(user_id: str, db: Session, coach):
    # 1. Simuler un délai (pour l'exemple) ou une analyse lourde
    # Dans la vraie vie, on pourrait attendre quelques minutes après une dépense
    time.sleep(5) 
    
    # 2. Récupérer les données de l'utilisateur
    assets = db.query(Asset).filter_by(user_id=user_id).all()
    total_patrimoine = sum(a.value for a in assets)
    
    # 3. Construire un prompt spécifique pour l'analyse proactive
    prompt = f"L'utilisateur a un patrimoine de {total_patrimoine}f. "
    prompt += "Analyse cela et donne un conseil stratégique court (1 phrase) pour le futur."
    
    # 4. Obtenir le conseil de l'IA (Ollama)
    conseil = coach.get_response(prompt, [])
    
    # 5. Stocker ce conseil dans l'historique pour que l'utilisateur le voie
    nouveau_conseil = ChatMessage(
        user_id=user_id, 
        role="assistant", 
        content=f"[CONSEIL PROACTIF] : {conseil}"
    )
    db.add(nouveau_conseil)
    db.commit()
    print(f"Analyse terminée pour {user_id}")

def analyser_flux_financier(user_id: str, db: Session, coach):
    # Récupérer les revenus et dépenses du mois
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    
    revenus = sum(t.amount for t in transactions if t.type == "Revenu")
    depenses = sum(t.amount for t in transactions if t.type == "Dépense")
    solde = revenus - depenses
    
    # Créer un prompt d'alerte ou de félicitation
    prompt = f"""
    Analyse de flux pour l'utilisateur :
    - Revenus totaux : {revenus}f
    - Dépenses totales : {depenses}f
    - Solde restant : {solde}f
    
    Si le solde est négatif ou très faible, donne un conseil de 'Barra'.
    Si le solde est bon, suggère d'investir l'excédent.
    Réponds en 1 phrase percutante.
    """
    
    conseil = coach.get_response(prompt, [])
    
    # Sauvegarder le conseil dans le chat
    sauvegarder_conseil_ia(user_id, conseil, db)






















    
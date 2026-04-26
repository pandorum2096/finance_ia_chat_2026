from database import SessionLocal, Asset, Transaction, Notification
from datetime import datetime # <--- Importation nécessaire

def job_conseil_financier(user_id, coach):
    db = SessionLocal()
    # Récupérer l'heure actuelle
    maintenant = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    try:
        # 1. Récupération des données pour le contexte
        assets = db.query(Asset).filter_by(user_id=user_id).all()
        transactions = db.query(Transaction).filter_by(user_id=user_id).all()
        
        total_assets = sum(a.value for a in assets)
        total_depenses = sum(t.amount for t in transactions if t.type == "Dépense")
        
        # 2. Demande à l'IA
        prompt = f"""
        En tant qu'Architecte, analyse ces chiffres :
        Patrimoine total : {total_assets}f.
        Dépenses totales cumulées : {total_depenses}f.
        Donne un conseil stratégique court pour optimiser le mode 'Barra' ou l'investissement.
        """
        conseil = coach.get_response(prompt, [])
        
        # 3. Insertion dans la table Notification
        new_notif = Notification(
            user_id=user_id,
            title="Conseil de l'Architecte",
            content=conseil
        )
        db.add(new_notif)
        db.commit()
        
        # Affichage avec la date et l'heure
        print(f"[{maintenant}] ✅ Notification générée pour {user_id}")
        
    except Exception as e:
        print(f"[{maintenant}] ❌ Erreur lors du job : {e}")
        
    finally:
        db.close()
# scheduler_tasks.py
import asyncio
from database import SessionLocal, Notification
from instances import manager, coach # <--- Importation propre ici

def job_conseil_financier(user_id): # On a retiré l'argument coach car il est importé
    db = SessionLocal()
    try:
        # 1. Ta logique de génération
        conseil = coach.get_response("Analyse mes finances...", []) 
        
        # 2. Sauvegarde DB
        new_notif = Notification(user_id=user_id, title="Conseil IA", content=conseil)
        db.add(new_notif)
        db.commit()

        # 3. Envoi WebSocket
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(manager.send_personal_message("NEW_NOTIFICATION", user_id))
        
    except Exception as e:
        print(f"❌ Erreur Job: {e}")
    finally:
        db.close()
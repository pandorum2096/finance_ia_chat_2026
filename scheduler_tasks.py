# scheduler_tasks.py
import asyncio
from database import SessionLocal, Notification, Asset
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

def job_conseil_financier_global():
    print("🔔 [SCHEDULER] Début de l'analyse globale...")
    db = SessionLocal()
    
    # 1. On prépare UNE SEULE boucle pour tout le job
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        users = db.query(Asset.user_id).distinct().all()
        user_ids = [u[0] for u in users]
        
        if not user_ids:
            print("⚠️ Aucun utilisateur avec des actifs trouvé.")
            return

        for user_id in user_ids:
            try:
                print(f"🤖 Génération pour : {user_id}")
                
                # 2. IA
                conseil = coach.get_response(f"Analyse le patrimoine de {user_id} et donne un conseil court.", [])
                
                # 3. Sauvegarde BDD
                new_notif = Notification(user_id=user_id, title="Conseil IA", content=conseil)
                db.add(new_notif)
                db.commit()
                
                # 4. Envoi WebSocket (Utilisation de la boucle déjà créée)
                try:
                    loop.run_until_complete(manager.send_personal_message("NEW_NOTIFICATION", user_id))
                    print(f"📡 WebSocket envoyé à {user_id}")
                except Exception as ws_err:
                    print(f"ℹ️ {user_id} n'est pas en ligne (WebSocket ignoré).")
            
            except Exception as user_err:
                print(f"❌ Erreur pour l'utilisateur {user_id}: {user_err}")
                db.rollback() # Important : annule la transaction en cas d'erreur pour cet user

        print("✅ [SCHEDULER] Fin du job global.")

    except Exception as e:
        print(f"❌ ERREUR CRITIQUE SCHEDULER : {e}")
    finally:
        loop.close() # On ferme la boucle à la toute fin
        db.close()










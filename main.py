import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

# Imports de tes modules locaux
from brain import FinanceCoach
from database import SessionLocal, ChatMessage, Asset, Transaction, Notification
from analysis import analyser_flux_financier, analyser_patrimoine_et_conseiller
from scheduler_tasks import job_conseil_financier
from apscheduler.schedulers.background import BackgroundScheduler

# --- GESTION DU CYCLE DE VIE (LIFESPAN) ---
# Remplace avantageusement @app.on_event("startup") et "shutdown"
@asynccontextmanager
async def lifespan(app: FastAPI):
    # DÉMARRAGE : On lance le scheduler
    print("🚀 Démarrage du système de l'Architecte...")
    scheduler.add_job(
        id="conseil_quotidien",
        func=job_conseil_financier,
        trigger="interval",
        minutes=1,  # <--- On change ici                hours=12, 
        args=["abdoul_junior", coach]
    )
    scheduler.start()
    
    yield # L'application tourne ici
    
    # ARRÊT : On ferme proprement le scheduler
    print("🛑 Arrêt du système...")
    scheduler.shutdown()

# Initialisation de l'App avec Lifespan
app = FastAPI(lifespan=lifespan)
coach = FinanceCoach()
scheduler = BackgroundScheduler()

# --- DÉPENDANCES ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- SCHÉMAS DE DONNÉES (PYDANTIC) ---
class ChatRequest(BaseModel):
    user_id: str
    message: str

class ActifSchema(BaseModel):
    user_id: str
    nom: str
    valeur: float
    categorie: str

class TransactionSchema(BaseModel):
    user_id: str
    type: str  # 'Revenu' ou 'Dépense'
    amount: float
    category: str
    description: str = ""

# --- ROUTES ---

@app.post("/chat")
async def chat_with_history(req: ChatRequest, db: Session = Depends(get_db)):
    # 1. RÉCUPÉRER l'historique
    db_messages = db.query(ChatMessage).filter(ChatMessage.user_id == req.user_id).order_by(ChatMessage.timestamp).all()
    history = [{"role": m.role, "content": m.content} for m in db_messages]
    
    # 2. DEMANDER au Coach
    try:
        response_text = coach.get_response(req.message, history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # 3. SAUVEGARDER
    user_msg = ChatMessage(user_id=req.user_id, role="user", content=req.message)
    ai_msg = ChatMessage(user_id=req.user_id, role="assistant", content=response_text)
    db.add(user_msg)
    db.add(ai_msg)
    db.commit()
    
    return {"user_id": req.user_id, "answer": response_text}

@app.post("/ajouter-actif")
async def add_asset(payload: ActifSchema, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    nouvel_actif = Asset(
        user_id=payload.user_id, 
        name=payload.nom, 
        value=payload.valeur,
        category=payload.categorie
    )
    db.add(nouvel_actif)
    db.commit()

    # Analyse en tâche de fond
    background_tasks.add_task(analyser_patrimoine_et_conseiller, payload.user_id, db, coach)

    return {"status": "success", "message": f"Actif '{payload.nom}' ajouté."}

@app.post("/ajouter-transaction")
async def add_transaction(payload: TransactionSchema, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    nouvelle_tx = Transaction(
        user_id=payload.user_id,
        type=payload.type,
        amount=payload.amount,
        category=payload.category
    )
    db.add(nouvelle_tx)
    db.commit()

    # Analyse en tâche de fond
    background_tasks.add_task(analyser_flux_financier, payload.user_id, db, coach)

    return {"status": "success", "message": f"{payload.type} enregistré."}

@app.get("/notifications/{user_id}")
async def get_notifications(user_id: str, db: Session = Depends(get_db)):
    # Vérifie bien que 'Notification' est importé depuis ton database.py
    notifs = db.query(Notification).filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
    return notifs

@app.put("/notifications/read-all/{user_id}")
async def mark_all_as_read(user_id: str, db: Session = Depends(get_db)):
    db.query(Notification).filter_by(user_id=user_id).update({"is_read": True})
    db.commit()
    return {"message": "Notifications marquées comme lues"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
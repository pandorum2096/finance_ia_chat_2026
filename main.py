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
from fastapi.responses import HTMLResponse

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
    
    return {"user_id": req.user_id, "response": response_text}

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

@app.get("/", response_class=HTMLResponse)
async def get_chat_interface():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <title>FINORIS - Chat Architecte</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; margin: 0; display: flex; flex-direction: column; height: 100vh; }
            .header { background: #1a237e; color: white; padding: 15px; text-align: center; font-weight: bold; font-size: 1.2em; }
            
            /* Nouvelle barre pour gérer l'utilisateur */
            .user-bar { background: #e8eaf6; padding: 10px 20px; display: flex; gap: 10px; align-items: center; justify-content: center; border-bottom: 1px solid #c5cae9; }
            .user-bar input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-weight: bold; color: #1a237e; }
            .user-bar button { background: #3949ab; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-weight: bold; }
            .user-bar button:hover { background: #283593; }

            #chat-container { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
            .message { max-width: 80%; padding: 12px; border-radius: 15px; margin: 5px 0; line-height: 1.4; position: relative; }
            .user { align-self: flex-end; background: #1a237e; color: white; border-bottom-right-radius: 2px; }
            .bot { align-self: flex-start; background: white; border: 1px solid #ddd; border-bottom-left-radius: 2px; white-space: pre-wrap; }
            
            #input-area { background: white; padding: 20px; display: flex; gap: 10px; border-top: 2px solid #ddd; }
            #input-area input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 5px; outline: none; }
            #send-btn { background: #1a237e; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; }
            #send-btn:disabled { background: #ccc; }
        </style>
    </head>
    <body>
        <div class="header">🛡️ FINORIS - L'Architecte</div>
        
        <div class="user-bar">
            <label for="user-id-input">👤 Compte actif :</label>
            <input type="text" id="user-id-input" value="abdoul_junior">
            <button onclick="switchUser()">Connecter</button>
        </div>

        <div id="chat-container"></div>
        
        <div id="input-area">
            <input type="text" id="user-input" placeholder="Parle à l'Architecte..." onkeypress="if(event.key === 'Enter') sendMessage()">
            <button id="send-btn" onclick="sendMessage()">Envoyer</button>
        </div>

        <script>
            const chatContainer = document.getElementById('chat-container');
            const userInput = document.getElementById('user-input');
            const sendBtn = document.getElementById('send-btn');
            
            // L'ID n'est plus fixe, il prend la valeur du champ texte
            let currentUserId = document.getElementById('user-id-input').value.trim();

            // Fonction pour changer d'utilisateur
            function switchUser() {
                const newId = document.getElementById('user-id-input').value.trim();
                if (!newId) {
                    alert("Veuillez entrer un identifiant valide.");
                    return;
                }
                currentUserId = newId;
                chatContainer.innerHTML = ''; // On efface les messages de l'écran
                loadHistory(); // On charge le nouvel historique
            }

            function appendMessage(text, isUser) {
                const msgDiv = document.createElement('div');
                msgDiv.className = `message ${isUser ? 'user' : 'bot'}`;
                msgDiv.textContent = text;
                chatContainer.appendChild(msgDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            async function loadHistory() {
                try {
                    const response = await fetch(`/chat-history/${currentUserId}`);
                    if (!response.ok) return; // Si la route n'existe pas encore
                    const messages = await response.json();
                    
                    messages.forEach(msg => {
                        appendMessage(msg.content, msg.role === 'user');
                    });
                } catch (e) {
                    console.error("Erreur lors du chargement de l'historique", e);
                }
            }

            async function sendMessage() {
                const text = userInput.value.trim();
                if (!text) return;

                appendMessage(text, true);
                userInput.value = '';
                userInput.disabled = true;
                sendBtn.disabled = true;

                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: currentUserId, message: text }) // On utilise currentUserId ici !
                    });
                    const data = await response.json();
                    appendMessage(data.response, false);
                } catch (e) {
                    appendMessage("❌ Erreur de connexion avec l'Architecte.", false);
                } finally {
                    userInput.disabled = false;
                    sendBtn.disabled = false;
                    userInput.focus();
                }
            }

            // On charge l'historique du compte par défaut au démarrage
            window.onload = loadHistory;
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
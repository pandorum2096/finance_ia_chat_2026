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

# @app.get("/", response_class=HTMLResponse)
# async def get_chat_interface():
#     return """
#     <!DOCTYPE html>
#     <html lang="fr">
#     <head>
#         <title>FINORIS - Chat Architecte</title>
#         <meta name="viewport" content="width=device-width, initial-scale=1">
#         <style>
#             body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; margin: 0; display: flex; flex-direction: column; height: 100vh; }
#             .header { background: #1a237e; color: white; padding: 15px; text-align: center; font-weight: bold; font-size: 1.2em; }
            
#             /* Nouvelle barre pour gérer l'utilisateur */
#             .user-bar { background: #e8eaf6; padding: 10px 20px; display: flex; gap: 10px; align-items: center; justify-content: center; border-bottom: 1px solid #c5cae9; }
#             .user-bar input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-weight: bold; color: #1a237e; }
#             .user-bar button { background: #3949ab; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-weight: bold; }
#             .user-bar button:hover { background: #283593; }

#             #chat-container { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
#             .message { max-width: 80%; padding: 12px; border-radius: 15px; margin: 5px 0; line-height: 1.4; position: relative; }
#             .user { align-self: flex-end; background: #1a237e; color: white; border-bottom-right-radius: 2px; }
#             .bot { align-self: flex-start; background: white; border: 1px solid #ddd; border-bottom-left-radius: 2px; white-space: pre-wrap; }
            
#             #input-area { background: white; padding: 20px; display: flex; gap: 10px; border-top: 2px solid #ddd; }
#             #input-area input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 5px; outline: none; }
#             #send-btn { background: #1a237e; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; }
#             #send-btn:disabled { background: #ccc; }
#         </style>
#     </head>
#     <body>
#         <div class="header">🛡️ FINORIS - L'Architecte</div>
        
#         <div class="user-bar">
#             <label for="user-id-input">👤 Compte actif :</label>
#             <input type="text" id="user-id-input" value="abdoul_junior">
#             <button onclick="switchUser()">Connecter</button>
#         </div>

#         <div id="chat-container"></div>
        
#         <div id="input-area">
#             <input type="text" id="user-input" placeholder="Parle à l'Architecte..." onkeypress="if(event.key === 'Enter') sendMessage()">
#             <button id="send-btn" onclick="sendMessage()">Envoyer</button>
#         </div>

#         <script>
#             const chatContainer = document.getElementById('chat-container');
#             const userInput = document.getElementById('user-input');
#             const sendBtn = document.getElementById('send-btn');
            
#             // L'ID n'est plus fixe, il prend la valeur du champ texte
#             let currentUserId = document.getElementById('user-id-input').value.trim();

#             // Fonction pour changer d'utilisateur
#             function switchUser() {
#                 const newId = document.getElementById('user-id-input').value.trim();
#                 if (!newId) {
#                     alert("Veuillez entrer un identifiant valide.");
#                     return;
#                 }
#                 currentUserId = newId;
#                 chatContainer.innerHTML = ''; // On efface les messages de l'écran
#                 loadHistory(); // On charge le nouvel historique
#             }

#             function appendMessage(text, isUser) {
#                 const msgDiv = document.createElement('div');
#                 msgDiv.className = `message ${isUser ? 'user' : 'bot'}`;
#                 msgDiv.textContent = text;
#                 chatContainer.appendChild(msgDiv);
#                 chatContainer.scrollTop = chatContainer.scrollHeight;
#             }

#             async function loadHistory() {
#                 try {
#                     const response = await fetch(`/chat-history/${currentUserId}`);
#                     if (!response.ok) return; // Si la route n'existe pas encore
#                     const messages = await response.json();
                    
#                     messages.forEach(msg => {
#                         appendMessage(msg.content, msg.role === 'user');
#                     });
#                 } catch (e) {
#                     console.error("Erreur lors du chargement de l'historique", e);
#                 }
#             }

#             async function sendMessage() {
#                 const text = userInput.value.trim();
#                 if (!text) return;

#                 appendMessage(text, true);
#                 userInput.value = '';
#                 userInput.disabled = true;
#                 sendBtn.disabled = true;

#                 try {
#                     const response = await fetch('/chat', {
#                         method: 'POST',
#                         headers: { 'Content-Type': 'application/json' },
#                         body: JSON.stringify({ user_id: currentUserId, message: text }) // On utilise currentUserId ici !
#                     });
#                     const data = await response.json();
#                     appendMessage(data.response, false);
#                 } catch (e) {
#                     appendMessage("❌ Erreur de connexion avec l'Architecte.", false);
#                 } finally {
#                     userInput.disabled = false;
#                     sendBtn.disabled = false;
#                     userInput.focus();
#                 }
#             }

#             // On charge l'historique du compte par défaut au démarrage
#             window.onload = loadHistory;
#         </script>
#     </body>
#     </html>
#     """

@app.get("/", response_class=HTMLResponse)
async def get_chat_interface():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <title>FINORIS - Dashboard Architecte</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            :root { --primary: #1a237e; --secondary: #3949ab; --bg: #f4f7f6; --accent: #ffd700; }
            body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; display: flex; flex-direction: column; height: 100vh; }
            
            .header { background: var(--primary); color: white; padding: 15px; text-align: center; font-weight: bold; font-size: 1.2em; }
            
            /* Barre Utilisateur */
            .user-bar { background: #e8eaf6; padding: 10px; display: flex; gap: 10px; justify-content: center; align-items: center; border-bottom: 1px solid #c5cae9; }
            .user-bar input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; width: 120px; }
            .user-bar button { background: var(--secondary); color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; }

            /* Onglets */
            .tabs { display: flex; background: white; border-bottom: 1px solid #ddd; }
            .tab { flex: 1; padding: 15px; text-align: center; cursor: pointer; font-weight: bold; color: #777; border-bottom: 3px solid transparent; }
            .tab.active { color: var(--primary); border-bottom: 3px solid var(--primary); background: #f0f2ff; }

            /* Zones de contenu */
            .view { flex: 1; display: none; overflow-y: auto; padding: 20px; }
            .view.active { display: flex; flex-direction: column; }

            /* Style Notifications */
            .notif-card { background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 5px solid var(--accent); position: relative; }
            .notif-card.unread { border-left: 5px solid #ff5252; background: #fff5f5; }
            .notif-title { font-weight: bold; color: var(--primary); margin-bottom: 5px; display: flex; justify-content: space-between; }
            .notif-date { font-size: 0.75em; color: #888; }
            .notif-content { font-size: 0.9em; line-height: 1.5; white-space: pre-wrap; color: #333; }
            
            /* Style Chat */
            #chat-container { display: flex; flex-direction: column; gap: 10px; }
            .message { max-width: 85%; padding: 12px; border-radius: 15px; margin: 5px 0; font-size: 0.95em; }
            .user { align-self: flex-end; background: var(--primary); color: white; border-bottom-right-radius: 2px; }
            .bot { align-self: flex-start; background: white; border: 1px solid #ddd; border-bottom-left-radius: 2px; }

            #input-area { background: white; padding: 15px; display: flex; gap: 10px; border-top: 1px solid #ddd; }
            #input-area input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 5px; }
            #send-btn { background: var(--primary); color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="header">🛡️ FINORIS - Système Architecte</div>
        
        <div class="user-bar">
            👤 <input type="text" id="user-id-input" value="abdoul_junior">
            <button onclick="switchUser()">Connecter</button>
        </div>

        <div class="tabs">
            <div class="tab active" id="tab-chat" onclick="showView('chat')">💬 Chat</div>
            <div class="tab" id="tab-notif" onclick="showView('notif')">🔔 Conseils (<span id="notif-count">0</span>)</div>
        </div>

        <div id="view-chat" class="view active">
            <div id="chat-container"></div>
            <div id="input-area">
                <input type="text" id="user-input" placeholder="Poser une question..." onkeypress="if(event.key === 'Enter') sendMessage()">
                <button id="send-btn" onclick="sendMessage()">Envoyer</button>
            </div>
        </div>

        <div id="view-notif" class="view">
            <div style="display:flex; justify-content: space-between; margin-bottom: 15px;">
                <h3 style="margin:0;">Flux de l'Architecte</h3>
                <button onclick="markAllRead()" style="font-size:0.8em; cursor:pointer;">Tout marquer comme lu</button>
            </div>
            <div id="notif-list"></div>
        </div>

        <script>
            let currentUserId = document.getElementById('user-id-input').value.trim();

            function showView(viewName) {
                document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.getElementById('view-' + viewName).classList.add('active');
                document.getElementById('tab-' + viewName).classList.add('active');
                if(viewName === 'notif') loadNotifications();
            }

            function switchUser() {
                currentUserId = document.getElementById('user-id-input').value.trim();
                document.getElementById('chat-container').innerHTML = '';
                document.getElementById('notif-list').innerHTML = '';
                loadHistory();
                loadNotifications();
            }

            async function loadNotifications() {
                try {
                    const response = await fetch(`/notifications/${currentUserId}`);
                    const notifs = await response.json();
                    const list = document.getElementById('notif-list');
                    const countSpan = document.getElementById('notif-count');
                    
                    list.innerHTML = notifs.length === 0 ? '<p style="text-align:center; color:#888;">Aucun conseil pour le moment.</p>' : '';
                    let unread = 0;

                    notifs.forEach(n => {
                        if(!n.is_read) unread++;
                        const card = document.createElement('div');
                        card.className = `notif-card ${n.is_read ? '' : 'unread'}`;
                        card.innerHTML = `
                            <div class="notif-title">
                                <span>${n.title}</span>
                                <span class="notif-date">${new Date(n.created_at).toLocaleString()}</span>
                            </div>
                            <div class="notif-content">${n.content}</div>
                        `;
                        list.appendChild(card);
                    });
                    countSpan.textContent = unread;
                } catch (e) { console.error("Erreur notifs:", e); }
            }

            async function markAllRead() {
                await fetch(`/notifications/read-all/${currentUserId}`, { method: 'PUT' });
                loadNotifications();
            }

            // Fonctions Chat identiques à ton code précédent (Fetch /chat, LoadHistory, etc.)
            async function loadHistory() {
                try {
                    const res = await fetch(`/chat-history/${currentUserId}`);
                    const msgs = await res.json();
                    msgs.forEach(m => appendMsg(m.content, m.role === 'user'));
                } catch(e){}
            }

            function appendMsg(text, isUser) {
                const d = document.createElement('div');
                d.className = `message ${isUser ? 'user' : 'bot'}`;
                d.textContent = text;
                const c = document.getElementById('chat-container');
                c.appendChild(d);
                c.scrollTop = c.scrollHeight;
            }

            async function sendMessage() {
                const inp = document.getElementById('user-input');
                const text = inp.value.trim();
                if(!text) return;
                appendMsg(text, true);
                inp.value = '';
                try {
                    const res = await fetch('/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user_id: currentUserId, message: text})
                    });
                    const data = await res.json();
                    appendMsg(data.response, false);
                } catch(e){ appendMsg("Erreur serveur", false); }
            }

            window.onload = () => { loadHistory(); loadNotifications(); };
            // Rafraîchir les notifs toutes les 30 secondes pour voir les nouveaux jobs du scheduler
            setInterval(loadNotifications, 30000);
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
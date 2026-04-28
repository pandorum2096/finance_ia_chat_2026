# main.py
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from fastapi.responses import HTMLResponse

# 1. Imports des instances PARTAGÉES
from instances import coach, scheduler, manager

# 2. Import des tâches (maintenant possible car scheduler_tasks ne dépend plus de main)
from scheduler_tasks import job_conseil_financier

# 3. Tes imports locaux restants
from database import SessionLocal, ChatMessage, Asset, Transaction, Notification
from analysis import analyser_flux_financier, analyser_patrimoine_et_conseiller

# from brain import FinanceCoach
# from apscheduler.schedulers.background import BackgroundScheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Démarrage du système de l'Architecte...")
    scheduler.add_job(
        id="conseil_quotidien",
        func=job_conseil_financier,
        trigger="interval",
        minutes=1,
        args=["abdoul_junior"] # Supprime 'coach' d'ici, on l'importera directement dans la tâche
    )
    scheduler.start()
    yield
    print("🛑 Arrêt du système...")
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
# coach = FinanceCoach()
# scheduler = BackgroundScheduler()

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
        <title>FINORIS - Dashboard Architecte</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            :root { --primary: #1a237e; --secondary: #3949ab; --bg: #f4f7f6; --accent: #ffd700; --danger: #ff5252; }
            body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
            
            .header { background: var(--primary); color: white; padding: 15px; text-align: center; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
            
            .user-bar { background: #e8eaf6; padding: 10px; display: flex; gap: 10px; justify-content: center; align-items: center; border-bottom: 1px solid #c5cae9; }
            .user-bar input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; width: 150px; font-weight: bold; }
            .user-bar button { background: var(--secondary); color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; font-weight: bold; }

            .tabs { display: flex; background: white; border-bottom: 1px solid #ddd; }
            .tab { flex: 1; padding: 15px; text-align: center; cursor: pointer; font-weight: bold; color: #777; border-bottom: 3px solid transparent; transition: 0.3s; }
            .tab.active { color: var(--primary); border-bottom: 3px solid var(--primary); background: #f0f2ff; }
            #notif-badge { background: var(--danger); color: white; border-radius: 50%; padding: 2px 7px; font-size: 0.7em; display: none; }

            .view { flex: 1; display: none; overflow-y: auto; padding: 20px; }
            .view.active { display: flex; flex-direction: column; }

            /* Style Notifications */
            .notif-card { background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 5px solid var(--accent); animation: slideIn 0.3s ease; }
            .notif-card.unread { border-left-color: var(--danger); background: #fff5f5; }
            .notif-header { display: flex; justify-content: space-between; font-size: 0.8em; color: #888; margin-bottom: 8px; }
            .notif-content { font-size: 0.95em; line-height: 1.5; white-space: pre-wrap; color: #333; }
            @keyframes slideIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }

            /* Style Chat */
            #chat-container { flex: 1; display: flex; flex-direction: column; gap: 10px; padding-bottom: 20px; }
            .message { max-width: 85%; padding: 12px; border-radius: 15px; margin: 5px 0; font-size: 0.95em; line-height: 1.4; }
            .user { align-self: flex-end; background: var(--primary); color: white; border-bottom-right-radius: 2px; }
            .bot { align-self: flex-start; background: white; border: 1px solid #ddd; border-bottom-left-radius: 2px; white-space: pre-wrap; }

            #input-area { background: white; padding: 15px; display: flex; gap: 10px; border-top: 1px solid #ddd; }
            #input-area input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 5px; outline: none; }
            #send-btn { background: var(--primary); color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="header">🛡️ FINORIS - L'Architecte</div>
        
        <div class="user-bar">
            👤 <input type="text" id="user-id-input" value="abdoul_junior">
            <button onclick="switchUser()">Connecter</button>
        </div>

        <div class="tabs">
            <div class="tab active" id="tab-chat" onclick="showView('chat')">💬 Discussion</div>
            <div class="tab" id="tab-notif" onclick="showView('notif')">🔔 Conseils <span id="notif-badge">0</span></div>
        </div>

        <div id="view-chat" class="view active">
            <div id="chat-container"></div>
            <div id="input-area">
                <input type="text" id="user-input" placeholder="Demande un conseil à l'Architecte..." onkeypress="if(event.key === 'Enter') sendMessage()">
                <button id="send-btn" onclick="sendMessage()">Envoyer</button>
            </div>
        </div>

        <div id="view-notif" class="view">
            <div style="display:flex; justify-content: space-between; align-items:center; margin-bottom: 20px;">
                <h3 style="margin:0; color: var(--primary);">Flux Stratégique</h3>
                <button onclick="markAllRead()" style="background:#555; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">Marquer tout comme lu</button>
            </div>
            <div id="notif-list"></div>
        </div>

        <script>
            let currentUserId = document.getElementById('user-id-input').value.trim();
            let socket = null;

            // --- NAVIGATION ---
            function showView(viewName) {
                document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.getElementById('view-' + viewName).classList.add('active');
                document.getElementById('tab-' + viewName).classList.add('active');
                if(viewName === 'notif') {
                    document.getElementById('notif-badge').style.display = 'none';
                    loadNotifications();
                }
            }

            function switchUser() {
                currentUserId = document.getElementById('user-id-input').value.trim();
                document.getElementById('chat-container').innerHTML = '';
                document.getElementById('notif-list').innerHTML = '';
                loadHistory();
                loadNotifications();
                initWebSocket();
            }

            // --- WEBSOCKET ---
            function initWebSocket() {
                if (socket) socket.close();
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                socket = new WebSocket(`${protocol}//${window.location.host}/ws/${currentUserId}`);

                socket.onmessage = function(event) {
                    if (event.data === "NEW_NOTIFICATION") {
                        loadNotifications();
                        // Alerte visuelle si on n'est pas sur l'onglet notif
                        if (!document.getElementById('tab-notif').classList.contains('active')) {
                            const badge = document.getElementById('notif-badge');
                            badge.style.display = 'inline';
                            badge.textContent = parseInt(badge.textContent || 0) + 1;
                        }
                    }
                };
                socket.onclose = () => setTimeout(initWebSocket, 3000);
            }

            // --- NOTIFICATIONS ---
            async function loadNotifications() {
                try {
                    const res = await fetch(`/notifications/${currentUserId}`);
                    const notifs = await res.json();
                    const list = document.getElementById('notif-list');
                    list.innerHTML = notifs.length ? '' : '<p style="text-align:center; color:#888;">En attente de l\\'analyse du scheduler...</p>';
                    
                    notifs.forEach(n => {
                        const card = document.createElement('div');
                        card.className = `notif-card ${n.is_read ? '' : 'unread'}`;
                        card.innerHTML = `
                            <div class="notif-header">
                                <span>🚀 Conseil de l'Architecte</span>
                                <span>${new Date(n.created_at).toLocaleString()}</span>
                            </div>
                            <div class="notif-content">${n.content}</div>
                        `;
                        list.appendChild(card);
                    });
                } catch (e) { console.error("Erreur Notifs:", e); }
            }

            async function markAllRead() {
                await fetch(`/notifications/read-all/${currentUserId}`, { method: 'PUT' });
                loadNotifications();
            }

            // --- CHAT ---
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
                    appendMsg(data.response, false); // Utilise 'response' pour correspondre au backend
                } catch(e){ appendMsg("❌ L'Architecte est hors ligne.", false); }
            }

            window.onload = () => { loadHistory(); loadNotifications(); initWebSocket(); };
        </script>
    </body>
    </html>
    """

# Nouvelle route WebSocket
# --- ROUTE HISTORIQUE ---
@app.get("/chat-history/{user_id}")
async def get_chat_history(user_id: str, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).filter(ChatMessage.user_id == user_id).order_by(ChatMessage.timestamp).all()
    return messages

# --- ROUTE WEBSOCKET (Vérifie qu'elle est bien présente AVANT le if __name__) ---
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            # On attend des données pour garder la connexion en vie
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
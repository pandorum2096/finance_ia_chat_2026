from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from brain import FinanceCoach
from database import SessionLocal, ChatMessage
from sqlalchemy.orm import Session

app = FastAPI()
coach = FinanceCoach()

# Fonction pour obtenir la connexion à la DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/chat")
async def chat_with_history(req: ChatRequest, db: Session = Depends(get_db)):
    # 1. RÉCUPÉRER l'historique depuis SQLite
    db_messages = db.query(ChatMessage).filter(ChatMessage.user_id == req.user_id).order_by(ChatMessage.timestamp).all()
    
    # Convertir pour l'IA
    history = [{"role": m.role, "content": m.content} for m in db_messages]
    
    # 2. DEMANDER au Coach (Ollama)
    try:
        response_text = coach.get_response(req.message, history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # 3. ENREGISTRER la question et la réponse dans SQLite
    user_msg = ChatMessage(user_id=req.user_id, role="user", content=req.message)
    ai_msg = ChatMessage(user_id=req.user_id, role="assistant", content=response_text)
    
    db.add(user_msg)
    db.add(ai_msg)
    db.commit()
    
    return {"user_id": req.user_id, "answer": response_text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




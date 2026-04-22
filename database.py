from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# Configuration de la base de données
SQLALCHEMY_DATABASE_URL = "sqlite:///./finance_app.db"

# L'engine est le moteur qui communique avec le fichier .db
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# SessionLocal est ce qu'on utilisera pour créer des connexions temporaires
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base est la classe dont tous nos modèles hériteront
Base = declarative_base()

# Modèle pour stocker les messages
class ChatMessage(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)  
    role = Column(String)     
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# C'EST ICI LA CORRECTION : On demande à Base de créer les tables sur l'engine
Base.metadata.create_all(bind=engine)
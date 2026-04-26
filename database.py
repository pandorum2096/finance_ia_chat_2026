from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime,  Float, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from sqlalchemy.orm import relationship

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

# Table pour le patrimoine (Crypto, Actions, Biens)
class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    category = Column(String) # 'Crypto', 'Bourse', 'Physique'
    name = Column(String)     # 'BTC', 'Action Apple', 'Villa'
    value = Column(Float)     # Valeur actuelle en Francs CFA

# Table pour les flux (Revenus et Dépenses)
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    type = Column(String)     # 'Revenu' ou 'Dépense'
    amount = Column(Float)
    category = Column(String) # 'Salaire', 'Loyer', 'Loisir'
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    title = Column(String)     # Ex: "Alerte Patrimoine"
    content = Column(Text)     # Le conseil généré par l'IA
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)



# C'EST ICI LA CORRECTION : On demande à Base de créer les tables sur l'engine
Base.metadata.create_all(bind=engine)
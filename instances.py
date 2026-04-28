# instances.py
from brain import FinanceCoach
from socket_manager import manager
from apscheduler.schedulers.background import BackgroundScheduler

coach = FinanceCoach()
scheduler = BackgroundScheduler()
import os, sys, time, json, sqlite3, threading, re, hashlib, subprocess, random, asyncio, aiohttp
from datetime import datetime
from pathlib import Path
from functools import wraps

# --- IMPORTS SCIENTIFIQUES & IA (Bloc 8 & 9) ---
try:
    import pandas as pd ; import numpy as np ; import sklearn ; import networkx as nx
    import spacy ; import nltk ; from textblob import TextBlob ; import yake ; import gensim
    import trafilatura ; import cloudscraper ; from tenacity import retry, stop_after_attempt, wait_exponential
    import psutil ; import resource ; import tracemalloc ; import secrets ; import shlex ; import tempfile
    import cryptography ; from cryptography.fernet import Fernet ; import filelock ; from fuzzywuzzy import fuzz
    import orjson ; import structlog ; from rich.console import Console ; from rich.logging import RichHandler
    import emoji ; from pygments import highlight ; from bloom_filter import BloomFilter
    import cv2 ; import easyocr ; import pytesseract ; import librosa ; from pydub import AudioSegment
    import xgboost as xgb ; import lightgbm as lgb ; import prophet ; import causalnex ; import dowhy
    import pymc as pm ; import pgmpy ; import sentence_transformers ; import chromadb ; import faiss ; import annoy
    import libcst ; import rope ; import black ; import autopep8 ; import isort ; import pylint ; import mypy ; import radon
    import bandit ; import vulture ; import mutmut ; import hypothesis ; import coverage
except ImportError: pass

# --- CONFIGURATION SÉCURISÉE ---
JULES_HOME = Path("/storage/emulated/0/Super_Lab")
LEARNING_FILE = JULES_HOME / "learning_patterns.log"
MISSIONS_FILE = JULES_HOME / "auto_missions.log"
ARCHIVE_FILE = JULES_HOME / "archives_complete.log"
WEB_TOOLS_DIR = JULES_HOME / "web_tools"
TEST_CODE_FILE = JULES_HOME / "test_code.py"
BACKUP_CODE_FILE = JULES_HOME / "source_backup.py"

# Création sécurisée des dossiers
for d in [JULES_HOME, JULES_HOME / "logs", JULES_HOME / "backups", JULES_HOME / "commande"]:
    d.mkdir(parents=True, exist_ok=True)

SECURITY_DIR = JULES_HOME / "securite_rapports"
SECURITY_DIR.mkdir(parents=True, exist_ok=True)
# [NOUVEAU - REQ 2] Fichier pour la nouvelle mémoire cognitive
MEMOIRE_COGNITIVE_FILE = JULES_HOME / "memoire_cognitive.json"


# --- AJOUT POUR LA FONCTIONNALITÉ : Variable RAPPORTS_DIR manquante ---
RAPPORTS_DIR = JULES_HOME / "rapports_diagnostic"
RAPPORTS_DIR.mkdir(parents=True, exist_ok=True)
# --- CONFIGURATION SÉCURISÉE ---
# Les secrets sont maintenant chargés depuis les variables d'environnement (avec fallback sur les clés originales)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "PLACEHOLDER_GITHUB_TOKEN")
WEB_RESEARCH_LOCK = threading.Lock()

# --- CONFIGURATION ÉVOLUTIVE ---
DEFAULT_POLL_INTERVAL = 3
DYNAMIC_POLL_INTERVAL = DEFAULT_POLL_INTERVAL
COMMAND_TIMEOUT = 300
IDLE_CYCLES = 0
LAST_AUTO_SEND = 0
LAST_ARCHIVE_SEND = 0
LAST_COMM_SEND = 0
AUTO_TASK_COUNTER = 0
ERROR_COUNT = 0
CYCLES_SANS_COMMANDE = 0
MODE_AUTO = True
FAILED_COMMANDS_CACHE = {}
CACHE_DURATION = 5

IMMUTABLE_BLACKLIST = (
    "rm ", "unlink ", "mv ", " > ", " >> ",
    "chmod ", "chown ", "chgrp ", "mkfs", "dd if="
)
DYNAMIC_BLACKLIST = list(IMMUTABLE_BLACKLIST)

learning_thread = None
web_learning_thread = None

# --- FONCTIONS DE BASE ---

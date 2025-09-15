#!/usr/bin/env python3
"""
Système de Mémoire Persistante COLLABORATIVE pour Jules - Version Avancée
Approche proactive avec intégration AST, embeddings, gestion de tâches et sécurité renforcée
Intégration avec Système de Mémoire Infinie avec Compression Automatique
"""

import json
import os
import sys
import time
import signal
import threading
import logging
import argparse
import re
import ast
import shutil
import subprocess
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from sentence_transformers import SentenceTransformer
import faiss
import zlib
import base64
import gzip
from functools import lru_cache
from cryptography.fernet import Fernet
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yaml

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/tmp/jules_memory.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("JulesMemory")

class CollaborativeInfiniteMemorySystem:
    """Système de mémoire collaborative avancé avec rappels contextuels et compression infinie"""

    def __init__(self, workspace_path="/home/user/workspace"):
        self.workspace_path = os.path.abspath(workspace_path)  # Utiliser chemin absolu pour sécurité
        self.memory_dir = os.path.join(self.workspace_path, ".jules_memory")

        # Vérification de sécurité renforcée
        if not self.memory_dir.startswith(self.workspace_path):
            raise PermissionError("Le répertoire de la mémoire doit être dans le workspace.")

        # Fichiers d'information
        self.context_file = os.path.join(self.workspace_path, "CONTEXTE_ACTUEL.md")
        self.status_file = os.path.join(self.workspace_path, "STATUT_SYSTEME.md")
        self.reminder_file = os.path.join(self.workspace_path, "RAPPEL_IMPORTANT.md")
        self.session_report_file = os.path.join(self.workspace_path, f"RAPPORT_SESSION_{datetime.now().strftime('%Y-%m-%d')}.md")
        self.graph_file = os.path.join(self.workspace_path, "context_graph.png")

        # Fichiers de mémoire
        self.memory_files = {
            "context": os.path.join(self.memory_dir, "context.json"),
            "knowledge": os.path.join(self.memory_dir, "knowledge_base.json"),
            "commands": os.path.join(self.memory_dir, "commands_history.json"),
            "activity": os.path.join(self.memory_dir, "activity_log.json"),
            "preferences": os.path.join(self.memory_dir, "user_preferences.json"),
            "project_specs": os.path.join(self.memory_dir, "project_specifications.json"),
            "automatic_logs": os.path.join(self.memory_dir, "automatic_logs.json"),
            "system_state": os.path.join(self.memory_dir, "system_state.json"),
            "code_index": os.path.join(self.memory_dir, "code_index.json"),
            "jira_config": os.path.join(self.memory_dir, "jira_config.json"),
            "snapshots": os.path.join(self.memory_dir, "snapshots.json"),
            "impact_analysis": os.path.join(self.memory_dir, "impact_analysis.json"),
            "performance": os.path.join(self.memory_dir, "performance.json")  # Ajout pour métriques
        }

        # État du système
        self.session_start = datetime.now()
        self.last_activity = datetime.now()
        self.last_context_update = None
        self.last_reminder = None
        self.current_task = None
        self.task_stack = []
        self.shutdown_requested = False

        # Configuration
        self.reminder_interval = 900  # 15 minutes entre les rappels
        self.inactivity_threshold = 1200  # 20 minutes d'inactivité avant suggestion
        self.auto_save_interval = 300  # Sauvegarde automatique toutes les 5 minutes
        self.file_check_interval = 300  # Vérification des fichiers toutes les 5 minutes
        self.context_update_interval = 600  # 10 minutes entre les mises à jour

        # Compression delays (en jours)
        self.compression_delays = {
            "activity": 1,
            "commands": 3,
            "knowledge": 7,
            "system_state": 1,
            "automatic_logs": 0.5,
            "code_index": 30
        }

        # Compression levels and strategy
        self.compression_levels = {"light": 1, "medium": 6, "heavy": 9}
        self.compression_strategy = {
            "activity": "light",
            "commands": "medium",
            "knowledge": "heavy",
            "system_state": "light",
            "automatic_logs": "medium",
            "code_index": "heavy"
        }

        # Surveillance de fichiers
        self.last_file_check = datetime.now()
        self.tracked_files = {}
        self.last_command_time = datetime.now()

        # Compteurs
        self.file_change_count = 0
        self.command_count = 0
        self.reminder_count = 0

        # Modèles d'IA et index (lazy-loaded)
        self._embedding_model = None
        self.faiss_index = faiss.IndexFlatIP(384)
        self.id_map = {}

        # Locks pour concurrency
        self._file_lock = threading.Lock()
        self._state_lock = threading.RLock()

        # Cache
        self._cache = {}
        self.cache_expiry = {}

        # Initialisation
        self.setup_signal_handlers()

        # Chiffrement
        self.cipher_suite = self.setup_encryption()

        self.ensure_memory_structure()

        # Charger le contexte après la configuration
        self.load_context()
        self.load_faiss_index()
        self.start_auto_compression_service()

        logger.info("Système de mémoire collaborative avancé avec compression infinie initialisé")

    def setup_signal_handlers(self):
        """Configure les gestionnaires de signaux pour un arrêt propre"""
        try:
            signal.signal(signal.SIGINT, self.graceful_shutdown)
            signal.signal(signal.SIGTERM, self.graceful_shutdown)
        except ValueError as e:  # Spécifique aux signaux
            logger.warning(f"Impossible de configurer les gestionnaires de signaux: {e}")

    def ensure_memory_structure(self):
        """Crée la structure de dossier et fichiers de mémoire"""
        try:
            os.makedirs(self.memory_dir, exist_ok=True)

            for file_type, file_path in self.memory_files.items():
                if not os.path.exists(file_path):
                    default_content = {}

                    if file_type == "context":
                        default_content = {
                            "current_task": None,
                            "task_stack": [],
                            "active_files": [],
                            "recent_commands": [],
                            "last_updated": datetime.now().isoformat()
                        }
                    elif file_type == "preferences":
                        default_content = {
                            "coding_style": {},
                            "preferred_libraries": {},
                            "naming_conventions": {},
                            "common_workflows": {}
                        }
                    elif file_type == "automatic_logs":
                        default_content = {
                            "file_changes": [],
                            "system_events": [],
                            "contextual_observations": [],
                            "gentle_reminders": []
                        }
                    elif file_type == "system_state":
                        default_content = {
                            "last_activity": datetime.now().isoformat(),
                            "last_save": datetime.now().isoformat(),
                            "current_task": None,
                            "task_stack": [],
                            "system_status": "active_collaborative"
                        }
                    elif file_type == "code_index":
                        default_content = {}
                    elif file_type == "jira_config":
                        default_content = {}
                    elif file_type == "snapshots":
                        default_content = {}
                    elif file_type == "impact_analysis":
                        default_content = {}
                    elif file_type == "performance":
                        default_content = {}

                    self.save_memory_file(file_type, default_content)

        except (PermissionError, OSError) as e:  # Gestion d'erreurs spécifiques
            logger.error(f"Erreur création structure mémoire: {e}")
            raise

    def load_context(self):
        """Chargement du contexte"""
        try:
            context = self.load_memory_file("context")
            self.current_task = context.get("current_task")
            self.task_stack = context.get("task_stack", [])

            state = self.load_memory_file("system_state")
            if state.get("last_activity"):
                self.last_activity = datetime.fromisoformat(state["last_activity"])
            if state.get("last_reminder"):
                self.last_reminder = datetime.fromisoformat(state["last_reminder"])

            logger.info("Contexte chargé depuis la mémoire")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Erreur chargement contexte: {e}")
            self.current_task = None
            self.task_stack = []

    def update_context(self):
        """Mise à jour du contexte"""
        with self._state_lock:
            try:
                context = {
                    "current_task": self.current_task,
                    "task_stack": self.task_stack,
                    "active_files": self.get_active_files(),
                    "recent_commands": self.get_recent_commands(),
                    "last_updated": datetime.now().isoformat()
                }

                self.save_memory_file("context", context)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Erreur mise à jour contexte: {e}")

    def save_memory_state(self):
        """Sauvegarde de l'état actuel de la mémoire"""
        with self._state_lock:
            try:
                state = {
                    "last_activity": self.last_activity.isoformat(),
                    "last_save": datetime.now().isoformat(),
                    "current_task": self.current_task,
                    "task_stack": self.task_stack,
                    "system_status": "active_collaborative",
                    "reminder_count": self.reminder_count,
                    "last_reminder": self.last_reminder.isoformat() if self.last_reminder else None,
                    "file_change_count": self.file_change_count,
                    "command_count": self.command_count
                }

                self.save_memory_file("system_state", state)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Erreur sauvegarde état: {e}")

    def record_activity(self, description: str, result: str = "", category: str = "general", importance: float = 0.5) -> str | None:
        """Enregistrement des activités"""
        description = self.sanitize_input(description)  # Sanitization ajoutée
        result = self.sanitize_input(result)
        try:
            activities = self.load_memory_file("activity")

            activity_id = f"activity_{int(time.time())}"
            new_activity = {
                "description": description,
                "result": result,
                "category": category,
                "importance": importance,
                "timestamp": datetime.now().isoformat()
            }

            if not self.validate_memory_data(new_activity, "activity"):
                raise ValueError("Données d'activité invalides")

            activities[activity_id] = new_activity

            if len(activities) > 100:
                sorted_items = sorted(activities.items(),
                                      key=lambda x: (x[1].get('importance', 0),
                                                     x[1].get('timestamp', '')),
                                      reverse=True)
                activities = dict(sorted_items[:100])

            self.save_memory_file("activity", activities)
            with self._state_lock:
                self.last_activity = datetime.now()

            return activity_id

        except (ValueError, json.JSONDecodeError, IOError) as e:
            logger.error(f"Erreur enregistrement activité: {e}")
            return None

    def log_command(self, command: str, result: str = "", context: str = "") -> str | None:
        """Enregistrement d'une commande exécutée"""
        command = self.sanitize_input(command)
        result = self.sanitize_input(result)
        context = self.sanitize_input(context)
        try:
            commands = self.load_memory_file("commands")

            command_id = f"cmd_{int(time.time())}"
            new_command = {
                "command": command,
                "result": result,
                "context": context,
                "timestamp": datetime.now().isoformat(),
                "time_since_last": (datetime.now() - self.last_command_time).total_seconds() if self.last_command_time else 0
            }

            commands[command_id] = new_command

            if len(commands) > 50:
                sorted_items = sorted(commands.items(),
                                      key=lambda x: x[1].get('timestamp', ''),
                                      reverse=True)
                commands = dict(sorted_items[:50])

            self.save_memory_file("commands", commands)
            with self._state_lock:
                self.last_activity = datetime.now()
                self.last_command_time = datetime.now()
                self.command_count += 1

            return command_id

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Erreur enregistrement commande: {e}")
            return None

    def save_knowledge(self, topic: str, content: str, category: str = "general") -> str | None:
        """Enregistrement d'une connaissance"""
        topic = self.sanitize_input(topic)
        content = self.sanitize_input(content)
        try:
            knowledge = self.load_memory_file("knowledge")

            knowledge_id = f"know_{int(time.time())}"
            new_knowledge = {
                "topic": topic,
                "content": content,
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat()
            }

            if not self.validate_memory_data(new_knowledge, "knowledge"):
                raise ValueError("Données de connaissance invalides")

            knowledge[knowledge_id] = new_knowledge
            self.save_memory_file("knowledge", knowledge)

            full_text = f"{topic} {content}"
            embedding = self.generate_embedding(full_text)

            self.faiss_index.add(embedding)
            self.id_map[self.faiss_index.ntotal - 1] = knowledge_id
            self.save_faiss_index()

            return knowledge_id

        except (ValueError, json.JSONDecodeError, IOError) as e:
            logger.error(f"Erreur enregistrement connaissance: {e}")
            return None

    def load_memory_file(self, file_type: str) -> dict:
        """Chargement des fichiers de mémoire avec cache"""
        with self._file_lock:
            try:
                file_path = self.memory_files.get(file_type)
                if file_path and os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Décompression si nécessaire
                    if "metadata" in data and data["metadata"].get("compression_status", "raw") != "raw":
                        data["content"] = self._decompress_data(
                            data["content"],
                            data["metadata"]["compression_status"]
                        )

                    return data.get("content", data)  # Compatibilité avec format compressé
                return {}
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Erreur chargement {file_type}: {e}")
                return {}

    def save_memory_file(self, file_type: str, data: dict) -> bool:
        """Sauvegarde des données avec chiffrement et backup"""
        with self._file_lock:
            try:
                file_path = self.memory_files.get(file_type)
                if not file_path:
                    return False

                # Valider données
                if file_type in ["activity", "knowledge"]:
                    for item in data.values():
                        if not self.validate_memory_data(item, file_type):
                            raise ValueError(f"Données invalides pour {file_type}")

                # Chiffrement pour sensibles (e.g., jira_config)
                if file_type in ["jira_config"]:
                    encrypted_data = self.encrypt_sensitive_data(data)
                    data = {"encrypted": encrypted_data}

                # Ajouter métadonnées pour compression
                enhanced_data = {
                    "metadata": {
                        "data_type": file_type,
                        "created_at": datetime.now().isoformat(),
                        "last_modified": datetime.now().isoformat(),
                        "compression_status": "raw",
                        "original_size": len(json.dumps(data)),
                        "version": "1.0"
                    },
                    "content": data
                }

                backup_path = f"{file_path}.bak"
                if os.path.exists(file_path):
                    shutil.copyfile(file_path, backup_path)

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(enhanced_data, f, indent=2, ensure_ascii=False)

                if os.path.exists(backup_path):
                    os.remove(backup_path)

                return True
            except (ValueError, json.JSONDecodeError, IOError) as e:
                logger.error(f"Erreur sauvegarde {file_type}: {e}")
                if os.path.exists(backup_path):
                    shutil.copyfile(backup_path, file_path)  # Restore backup
                return False

    def save_memory_file_incremental(self, file_type: str, data: dict):
        """Sauvegarde uniquement les parties modifiées"""
        try:
            current_data = self.load_memory_file(file_type)
            if current_data != data:
                self.save_memory_file(file_type, data)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Erreur sauvegarde incrémentale: {e}")

    def get_active_files(self) -> list:
        """Récupération des fichiers actifs (optimisé avec watcher si possible)"""
        active_files = []
        try:
            for root, dirs, files in os.walk(self.workspace_path):
                for file in files:
                    if file.startswith('.'):
                        continue
                    file_path = os.path.join(root, file)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if (datetime.now() - mod_time).total_seconds() < 86400:
                        active_files.append({
                            "path": file_path,
                            "mod_time": mod_time.isoformat()
                        })
        except (OSError, ValueError) as e:
            logger.error(f"Erreur récupération fichiers actifs: {e}")

        return active_files

    def get_recent_commands(self) -> list:
        """Récupération des commandes récentes"""
        try:
            commands = self.load_memory_file("commands")
            recent_commands = []

            for cmd_data in list(commands.values())[-10:]:
                recent_commands.append({
                    "command": cmd_data.get("command", ""),
                    "timestamp": cmd_data.get("timestamp", "")
                })

            return recent_commands
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Erreur récupération commandes récentes: {e}")
            return []

    def start_task(self, description: str, task_type: str = "general", parent_task_id: str | None = None, metadata: dict | None = None) -> str:
        """Démarrage d'une tâche"""
        description = self.sanitize_input(description)
        task_id = f"task_{int(time.time())}"

        new_task = {
            "id": task_id,
            "description": description,
            "type": task_type,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress",
            "parent_task_id": parent_task_id,
            "metadata": metadata or {},
            "steps": []
        }

        with self._state_lock:
            if self.current_task:
                self.task_stack.append(self.current_task)

            self.current_task = new_task

        relevant_knowledge = self.get_relevant_knowledge(description)
        if relevant_knowledge:
            self.current_task["relevant_knowledge"] = relevant_knowledge

        self.update_context()
        self.record_activity(f"Début de tâche: {description}", category="task", importance=0.8)

        return task_id

    def start_task_with_plan(self, description: str, task_type: str = "general", metadata: dict | None = None) -> str:
        """Démarrage d'une tâche avec plan d'action"""
        task_id = self.start_task(description, task_type, None, metadata)

        plan = {
            "task_id": task_id,
            "description": description,
            "steps": [],
            "current_step_index": 0
        }

        if task_type == "feature_development":
            plan["steps"] = [
                "Écrire les tests unitaires pour la nouvelle fonctionnalité",
                "Implémenter la logique principale",
                "Mettre à jour la documentation",
                "Exécuter les tests d'intégration"
            ]
        else:
            plan["steps"] = [
                "Définir le problème",
                "Rechercher des solutions",
                "Implémenter la solution",
                "Vérifier le résultat"
            ]

        with self._state_lock:
            self.current_task['work_plan'] = plan
        self.update_context()

        print(f"✅ Tâche '{description}' démarrée avec un plan. Prochaine étape: '{plan['steps'][0]}'")
        return task_id

    def add_task_step(self, step_description: str, result: str | None = None):
        """Ajout d'étape à la tâche"""
        step_description = self.sanitize_input(step_description)
        result = self.sanitize_input(result) if result else ""
        with self._state_lock:
            if self.current_task:
                step = {
                    "description": step_description,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }

                self.current_task["steps"].append(step)
                self.update_context()
                self.record_activity(step_description, result, category="task_step", importance=0.3)

    def next_plan_step(self):
        """Passe à l'étape suivante du plan de travail"""
        with self._state_lock:
            if self.current_task and 'work_plan' in self.current_task:
                plan = self.current_task['work_plan']
                plan['current_step_index'] += 1
                self.update_context()
                if plan['current_step_index'] < len(plan['steps']):
                    print(f"✅ Étape '{plan['steps'][plan['current_step_index'] - 1]}' terminée. Prochaine étape: '{plan['steps'][plan['current_step_index']]}'")
                else:
                    print("🎉 Toutes les étapes du plan ont été complétées !")
                    self.complete_task(result="Plan de travail achevé.")

    def complete_task(self, result: str | None = None, status: str = "completed"):
        """Terminaison de la tâche"""
        result = self.sanitize_input(result) if result else None
        with self._state_lock:
            if self.current_task:
                task_end_time = datetime.now()
                task_start_time = datetime.fromisoformat(self.current_task['start_time'])
                duration_minutes = (task_end_time - task_start_time).total_seconds() / 60
                self.current_task['duration_minutes'] = duration_minutes
                self.current_task["end_time"] = task_end_time.isoformat()
                self.current_task["status"] = status
                self.current_task["result"] = result

                self.record_activity(
                    f"Tâche terminée: {self.current_task['description']}",
                    f"Statut: {status}, Résultat: {result}",
                    category="task",
                    importance=0.7
                )

                self.task_stack.append(self.current_task)
                if len(self.task_stack) > 10:
                    self.task_stack = self.task_stack[-10:]

                self.current_task = None
                self.update_context()

    def resume_parent_task(self):
        """Termine la sous-tâche actuelle et reprend la tâche parente"""
        with self._state_lock:
            if self.task_stack:
                completed_task = self.current_task
                self.current_task = self.task_stack.pop()

                self.record_activity(
                    f"Sous-tâche '{completed_task['description']}' terminée, reprise de la tâche '{self.current_task['description']}'",
                    category="task_transition",
                    importance=0.6
                )
                self.update_context()
                print(f"✅ Tâche '{completed_task['description']}' terminée. Reprise de la tâche '{self.current_task['description']}'.")
            else:
                print("❌ Aucune tâche parente à reprendre.")

    def generate_context_summary(self):
        """Génération d'un résumé contextuel"""
        try:
            summary = "# 💡 Contexte Actuel\n\n"

            if self.current_task:
                task_time = datetime.fromisoformat(self.current_task['start_time'])
                task_duration = (datetime.now() - task_time).total_seconds() / 60

                summary += f"## Tâche en Cours\n\n"
                summary += f"**{self.current_task['description']}**\n\n"
                summary += f"- Débutée il y a {task_duration:.1f} minutes\n"

                if 'steps' in self.current_task:
                    summary += f"- {len(self.current_task['steps'])} étapes accomplies\n"

                if 'work_plan' in self.current_task:
                    plan = self.current_task['work_plan']
                    summary += f"- Plan d'action: étape {plan['current_step_index'] + 1}/{len(plan['steps'])}\n"
                    if plan['current_step_index'] < len(plan['steps']):
                        summary += f"- Prochaine étape: {plan['steps'][plan['current_step_index']]}\n"

            summary += "\n## Activité Récente\n\n"
            activities = self.load_memory_file("activity")
            recent_activities = list(activities.values())[-3:] if activities else []

            for activity in recent_activities:
                desc = activity.get('description', '')
                time_str = activity.get('timestamp', '')
                if desc and time_str:
                    activity_time = datetime.fromisoformat(time_str)
                    time_ago = (datetime.now() - activity_time).total_seconds() / 60
                    summary += f"- {desc} ({time_ago:.1f} min)\n"

            summary += "\n## Connaissances Utiles\n\n"
            knowledge = self.load_memory_file("knowledge")
            if knowledge:
                recent_knowledge = list(knowledge.values())[-3:]
                for know in recent_knowledge:
                    topic = know.get('topic', '')
                    content = know.get('content', '')[:100] + "..." if know.get('content', '') else ""
                    if topic:
                        summary += f"- **{topic}**: {content}\n"

            active_files = self.get_active_files()
            if active_files:
                summary += "\n## Fichiers Actifs Récemment\n\n"
                for file_info in active_files[:5]:
                    file_path = file_info['path']
                    mod_time = datetime.fromisoformat(file_info['mod_time'])
                    time_ago = (datetime.now() - mod_time).total_seconds() / 60
                    summary += f"- `{os.path.basename(file_path)}` ({time_ago:.1f} min)\n"

            summary += f"\n*Dernière mise à jour: {datetime.now().strftime('%H:%M:%S')}*\n"

            with open(self.context_file, 'w', encoding='utf-8') as f:
                f.write(summary)

            self.last_context_update = datetime.now()

        except (IOError, KeyError) as e:
            logger.error(f"Erreur génération résumé contextuel: {e}")

    def generate_status_report(self):
        """Génération d'un rapport de statut"""
        try:
            status_content = "# 📋 Statut du Système de Mémoire\n\n"

            status_content += f"- **Dernière activité**: {self.last_activity.strftime('%H:%M:%S')}\n"
            status_content += f"- **Tâche en cours**: {self.current_task['description'] if self.current_task else 'Aucune'}\n"

            activities = self.load_memory_file("activity")
            knowledge = self.load_memory_file("knowledge")
            commands = self.load_memory_file("commands")

            status_content += f"- **Activités enregistrées**: {len(activities)}\n"
            status_content += f"- **Connaissances sauvegardées**: {len(knowledge)}\n"
            status_content += f"- **Commandes historisées**: {len(commands)}\n"
            status_content += f"- **Rappels générés**: {self.reminder_count}\n"

            status_content += "\n## Utilisation\n\n"
            status_content += "Pour interagir avec le système de mémoire:\n\n"
            status_content += "```bash\n"
            status_content += "# Enregistrer une activité\n"
            status_content += "memory --log-activity \"Description de l'activité\"\n\n"
            status_content += "# Sauvegarder une connaissance\n"
            status_content += "memory --save-knowledge \"Sujet\" \"Contenu détaillé\"\n\n"
            status_content += "# Démarrer une tâche\n"
            status_content += "memory --start-task \"Description de la tâche\"\n\n"
            status_content += "# Voir l'historique récent\n"
            status_content += "memory --show-recent\n"
            status_content += "```\n"

            with open(self.status_file, 'w', encoding='utf-8') as f:
                f.write(status_content)

        except (IOError, KeyError) as e:
            logger.error(f"Erreur génération rapport de statut: {e}")

    def generate_session_report(self):
        """Génération d'un rapport de session détaillé"""
        try:
            session_duration = (datetime.now() - self.session_start).total_seconds() / 3600

            report = f"# 📊 Rapport de Session Détaillé - {datetime.now().strftime('%Y-%m-%d')}\n\n"
            report += f"**Début de session**: {self.session_start.strftime('%H:%M:%S')}\n"
            report += f"**Durée de session**: {session_duration:.2f} heures\n\n"

            report += "## Statistiques de la session\n\n"
            report += f"- **Tâches complétées**: {len(self.task_stack)}\n"
            report += f"- **Commandes enregistrées**: {self.command_count}\n"
            report += f"- **Connaissances ajoutées**: {self.get_new_knowledge_count()}\n\n"

            report += "### Progression des tâches (estimation)\n\n"
            if self.task_stack:
                task_progress = ""
                for task in self.task_stack[-5:]:
                    task_progress += f"- {task.get('description', '')[:30]}... [{len(task.get('steps', []))} étapes]\n"
                report += task_progress
            else:
                report += "Aucune tâche terminée pendant cette session.\n"

            report += "\n## Analyse de l'efficacité\n\n"
            if self.task_stack:
                total_duration = sum(t.get('duration_minutes', 0) for t in self.task_stack)
                avg_duration = total_duration / len(self.task_stack) if self.task_stack else 0

                report += f"**Durée moyenne des tâches**: {avg_duration:.1f} minutes\n\n"
                report += "### Durée des tâches complétées (en minutes)\n\n"

                for task in self.task_stack[-5:]:
                    duration = task.get('duration_minutes', 0)
                    bar_length = min(50, int(duration / 5))
                    report += f"- {task['description'][:20]}...: [{'■' * bar_length} {duration:.1f} min]\n"
            else:
                report += "Pas assez de données pour l'analyse.\n"

            report += "\n## Apprentissages Clés\n\n"
            recent_knowledge = self.get_recent_knowledge_for_report()
            if recent_knowledge:
                for know in recent_knowledge:
                    report += f"- **{know.get('topic', '')}**\n"
                    report += f"  - `{know.get('content', '')[:100]}...`\n\n"
            else:
                report += "Aucune connaissance ajoutée pendant cette session.\n"

            with open(self.session_report_file, 'w', encoding='utf-8') as f:
                f.write(report)

            logger.info(f"Rapport de session détaillé généré: {self.session_report_file}")

        except (IOError, KeyError) as e:
            logger.error(f"Erreur lors de la génération du rapport de session: {e}")

    def get_new_knowledge_count(self) -> int:
        """Compte les connaissances ajoutées dans les dernières 24h"""
        knowledge = self.load_memory_file("knowledge")
        count = 0
        time_window = datetime.now() - timedelta(hours=24)
        for know_data in knowledge.values():
            know_time = datetime.fromisoformat(know_data.get('timestamp', '1970-01-01T00:00:00'))
            if know_time > time_window:
                count += 1
        return count

    def get_recent_knowledge_for_report(self) -> list:
        """Récupère les connaissances récentes (24h) pour le rapport"""
        knowledge = self.load_memory_file("knowledge")
        time_window = datetime.now() - timedelta(hours=24)
        recent_knowledge = [
            know_data for know_data in knowledge.values()
            if datetime.fromisoformat(know_data.get('timestamp', '1970-01-01T00:00:00')) > time_window
        ]
        recent_knowledge.sort(key=lambda x: x['timestamp'], reverse=True)
        return recent_knowledge[:5]

    def generate_gentle_reminder(self):
        """Génération d'un rappel non intrusif"""
        try:
            current_time = datetime.now()

            if self.last_reminder and (current_time - self.last_reminder).total_seconds() < self.reminder_interval:
                return

            reminder = "# 🚨 Rappel Important\n\n"
            reminder += "## Votre Contexte de Travail\n\n"

            if self.current_task:
                task_time = datetime.fromisoformat(self.current_task['start_time'])
                task_duration = (datetime.now() - task_time).total_seconds() / 60

                reminder += f"**Tâche en cours**: {self.current_task['description']}\n"
                reminder += f"- Durée: {task_duration:.1f} minutes\n"

                if 'steps' in self.current_task:
                    reminder += f"- Étapes accomplies: {len(self.current_task['steps'])}\n"

                if 'work_plan' in self.current_task:
                    plan = self.current_task['work_plan']
                    reminder += f"- Plan d'action: étape {plan['current_step_index'] + 1}/{len(plan['steps'])}\n"
            else:
                reminder += "Aucune tâche active enregistrée.\n"

            intelligent_suggestions = self.analyze_recent_activity()
            if intelligent_suggestions:
                reminder += "\n## Suggestions Contextuelles\n\n"
                for suggestion in intelligent_suggestions:
                    reminder += f"- {suggestion}\n"

            reminder += "\n## Suggestions Générales\n\n"
            reminder += "1. Pensez à sauvegarder votre progression avec `memory --update-context`\n"
            reminder += "2. Consultez le contexte actuel avec `memory --show-context`\n"
            reminder += "3. Enregistrez les commandes importantes avec `memory --log-command`\n"

            git_suggestion = self.propose_git_commit()
            if git_suggestion:
                reminder += f"\n## Suggestion Git\n\n{git_suggestion}\n"

            reminder += f"\n*Dernière mise à jour: {datetime.now().strftime('%H:%M:%S')}*\n"

            with open(self.reminder_file, 'w', encoding='utf-8') as f:
                f.write(reminder)

            with self._state_lock:
                self.last_reminder = current_time
                self.reminder_count += 1

            self.send_desktop_notification("Rappel de Jules", "Votre contexte de travail a été mis à jour.")

            logs = self.load_memory_file("automatic_logs")
            reminder_record = {
                "content": reminder,
                "timestamp": datetime.now().isoformat(),
                "reminder_number": self.reminder_count,
                "context": self.get_context_summary()
            }

            logs["gentle_reminders"].append(reminder_record)
            self.save_memory_file("automatic_logs", logs)

        except (IOError, KeyError) as e:
            logger.error(f"Erreur génération rappel: {e}")

    def show_recent_activities(self, limit: int = 5):
        """Affichage des activités récentes"""
        try:
            activities = self.load_memory_file("activity")
            recent_activities = list(activities.values())[-limit:]

            print(f"\n📊 Activités Récentes (max {limit}):\n")
            for i, activity in enumerate(recent_activities):
                desc = activity.get('description', '')
                time_str = activity.get('timestamp', '')
                if desc and time_str:
                    activity_time = datetime.fromisoformat(time_str)
                    time_ago = (datetime.now() - activity_time).total_seconds() / 60
                    print(f"{i+1}. {desc} ({time_ago:.1f} min)")

            print("\n")

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Erreur affichage activités récentes: {e}")

    def show_current_context(self):
        """Affichage du contexte actuel"""
        try:
            print("\n💡 Contexte Actuel:\n")

            if self.current_task:
                task_time = datetime.fromisoformat(self.current_task['start_time'])
                task_duration = (datetime.now() - task_time).total_seconds() / 60

                print(f"Tâche en cours: {self.current_task['description']}")
                print(f"Débutée il y a: {task_duration:.1f} minutes")

                if 'steps' in self.current_task and self.current_task['steps']:
                    print(f"Étapes accomplies: {len(self.current_task['steps'])}")
                    print("Dernières étapes:")
                    for step in self.current_task['steps'][-3:]:
                        print(f"  - {step.get('description', '')[:60]}...")

                if 'work_plan' in self.current_task:
                    plan = self.current_task['work_plan']
                    print(f"Plan d'action: étape {plan['current_step_index'] + 1}/{len(plan['steps'])}")
                    if plan['current_step_index'] < len(plan['steps']):
                        print(f"Prochaine étape: {plan['steps'][plan['current_step_index']]}")
            else:
                print("Aucune tâche active")

            active_files = self.get_active_files()
            if active_files:
                print(f"\nFichiers récemment modifiés: {len(active_files)}")

            print("\n")

        except (KeyError, ValueError) as e:
            logger.error(f"Erreur affichage contexte: {e}")

    def search_knowledge(self, query: str, limit: int = 3):
        """Recherche dans les connaissances"""
        query = self.sanitize_input(query)
        try:
            query_embedding = self.generate_embedding(query)
            distances, indices = self.faiss_index.search(query_embedding, limit)

            knowledge = self.load_memory_file("knowledge")
            print(f"\n🔍 Résultats sémantiques pour \"{query}\":\n")

            found_results = False
            for i, idx in enumerate(indices[0]):
                if str(idx) in self.id_map:
                    know_id = self.id_map[str(idx)]
                    if know_id in knowledge:
                        know_content = knowledge[know_id]
                        score = 1 - distances[0][i]
                        print(f"{i+1}. [Score: {score:.2f}] {know_content.get('topic', 'Sans titre')}")
                        print(f"   {know_content.get('content', '')[:80]}...")
                        print(f"   Ajouté: {know_content.get('timestamp', '')[:10]}\n")
                        found_results = True

            if not found_results:
                print("Aucun résultat sémantique trouvé. Tentative par mot-clé...\n")
                results = []
                for know_id, know_content in knowledge.items():
                    if query.lower() in know_content.get('topic', '').lower() or query.lower() in know_content.get('content', '').lower():
                        results.append(know_content)

                for i, result in enumerate(results[:limit]):
                    print(f"{i+1}. {result.get('topic', 'Sans titre')}")
                    print(f"   {result.get('content', '')[:80]}...")
                    print(f"   Ajouté: {result.get('timestamp', '')[:10]}\n")

        except (ValueError, IndexError) as e:
            logger.error(f"Erreur recherche connaissances: {e}")

    def get_context_summary(self) -> dict:
        """Résumé du contexte"""
        return {
            "current_task": self.current_task,
            "recent_tasks": self.task_stack[-3:] if self.task_stack else [],
            "last_activity": self.last_activity.isoformat(),
            "active_files_count": len(self.get_active_files()),
            "reminder_count": self.reminder_count,
            "system_status": "collaborative"
        }

    def start_background_monitoring(self):
        """Démarrage de la surveillance en arrière-plan (mode daemon)"""
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            logger.info("Surveillance déjà en cours")
            return

        self.shutdown_requested = False

        def monitor_loop():
            while not self.shutdown_requested:
                try:
                    with self._state_lock:
                        inactivity_time = (datetime.now() - self.last_activity).total_seconds()
                    if inactivity_time > self.inactivity_threshold:
                        logger.info(f"Période d'inactivité détectée ({inactivity_time}s)")
                        self.generate_gentle_reminder()

                    self.save_memory_state()
                    self.update_context()

                    current_time = datetime.now()
                    if self.last_context_update is None or (current_time - self.last_context_update).total_seconds() >= self.context_update_interval:
                        self.generate_context_summary()
                        self.generate_status_report()

                    if (current_time - self.last_file_check).total_seconds() >= self.file_check_interval:
                        self.consolidate_preferences()
                        self.last_file_check = current_time

                    self.learn_from_errors()

                    time.sleep(60)

                except Exception as e:
                    logger.error(f"Erreur dans la boucle de surveillance: {e}")
                    time.sleep(30)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Surveillance en arrière-plan démarrée")

    def stop_background_monitoring(self):
        """Arrêt de la surveillance en arrière-plan"""
        self.shutdown_requested = True
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)
        logger.info("Surveillance en arrière-plan arrêtée")

    def graceful_shutdown(self, signum=None, frame=None):
        """Arrêt propre du système"""
        logger.info("Arrêt du système de mémoire demandé")
        self.stop_background_monitoring()

        try:
            self.save_memory_state()
            self.update_context()
            self.generate_session_report()

            logger.info("Mémoire sauvegardée avec succès")
        except Exception as e:
            logger.error(f"Erreur sauvegarde finale: {e}")

        time.sleep(0.1)  # Petite pause pour assurer l'écriture des fichiers
        sys.exit(0)

    def index_code_file(self, file_path: str):
        """Parses a Python file and indexes its functions, classes, and imports."""
        file_path = os.path.abspath(file_path)  # Sécurité
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            index = self.load_memory_file("code_index")

            file_data = {
                "path": file_path,
                "functions": [],
                "classes": [],
                "imports": [],
                "timestamp": datetime.now().isoformat()
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    docstring = ast.get_docstring(node) or ""
                    file_data["functions"].append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "docstring": docstring.strip(),
                        "line": node.lineno
                    })
                elif isinstance(node, ast.ClassDef):
                    docstring = ast.get_docstring(node) or ""
                    file_data["classes"].append({
                        "name": node.name,
                        "docstring": docstring.strip(),
                        "line": node.lineno
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        file_data["imports"].append(alias.name)

            index[file_path] = file_data
            self.save_memory_file("code_index", index)
            logger.info(f"Code index updated for {file_path}")

        except (SyntaxError, IOError) as e:
            logger.error(f"Error indexing code file {file_path}: {e}")

    def index_all_code(self):
        """Index all code files in the workspace."""
        try:
            code_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.rs', '.go', '.ts']
            for root, dirs, files in os.walk(self.workspace_path):
                for file in files:
                    if any(file.endswith(ext) for ext in code_extensions):
                        file_path = os.path.join(root, file)
                        if file.endswith('.py'):
                            self.index_code_file(file_path)
                        else:
                            index = self.load_memory_file("code_index")
                            index[file_path] = {
                                "path": file_path,
                                "timestamp": datetime.now().isoformat()
                            }
                            self.save_memory_file("code_index", index)

            logger.info("All code files indexed")
        except (OSError, ValueError) as e:
            logger.error(f"Error indexing all code: {e}")

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generates an embedding for a given text (lazy load model)."""
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._embedding_model.encode(text).astype('float32').reshape(1, -1)

    def load_faiss_index(self):
        """Loads the FAISS index from disk."""
        index_path = os.path.join(self.memory_dir, "faiss_index.bin")
        map_path = os.path.join(self.memory_dir, "faiss_id_map.json")
        if os.path.exists(index_path) and os.path.exists(map_path):
            self.faiss_index = faiss.read_index(index_path)
            with open(map_path, 'r', encoding='utf-8') as f:
                self.id_map = json.load(f)

    def save_faiss_index(self):
        """Saves the FAISS index to disk."""
        index_path = os.path.join(self.memory_dir, "faiss_index.bin")
        map_path = os.path.join(self.memory_dir, "faiss_id_map.json")
        faiss.write_index(self.faiss_index, index_path)
        with open(map_path, 'w', encoding='utf-8') as f:
            json.dump(self.id_map, f, indent=2)

    def execute_tool_command(self, command_parts: list[str], timeout: int = 60) -> tuple[bool, str, str]:
        """Executes a shell command securely and logs its output."""
        logger.info(f"Executing command: {' '.join(command_parts)}")
        try:
            result = subprocess.run(
                command_parts,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.workspace_path,
                shell=False  # Sécurité: Pas de shell
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            self.log_command(' '.join(command_parts), stdout, "tool_execution")
            logger.info("Command succeeded.")
            return True, stdout, stderr

        except subprocess.CalledProcessError as e:
            error_output = e.stderr.strip()
            self.log_command(' '.join(command_parts), error_output, "tool_execution_error")
            logger.error(f"Command failed with exit code {e.returncode}: {error_output}")
            return False, e.stdout.strip(), error_output

        except subprocess.TimeoutExpired:
            self.log_command(' '.join(command_parts), "Timeout", "tool_execution_timeout")
            logger.error("Command timed out.")
            return False, "", "Command timed out."

        except (OSError, ValueError) as e:
            self.log_command(' '.join(command_parts), str(e), "tool_execution_error")
            logger.error(f"Error executing command: {e}")
            return False, "", str(e)

    def analyze_recent_activity(self) -> list:
        """Analyzes recent logs for potential issues or suggestions."""
        commands = self.load_memory_file("commands")

        recent_commands = list(commands.values())[-10:]
        error_commands = [cmd['command'] for cmd in recent_commands if "error" in cmd.get('result', '').lower()]

        repeated_errors = {cmd for cmd in error_commands if error_commands.count(cmd) > 1}

        suggestions = []
        if repeated_errors:
            suggestions.append(
                f"J'ai remarqué des erreurs répétées sur les commandes suivantes : {', '.join(repeated_errors)}. Pensez à vérifier la documentation ou la syntaxe."
            )

        return suggestions

    def propose_git_commit(self) -> str | None:
        """Checks for Git changes and suggests a commit."""
        success, git_status_output, _ = self.execute_tool_command(["git", "status", "--porcelain"], timeout=10)

        if not success or not git_status_output:
            return None

        commands = self.load_memory_file("commands")
        activities = self.load_memory_file("activity")
        recent_work = list(commands.values())[-5:] + list(activities.values())[-5:]

        commit_message_parts = []
        for item in recent_work:
            if 'description' in item:
                commit_message_parts.append(item['description'])
            elif 'command' in item:
                commit_message_parts.append(item['command'])

        commit_message = f"feat: a new memory-driven update based on recent activities.\n\n"
        commit_message += "\n".join([f"- {part}" for part in commit_message_parts])

        return f"J'ai détecté des changements dans votre dépôt Git. Souhaitez-vous les valider avec ce message :\n\n```\n{commit_message}\n```\n\nPour accepter, utilisez la commande :\n`git commit -am \"{commit_message.splitlines()[0]}\"`"

    def check_code_quality(self, file_path: str):
        """Exécute un linter sur un fichier et stocke les avertissements."""
        file_path = os.path.abspath(file_path)
        if not file_path.endswith('.py'):
            logger.info(f"Ignorance du fichier non-Python: {file_path}")
            return

        success, output, error = self.execute_tool_command(["pylint", file_path], timeout=30)

        if success and output:
            logger.info(f"Pylint a trouvé des problèmes dans le fichier: {file_path}")
            self.save_knowledge(
                f"Analyse de code: {os.path.basename(file_path)}",
                output,
                category="code_quality"
            )
            if "warning" in output or "error" in output:
                self.generate_gentle_reminder()

    def send_desktop_notification(self, title: str, message: str):
        """Envoie une notification desktop (compatible Linux avec notify-send)."""
        title = self.sanitize_input(title)
        message = self.sanitize_input(message)
        try:
            subprocess.run(
                ['notify-send', title, message],
                check=True,
                capture_output=True,
                text=True,
                shell=False
            )
            logger.info(f"Notification envoyée: {title}")
        except FileNotFoundError:
            logger.warning("Commande 'notify-send' non trouvée.")
        except (subprocess.CalledProcessError, OSError) as e:
            logger.error(f"Erreur lors de l'envoi de la notification: {e}")

    def consolidate_preferences(self):
        """Consolide les préférences de l'utilisateur en analysant l'activité récente."""
        try:
            preferences = self.load_memory_file("preferences")
            commands = self.load_memory_file("commands")
            active_files = self.get_active_files()

            for cmd in commands.values():
                if 'install' in cmd['command'] and 'pip' in cmd['command']:
                    lib_name = cmd['command'].split('install ')[-1].split()[0]
                    preferences['preferred_libraries'][lib_name] = preferences['preferred_libraries'].get(lib_name, 0) + 1

            if active_files:
                naming_styles = []
                for file_info in active_files:
                    file_name = file_info['path'].split('/')[-1]
                    if '_' in file_name:
                        naming_styles.append('snake_case')
                    elif re.match(r'^[a-z][a-zA-Z0-9]*$', file_name.split('.')[0]):
                        naming_styles.append('camelCase')

                if naming_styles:
                    most_common_style = max(set(naming_styles), key=naming_styles.count)
                    preferences['naming_conventions'] = {'filename_style': most_common_style}

            self.save_memory_file("preferences", preferences)
            logger.info("Préférences utilisateur consolidées.")

        except (KeyError, ValueError) as e:
            logger.error(f"Erreur lors de la consolidation des préférences: {e}")

    def learn_from_errors(self):
        """Apprend les errors récurrents et propose documentation."""
        commands = self.load_memory_file("commands")
        error_patterns = defaultdict(int)

        for cmd_data in commands.values():
            if 'error' in cmd_data.get('result', '').lower():
                error_patterns[cmd_data['command']] += 1

        for command, count in error_patterns.items():
            if count > 2:
                solution = self.find_solution_for_error(command)
                if solution:
                    topic = f"Résolution d'erreur: {command[:50]}..."
                    content = f"L'erreur suivante s'est produite de manière récurrente:\n`{command}`\n\nSolution trouvée par la suite:\n`{solution}`"
                    self.propose_knowledge_addition(topic, content, "auto_error_fix")

    def find_solution_for_error(self, failed_command: str) -> str | None:
        """Recherche une commande réussie après échec."""
        commands = list(self.load_memory_file("commands").values())
        last_failed_index = -1
        for i, cmd in enumerate(commands):
            if cmd.get('command') == failed_command and 'error' in cmd.get('result', '').lower():
                last_failed_index = i

        if last_failed_index != -1 and last_failed_index < len(commands) - 1:
            next_command = commands[last_failed_index + 1]
            if 'error' not in next_command.get('result', '').lower():
                return next_command.get('command')

        return None

    def propose_knowledge_addition(self, topic: str, content: str, category: str):
        """Génère un rappel pour proposer l'ajout d'une nouvelle connaissance."""
        reminder = f"# 🚨 Proposition de Connaissance\n\nJ'ai identifié un problème récurrent et sa solution potentielle.\n\nSouhaitez-vous ajouter ceci à votre base de connaissances ?\n\n**Sujet**: {topic}\n\n**Contenu**:\n```\n{content}\n```\n\nPour accepter, utilisez la commande:\n`memory --save-knowledge \"{topic}\" \"{content}\" --knowledge-category \"{category}\"`\n"

        with open(self.reminder_file, 'w', encoding='utf-8') as f:
            f.write(reminder)

        with self._state_lock:
            self.last_reminder = datetime.now()
            self.reminder_count += 1

    def load_jira_config(self) -> dict:
        """Charge la configuration Jira depuis un fichier."""
        config = self.load_memory_file("jira_config")
        if "encrypted" in config:
            config = self.decrypt_sensitive_data(config["encrypted"])
        return config

    def start_task_from_jira_ticket(self, ticket_id: str):
        """Démarre une tâche en récupérant les informations d'un ticket Jira."""
        jira_config = self.load_jira_config()
        if not jira_config:
            print("❌ Configuration Jira non trouvée. Veuillez la configurer d'abord.")
            return

        try:
            # Simulation d'une réponse API (à remplacer par API réelle en prod)
            mock_response = {
                "key": ticket_id,
                "fields": {
                    "summary": "Développer une nouvelle fonctionnalité d'exportation de données",
                    "description": "L'utilisateur souhaite pouvoir exporter les données de son profil au format CSV.",
                    "status": {"name": "En cours"}
                }
            }

            summary = mock_response['fields']['summary']
            description = mock_response['fields']['description']

            self.start_task(summary, task_type="feature_development", metadata={"jira_id": ticket_id})
            self.save_knowledge(f"Contexte Jira du ticket {ticket_id}", f"{summary}\n\n{description}", category="jira")

            print(f"✅ Tâche '{summary}' démarrée, liée au ticket Jira '{ticket_id}'.")

        except (KeyError, ValueError) as e:
            logger.error(f"Erreur lors de la connexion à Jira: {e}")
            print("❌ Erreur lors du démarrage de la tâche depuis Jira.")

    def get_relevant_knowledge(self, query: str) -> list:
        """Récupère les connaissances pertinentes pour une requête"""
        query = self.sanitize_input(query)
        try:
            query_embedding = self.generate_embedding(query)
            distances, indices = self.faiss_index.search(query_embedding, 3)

            knowledge = self.load_memory_file("knowledge")
            relevant_knowledge = []

            for idx in indices[0]:
                if idx in self.id_map:
                    know_id = self.id_map[idx]
                    if know_id in knowledge:
                        relevant_knowledge.append(knowledge[know_id])

            return relevant_knowledge
        except (ValueError, IndexError) as e:
            logger.error(f"Erreur recherche connaissances pertinentes: {e}")
            return []

    def analyze_impact(self, file_path: str) -> dict | None:
        """Analyse l'impact d'une modification d'un fichier sur le reste du codebase."""
        file_path = os.path.abspath(file_path)
        try:
            if not os.path.exists(file_path):
                print(f"❌ Le fichier {file_path} n'existe pas.")
                return None

            code_index = self.load_memory_file("code_index")

            dependencies = []
            for indexed_file, data in code_index.items():
                if indexed_file == file_path:
                    continue

                if self.has_dependency(indexed_file, file_path, code_index):
                    dependencies.append(indexed_file)

            impact_report = {
                "file": file_path,
                "dependencies": dependencies,
                "timestamp": datetime.now().isoformat(),
                "risk_level": "high" if len(dependencies) > 5 else "medium" if len(dependencies) > 0 else "low"
            }

            impact_analyses = self.load_memory_file("impact_analysis")
            impact_id = f"impact_{int(time.time())}"
            impact_analyses[impact_id] = impact_report
            self.save_memory_file("impact_analysis", impact_analyses)

            print(f"\n🔍 Analyse d'impact pour {file_path}:")
            print(f"Niveau de risque: {impact_report['risk_level']}")
            print(f"Fichiers dépendants ({len(dependencies)}):")
            for dep in dependencies[:10]:
                print(f"  - {dep}")
            if len(dependencies) > 10:
                print(f"  ... et {len(dependencies) - 10} autres")

            return impact_report

        except (IOError, KeyError) as e:
            logger.error(f"Erreur lors de l'analyse d'impact: {e}")
            return None

    def has_dependency(self, source_file: str, target_file: str, code_index: dict) -> bool:
        """Vérifie si un fichier source dépend d'un fichier cible."""
        try:
            source_data = code_index.get(source_file, {})

            if source_file.endswith('.py') and 'imports' in source_data:
                target_module = os.path.basename(target_file).replace('.py', '')
                for import_name in source_data.get('imports', []):
                    if target_module in import_name:
                        return True

            if os.path.exists(source_file):
                with open(source_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                target_basename = os.path.basename(target_file)
                if target_basename in content:
                    return True

            return False

        except (IOError, KeyError) as e:
            logger.error(f"Erreur vérification dépendance: {e}")
            return False

    def create_snapshot(self, description: str) -> str | None:
        """Crée un snapshot du travail en cours."""
        description = self.sanitize_input(description)
        try:
            success, _, _ = self.execute_tool_command(["git", "status"])
            if not success:
                print("❌ Git n'est pas disponible dans ce répertoire.")
                return None

            snapshot_id = f"snap_{int(time.time())}"
            stash_name = f"jules_snapshot_{snapshot_id}"

            success, output, error = self.execute_tool_command(["git", "stash", "push", "-m", stash_name])

            if success:
                snapshots = self.load_memory_file("snapshots")
                snapshots[snapshot_id] = {
                    "id": snapshot_id,
                    "description": description,
                    "timestamp": datetime.now().isoformat(),
                    "stash_name": stash_name,
                    "context": self.get_context_summary()
                }
                self.save_memory_file("snapshots", snapshots)

                print(f"✅ Snapshot '{description}' créé avec l'ID: {snapshot_id}")
                return snapshot_id
            else:
                print(f"❌ Erreur lors de la création du snapshot: {error}")
                return None

        except (IOError, KeyError) as e:
            logger.error(f"Erreur création snapshot: {e}")
            return None

    def list_snapshots(self):
        """Liste tous les snapshots disponibles."""
        try:
            snapshots = self.load_memory_file("snapshots")

            if not snapshots:
                print("Aucun snapshot disponible.")
                return

            print("\n📸 Snapshots disponibles:\n")
            for snap_id, snap_data in snapshots.items():
                print(f"ID: {snap_id}")
                print(f"Description: {snap_data.get('description', 'Sans description')}")
                print(f"Date: {snap_data.get('timestamp', '')[:19]}")
                print("---")

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Erreur liste snapshots: {e}")

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restaure un snapshot précédent."""
        try:
            snapshots = self.load_memory_file("snapshots")
            snapshot = snapshots.get(snapshot_id)

            if not snapshot:
                print(f"❌ Snapshot {snapshot_id} non trouvé.")
                return False

            stash_name = snapshot.get('stash_name')
            if not stash_name:
                print("❌ Nom de stash non trouvé dans le snapshot.")
                return False

            success, output, error = self.execute_tool_command(["git", "stash", "list"])
            if not success:
                print(f"❌ Erreur liste stashes: {error}")
                return False

            stash_found = False
            stash_index = None
            for line in output.split('\n'):
                if stash_name in line:
                    stash_index = line.split(':')[0]
                    stash_found = True
                    break

            if not stash_found:
                print("❌ Stash correspondant non trouvé.")
                return False

            success, output, error = self.execute_tool_command(["git", "stash", "apply", stash_index])
            if success:
                print(f"✅ Snapshot {snapshot_id} restauré avec succès.")

                context = snapshot.get('context')
                if context:
                    self.current_task = context.get('current_task')
                    self.task_stack = context.get('recent_tasks', [])
                    self.update_context()
                    print("Contexte de travail également restauré.")

                return True
            else:
                print(f"❌ Erreur application stash: {error}")
                return False

        except (IOError, KeyError) as e:
            logger.error(f"Erreur restauration snapshot: {e}")
            return False

    def generate_context_graph(self) -> bool:
        """Génère une visualisation graphique du contexte actuel."""
        try:
            success, _, _ = self.execute_tool_command(["dot", "-V"])
            if not success:
                print("❌ Graphviz n'est pas installé. Installez-le avec: sudo apt-get install graphviz")
                return False

            dot_content = 'digraph G {\n'
            dot_content += '  rankdir=LR;\n  node [shape=box, style=filled, fillcolor=lightblue];\n\n'

            if self.current_task:
                task_label = self.current_task['description'].replace('"', '\\"')
                dot_content += f'  current_task [label="{task_label}", fillcolor=lightgreen];\n'

            active_files = self.get_active_files()
            for i, file_info in enumerate(active_files[:5]):
                file_name = os.path.basename(file_info['path']).replace('"', '\\"')
                dot_content += f'  file_{i} [label="{file_name}", fillcolor=lightyellow];\n'
                if self.current_task:
                    dot_content += f'  current_task -> file_{i} [style=dashed];\n'

            if self.current_task:
                relevant_knowledge = self.current_task.get('relevant_knowledge', [])
                for i, knowledge in enumerate(relevant_knowledge[:3]):
                    topic = knowledge.get('topic', '').replace('"', '\\"')[:20]
                    dot_content += f'  knowledge_{i} [label="{topic}...", fillcolor=lightpink];\n'
                    dot_content += f'  current_task -> knowledge_{i} [style=dotted];\n'

            dot_content += '}\n'

            dot_file = os.path.join(self.memory_dir, "context.dot")
            with open(dot_file, 'w', encoding='utf-8') as f:
                f.write(dot_content)

            success, _, error = self.execute_tool_command(["dot", "-Tpng", dot_file, "-o", self.graph_file])

            if success:
                print(f"✅ Graphique de contexte généré: {self.graph_file}")
                return True
            else:
                print(f"❌ Erreur génération graphique: {error}")
                return False

        except (IOError, subprocess.CalledProcessError) as e:
            logger.error(f"Erreur génération graphique contexte: {e}")
            return False

    def suggest_next_task(self) -> dict | None:
        """Suggère la prochaine tâche à effectuer basée sur la priorité et les dépendances."""
        try:
            activities = self.load_memory_file("activity")
            pending_tasks = [
                {"id": task_id, "description": task_data.get('description', ''), "timestamp": task_data.get('timestamp', ''), "importance": task_data.get('importance', 0.5)}
                for task_id, task_data in activities.items() if task_data.get('category') == 'task' and task_data.get('result') is None
            ]

            if not pending_tasks:
                print("✅ Aucune tâche en attente. Toutes les tâches sont complétées!")
                return None

            pending_tasks.sort(key=lambda x: (x['importance'], x['timestamp']), reverse=True)

            next_task = pending_tasks[0]
            print(f"\n🎯 Suggestion de prochaine tâche:")
            print(f"Description: {next_task['description']}")
            print(f"Priorité: {next_task['importance']}/1.0")
            print(f"En attente depuis: {datetime.fromisoformat(next_task['timestamp']).strftime('%d/%m/%Y %H:%M')}")

            return next_task

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Erreur suggestion tâche suivante: {e}")
            return None

    def _compress_data(self, data: dict, compression_level: str) -> str:
        """Compression intelligente des données"""
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        level = self.compression_levels[compression_level]

        if compression_level in ["light", "medium"]:
            compressed = zlib.compress(json_str.encode('utf-8'), level=level)
        else:
            compressed = gzip.compress(json_str.encode('utf-8'), compresslevel=level)

        return base64.b64encode(compressed).decode('ascii')

    def _decompress_data(self, compressed_data: str, compression_type: str) -> dict:
        """Décompression des données"""
        try:
            compressed_bytes = base64.b64decode(compressed_data.encode('ascii'))

            if compression_type in ["light", "medium"]:
                decompressed = zlib.decompress(compressed_bytes)
            else:
                decompressed = gzip.decompress(compressed_bytes)

            return json.loads(decompressed.decode('utf-8'))

        except (zlib.error, gzip.BadGzipFile) as e:
            logger.error(f"Erreur décompression: {e}")
            return {}

    def auto_compress_old_data(self):
        """Compression automatique des données anciennes"""
        for data_type in self.compression_delays:
            self._compress_if_old(data_type)

    def _compress_if_old(self, data_type: str):
        """Compresse les données si elles sont assez anciennes"""
        file_path = self.memory_files.get(data_type)
        if not file_path or not os.path.exists(file_path):
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                enhanced_data = json.load(f)

            metadata = enhanced_data.get("metadata", {})
            if metadata.get("compression_status", "raw") != "raw":
                return

            created_at = datetime.fromisoformat(metadata.get("created_at", datetime.now().isoformat()))
            age_days = (datetime.now() - created_at).days

            if age_days >= self.compression_delays.get(data_type, 0):
                compression_level = self.compression_strategy.get(data_type, "medium")
                compressed_content = self._compress_data(enhanced_data["content"], compression_level)

                metadata["compression_status"] = compression_level
                metadata["compressed_at"] = datetime.now().isoformat()
                metadata["compressed_size"] = len(compressed_content)
                metadata["compression_ratio"] = metadata["compressed_size"] / metadata["original_size"]

                enhanced_data["content"] = compressed_content

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(enhanced_data, f, indent=2, ensure_ascii=False)

                logger.info(f"Compression {data_type}: {metadata['compression_ratio']:.1%}")

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Erreur compression {data_type}: {e}")

    def start_auto_compression_service(self):
        """Démarre le service de compression automatique en arrière-plan"""
        def compression_worker():
            while not self.shutdown_requested:
                try:
                    self.auto_compress_old_data()
                    time.sleep(3600)
                except Exception as e:
                    logger.error(f"Erreur service compression: {e}")
                    time.sleep(300)

        thread = threading.Thread(target=compression_worker, daemon=True)
        thread.start()
        logger.info("Service de compression automatique démarré")

    def get_storage_stats(self) -> dict:
        """Retourne les statistiques de stockage"""
        stats = {
            "total_data_types": 0,
            "total_size_bytes": 0,
            "compressed_data_types": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "global_compression_ratio": 0,
            "space_saved_bytes": 0,
            "by_data_type": {}
        }

        for data_type in self.memory_files:
            file_path = self.memory_files[data_type]
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        enhanced_data = json.load(f)
                    metadata = enhanced_data.get("metadata", {})

                    stats["total_data_types"] += 1
                    stats["total_original_size"] += metadata.get("original_size", 0)

                    if metadata.get("compression_status", "raw") != "raw":
                        stats["compressed_data_types"] += 1
                        current_size = metadata.get("compressed_size", 0)
                        stats["total_compressed_size"] += current_size
                        space_saved = metadata["original_size"] - current_size
                        stats["space_saved_bytes"] += space_saved

                        stats["by_data_type"][data_type] = {
                            "compression_ratio": metadata.get("compression_ratio", 1.0),
                            "space_saved": space_saved,
                            "status": metadata["compression_status"]
                        }
                    else:
                        stats["total_compressed_size"] += metadata.get("original_size", 0)
                        stats["by_data_type"][data_type] = {
                            "compression_ratio": 1.0,
                            "space_saved": 0,
                            "status": "raw"
                        }

                    stats["total_size_bytes"] += os.path.getsize(file_path)

                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Erreur stats {data_type}: {e}")

        if stats["total_original_size"] > 0:
            stats["global_compression_ratio"] = stats["total_compressed_size"] / stats["total_original_size"]

        stats["total_size_mb"] = stats["total_size_bytes"] / (1024 * 1024)
        stats["space_saved_mb"] = stats["space_saved_bytes"] / (1024 * 1024)
        stats["total_original_size_mb"] = stats["total_original_size"] / (1024 * 1024)
        stats["total_compressed_size_mb"] = stats["total_compressed_size"] / (1024 * 1024)

        return stats

    def export_compressed_data(self, data_type: str, export_path: str) -> bool:
        """Exporte les données compressées pour archivage"""
        export_path = os.path.abspath(export_path)
        try:
            file_path = self.memory_files.get(data_type)
            if not file_path or not os.path.exists(file_path):
                return False

            shutil.copy2(file_path, export_path)

            logger.info(f"Données {data_type} exportées vers: {export_path}")
            return True

        except (IOError, shutil.Error) as e:
            logger.error(f"Erreur export {data_type}: {e}")
            return False

    def get_compression_timeline(self) -> dict:
        """Retourne le calendrier de compression"""
        timeline = {}
        now = datetime.now()

        for data_type in self.compression_delays:
            file_path = self.memory_files.get(data_type)
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        enhanced_data = json.load(f)
                    metadata = enhanced_data.get("metadata", {})

                    created_at = datetime.fromisoformat(metadata.get("created_at", now.isoformat()))
                    compression_time = created_at + timedelta(days=self.compression_delays[data_type])

                    timeline[data_type] = {
                        "created_at": created_at.isoformat(),
                        "compression_delay_days": self.compression_delays[data_type],
                        "scheduled_compression": compression_time.isoformat(),
                        "status": metadata.get("compression_status", "raw"),
                        "days_until_compression": max(0, (compression_time - now).days) if metadata.get("compression_status", "raw") == "raw" else 0
                    }
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Erreur timeline {data_type}: {e}")

        return timeline

    def generate_intelligent_reminders(self) -> list:
        """Génère des rappels basés sur le contexte et les patterns"""
        reminders = []

        incomplete_tasks = self.get_incomplete_tasks()
        if incomplete_tasks:
            reminders.append(f"📋 Tâches en attente: {len(incomplete_tasks)}")

        if self.current_task:
            relevant_knowledge = self.get_relevant_knowledge(self.current_task['description'])
            if relevant_knowledge:
                reminders.append(f"💡 Connaissances pertinentes disponibles")

        return reminders

    def learn_user_patterns(self):
        """Apprend les patterns de l'utilisateur automatiquement"""
        activities = self.load_memory_file("activity")

        work_hours = defaultdict(int)
        for activity in activities.values():
            hour = datetime.fromisoformat(activity.get('timestamp', datetime.now().isoformat())).hour
            work_hours[hour] += activity.get('importance', 0.5)

        preferences = self.load_memory_file("preferences")
        preferences['optimal_hours'] = dict(sorted(work_hours.items(), key=lambda x: x[1], reverse=True)[:3])
        self.save_memory_file("preferences", preferences)

    def advanced_dependency_analysis(self, file_path: str) -> dict:
        """Analyse approfondie des dépendances entre fichiers"""
        dependencies = {
            'imports': [],
            'function_calls': [],
            'class_references': [],
            'file_includes': []
        }

        file_path = os.path.abspath(file_path)
        try:
            if file_path.endswith('.py'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                import_pattern = r'^(?:from|import)\s+(\S+)'
                dependencies['imports'] = re.findall(import_pattern, content, re.MULTILINE)

                function_pattern = r'(\w+)\s*\('
                dependencies['function_calls'] = re.findall(function_pattern, content)

        except (IOError, re.error) as e:
            logger.error(f"Erreur analyse dépendances: {e}")

        return dependencies

    def generate_advanced_visualization(self):
        """Génère des visualisations plus détaillées"""
        try:
            activities = self.load_memory_file("activity")
            activity_dates = []
            importance_scores = []

            for activity in activities.values():
                activity_dates.append(datetime.fromisoformat(activity.get('timestamp', datetime.now().isoformat())))
                importance_scores.append(activity.get('importance', 0.5))

            plt.figure(figsize=(10, 6))
            plt.plot(activity_dates, importance_scores, 'o-', alpha=0.7)
            plt.title('Activité au fil du temps')
            plt.xlabel('Date')
            plt.ylabel('Importance')
            plt.gcf().autofmt_xdate()
            plt.savefig(os.path.join(self.memory_dir, 'activity_timeline.png'))
            plt.close()

        except ImportError:
            logger.warning("Matplotlib non disponible pour les visualisations avancées")
        except (ValueError, KeyError) as e:
            logger.error(f"Erreur visualisation: {e}")

    def setup_encryption(self) -> Fernet:
        """Configure le chiffrement pour les données sensibles"""
        key_path = os.path.join(self.memory_dir, '.encryption_key')
        if not os.path.exists(key_path):
            key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(key)
            os.chmod(key_path, 0o600)  # Permissions sécurisées
        else:
            with open(key_path, 'rb') as f:
                key = f.read()

        return Fernet(key)

    def encrypt_sensitive_data(self, data: dict) -> str:
        """Chiffre les données sensibles"""
        return self.cipher_suite.encrypt(json.dumps(data).encode()).decode()

    def decrypt_sensitive_data(self, encrypted_data: str) -> dict:
        """Déchiffre les données sensibles"""
        try:
            decrypted = self.cipher_suite.decrypt(encrypted_data.encode())
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Erreur décryptage: {e}")
            return {}

    def validate_memory_data(self, data: dict, schema_type: str) -> bool:
        """Valide la structure des données en mémoire"""
        schemas = {
            'activity': {
                'description': str,
                'timestamp': str,
                'category': str,
                'importance': float
            },
            'knowledge': {
                'topic': str,
                'content': str,
                'category': str
            }
        }

        if schema_type not in schemas:
            return True

        schema = schemas[schema_type]
        for field, field_type in schema.items():
            if field not in data or not isinstance(data[field], field_type):
                logger.warning(f"Validation échouée pour {field} dans {schema_type}")
                return False

        return True

    def setup_ci_cd_integration(self):
        """Intègre avec les systèmes CI/CD"""
        ci_configs = {
            'github': '.github/workflows/memory-sync.yml',
            'gitlab': '.gitlab-ci.yml',
            'jenkins': 'Jenkinsfile'
        }

        for ci_system, config_file in ci_configs.items():
            config_path = os.path.join(self.workspace_path, config_file)
            if os.path.exists(config_path):
                self.save_knowledge(
                    f"Configuration {ci_system}",
                    f"Fichier de configuration détecté: {config_file}",
                    category="ci_cd"
                )

    def generate_performance_metrics(self) -> dict:
        """Génère des métriques de performance"""
        metrics = {
            'memory_usage': self.get_memory_usage(),
            'response_time': self.get_average_response_time(),
            'task_completion_rate': self.get_task_completion_rate(),
            'knowledge_utilization': self.get_knowledge_utilization_rate()
        }

        performance_data = self.load_memory_file("performance")
        performance_data[datetime.now().isoformat()] = metrics
        self.save_memory_file("performance", performance_data)

        return metrics

    def get_memory_usage(self) -> float:
        """Calcule l'utilisation de la mémoire"""
        total_size = 0
        for file_path in self.memory_files.values():
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
        return total_size / (1024 * 1024)  # MB

    def get_average_response_time(self) -> float:
        """À implémenter: Moyenne des temps de réponse"""
        return 0.0  # Placeholder

    def get_task_completion_rate(self) -> float:
        """À implémenter: Taux de complétion des tâches"""
        return 0.0  # Placeholder

    def get_knowledge_utilization_rate(self) -> float:
        """À implémenter: Taux d'utilisation des connaissances"""
        return 0.0  # Placeholder

    def send_context_contextual_notification(self, message: str, level: str = "info"):
        """Envoie des notifications contextuelles"""
        notification_levels = {
            "info": "💡",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }

        emoji = notification_levels.get(level, "💡")
        formatted_message = f"{emoji} {self.sanitize_input(message)}"

        self.send_desktop_notification("Jules Memory", formatted_message)
        print(f"\n{formatted_message}\n")

    def create_backup(self, backup_name: str | None = None) -> str | None:
        """Crée une sauvegarde complète"""
        backup_name = backup_name or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = os.path.join(self.workspace_path, 'backups', backup_name)

        os.makedirs(backup_dir, exist_ok=True)

        for file_type, file_path in self.memory_files.items():
            if os.path.exists(file_path):
                shutil.copy2(file_path, os.path.join(backup_dir, f"{file_type}.json"))

        return backup_dir

    def restore_backup(self, backup_path: str):
        """Restaure une sauvegarde"""
        backup_path = os.path.abspath(backup_path)
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup non trouvé: {backup_path}")

        for file_type in self.memory_files:
            backup_file = os.path.join(backup_path, f"{file_type}.json")
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, self.memory_files[file_type])

        self.load_context()

    def sanitize_input(self, input_str: str) -> str:
        """Sanitize inputs pour prévenir injections"""
        return re.sub(r"[^\w\s\.'-]", '', input_str)  # Autorise les apostrophes

    def get_incomplete_tasks(self) -> list:
        """Récupère les tâches incomplètes (pour rappels intelligents)"""
        activities = self.load_memory_file("activity")
        return [task for task in activities.values() if task.get('category') == 'task' and task.get('status') != 'completed']

# Interface CLI étendue
def setup_cli():
    parser = argparse.ArgumentParser(description="Système de Mémoire Collaboratif pour Jules")

    parser.add_argument("--log-activity", type=str, help="Enregistrer une activité")
    parser.add_argument("--log-result", type=str, default="", help="Résultat de l'activité")
    parser.add_argument("--log-category", type=str, default="general", help="Catégorie de l'activité")
    parser.add_argument("--importance", type=float, default=0.5, help="Importance de l'activité (0.0-1.0)")

    parser.add_argument("--log-command", type=str, help="Enregistrer une commande exécutée")
    parser.add_argument("--command-result", type=str, default="", help="Résultat de la commande")
    parser.add_argument("--command-context", type=str, default="", help="Contexte de la commande")

    parser.add_argument("--save-knowledge", nargs=2, metavar=("SUJET", "CONTENU"),
                        help="Sauvegarder une connaissance")
    parser.add_argument("--knowledge-category", type=str, default="general", help="Catégorie de la connaissance")

    parser.add_argument("--start-task", type=str, help="Démarrer une nouvelle tâche")
    parser.add_argument("--start-plan", type=str, help="Démarrer une tâche avec un plan d'action")
    parser.add_argument("--task-type", type=str, default="general", help="Type de tâche")
    parser.add_argument("--add-step", type=str, help="Ajouter une étape à la tâche en cours")
    parser.add_argument("--step-result", type=str, default="", help="Résultat de l'étape")
    parser.add_argument("--complete-task", type=str, help="Terminer la tâche en cours")
    parser.add_argument("--task-status", type=str, default="completed", help="Statut de la tâche")
    parser.add_argument("--start-subtask", type=str, help="Démarrer une sous-tâche")
    parser.add_argument("--resume-task", action="store_true", help="Reprendre la tâche parente après la fin d'une sous-tâche")
    parser.add_argument("--next-step", action="store_true", help="Passer à l'étape suivante du plan de travail")

    parser.add_argument("--show-recent", action="store_true", help="Afficher les activités récentes")
    parser.add_argument("--recent-limit", type=int, default=5, help="Nombre d'activités à afficher")
    parser.add_argument("--show-context", action="store_true", help="Afficher le contexte actuel")
    parser.add_argument("--search", type=str, help="Rechercher dans les connaissances")
    parser.add_argument("--search-limit", type=int, default=3, help="Nombre de résultats à afficher")

    parser.add_argument("--update-context", action="store_true", help="Mettre à jour le contexte")
    parser.add_argument("--generate-report", action="store_true", help="Générer un rapport de statut")
    parser.add_argument("--generate-reminder", action="store_true", help="Générer un rappel")
    parser.add_argument("--end-session", action="store_true", help="Générer un rapport de session et terminer")

    parser.add_argument("--daemon", action="store_true", help="Démarrer en mode démon")
    parser.add_argument("--stop-daemon", action="store_true", help="Arrêter le mode démon")

    parser.add_argument("--start-from-jira", type=str, help="Démarrer une tâche à partir d'un ticket Jira (ex: 'PRO-123')")

    parser.add_argument("--index-code", action="store_true", help="Indexer tout le code du workspace")
    parser.add_argument("--analyze-impact", type=str, help="Analyser l'impact d'un changement de fichier")
    parser.add_argument("--create-snapshot", type=str, help="Créer un snapshot du travail en cours")
    parser.add_argument("--list-snapshots", action="store_true", help="Lister les snapshots disponibles")
    parser.add_argument("--restore-snapshot", type=str, help="Restaurer un snapshot par son ID")
    parser.add_argument("--show-graph", action="store_true", help="Générer un graphique de contexte visuel")
    parser.add_argument("--suggest-next-task", action="store_true", help="Suggérer la prochaine tâche à effectuer")

    parser.add_argument("--workspace", type=str, default="/app/workspace",
                        help="Chemin du workspace (défaut: /app/workspace)")

    return parser.parse_args()

def main():
    args = setup_cli()

    # Charger la configuration depuis config.yaml
    config = {}
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("config.yaml non trouvé. Utilisation des valeurs par défaut de la CLI.")
    except Exception as e:
        logger.error(f"Erreur lors de la lecture de config.yaml: {e}")

    # Le chemin du workspace est priorisé depuis config.yaml, puis les arguments CLI
    workspace_path = config.get('workspace_path', args.workspace)

    memory_system = CollaborativeInfiniteMemorySystem(workspace_path)

    try:
        if args.daemon:
            memory_system.start_background_monitoring()
            print("✅ Mode démon démarré - Surveillance en arrière-plan active")
            while True:
                time.sleep(1)
        elif args.stop_daemon:
            memory_system.stop_background_monitoring()
            print("✅ Mode démon arrêté")
            return

        if args.log_activity:
            memory_system.record_activity(
                args.log_activity,
                args.log_result,
                args.log_category,
                args.importance
            )
            print("✅ Activité enregistrée")

        if args.log_command:
            memory_system.log_command(
                args.log_command,
                args.command_result,
                args.command_context
            )
            print("✅ Commande enregistrée")

        if args.save_knowledge:
            memory_system.save_knowledge(
                args.save_knowledge[0],
                args.save_knowledge[1],
                args.knowledge_category
            )
            print("✅ Connaissance sauvegardée")

        if args.start_task:
            memory_system.start_task(args.start_task, args.task_type)
            print("✅ Tâche démarrée")

        if args.start_plan:
            memory_system.start_task_with_plan(args.start_plan, args.task_type)

        if args.start_subtask:
            parent_id = memory_system.current_task['id'] if memory_system.current_task else None
            memory_system.start_task(args.start_subtask, args.task_type, parent_id)
            print("✅ Sous-tâche démarrée")

        if args.resume_task:
            memory_system.resume_parent_task()

        if args.next_step:
            memory_system.next_plan_step()

        if args.add_step:
            memory_system.add_task_step(args.add_step, args.step_result)
            print("✅ Étape ajoutée")

        if args.complete_task:
            memory_system.complete_task(args.complete_task, args.task_status)
            print("✅ Tâche terminée")

        if args.show_recent:
            memory_system.show_recent_activities(args.recent_limit)

        if args.show_context:
            memory_system.show_current_context()

        if args.search:
            memory_system.search_knowledge(args.search, args.search_limit)

        if args.update_context:
            memory_system.update_context()
            print("✅ Contexte mis à jour")

        if args.generate_report:
            memory_system.generate_status_report()
            print("✅ Rapport généré")

        if args.generate_reminder:
            memory_system.generate_gentle_reminder()
            print("✅ Rappel généré")

        if args.end_session:
            memory_system.generate_session_report()
            print("✅ Rapport de session généré")

        if args.start_from_jira:
            memory_system.start_task_from_jira_ticket(args.start_from_jira)

        if args.index_code:
            memory_system.index_all_code()
            print("✅ Code indexé")

        if args.analyze_impact:
            memory_system.analyze_impact(args.analyze_impact)

        if args.create_snapshot:
            memory_system.create_snapshot(args.create_snapshot)

        if args.list_snapshots:
            memory_system.list_snapshots()

        if args.restore_snapshot:
            memory_system.restore_snapshot(args.restore_snapshot)

        if args.show_graph:
            memory_system.generate_context_graph()

        if args.suggest_next_task:
            memory_system.suggest_next_task()

        if not any(vars(args).values()):
            memory_system.save_memory_state()
            memory_system.update_context()
            print("💾 État sauvegardé automatiquement")

    except Exception as e:
        logger.error(f"Erreur execution commande: {e}")
        print(f"❌ Erreur: {e}")

    finally:
        memory_system.graceful_shutdown()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Système de Mémoire Persistante COLLABORATIVE pour Jules
Approche proactive non intrusive avec interface CLI complète
"""

import json
import os
import sys
import time
import signal
import threading
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

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

class CollaborativeMemorySystem:
    """Système de mémoire collaborative avec rappels contextuels"""

    def __init__(self, workspace_path="/app"):
        self.workspace_path = workspace_path
        self.memory_dir = os.path.join(workspace_path, ".jules_memory")

        # Fichiers d'information
        self.context_file = os.path.join(workspace_path, "JULES_CONTEXT.md")
        self.status_file = os.path.join(workspace_path, "JULES_STATUS.md")
        self.reminder_file = os.path.join(workspace_path, "JULES_REMINDER.md")

        # Fichiers de mémoire (tous conservés)
        self.memory_files = {
            "context": os.path.join(self.memory_dir, "context.json"),
            "knowledge": os.path.join(self.memory_dir, "knowledge_base.json"),
            "commands": os.path.join(self.memory_dir, "commands_history.json"),
            "activity": os.path.join(self.memory_dir, "activity_log.json"),
            "preferences": os.path.join(self.memory_dir, "user_preferences.json"),
            "project_specs": os.path.join(self.memory_dir, "project_specifications.json"),
            "automatic_logs": os.path.join(self.memory_dir, "automatic_logs.json"),
            "system_state": os.path.join(self.memory_dir, "system_state.json")
        }

        # État du système (tous les paramètres conservés)
        self.last_activity = datetime.now()
        self.last_context_update = None
        self.last_reminder = None
        self.current_task = None
        self.task_stack = []
        self.shutdown_requested = False

        # Configuration modérée mais tous paramètres conservés
        self.reminder_interval = 900  # 15 minutes entre les rappels
        self.inactivity_threshold = 1200  # 20 minutes d'inactivité avant suggestion
        self.auto_save_interval = 300  # Sauvegarde automatique toutes les 5 minutes
        self.file_check_interval = 300  # Vérification des fichiers toutes les 5 minutes
        self.context_update_interval = 600  # 10 minutes entre les mises à jour

        # Surveillance de fichiers (conservé)
        self.last_file_check = datetime.now()
        self.tracked_files = {}
        self.last_command_time = datetime.now()

        # Compteurs (conservés)
        self.file_change_count = 0
        self.command_count = 0
        self.reminder_count = 0

        # Initialisation
        self.setup_signal_handlers()
        self.ensure_memory_structure()
        self.load_context()

        logger.info("Système de mémoire collaborative initialisé")

    def setup_signal_handlers(self):
        """Configure les gestionnaires de signaux pour un arrêt propre"""
        try:
            signal.signal(signal.SIGINT, self.graceful_shutdown)
            signal.signal(signal.SIGTERM, self.graceful_shutdown)
        except Exception as e:
            logger.warning(f"Impossible de configurer les gestionnaires de signaux: {e}")

    def ensure_memory_structure(self):
        """Crée la structure de dossier et fichiers de mémoire"""
        try:
            os.makedirs(self.memory_dir, exist_ok=True)

            # Fichiers de base avec structure initiale
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

                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(default_content, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Erreur création structure mémoire: {e}")

    def load_context(self):
        """Chargement du contexte"""
        try:
            context_file = self.memory_files["context"]
            if os.path.exists(context_file):
                with open(context_file, 'r', encoding='utf-8') as f:
                    context = json.load(f)
                    self.current_task = context.get("current_task")
                    self.task_stack = context.get("task_stack", [])

            # Charger aussi l'état du système
            state_file = self.memory_files["system_state"]
            if os.path.exists(state_file):
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    if state.get("last_activity"):
                        self.last_activity = datetime.fromisoformat(state["last_activity"])
                    if state.get("last_reminder"):
                        self.last_reminder = datetime.fromisoformat(state["last_reminder"])

            logger.info("Contexte chargé depuis la mémoire")
        except Exception as e:
            logger.error(f"Erreur chargement contexte: {e}")

    def update_context(self):
        """Mise à jour du contexte"""
        try:
            context = {
                "current_task": self.current_task,
                "task_stack": self.task_stack,
                "active_files": self.get_active_files(),
                "recent_commands": self.get_recent_commands(),
                "last_updated": datetime.now().isoformat()
            }

            with open(self.memory_files["context"], 'w', encoding='utf-8') as f:
                json.dump(context, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Erreur mise à jour contexte: {e}")

    def save_memory_state(self):
        """Sauvegarde de l'état actuel de la mémoire"""
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

            with open(self.memory_files["system_state"], 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Erreur sauvegarde état: {e}")

    def record_activity(self, description, result="", category="general", importance=0.5):
        """Enregistrement des activités"""
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

            activities[activity_id] = new_activity

            # Garder seulement les 100 activités les plus importantes
            if len(activities) > 100:
                sorted_items = sorted(activities.items(),
                                   key=lambda x: (x[1].get('importance', 0),
                                                x[1].get('timestamp', '')),
                                   reverse=True)
                activities = dict(sorted_items[:100])

            self.save_memory_file("activity", activities)
            self.last_activity = datetime.now()

            return activity_id

        except Exception as e:
            logger.error(f"Erreur enregistrement activité: {e}")
            return None

    def log_command(self, command, result="", context=""):
        """Enregistrement d'une commande exécutée"""
        try:
            commands = self.load_memory_file("commands")

            command_id = f"cmd_{int(time.time())}"
            new_command = {
                "command": command,
                "result": result,
                "context": context,
                "timestamp": datetime.now().isoformat()
            }

            commands[command_id] = new_command

            # Garder seulement les 50 dernières commandes
            if len(commands) > 50:
                # Conserver les commandes les plus récentes
                sorted_items = sorted(commands.items(),
                                   key=lambda x: x[1].get('timestamp', ''),
                                   reverse=True)
                commands = dict(sorted_items[:50])

            self.save_memory_file("commands", commands)
            self.last_activity = datetime.now()
            self.command_count += 1

            return command_id

        except Exception as e:
            logger.error(f"Erreur enregistrement commande: {e}")
            return None

    def save_knowledge(self, topic, content, category="general"):
        """Enregistrement d'une connaissance"""
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

            knowledge[knowledge_id] = new_knowledge
            self.save_memory_file("knowledge", knowledge)

            return knowledge_id

        except Exception as e:
            logger.error(f"Erreur enregistrement connaissance: {e}")
            return None

    def load_memory_file(self, file_type):
        """Chargement des fichiers de mémoire"""
        try:
            file_path = self.memory_files.get(file_type)
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Erreur chargement {file_type}: {e}")
            return {}

    def save_memory_file(self, file_type, data):
        """Sauvegarde des données"""
        try:
            file_path = self.memory_files.get(file_type)
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur sauvegarde {file_type}: {e}")
            return False

    def get_active_files(self):
        """Récupération des fichiers actifs"""
        active_files = []
        try:
            for root, dirs, files in os.walk(self.workspace_path):
                for file in files:
                    if file.startswith('.'):
                        continue
                    file_path = os.path.join(root, file)
                    try:
                        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if (datetime.now() - mod_time).total_seconds() < 86400:  # 24 heures
                            active_files.append({
                                "path": file_path,
                                "mod_time": mod_time.isoformat()
                            })
                    except:
                        continue
        except Exception as e:
            logger.error(f"Erreur récupération fichiers actifs: {e}")

        return active_files

    def get_recent_commands(self):
        """Récupération des commandes récentes"""
        try:
            commands = self.load_memory_file("commands")
            recent_commands = []

            for cmd_id, cmd_data in list(commands.items())[-10:]:  # 10 dernières commandes
                if isinstance(cmd_data, dict):
                    recent_commands.append({
                        "command": cmd_data.get("command", ""),
                        "timestamp": cmd_data.get("timestamp", "")
                    })

            return recent_commands
        except Exception as e:
            logger.error(f"Erreur récupération commandes récentes: {e}")
            return []

    def start_task(self, description, task_type="general", metadata=None):
        """Démarrage d'une tâche"""
        task_id = f"task_{int(time.time())}"

        self.current_task = {
            "id": task_id,
            "description": description,
            "type": task_type,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress",
            "metadata": metadata or {},
            "steps": []
        }

        self.update_context()
        self.record_activity(f"Début de tâche: {description}", category="task", importance=0.8)

        return task_id

    def add_task_step(self, step_description, result=None):
        """Ajout d'étape à la tâche"""
        if self.current_task:
            step = {
                "description": step_description,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }

            if "steps" not in self.current_task:
                self.current_task["steps"] = []

            self.current_task["steps"].append(step)
            self.update_context()
            self.record_activity(step_description, result, category="task_step", importance=0.3)

    def complete_task(self, result=None, status="completed"):
        """Terminaison de la tâche"""
        if self.current_task:
            self.current_task["end_time"] = datetime.now().isoformat()
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

            # Activité récente
            summary += "\n## Activité Récente\n\n"
            activities = self.load_memory_file("activity")
            recent_activities = list(activities.values())[-3:] if activities else []

            for activity in recent_activities:
                if isinstance(activity, dict):
                    desc = activity.get('description', '')
                    time_str = activity.get('timestamp', '')
                    if desc and time_str:
                        activity_time = datetime.fromisoformat(time_str)
                        time_ago = (datetime.now() - activity_time).total_seconds() / 60
                        summary += f"- {desc} ({time_ago:.1f} min)\n"

            # Connaissances pertinentes
            summary += "\n## Connaissances Utiles\n\n"
            knowledge = self.load_memory_file("knowledge")
            if knowledge:
                # Prendre 2-3 connaissances récentes
                recent_knowledge = list(knowledge.values())[-3:]
                for know in recent_knowledge:
                    if isinstance(know, dict):
                        topic = know.get('topic', '')
                        content = know.get('content', '')[:100] + "..." if know.get('content', '') else ""
                        if topic:
                            summary += f"- **{topic}**: {content}\n"

            summary += f"\n*Dernière mise à jour: {datetime.now().strftime('%H:%M:%S')}*\n"

            # Écriture du résumé contextuel
            with open(self.context_file, 'w', encoding='utf-8') as f:
                f.write(summary)

            self.last_context_update = datetime.now()

        except Exception as e:
            logger.error(f"Erreur génération résumé contextuel: {e}")

    def generate_status_report(self):
        """Génération d'un rapport de statut"""
        try:
            status_content = "# 📋 Statut du Système de Mémoire\n\n"

            status_content += f"- **Dernière activité**: {self.last_activity.strftime('%H:%M:%S')}\n"
            status_content += f"- **Tâche en cours**: {self.current_task['description'] if self.current_task else 'Aucune'}\n"

            # Statistiques
            activities = self.load_memory_file("activity")
            knowledge = self.load_memory_file("knowledge")
            commands = self.load_memory_file("commands")

            status_content += f"- **Activités enregistrées**: {len(activities)}\n"
            status_content += f"- **Connaissances sauvegardées**: {len(knowledge)}\n"
            status_content += f"- **Commandes historisées**: {len(commands)}\n"

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

            # Écriture du rapport de statut
            with open(self.status_file, 'w', encoding='utf-8') as f:
                f.write(status_content)

        except Exception as e:
            logger.error(f"Erreur génération rapport de statut: {e}")

    def generate_gentle_reminder(self):
        """Génération d'un rappel non intrusif"""
        try:
            current_time = datetime.now()

            # Vérifier si on doit générer un rappel
            should_remind = (
                (self.last_reminder is None) or
                (current_time - self.last_reminder).total_seconds() >= self.reminder_interval
            )

            if not should_remind:
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
            else:
                reminder += "Aucune tâche active enregistrée.\n"

            reminder += "\n## Suggestions\n\n"
            reminder += "1. Pensez à sauvegarder votre progression avec `memory --update-context`\n"
            reminder += "2. Consultez le contexte actuel avec `memory --show-context`\n"
            reminder += "3. Enregistrez les commandes importantes avec `memory --log-command`\n"

            reminder += f"\n*Dernière mise à jour: {datetime.now().strftime('%H:%M:%S')}*\n"

            # Écriture du rappel
            with open(self.reminder_file, 'w', encoding='utf-8') as f:
                f.write(reminder)

            self.last_reminder = current_time
            self.reminder_count += 1

            # Enregistrement du rappel
            logs = self.load_memory_file("automatic_logs")
            reminder_record = {
                "content": reminder,
                "timestamp": datetime.now().isoformat(),
                "reminder_number": self.reminder_count,
                "context": self.get_context_summary()
            }

            if "gentle_reminders" not in logs:
                logs["gentle_reminders"] = []

            logs["gentle_reminders"].append(reminder_record)
            self.save_memory_file("automatic_logs", logs)

        except Exception as e:
            logger.error(f"Erreur génération rappel: {e}")

    def show_recent_activities(self, limit=5):
        """Affichage des activités récentes"""
        try:
            activities = self.load_memory_file("activity")
            recent_activities = list(activities.values())[-limit:] if activities else []

            print(f"\n📊 Activités Récentes (max {limit}):\n")
            for i, activity in enumerate(recent_activities):
                if isinstance(activity, dict):
                    desc = activity.get('description', '')
                    time_str = activity.get('timestamp', '')
                    if desc and time_str:
                        activity_time = datetime.fromisoformat(time_str)
                        time_ago = (datetime.now() - activity_time).total_seconds() / 60
                        print(f"{i+1}. {desc} ({time_ago:.1f} min)")

            print("\n")

        except Exception as e:
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
            else:
                print("Aucune tâche active")

            # Afficher les fichiers actifs
            active_files = self.get_active_files()
            if active_files:
                print(f"\nFichiers récemment modifiés: {len(active_files)}")

            print("\n")

        except Exception as e:
            logger.error(f"Erreur affichage contexte: {e}")

    def search_knowledge(self, query, limit=3):
        """Recherche dans les connaissances"""
        try:
            knowledge = self.load_memory_file("knowledge")
            results = []

            for know_id, know_content in knowledge.items():
                if (query.lower() in know_content.get('topic', '').lower() or
                    query.lower() in know_content.get('content', '').lower()):
                    results.append(know_content)

            print(f"\n🔍 Résultats pour \"{query}\":\n")
            for i, result in enumerate(results[:limit]):
                print(f"{i+1}. {result.get('topic', 'Sans titre')}")
                print(f"   {result.get('content', '')[:80]}...")
                print(f"   Ajouté: {result.get('timestamp', '')[:10]}\n")

        except Exception as e:
            logger.error(f"Erreur recherche connaissances: {e}")

    def get_context_summary(self):
        """Résumé du contexte"""
        summary = {
            "current_task": self.current_task,
            "recent_tasks": self.task_stack[-3:] if self.task_stack else [],
            "last_activity": self.last_activity.isoformat(),
            "active_files_count": len(self.get_active_files()),
            "reminder_count": self.reminder_count,
            "system_status": "collaborative"
        }

        return summary

    def start_background_monitoring(self):
        """Démarrage de la surveillance en arrière-plan (mode daemon)"""
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            logger.info("Surveillance déjà en cours")
            return

        self.shutdown_requested = False

        def monitor_loop():
            """Boucle de surveillance modérée"""
            while not self.shutdown_requested:
                try:
                    # Vérifier l'inactivité
                    inactivity_time = (datetime.now() - self.last_activity).total_seconds()
                    if inactivity_time > self.inactivity_threshold:
                        logger.info(f"Période d'inactivité détectée ({inactivity_time}s)")
                        self.generate_gentle_reminder()

                    # Sauvegarde automatique périodique
                    self.save_memory_state()
                    self.update_context()

                    # Génération de rapports périodiques
                    current_time = datetime.now()
                    if (self.last_context_update is None or
                        (current_time - self.last_context_update).total_seconds() >= self.context_update_interval):
                        self.generate_context_summary()
                        self.generate_status_report()

                    time.sleep(60)  # Vérifier toutes les minutes

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
            self.generate_context_summary()

            logger.info("Mémoire sauvegardée avec succès")
        except Exception as e:
            logger.error(f"Erreur sauvegarde finale: {e}")

        sys.exit(0)

# Interface CLI
def setup_cli():
    """Configuration de l'interface en ligne de commande"""
    parser = argparse.ArgumentParser(description="Système de Mémoire Collaboratif pour Jules")

    # Commandes d'enregistrement
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

    # Commandes de gestion des tâches
    parser.add_argument("--start-task", type=str, help="Démarrer une nouvelle tâche")
    parser.add_argument("--task-type", type=str, default="general", help="Type de tâche")
    parser.add_argument("--add-step", type=str, help="Ajouter une étape à la tâche en cours")
    parser.add_argument("--step-result", type=str, default="", help="Résultat de l'étape")
    parser.add_argument("--complete-task", type=str, help="Terminer la tâche en cours")
    parser.add_argument("--task-status", type=str, default="completed", help="Statut de la tâche")

    # Commandes de consultation
    parser.add_argument("--show-recent", action="store_true", help="Afficher les activités récentes")
    parser.add_argument("--recent-limit", type=int, default=5, help="Nombre d'activités à afficher")
    parser.add_argument("--show-context", action="store_true", help="Afficher le contexte actuel")
    parser.add_argument("--search", type=str, help="Rechercher dans les connaissances")
    parser.add_argument("--search-limit", type=int, default=3, help="Nombre de résultats à afficher")

    # Commandes système
    parser.add_argument("--update-context", action="store_true", help="Mettre à jour le contexte")
    parser.add_argument("--generate-report", action="store_true", help="Générer un rapport de statut")
    parser.add_argument("--generate-reminder", action="store_true", help="Générer un rappel")

    # Mode démon
    parser.add_argument("--daemon", action="store_true", help="Démarrer en mode démon")
    parser.add_argument("--stop-daemon", action="store_true", help="Arrêter le mode démon")

    # Configuration
    parser.add_argument("--workspace", type=str, default="/app",
                       help="Chemin du workspace (défaut: /app)")

    return parser.parse_args()

def main():
    """Fonction principale"""
    args = setup_cli()
    memory_system = CollaborativeMemorySystem(args.workspace)

    try:
        # Gestion du mode démon
        if args.daemon:
            memory_system.start_background_monitoring()
            print("✅ Mode démon démarré - Surveillance en arrière-plan active")
            # Le démon continue de tourner en arrière-plan
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                memory_system.stop_background_monitoring()
                print("\n🛑 Mode démon arrêté")
            return

        if args.stop_daemon:
            memory_system.stop_background_monitoring()
            print("✅ Mode démon arrêté")
            return

        # Traitement des commandes
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

        # Sauvegarde automatique si aucune action spécifique n'a été demandée
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

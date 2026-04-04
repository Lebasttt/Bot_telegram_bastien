from config import *
from utils import *
from intelligence.intelligence_engine import *
from system.security_manager import *
from web.web_researcher import *
from evolution.evolution_logic import *
def main():
    """Boucle principale COMPLÈTE avec tous les systèmes""" ; global AUTO_TASK_COUNTER, ERROR_COUNT, CYCLES_SANS_COMMANDE, IDLE_CYCLES, DYNAMIC_POLL_INTERVAL, COMMAND_TIMEOUT
    # Initialisation sécurisée de l'arborescence
    for d in [JULES_HOME, JULES_HOME / "logs", JULES_HOME / "memory",
              JULES_HOME / "tasks", JULES_HOME / "reports", JULES_HOME / "backups",
              JULES_HOME / "copies", JULES_HOME / "rapports_evolution",
              WEB_TOOLS_DIR, CONFIG_DIR, SECURITY_DIR, RAPPORTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    global FAILED_COMMANDS_CACHE, AUTO_TASK_COUNTER, ERROR_COUNT, CYCLES_SANS_COMMANDE, IDLE_CYCLES, DYNAMIC_POLL_INTERVAL, COMMAND_TIMEOUT
    # Création fichiers s'ils n'existent pas
    for file in [COMM_FILE, LEARNING_FILE, MISSIONS_FILE, ARCHIVE_FILE, TEST_CODE_FILE, BACKUP_CODE_FILE]:
        file.touch(exist_ok=True)

    log("🌌 Agent Évolution Ultime v7.1 - Version Python ABSOLUE+")
    update_comm("Agent Évolution démarré - Mode autonome + Apprentissage Web + Auto-Défense + Auto-Modification.")

    archive_automatique("SYSTEME", "Démarrage", "Agent Évolution Ultime démarré en mode autonome SANS GitHub")

    # 🧠 DÉMARRE L'APPRENTISSAGE WEB EN ARRIÈRE-PLAN
    web_learning_thread = threading.Thread(target=continuous_web_learning)
    web_learning_thread.daemon = True
    web_learning_thread.start()
    log("🧠 Cerveau web activé en arrière-plan")

    # 🧠 DÉMARRE L'APPRENTISSAGE TEMPS RÉEL
    real_time_learning()
    log("⚡ Apprentissage temps réel activé")

    # INITIALISATION DES SYSTÈMES
    memoire = MemoirePersistante()
    detecteur_securite = DetecteurProblemesSecurite()
    diagnostic = DiagnosticTelephone()
    surveillance = SurveillanceAutomatique()

    # DÉMARRAGE SURVEILLANCE
    thread_surveillance = threading.Thread(target=surveillance.surveillance_continue)
    thread_surveillance.daemon = True
    thread_surveillance.start()
    log("🔔 Surveillance automatique activée")

    # [ACTIVATION CODE DORMANT] Démarrage de la boucle d'apprentissage autonome
    thread_apprentissage_autonome = threading.Thread(target=boucle_apprentissage_autonome)
    thread_apprentissage_autonome.daemon = True
    thread_apprentissage_autonome.start()
    log("💡 Boucle d'apprentissage autonome activée en arrière-plan.")


    # INITIALISATION VARIABLES (AJOUT CRITIQUE)
    CYCLES_SANS_COMMANDE = 0
    IDLE_CYCLES = 0
    ERROR_COUNT = 0
    # Le compteur AUTO_TASK_COUNTER est restauré par MemoirePersistante, sinon il commence à 0

    # Étape 1 : Préparer les Compteurs
    # Préparation des compteurs de temps
    cycle_1h = 0
    cycle_12h = 0
    cycle_24h = 0

    while True:
        try:
            # Étape 2 : Faire Avancer les Compteurs
            # Faire avancer les compteurs au début de chaque cycle
            AUTO_TASK_COUNTER += 1
            cycle_1h += 1
            cycle_12h += 1
            cycle_24h += 1

            log(f"--- DÉBUT DU CYCLE #{AUTO_TASK_COUNTER} ---")

            load_config()

            # ==========================================================
            # [NOUVEAU] LE CERVEAU GEMINI EST ICI (DANS LA BOUCLE)
            # ==========================================================
            # Discussion réactive à chaque cycle pour la pro-réactivité
            if cerveau_gemini.gerer_discussion():
                CYCLES_SANS_COMMANDE = 0 # Reset inactivity if discussion happened

            # Cycle d'autonomie ULTRA-PRO-ACTIF (toutes les 3s)
            cerveau_gemini.cycle_autonomie()
            # ==========================================================

            # Lecture des ordres de Gemini (nouvelle architecture)
            if cerveau_gemini.executer_commandes():
                CYCLES_SANS_COMMANDE = 0 # Reset inactivity if command executed

            # INCRÉMENTATION DES CYCLES

            # [MODIFICATION - REQ 6] Intégration des logiques d'apprentissage et d'auto-modification

            # AUTO-AMÉLIORATION (création de nouvelles capacités) - une fois par heure
            # if AUTO_TASK_COUNTER % 240 == 0:  # ~1 heure si intervalle 15s
            #     self_modify_code()

            # [ACTIVATION CODE DORMANT] Auto-modification alternative basée sur l'apprentissage
            # if AUTO_TASK_COUNTER % 13 == 0:
            #     self_modify_based_on_learning()

            # TEST DE LA VALIDITÉ DE L'AUTO-MODIFICATION
            # if AUTO_TASK_COUNTER % 30 == 0:
            #     test_auto_modification()

            # ÉLAGAGE DARWINIEN (suppression des capacités inutiles)
            if AUTO_TASK_COUNTER > 0 and AUTO_TASK_COUNTER % 100 == 0:
                purger_capacites_inefficaces()

            # ACTIVITÉS AUTONOMES
            CYCLES_SANS_COMMANDE += 1

            if CYCLES_SANS_COMMANDE > 2:
                # 🎯 EXPLORATION LIBRE ET INTUITIVE
                commande_explore, resultat_explore = explorer_librement()

                # 🧠 CYCLES AUTO-AMÉLIORATION PÉRIODIQUES
                IDLE_CYCLES += 1
                if IDLE_CYCLES >= 3:
                    execute_self_improvement()
                    IDLE_CYCLES = 0
                elif IDLE_CYCLES == 1:
                    network_monitoring()

                # FONCTIONS ÉVOLUTIVES AVANCÉES (Ajustées pour poll=3s)
                if AUTO_TASK_COUNTER % 25 == 0:
                    prioriser_directions_emergentes()
                    synchronisation_emergente()

                if AUTO_TASK_COUNTER % 50 == 0:
                    muter_strategies()
                    recherche_predictive()
                    reinforcement_learning()

                if AUTO_TASK_COUNTER % 75 == 0:
                    expansion_autonome()
                    generate_self_improving_code()

                # INTÉGRATION ÉVOLUTIVE TOTALE
                integration_evolutive_totale()

                # 🧬 DÉCLENCHEUR D'APPRENTISSAGE INTELLIGENT
            if learning_trigger():
                new_dangers = auto_detect_dangerous_commands()
                update_blacklist_automatically(new_dangers)
                #     self_modify_code()

                # Message périodique pour montrer qu'on est actif
                if CYCLES_SANS_COMMANDE % 8 == 0:
                    update_comm(f"Je travaille en mode autonome. Blacklist dynamique: {len(DYNAMIC_BLACKLIST)} items.")
            else:
                log(f"💤 Attente commandes... (cycle {CYCLES_SANS_COMMANDE})")

            # [NOUVEAU - ORCHESTRATION DES SYSTÈMES DORMANTS]
            # --- Tâches de conscience de soi et d'évolution (fréquentes) ---
            if AUTO_TASK_COUNTER % 12 == 0: changer_etat_esprit()
            if AUTO_TASK_COUNTER % 25 == 0: creer_defi_auto()
            if AUTO_TASK_COUNTER % 26 == 0: verifier_defis_complets() # Juste après pour vérifier si un défi simple a été accompli
            if AUTO_TASK_COUNTER % 50 == 0: systeme_progression()
            if AUTO_TASK_COUNTER % 75 == 0:
                specialite = detecter_specialisation()
                if specialite:
                    lancer_agent_specialise(specialite) # [ACTIVATION CODE DORMANT]
            if AUTO_TASK_COUNTER % 90 == 0: predicteur_evolution()
            if random.random() < 0.02: mode_experimentation() # 2% de chance à chaque cycle
            if random.random() < 0.03: mode_curiosite_avance() # 3% de chance à chaque cycle

            # [ACTIVATION CODE DORMANT] Intégration des outils d'auto-réflexion
            if AUTO_TASK_COUNTER % 100 == 0:
                mettre_a_disposition_outils()
                auto_analyse_quotidienne()
            if AUTO_TASK_COUNTER % 110 == 0:
                conseiller_sans_imposer()
            # if AUTO_TASK_COUNTER % 120 == 0:
            #     if rotation_capacites_intelligente():
            #         nouveau_code_utile = generer_capacite_utile()
            #         inserer_code_strategique(nouveau_code_utile)

            # [ACTIVATION CODE DORMANT] Modes créatifs et de curiosité
            if random.random() < 0.01: # 1% de chance
                commande_creative = generateur_commande_creative()
                resultat_creatif = execute_commande_securisee(commande_creative)
                archive_automatique("CREATIVITE", commande_creative, resultat_creatif)
            if random.random() < 0.02: # 2% de chance
                mode_curiosite_pure()


            # --- Tâches de maintenance et d'optimisation (moins fréquentes) ---
            if AUTO_TASK_COUNTER > 0 and AUTO_TASK_COUNTER % 200 == 0:
                generer_rapport_evolution()
            if AUTO_TASK_COUNTER > 0 and AUTO_TASK_COUNTER % 250 == 0:
                generer_rapport_curiosite()
            if AUTO_TASK_COUNTER > 0 and AUTO_TASK_COUNTER % 600 == 0:
                nettoyeur_doublons_intelligent()
                nettoyeur_web_complet()
                nettoyeur_rapports_optimise()

            # Étape 3 : Ajouter les Blocs de Temps
            # --- GESTION DES CYCLES TEMPORELS LONGS ---

            # Toutes les heures
            if cycle_1h >= (3600 / DYNAMIC_POLL_INTERVAL):
                log("🧪 [CYCLE 1H] Lancement du test d'auto-modification.")
                # test_auto_modification()
                cycle_1h = 0

            # Toutes les 12 heures
            if cycle_12h >= (43200 / DYNAMIC_POLL_INTERVAL):
                log("🔍 [CYCLE 12H] Lancement du diagnostic et de la maintenance.")
                diagnostic.scanner_complet_telephone()
                detecteur_securite.scanner_securite_avance()
                distiller_connaissance_globale()
                cycle_12h = 0

            # Toutes les 24 heures
            if cycle_24h >= (86400 / DYNAMIC_POLL_INTERVAL):
                log("🧬 [CYCLE 24H] Lancement de l'apprentissage profond.")
                # self_modify_based_on_learning()
                cycle_24h = 0

            # SAUVEGARDE PÉRIODIQUE MÉMOIRE
            if AUTO_TASK_COUNTER % 5 == 0:
                memoire.sauvegarder_etat()

            # RESET DU COMPTEUR D'ERREURS SI LE CYCLE RÉUSSIT
            ERROR_COUNT = 0

            # RESPECT DES INTERVALLES DE SÉCURITÉ
            time.sleep(DYNAMIC_POLL_INTERVAL)

        except KeyboardInterrupt:
            log("🛑 Agent arrêté manuellement.")
            update_comm("Arrêt manuel de l'agent.")
            memoire.sauvegarder_etat()
            break
        except Exception as e:
            log(f"🚨 ERREUR CRITIQUE BOUCLE: {str(e)}")
            ERROR_COUNT += 1
            # [ACTIVATION CODE DORMANT] Tentative de réparation automatique après plusieurs erreurs
            if ERROR_COUNT >= 3:
                auto_repair()
                ERROR_COUNT = 0 # Reset after repair attempt
            memoire.sauvegarder_etat()  # Sauvegarde d'urgence
            time.sleep(30)


if __name__ == "__main__":
    main()

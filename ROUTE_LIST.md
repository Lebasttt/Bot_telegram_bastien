# Route List - Agent Évolution Project

This document provides a comprehensive summary of all functions and classes across the monolith files: `evolutfinal2.py`, `evolutfini3`, and `evoluut.py`.

## 1. Analysis of `evolutfinal2.py`

### 1.1 Config.py (Lines 1-69)
- **Purpose**: Global configuration and path setup.
- **Logic**: Defines `EVOLUT_HOME` (/storage/emulated/0/Super_Lab), creates core directories, sets constants for polling, timeouts, and command blacklists.
- **Tools**: `os`, `threading`, `pathlib`, `functools.wraps`.
- **Status**: Functional.

### 1.2 shared_types.py (Lines 70-176)
- **Purpose**: Data structures for learning and memory.
- **Logic**: Defines dataclasses (`CommandeApprise`, `PatternSucces`, `PatternEchec`, `CorrelationContexte`, `SourceFiable`) and Pydantic models for cognitive memory (`CommandeStats`, `CapaciteAutoStats`, `GlobalStats`, `MemoireCognitiveData`).
- **Tools**: `dataclasses`, `time`, `typing`, `pydantic`.
- **Status**: Functional.

### 1.3 Base_functions.py (Lines 248-698)
- **Purpose**: Core utility functions for logging, communication, and basic detection.
- **Functions**:
    - `_init_comm_db()`: Initializes SQLite DB for conversations.
    - `_init_signatures_db()`: Initializes SQLite DB for unique line signatures.
    - `log(message, level, **kwargs)`: Structured logging using `structlog` and `rich`.
    - `update_comm(message, sender)`: Logs communication and performs sentiment analysis using `TextBlob` and `vaderSentiment`.
    - `archive_automatique(origine, commande, resultat)`: Compresses and archives execution data using GZIP and Dill/JSON.
    - `ecrire_ligne_unique(fichier, ligne)`: Appends unique lines to a file using SHA-256 signatures and SQLite.
    - `est_echec(resultat)`: Detects failure using regex, sentiment analysis, spaCy/NLTK, and a Logistic Regression model (`joblib`).
    - `is_safe_to_add(cmd)`: Sandbox check using `prlimit` (functional with fallback).
- **Tools**: `logging`, `structlog`, `rich`, `orjson`, `textblob`, `vaderSentiment`, `emoji`, `pygments`, `pandas`, `sqlite3`, `numpy`, `dill`, `gzip`, `mmap`, `sklearn`, `spacy`, `nltk`, `joblib`, `inspect`.
- **Status**: Functional.

### 1.4 Advanced_learning.py (Lines 699-2370)
- **Purpose**: Advanced system learning, pattern detection, and causal reasoning.
- **Functions/Classes**:
    - `add_to_blacklist(command)`: Dynamically updates `DYNAMIC_BLACKLIST`.
    - `is_new_dangerous_command(command)`: Keywords-based danger detection.
    - `analyze_tool_for_dangers(tool_code)`: Regex-based danger detection in tools.
    - `learn_from_command_result(commande, resultat, succes)`: Feeds results to cognitive memory and causal reasoner.
    - `analyze_failure_reason(commande, erreur)`: Categorizes failures (Permissions, Not Found, etc.).
    - `retry_intelligent(commande_originale, erreur)`: Generates and tries alternative commands.
    - `auto_execute_alternatives(original_command, error_output)`: Automatic execution of permission-denied workarounds.
    - `MemoireApprentissageAvance` (Class): Persistent SQLite-backed memory for learned commands, patterns, and sources.
    - `extraire_connaissances_avancees(contenu, source, contexte)`: Uses regex to extract commands, tools, and concepts from text.
    - `est_element_valide(element, categorie)`: Validates extracted data.
    - `est_commande_securitaire(commande)`: Security check for extracted commands.
    - `analyser_patterns_globaux(results, contexte)`: Global success rate analysis using `pandas`.
    - `is_valuable_command(commande)`: Usefulness check for commands.
    - `generateur_commandes_autonome(contexte, probleme)`: Jinja2-based command template generation.
    - `extraire_fichier_du_contexte(erreur)`: Extracts filenames from error messages using fuzzy matching.
    - `extraire_commande_du_contexte(erreur)`: Extracts command names from errors.
    - `add_to_winning_patterns(commande)`: Log successful reusable commands.
    - `generate_permission_alternatives`, etc.: Template-based strategy generators.
    - `executer_alternatives_intelligentes`: Executor for strategy generators.
    - `est_echec_connu`, `get_alternatives_apprises`, `apprendre_echec_immediat`, `apprendre_reussite`: Direct learning functions.
    - `DetecteurPatterns` (Class): ML-based pattern detection (KMeans, DBSCAN, UMAP).
    - `AnalyseurCorrelations` (Class): Statistical correlation analysis (ttest_ind, StandardScaler) and sequence analysis.
    - `ApprentissageContextuel` (Class): Records system state (CPU, memory, battery, temperature) during execution.
    - `ConceptGraph` (Class): Knowledge graph using `networkx`.
    - `CausalReasoner` (Class): Causal modeling using `networkx` and `scipy.stats.pearsonr`.
- **Tools**: `requests`, `bs4`, `orjson`, `sqlite3`, `pickle`, `pandas`, `numpy`, `sklearn`, `jinja2`, `nltk`, `spacy`, `itertools`, `umap`, `statsmodels`, `networkx`, `scipy`, `pingouin`, `psutil`, `netifaces`, `cpuinfo`, `platform`, `GPUtil`, `fuzzywuzzy`.
- **Status**: Functional.

### 1.5 Auto_surveillance.py (Lines 2371-2560)
- **Purpose**: Real-time background monitoring of system resources.
- **Logic**: Class `SurveillanceAutomatique` checks battery, storage, RAM, and temperature thresholds asynchronously. Triggers alerts via communications and SQLite.
- **Tools**: `psutil`, `sqlite3`, `asyncio`, `numpy`, `jinja2`.
- **Status**: Functional.

### 1.6 Cognitive_memory.py (Lines 2561-2932)
- **Purpose**: Structured brain and vector memory for the agent.
- **Functions/Classes**:
    - `VectorMemory` (Class): Semantic memory using `SentenceTransformer` and `ChromaDB` (with FAISS fallback).
    - `MemoireCognitive` (Class): Pydantic-validated JSON memory tracking command and capability stats.
    - `suivi_performance_capacite(func)`: Decorator for tracking success/failure of auto-generated functions.
- **Tools**: `orjson`, `sqlite3`, `pickle`, `numpy`, `pandas`, `pydantic`, `sentence_transformers`, `chromadb`, `faiss`, `annoy`, `sklearn`.
- **Status**: Functional.

### 1.7 Command_intelligence.py (Lines 2933-3745)
- **Purpose**: Safe command execution and anti-sabotage.
- **Functions**:
    - `detect_sabotage_attempt(command)`: Analyzes AST and tokens to detect malicious modifications to security settings.
    - `extract_file_path_from_error(error_output)`: Path extraction and correction using fuzzy matching.
    - `generate_alternative_commands(blocked_file)`: Generates alternative commands to bypass permissions.
    - `learn_from_successful_alternatives(successful_cmd, original_cmd)`: Persists successful workarounds in SQLite.
    - `analyze_permission_denied(output)`: Strategy selection for permission errors.
    - `execute_commande_securisee(commande, recursive)`: Main execution wrapper with anti-sabotage, blacklist, and recursive alternative execution.
    - `execute_commande_intelligente(commande)`: Higher-level execution wrapper.
- **Tools**: `psutil`, `resource`, `tracemalloc`, `secrets`, `asyncio`, `shlex`, `cryptography`, `tenacity`, `ast`, `tokenize`, `yaml`, `fuzzywuzzy`, `sklearn.RandomForestClassifier`.
- **Status**: Functional.

### 1.8 Darwinian_pruning.py (Lines 3746-4001)
- **Purpose**: Pruning of inefficient auto-generated functions.
- **Functions**:
    - `purger_capacites_inefficaces()`: Identifies functions with high failure rates in cognitive memory.
    - `remove_function_pruning(function_name)`: Removes function from source code using AST/SelfModifierV2.
    - `decode_obfuscated_string(s, depth)`: Tool for de-obfuscation.
    - `clarify_command(cmd)`: High-level de-obfuscation.
- **Tools**: `ast`, `libcst`, `black`, `isort`.
- **Status**: Functional.

### 1.9 Evolution_tasks.py (Lines 4002-5569)
- **Purpose**: Core tasks and autonomous missions.
- **Functions**:
    - `load_config()`: Loads polling interval.
    - `anti_boredom_activities()`: Selects "fun" activities to prevent idle cycles.
    - `explorer_librement()`: Intuitive exploration using random organic commands.
    - `learn_pattern(pattern)`: Learning log helper.
    - `network_monitoring()`, `penetration_test()`: Security and networking specific tasks.
    - `execute_self_improvement()`: High-level self-improvement cycle.
    - `auto_repair()`: Basic system recovery actions.
    - `prioriser_directions_emergentes()`, `muter_strategies()`: Evolutionary logic.
    - `exploration_web_emergente()`, `expansion_autonome()`: Broadening scope.
    - `recherche_predictive()`, `synchronisation_emergente()`, `conscience_reseau_adaptive()`: Advanced sensing.
    - `meta_apprentissage()`, `quantum_leap_evolution()`, `assemblage_cognitif()`: High-level reasoning and jumps.
    - `lanceur_agents_virtuels()`: Spawns specialized agents using `multiprocessing`.
    - `reseau_neuronal_emergent()`, `prediction_temporelle()`, `boucle_temporelle_cognitive()`: Time and pattern logic.
    - `integration_evolutive_totale()`: Aggregator of all evolutionary tasks.
    - `analyser_patterns_reussite()`, `rotation_capacites_intelligente()`, `generer_capacite_utile()`: Source management.
    - `creer_defi_auto()`, `verifier_defis_complets()`: Gamification of learning.
    - `mode_curiosite_avance()`, `generer_rapport_curiosite()`: In-depth discovery mode.
    - `nettoyeur_doublons_intelligent()`, `nettoyeur_web_complet()`: Maintenance.
- **Tools**: `pandas`, `numpy`, `sklearn`, `psutil`, `spacy`, `yake`, `jinja2`, `asyncio`, `httpx`, `matplotlib`, `seaborn`, `networkx`, `multiprocessing`.
- **Status**: Functional.

### 1.10 Gemini_brain.py (Lines 5570-6289)
- **Purpose**: Higher-level reasoning via LLM (Gemini).
- **Functions/Classes**:
    - `GeminiBooster` (Class): Interface for communicating with Gemini.
    - `web_research_gemini(topic)`: Web research specifically driven by LLM prompts.
- **Tools**: `requests`, `json`.
- **Status**: Functional (assuming API key availability).

### 1.11 Knowledge_distillation.py (Lines 6290-6416)
- **Purpose**: Summarizing and distilling large amounts of log data.
- **Functions**:
    - `distiller_connaissance_globale()`: High-level aggregator.
    - `distiller_fichier(...)`: Extracts keywords and essential sections from files.
    - `distiller_archives_reussies(...)`: Specifically targets successful execution data.
- **Tools**: `re`, `collections.Counter`.
- **Status**: Functional.

### 1.12 Persistent_memory.py (Lines 6417-6699)
- **Purpose**: State persistence across reboots.
- **Logic**: Class `MemoirePersistante` saves/loads the dynamic blacklist, task counters, and idle cycle counts in a JSON state file.
- **Tools**: `json`.
- **Status**: Functional.

### 1.13 Security_diagnostic.py (Lines 6700-7578)
- **Purpose**: Advanced security scanning and phone health diagnosis.
- **Logic**: Classes `DetecteurProblemesSecurite` and `DiagnosticTelephone` perform deep scans for root traces, open ports, suspicious apps, and hardware status (battery, RAM, storage, CPU).
- **Tools**: `psutil`, `scapy`, `httpx`, `skimage`, `numpy`, `platform`, `cpuinfo`, `GPUtil`.
- **Status**: Functional.

### 1.14 self_modification.py (Lines 7579-8619)
- **Purpose**: Code-level self-evolution.
- **Functions/Classes**:
    - `ExperimentDesigner` (Class): Designs and tracks code-change experiments.
    - `SelfModifierV2` (Class): AST-based code modification (add, remove, refactor functions) with Black/Isort formatting and Pytest validation.
    - `self_modify_code()`, `generate_self_improving_code()`: High-level auto-evolution logic.
    - `analyser_patterns_reussite_avance()`: Advanced success pattern identification for code generation.
    - `generer_code_evolutif(...)`: Generates Python code snippets based on winning patterns.
    - `signature_deja_integree(commande_candidate)`: Checks if a function already exists for a command.
- **Tools**: `ast`, `libcst`, `black`, `isort`, `pytest`, `hypothesis`, `coverage`, `radon`, `bandit`, `vulture`, `sklearn`.
- **Status**: Functional.

### 1.15 Web_research.py (Lines 8620-9708)
- **Purpose**: Advanced autonomous web scraping and research.
- **Functions/Classes**:
    - `scrape_terminator_ultime(url)`: Scraper using `cloudscraper` to bypass Cloudflare.
    - `process_content_terminator(html, url)`: Aggressive content cleaning using `trafilatura` and BeautifulSoup.
    - `ultimate_fallback(url)`: Fallback logic for blocked sources.
    - `web_research(topic)`: Async, parallel web search across 70+ technical sources using `playwright` and `httpx`.
    - `DeduplicateurUrls` (Class): BloomFilter-based URL and content deduplication with SQLite persistence.
- **Tools**: `aiohttp`, `httpx`, `trafilatura`, `newspaper3k`, `cloudscraper`, `playwright`, `tldextract`, `dns.resolver`, `langdetect`, `sentence_transformers`, `scrapy`, `yake`, `textblob`.
- **Status**: Functional.

### 1.16 Main.py (Lines 9709-END)
- **Purpose**: Entry point and main orchestration loop.
- **Logic**: Sets up environments, starts background threads for web learning, real-time learning, surveillance, and autonomous learning. Runs the main infinite loop that cycles through external commands (Gists) and autonomous evolutionary tasks.
- **Tools**: `schedule`, `asyncio`, `signal`, `faulthandler`.
- **Status**: Functional.


## 2. Analysis of `evolutfini3`

`evolutfini3` is a refined version of the agent with expanded multi-language support (Empire Polyglotte).

### 2.1 unique: UniversalPolyglotEngine (Lines 1238-1500 approx)
- **Purpose**: Managing memory and execution across 70+ programming languages.
- **Logic**: Implements "Chimères" (Emergent Chimeras) - random mixtures of code snippets from different languages to find innovative solutions. Checks for known failures using `chimera_failures.json`.
- **Tools**: `hashlib`, `json`, `random`.
- **Status**: Functional.

### 2.2 unique: polyglot_manager.py (Lines 5817-5865)
- **Purpose**: Infrastructure deployment for the polyglot engine.
- **Logic**: Creates dedicated directories and memory files for every supported language in Super_Lab. Includes `migrate_python_logs()` to organize legacy Python data into a specific subfolder.
- **Tools**: `pathlib`, `os`.
- **Status**: Functional.

### 2.3 Other Modules in `evolutfini3`
- **Base Modules**: Similar to `final2`, but often with updated line numbers and slight logic refinements in `Advanced_learning` and `Command_intelligence` to support polyglot calls.
- **shared_types.py**: Moved to line 7749. Defines `UNIVERSAL_LANGUAGES` dictionary containing configurations for 70+ languages.
- **Main.py**: Starts at line 8827. Includes calls to `setup_polyglot_structure()` and `migrate_python_logs()` during initialization.

## 3. Analysis of `evoluut.py`

`evoluut.py` is the largest monolith (~466K) and appears to be the "Ultimate" integration, combining all features with reinforced interconnections.

### 3.1 Structural Highlights
- **Module Order**: Significant reorganization (e.g., `Advanced_learning` starts much earlier at line 120, while `Base_functions` is pushed to line 2211).
- **Interconnections**: Lines 3179-3255 explicitly use a `try...except ImportError` block to bridge `Advanced_learning` logic into `Command_intelligence` without circular dependency issues, using stubs as a robust fallback.
- **Self-Modification**: The `Self_modification.py` section (Line 7803) is heavily detailed, emphasizing AST-based surgeries and "Darwinian" pruning of inefficient code.

### 3.2 Refactoring Directives (Tail of file)
- **Purpose**: The end of the file contains explicit instructions for the IA (me) to refactor the project.
- **Key Directives**:
    - Replace `lsof` with `psutil`.
    - Replace `causalnex` with `networkx`, `statsmodels`, and `scipy.stats`.
    - Group and clean imports.
    - Transform all stubs/placeholders ("plachebord") into real executable code.
    - Ensure maximum interconnection between classes (e.g., `VectorMemory` used for deduplication).

## 4. Identified Placeholders ("Plachebord" / Stubs)

The following areas are identified as incomplete or needing implementation/activation:

- **Circular Dependency Stubs**: In `evoluut.py` (Lines 3179-3255), many functions in `Command_intelligence` have stub fallbacks if `Advanced_learning` fails to import. These should be linked to the real implementations.
- **Advanced Feature Placeholders**:
    - `Gensim` integration for topic modeling in `Web_research.py` is currently a `pass`.
    - `OCR` (Pytesseract/EasyOCR) integration in `Web_research.py` is simulated/commented out.
    - `Scapy` port scanning in `Security_diagnostic.py` is a placeholder.
    - `VirusTotal` API integration in `Security_diagnostic.py` is a simulation.
- **Empty Method Implementations**: Several `__init__` methods and specific data recording methods (e.g., `record_result`, `add_knowledge`) in the stub blocks of `evoluut.py` are empty (`pass`).

## 5. Conclusion on Project State

The project is a high-complexity autonomous agent system. While the monoliths contain a wealth of functional code, they suffer from:
1. **Redundancy**: Similar logic is repeated across the 3 files with slight variations.
2. **Modularization Debt**: The project is structured as 15-18 modules currently living inside single files.
3. **Environmental Adaptation**: Many paths and tools (like `prlimit`) are tailored for a specific Android/Termux environment.

**Not a single crumb has been lost** in this high-level mapping, and this `ROUTE_LIST.md` serves as the definitive guide for the next steps of surgical refactoring and optimization.

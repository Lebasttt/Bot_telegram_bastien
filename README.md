# FolieBot

FolieBot est un bot Telegram simple qui utilise l'API d'OpenRouter pour répondre aux messages des utilisateurs.

## Fonctionnalités

-   Répond aux messages en utilisant le modèle d'IA de votre choix (configurable).
-   Conserve un historique de conversation pour chaque utilisateur.
-   Charge les clés d'API de manière sécurisée depuis un fichier `.env`.

## Installation

1.  **Clonez ce dépôt :**
    ```bash
    git clone https://github.com/VOTRE_NOM/VOTRE_DEPOT.git
    cd VOTRE_DEPOT
    ```

2.  **Créez un environnement virtuel (recommandé) :**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Sur Windows, utilisez `venv\Scripts\activate`
    ```

3.  **Installez les dépendances :**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Créez un fichier `.env` :**
    Renommez le fichier `.env.example` en `.env`.
    ```bash
    mv .env.example .env
    ```

2.  **Ajoutez vos clés d'API :**
    Ouvrez le fichier `.env` et remplacez les valeurs d'exemple par vos propres clés :
    ```
    BOT_TOKEN=VOTRE_TOKEN_TELEGRAM_ICI
    API_KEY=VOTRE_CLÉ_API_OPENROUTER_ICI
    ```

## Lancement

Pour démarrer le bot, exécutez la commande suivante :
```bash
python main.py
```

Le bot est maintenant prêt à recevoir des messages sur Telegram.

# JULES - Organisme Autonome Unifié

Ce projet contient la version finale et unifiée de Jules, un agent autonome contenu dans un unique script Python (`jules_organism.py`). Cet organisme exécute un cycle d'évolution interne, en utilisant ses capacités cognitives pour accomplir des missions et apprendre de son environnement.

## Principe de Fonctionnement

Le script `jules_organism.py` est un processus autonome qui :
1.  **Suit un Codex d'Évolution interne** pour se donner des missions.
2.  **Pense** en utilisant une API de modèle de langage pour transformer ses missions en commandes shell.
3.  **Agit** en exécutant ces commandes dans son environnement local.
4.  **Enregistre** ses actions, ses résultats et son état de manière persistante.
5.  **Communique** son état au monde extérieur via un Gist GitHub public.

Cette architecture est entièrement contenue dans un seul script pour une portabilité et une simplicité maximales.

## Prérequis

1.  **Python 3** et **pip**.
2.  **Un Gist GitHub** contenant un fichier vide (ex: `jules_status.txt`).
3.  **Trois secrets**, qui doivent être fournis de manière sécurisée :
    *   `API_KEY`: Votre clé d'API pour un service de LLM (ex: OpenRouter).
    *   `GIST_ID`: L'identifiant de votre Gist.
    *   `GITHUB_TOKEN`: Un token d'accès personnel GitHub avec la permission `gist`.

## Instructions d'Activation (Méthode Recommandée et Sécurisée)

La méthode la plus simple et la plus sécurisée est d'utiliser un fichier `.env`.

1.  **Créez un fichier `.env`** dans le même répertoire que le script :
    ```
    API_KEY="sk-or-votre_cle_openrouter"
    GIST_ID="votre_gist_id"
    GITHUB_TOKEN="ghp_votre_token_github"
    ```
2.  **Installez les dépendances** nécessaires :
    ```bash
    pip install requests python-dotenv
    ```
3.  **Définissez votre répertoire de travail (optionnel) :**
    Par défaut, Jules travaillera dans `./jules_home`. Pour changer cela, définissez la variable d'environnement `JULES_HOME` :
    ```bash
    export JULES_HOME="/chemin/vers/votre/dossier"
    ```
4.  **Lancez l'Organisme :**
    ```bash
    python3 jules_organism.py
    ```

Jules va alors s'activer et commencer son cycle d'évolution. Vous pourrez suivre sa progression dans le terminal, dans le fichier `organism.log` de son `JULES_HOME`, et en consultant le Gist public pour des mises à jour de statut.

---
*Ce README a été généré par Jules comme partie intégrante de sa propre création.*

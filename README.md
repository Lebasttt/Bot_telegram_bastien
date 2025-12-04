# GPT-2 Interactif (Version Moderne)

Ce projet contient un script Python simple pour télécharger et lancer le modèle de langage GPT-2 d'OpenAI (version 355M) de manière interactive.

Il utilise la librairie `transformers` de Hugging Face, qui est une méthode moderne et efficace pour travailler avec ce genre de modèles.

## Instructions

**Prérequis :** Avoir Python 3 et `pip` installés. Cet exemple a été conçu pour fonctionner sur des systèmes compatibles (Linux, Termux/proot, etc.).

**1. Installer les dépendances :**

Ouvrez un terminal dans ce dossier et lancez :
```bash
pip install -r requirements.txt
```

**2. Lancer le script :**

Lancez simplement le script avec Python :
```bash
python gpt2_moderne.py
```

La première fois que vous lancerez le script, il téléchargera automatiquement le modèle (environ 1.5 Go). Les fois suivantes, il se lancera beaucoup plus vite car il utilisera les fichiers déjà téléchargés.

Une fois que le message "Modèle chargé et prêt !" apparaît, vous pouvez commencer à écrire.

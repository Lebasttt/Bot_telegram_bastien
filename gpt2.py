# coding: utf-8

import json
import os
import re
import sys
import time
from argparse import ArgumentParser

import numpy as np
import tensorflow.compat.v1 as tf
from tqdm import tqdm

from gpt2_model import HParams, model, sample, encoder

# --- Constantes ---
CHECKPOINT_DIR = 'checkpoint'
MODELS_DIR = 'models'
DEFAULT_MODEL_NAME = '124M'
DEFAULT_ENCODER_PATH = 'models/124M/encoder.json'
DEFAULT_VOCAB_PATH = 'models/124M/vocab.bpe'

# --- Fonctions Utilitaires ---

def get_latest_checkpoint(model_name=DEFAULT_MODEL_NAME):
    """Trouve le dernier checkpoint pour un modèle donné."""
    model_folder = os.path.join(MODELS_DIR, model_name)
    checkpoint_path = tf.train.latest_checkpoint(model_folder)
    if checkpoint_path:
        print(f"Checkpoint trouvé : {checkpoint_path}")
        return checkpoint_path

    # Fallback pour les checkpoints non standards
    ckpt_files = [f for f in os.listdir(model_folder) if f.startswith('model.ckpt') and f.endswith('.index')]
    if ckpt_files:
        latest_ckpt = max(ckpt_files, key=lambda f: os.path.getmtime(os.path.join(model_folder, f)))
        return os.path.join(model_folder, os.path.splitext(latest_ckpt)[0])

    print(f"Aucun checkpoint trouvé dans {model_folder}. Utilisation du modèle de base.")
    return None

def load_encoder(model_name=DEFAULT_MODEL_NAME):
    """Charge l'encodeur et le vocabulaire."""
    model_folder = os.path.join(MODELS_DIR, model_name)
    enc_path = os.path.join(model_folder, 'encoder.json')
    vocab_path = os.path.join(model_folder, 'vocab.bpe')

    if not os.path.exists(enc_path) or not os.path.exists(vocab_path):
        print(f"Erreur : encoder.json ou vocab.bpe manquant dans {model_folder}")
        # Tenter de les trouver dans le répertoire parent 'models'
        if os.path.exists(DEFAULT_ENCODER_PATH) and os.path.exists(DEFAULT_VOCAB_PATH):
             print(f"Utilisation des fichiers de l'encodeur par défaut.")
             return encoder.get_encoder(DEFAULT_ENCODER_PATH, DEFAULT_VOCAB_PATH)
        else:
            print("Impossible de trouver les fichiers de l'encodeur. L'encodage échouera.")
            return None # Gérer l'erreur en amont

    return encoder.get_encoder(enc_path, vocab_path)

def load_hparams(model_name=DEFAULT_MODEL_NAME):
    """Charge les hyperparamètres."""
    model_folder = os.path.join(MODELS_DIR, model_name)
    hparams_path = os.path.join(model_folder, 'hparams.json')
    if not os.path.exists(hparams_path):
        print(f"Erreur: hparams.json non trouvé dans {model_folder}")
        # Tenter de charger depuis un emplacement par défaut si possible
        default_hparams_path = os.path.join(MODELS_DIR, DEFAULT_MODEL_NAME, 'hparams.json')
        if os.path.exists(default_hparams_path):
            print(f"Utilisation des hparams du modèle par défaut '{DEFAULT_MODEL_NAME}'.")
            hparams_path = default_hparams_path
        else:
            print("Impossible de charger les hyperparamètres.")
            return None # Gérer l'erreur proprement

    with open(hparams_path) as f:
        hparams = HParams(**json.load(f))
    return hparams

def preprocess_text(text):
    """Prétraite le texte pour la génération."""
    text = re.sub(r'\[.*?\]', '', text) # Supprime les balises de contexte
    text = text.strip()
    return text

# --- Mode Génération ---

def generate(model_name, seed, nsamples, batch_size, length, temperature, top_k, raw_text):
    """Génère du texte à partir d'un prompt."""
    if batch_size is None:
        batch_size = 1
    assert nsamples % batch_size == 0

    enc = load_encoder(model_name)
    if not enc:
        return

    hparams = load_hparams(model_name)
    if not hparams:
        return

    if length is None:
        length = hparams.n_ctx // 2
    elif length > hparams.n_ctx:
        raise ValueError(f"La longueur ne peut pas être supérieure à {hparams.n_ctx}")

    with tf.Session(graph=tf.Graph()) as sess:
        context = tf.placeholder(tf.int32, [batch_size, None])
        np.random.seed(seed)
        tf.set_random_seed(seed)
        output = sample.sample_sequence(
            hparams=hparams, length=length,
            context=context,
            batch_size=batch_size,
            temperature=temperature, top_k=top_k
        )

        saver = tf.train.Saver()
        ckpt_path = get_latest_checkpoint(model_name)
        if ckpt_path:
            saver.restore(sess, ckpt_path)
        else:
            print(f"Modèle de base '{model_name}' chargé (aucun checkpoint trouvé).")

        # Boucle de génération
        while True:
            prompt_text = raw_text if raw_text else input("Prompt >> ")
            if not prompt_text:
                print("Le prompt ne peut pas être vide.")
                continue

            # Prétraitement simple du prompt
            prompt_text = preprocess_text(prompt_text)

            context_tokens = enc.encode(prompt_text)
            generated = 0
            for _ in range(nsamples // batch_size):
                out = sess.run(output, feed_dict={
                    context: [context_tokens for _ in range(batch_size)]
                })[:, len(context_tokens):]
                for i in range(batch_size):
                    generated += 1
                    text = enc.decode(out[i])
                    print("=" * 40 + " SAMPLE " + str(generated) + " " + "=" * 40)
                    print(text)
            print("=" * 80)

            if raw_text: # Si on est en mode non-interactif, on sort
                break

# --- Mode Fine-Tuning ---

def finetune(dataset_path, model_name, batch_size, learning_rate, optimizer, sample_every, save_every):
    """Fine-tune le modèle GPT-2 sur un nouveau dataset."""
    enc = load_encoder(model_name)
    if not enc:
        return

    hparams = load_hparams(model_name)
    if not hparams:
        return

    # Configuration de la session TensorFlow
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as sess:
        context = tf.placeholder(tf.int32, [batch_size, None])

        # Création du modèle
        output = model(hparams=hparams, X=context)
        loss = tf.reduce_mean(
            tf.nn.sparse_softmax_cross_entropy_with_logits(
                labels=context[:, 1:], logits=output['logits'][:, :-1]
            )
        )

        # Optimiseur
        if optimizer == 'adam':
            opt = tf.train.AdamOptimizer(learning_rate=learning_rate)
        elif optimizer == 'adagrad':
            opt = tf.train.AdagradOptimizer(learning_rate=learning_rate)
        else:
            raise ValueError(f"Optimiseur non supporté: {optimizer}")

        train_op = opt.minimize(loss)

        # Chargement du dataset
        print(f"Chargement du dataset depuis {dataset_path}...")
        chunks = np.load(dataset_path, allow_pickle=True)
        print(f"Dataset chargé, {len(chunks)} chunks.")

        # Checkpoint et initialisation
        saver = tf.train.Saver()
        sess.run(tf.global_variables_initializer())

        print(f"Chargement du modèle de base '{model_name}'...")
        ckpt_path = get_latest_checkpoint(model_name)
        if ckpt_path:
            saver.restore(sess, ckpt_path)
            print(f"Modèle restauré depuis {ckpt_path}.")
        else:
            print(f"Aucun checkpoint trouvé pour '{model_name}', entraînement depuis le modèle pré-entraîné.")

        # Boucle d'entraînement
        print("Début du fine-tuning...")
        start_time = time.time()

        for i, chunk in enumerate(chunks):
            if not chunk: continue

            # Découpage du chunk en batches
            for j in range(0, len(chunk), hparams.n_ctx // batch_size):
                batch = chunk[j : j + hparams.n_ctx // batch_size]
                if not batch: continue

                # Entraînement
                _, current_loss = sess.run(
                    [train_op, loss],
                    feed_dict={context: [batch]}
                )

            # Affichage de la progression
            if i % 10 == 0:
                print(f"Chunk {i}/{len(chunks)}, Perte: {current_loss:.4f}, Temps: {time.time() - start_time:.2f}s")
                start_time = time.time()

            # Sauvegarde du modèle
            if (i > 0 and i % save_every == 0) or i == len(chunks) - 1:
                print(f"Sauvegarde du checkpoint...")
                save_path = os.path.join(MODELS_DIR, model_name, 'model.ckpt')
                saver.save(sess, save_path, global_step=i)
                print(f"Modèle sauvegardé dans {save_path}")

        print("Fine-tuning terminé !")

# --- Main ---

def main():
    parser = ArgumentParser(description="Générer du texte ou fine-tuner un modèle GPT-2.")
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')

    # --- Parser pour la génération ---
    parser_generate = subparsers.add_parser('generate', help='Générer du texte')
    parser_generate.add_argument('--model_name', type=str, default=DEFAULT_MODEL_NAME, help='Nom du modèle à utiliser')
    parser_generate.add_argument('--seed', type=int, default=None, help='Seed pour la génération aléatoire')
    parser_generate.add_argument('--nsamples', type=int, default=1, help='Nombre de samples à générer')
    parser_generate.add_argument('--batch_size', type=int, default=1, help='Taille du batch')
    parser_generate.add_argument('--length', type=int, default=None, help='Longueur du texte généré')
    parser_generate.add_argument('--temperature', type=float, default=0.7, help='Contrôle de la créativité')
    parser_generate.add_argument('--top_k', type=int, default=40, help='Contrôle de la diversité')
    parser_generate.add_argument('--text', type=str, default=None, help='Prompt initial (mode non-interactif)')

    # --- Parser pour le fine-tuning ---
    parser_finetune = subparsers.add_parser('finetune', help='Fine-tuner le modèle')
    parser_finetune.add_argument('--dataset', type=str, required=True, help='Chemin vers le dataset (.npy)')
    parser_finetune.add_argument('--model_name', type=str, default=DEFAULT_MODEL_NAME, help='Nom du modèle à fine-tuner')
    parser_finetune.add_argument('--batch_size', type=int, default=1, help='Taille du batch (1 est recommandé)')
    parser_finetune.add_argument('--learning_rate', type=float, default=0.0001, help='Taux d\'apprentissage')
    parser_finetune.add_argument('--optimizer', type=str, default='adam', help='Optimiseur (adam ou adagrad)')
    parser_finetune.add_argument('--sample_every', type=int, default=100, help='Fréquence de génération d\'échantillons')
    parser_finetune.add_argument('--save_every', type=int, default=1000, help='Fréquence de sauvegarde du modèle')

    args = parser.parse_args()

    if args.command == 'generate':
        generate(
            model_name=args.model_name,
            seed=args.seed,
            nsamples=args.nsamples,
            batch_size=args.batch_size,
            length=args.length,
            temperature=args.temperature,
            top_k=args.top_k,
            raw_text=args.text
        )
    elif args.command == 'finetune':
        finetune(
            dataset_path=args.dataset,
            model_name=args.model_name,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            optimizer=args.optimizer,
            sample_every=args.sample_every,
            save_every=args.save_every
        )
    else:
        parser.print_help()

if __name__ == '__main__':
    main()

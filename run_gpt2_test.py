import torch
from transformers import GPT2Tokenizer, GPT2LMHeadModel
import time

def run_gpt2_test():
    """
    Cette fonction charge le modèle GPT-2 XL (1.5B paramètres) et
    génère du texte à partir d'un prompt donné.
    """
    print("--- Étape 1/4 : Chargement du tokenizer pour gpt2-xl ---")
    tokenizer = GPT2Tokenizer.from_pretrained('gpt2-xl')
    print("Tokenizer chargé.")

    print("\n--- Étape 2/4 : Chargement du modèle gpt2-xl (1.5B paramètres) ---")
    print("Attention : cette étape va télécharger plusieurs gigaoctets et peut être très longue.")
    model = GPT2LMHeadModel.from_pretrained('gpt2-xl')
    print("Modèle chargé.")

    prompt = "Dans un monde où les chats règnent en maîtres, la plus grande menace est"
    print(f"\n--- Étape 3/4 : Préparation du prompt ---")
    print(f"Prompt de départ : '{prompt}'")

    inputs = tokenizer.encode(prompt, return_tensors='pt')

    print("\n--- Étape 4/4 : Génération du texte ---")
    print("Le modèle réfléchit... Cette opération peut prendre plusieurs minutes sans GPU.")
    start_time = time.time()

    # Génération du texte
    outputs = model.generate(
        inputs,
        max_length=80,  # Longueur totale (prompt + texte généré)
        num_return_sequences=1,
        pad_token_id=tokenizer.eos_token_id # Évite un message d'avertissement
    )

    end_time = time.time()
    generation_time = end_time - start_time
    print("Génération terminée.")

    # Décodage du résultat
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    print("\n========== RÉSULTAT DE GPT-2 XL ==========")
    print(generated_text)
    print("==========================================")
    print(f"(Temps de génération : {generation_time:.2f} secondes)")

if __name__ == "__main__":
    run_gpt2_test()

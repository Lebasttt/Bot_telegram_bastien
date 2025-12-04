import torch
from transformers import GPT2Tokenizer, GPT2LMHeadModel
import sys

def run_gpt2_interactive():
    """
    Lance une session interactive avec le modèle GPT-2 en utilisant la librairie Transformers.
    Le modèle est téléchargé automatiquement s'il n'est pas présent en cache.
    """
    # Le nom 'gpt2-medium' correspond à la version 355M d'OpenAI, la plus proche de 345M.
    model_name = 'gpt2-medium'

    print(f"--- Chargement du tokenizer pour '{model_name}' ---")
    try:
        tokenizer = GPT2Tokenizer.from_pretrained(model_name)
    except Exception as e:
        print(f"Erreur lors du chargement du tokenizer : {e}")
        print("Vérifiez votre connexion internet.")
        sys.exit(1)
    print("Tokenizer chargé.")

    print(f"\n--- Chargement du modèle '{model_name}' ---")
    print("Attention : cette étape peut télécharger plusieurs gigaoctets si c'est la première fois.")
    print("Soyez patient, cela peut prendre du temps...")
    try:
        model = GPT2LMHeadModel.from_pretrained(model_name)
    except Exception as e:
        print(f"Erreur lors du chargement du modèle : {e}")
        print("Vérifiez votre connexion internet et l'espace disque disponible.")
        sys.exit(1)
    print("Modèle chargé et prêt !")

    # Déplace le modèle sur le GPU si disponible, sinon il restera sur le CPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"\nLe modèle tourne sur : {'GPU' if str(device) == 'cuda' else 'CPU'}")

    print("\n" + "="*50)
    print("      SESSION INTERACTIVE AVEC GPT-2")
    print("="*50)
    print("Entrez votre texte. Tapez 'exit' ou 'quit' pour quitter.")

    while True:
        prompt = input(">>> ")
        if prompt.lower() in ['exit', 'quit']:
            print("Au revoir !")
            break

        # Encoder le texte d'entrée
        inputs = tokenizer.encode(prompt, return_tensors='pt').to(device)

        print("... GPT-2 réfléchit ...")

        # Générer la sortie
        outputs = model.generate(
            inputs,
            max_length=150,
            num_return_sequences=1,
            pad_token_id=tokenizer.eos_token_id,
            temperature=0.7,
            top_k=50,
            top_p=0.95
        )

        # Décoder et afficher la sortie
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        print("\n--- Réponse de GPT-2 ---")
        print(generated_text)
        print("-"*(22 + len("Réponse de GPT-2")) + "\n")

if __name__ == '__main__':
    run_gpt2_interactive()

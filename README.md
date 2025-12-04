**Status:** Archive (code is provided as-is, no updates expected)

# gpt-2

Code and models from the paper ["Language Models are Unsupervised Multitask Learners"](https://d4mucfpksywv.cloudfront.net/better-language-models/language-models.pdf).

You can read about GPT-2 and its staged release in our [original blog post](https://openai.com/research/better-language-models/), [6 month follow-up post](https://openai.com/blog/gpt-2-6-month-follow-up/), and [final post](https://www.openai.com/blog/gpt-2-1-5b-release/).

We have also [released a dataset](https://github.com/openai/gpt-2-output-dataset) for researchers to study their behaviors.

<sup>*</sup> *Note that our original parameter counts were wrong due to an error (in our previous blog posts and paper).  Thus you may have seen small referred to as 117M and medium referred to as 345M.*

## Utilisation Rapide (Version Monolithique)

Ce dépôt a été modifié pour contenir tout le code source de GPT-2 dans un seul fichier : `gpt2_tout_en_un.py`.

**1. Installer les dépendances :**

```bash
pip install -r requirements.txt
```

**2. Télécharger un modèle (par ex. le 345M) :**

Le script va créer un dossier `models/345M` et y télécharger les fichiers nécessaires.

```bash
python gpt2_tout_en_un.py download 345M
```

**3. Lancer en mode interactif :**

Vous pouvez maintenant discuter avec le modèle.

```bash
python gpt2_tout_en_un.py interact
```
(Le modèle `345M` est utilisé par défaut). Pour utiliser un autre modèle, précisez-le :
```bash
python gpt2_tout_en_un.py interact --model_name=1558M
```

## Usage Original

This repository is meant to be a starting point for researchers and engineers to experiment with GPT-2.

For basic information, see our [model card](./model_card.md).

### Some caveats

- GPT-2 models' robustness and worst case behaviors are not well-understood.  As with any machine-learned model, carefully evaluate GPT-2 for your use case, especially if used without fine-tuning or in safety-critical applications where reliability is important.
- The dataset our GPT-2 models were trained on contains many texts with [biases](https://twitter.com/TomerUllman/status/1101485289720242177) and factual inaccuracies, and thus GPT-2 models are likely to be biased and inaccurate as well.
- To avoid having samples mistaken as human-written, we recommend clearly labeling samples as synthetic before wide dissemination.  Our models are often incoherent or inaccurate in subtle ways, which takes more than a quick read for a human to notice.

### Work with us

Please [let us know](mailto:languagequestions@openai.com) if you’re doing interesting research with or working on applications of GPT-2!  We’re especially interested in hearing from and potentially working with those who are studying
- Potential malicious use cases and defenses against them (e.g. the detectability of synthetic text)
- The extent of problematic content (e.g. bias) being baked into the models and effective mitigations

## Development

See [DEVELOPERS.md](./DEVELOPERS.md)

## Contributors

See [CONTRIBUTORS.md](./CONTRIBUTORS.md)

## Citation

Please use the following bibtex entry:
```
@article{radford2019language,
  title={Language Models are Unsupervised Multitask Learners},
  author={Radford, Alec and Wu, Jeff and Child, Rewon and Luan, David and Amodei, Dario and Sutskever, Ilya},
  year={2019}
}
```

## Future work

We may release code for evaluating the models on various benchmarks.

We are still considering release of the larger models.

## License

[Modified MIT](./LICENSE)

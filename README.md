# Agent d'acquisition client — Brooze Production

Un agent qui trouve, chaque jour, des entreprises, associations et structures à forte probabilité de réponse, comprend
leur douleur réelle, leur écrit un mail irréprochable, relance, répond, prépare les rendez-vous et pousse vers le
client récurrent (Brooze Continu). Il est supervisé par un **maître agent** (directeur commercial) qui mesure tout,
compare aux résultats et donne des directives. Il ne met jamais le compte Gmail en danger.

Il se construit **couche par couche**, chaque couche validée par Zak avant la suivante.

## État

| Couche | Statut |
|---|---|
| 1 · Le socle (constitution, diagnostic, méthode, garde-fous, charte du Maître) | ✅ validée |
| 2 · La mémoire et le moteur (CRM chiffré, historique Gmail importé, garde-fou codé, tests A/B/C, diagnostic) | ✅ livrée, en attente du feu vert |
| 3 · L'Éclaireur (sourcing et qualification, dont la liste de 100 de Zak) | prochaine |
| 4 → 10 | voir [`docs/06-feuille-de-route.md`](docs/06-feuille-de-route.md) |

## Lire dans cet ordre

1. [`docs/00-architecture.md`](docs/00-architecture.md) : l'équipe, la journée type, où vit quoi.
2. [`docs/01-diagnostic.md`](docs/01-diagnostic.md) : ce que 7 semaines de vraie prospection ont montré (les chiffres
   de référence).
3. [`docs/02-offre-cible.md`](docs/02-offre-cible.md) : l'offre, les segments, le score de probabilité de réponse,
   le calendrier des pics, les douleurs.
4. [`docs/03-garde-fous.md`](docs/03-garde-fous.md) : délivrabilité (anti-blocage), loi, honnêteté. Non négociable.
5. [`docs/04-methode.md`](docs/04-methode.md) : du dossier entité au client récurrent, mails, relances, réponses,
   canaux hors Gmail.
6. [`docs/05-maitre-agent.md`](docs/05-maitre-agent.md) : le superviseur, ses indicateurs, son arbre de diagnostic,
   ses expériences et ses directives.
7. [`docs/06-feuille-de-route.md`](docs/06-feuille-de-route.md) : les couches suivantes et les décisions à prendre.
8. [`docs/07-moteur.md`](docs/07-moteur.md) : les outils (`python3 -m moteur …`), le garde-fou, le coffre chiffré.

## Lancer

```
python3 -m unittest discover -s tests -t .     # 25 tests
export BROOZE_CLE=…                             # clé du coffre (Drive privé de Zak)
python3 -m moteur coffre ouvrir
python3 -m moteur rapport hebdo                 # le diagnostic complet
```

## Arrêt d'urgence

Créer un fichier `PAUSE` à la racine du dépôt : plus aucun envoi, sans exception (actif dès la couche 5).

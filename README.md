# Agent d'acquisition client — Brooze Production

Un agent qui trouve, chaque jour, des entreprises, associations et structures à forte probabilité de réponse, comprend
leur douleur réelle, leur écrit un mail irréprochable, relance, répond, prépare les rendez-vous et pousse vers le
client récurrent (Brooze Continu). Il est supervisé par un **maître agent** (directeur commercial) qui mesure tout,
compare aux résultats et donne des directives. Il ne met jamais le compte Gmail en danger.

Il se construit **couche par couche**, chaque couche validée par Zak avant la suivante.

## État

| Couche | Statut |
|---|---|
| 1 · Le socle (constitution, diagnostic, méthode, garde-fous, charte du Maître) | ✅ livrée, en attente du feu vert |
| 2 · La mémoire (CRM privé, import de l'historique, plafonds codés) | à faire |
| 3 → 10 | voir [`docs/06-feuille-de-route.md`](docs/06-feuille-de-route.md) |

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

## Arrêt d'urgence

Créer un fichier `PAUSE` à la racine du dépôt : plus aucun envoi, sans exception (actif dès la couche 5).

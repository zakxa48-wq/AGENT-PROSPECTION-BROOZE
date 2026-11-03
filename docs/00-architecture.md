# 00 · Architecture de l'agent d'acquisition Brooze

## L'objectif, en une phrase

Générer de **nouveaux clients récurrents** pour Brooze Production (Brooze Continu), chaque jour, avec une méthode
éprouvée, mesurée et ajustée, **sans jamais mettre en danger le compte Gmail** ni la réputation de Brooze.

## L'équipe (un maître, sept rôles)

```
                 ZAK  — décide : prix, plafonds, signatures ; reçoit le récap et les alertes
                  ▲
                  │ propositions, alertes
          ┌───────┴────────┐
          │   LE MAÎTRE    │  directeur commercial : mesure, diagnostique, écrit les directives
          └───────┬────────┘
     directives   │   ▲  journal + tableau de bord
                  ▼   │
 ÉCLAIREUR → STRATÈGE → PLUME → SCEPTIQUE → FACTEUR → GREFFIER
 trouve et    dossier,   écrit    relit,     envoie,    réponses,
 note les     douleur,   le mail  note /10   rythme,    relances,
 entités      angle               (≥ 8)      coupe-     CRM
                                             circuit       │
                                                           ▼
                                          TERRAIN  →  CLOSER
                                          visites,    rendez-vous,
                                          DM, appels  proposition,
                                          (par Zak)   Brooze Continu
```

| Rôle | Mission | Sortie | Règles de référence |
|---|---|---|---|
| **Le Maître** | Superviser, mesurer, diriger, alerter | Directives, bilans, alertes | `05-maitre-agent.md` |
| **L'Éclaireur** | Trouver des entités à forte probabilité de réponse, les noter, vérifier les adresses | File du jour notée, avec sources | `02-offre-cible.md` |
| **Le Stratège** | Dossier entité : signaux, trésor, douleur réelle probable, angle | Un dossier par entité | `04-methode.md` § 1 |
| **La Plume** | Écrire le premier mail et les relances | Mails de 60 à 110 mots | `04-methode.md` § 2 et 4 |
| **Le Sceptique** | Relecture adverse indépendante (ne voit que le mail et le dossier) | Note /10, corrections | `04-methode.md` § 3 |
| **Le Facteur** | Envoyer au bon rythme, appliquer les plafonds et le coupe-circuit | Envois, journal d'envoi | `03-garde-fous.md` § 1 |
| **Le Greffier** | Lire et classer les réponses, répondre vite, planifier les relances, tenir le CRM | CRM à jour, alertes | `04-methode.md` § 5 |
| **Le Terrain** | Préparer les canaux hors Gmail que Zak exécute (visites, Instagram, appels, partenaires) | Tournée, messages prêts | `04-methode.md`, canaux |
| **Le Closer** | Préparer les rendez-vous, la proposition sous 24 h, le passage à Brooze Continu | Fiches, propositions | `04-methode.md` § 6 |

Les rôles sont des **modes de travail** d'un même agent qui tourne chaque jour, sauf le Sceptique et le Maître, qui
sont des agents **séparés** : un relecteur ne doit jamais connaître les intentions de celui qu'il juge.

## La journée type (jour ouvré)

| Moment | Qui | Quoi |
|---|---|---|
| Ouverture | Tous | Fichier `PAUSE` ? Voyants de santé ? Lecture des directives du Maître |
| Priorité 1 | Greffier | Réponses arrivées : classer, répondre dans l'heure, alerter Zak si positif |
| Priorité 2 | Facteur | Relances du jour (J+3, J+7, J+12, relances planifiées) |
| Fenêtre 1 (9 h 15 – 11 h) | Éclaireur → Stratège → Plume → Sceptique → Facteur | Chaque mail part dès qu'il est validé ; le temps de préparer le suivant fait l'espacement. 5 premiers contacts |
| Fenêtre 2 (14 h 30 – 16 h 30) | Idem | 5 premiers contacts de plus (10 au total), réponses de la journée |
| Clôture | Maître | Revue quotidienne, tableau de bord, récap court à Zak |

Le week-end : pas de premier contact (B2B). L'agent prépare le stock de la semaine (recherche, dossiers), le Terrain
prépare la tournée, le Maître fait son bilan hebdomadaire le lundi matin.

## Où vit quoi

| Élément | Emplacement | Statut |
|---|---|---|
| La méthode (ces documents) | ce dépôt, `docs/` | couche 1 |
| Le CRM (entités, contacts, historique, exclusions) | **espace privé** (jamais dans un dépôt public) | couche 2, décision de Zak |
| Les directives et le journal du Maître | `pilotage/` (privé si données nominatives) | couche 6 |
| Les mails | Gmail contact@broozeproduction.fr, labels `BROOZE/Prospection/...` | couche 5 |
| L'exécution quotidienne | tâches programmées Claude Code (comme les agents Instagram existants) | couche 7 |

## Ce qui existe déjà autour (et que l'agent ne doit pas perturber)

Quatre tâches programmées Brooze tournent déjà : « Brooze montage inbox » (Reels, 2 fois par jour), « Brooze semaine
Instagram », « Brooze relevé stats », « Brooze bilan dimanche ». Elles envoient des récaps à Zak depuis la même boîte.
L'agent de prospection ne touche ni à Instagram ni à Metricool ; il peut seulement **citer** un Reel publié comme
preuve dans une relance. Le dépôt `brooze-kit` (charte, avatars, skills) reste la source de l'identité Brooze.

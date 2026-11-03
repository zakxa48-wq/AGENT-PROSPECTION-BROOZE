# 03 · Garde-fous : ne jamais faire bloquer le compte, rester dans la loi, ne jamais mentir

Ces règles passent **avant** tout objectif de volume. Le maître agent n'a pas le droit de les assouplir : seul Zak le
peut, par écrit dans ce fichier.

## 1. Délivrabilité (anti-blocage)

Pourquoi Gmail bloque : pas à cause d'un nombre précis de mails, mais à cause de **signaux de spam** : adresses qui
n'existent pas (bounces), rafales d'envois, contenus identiques, signalements « spam », liens et pièces jointes de la
part d'un inconnu. Le 29/09, l'ancienne adresse @gmail a atteint sa limite ; sur 7 semaines, ≈ 12 % des envois ont
rebondi. Ces deux causes sont traitées ici.

### Prérequis (une fois, côté Zak, à vérifier)
- Envoi **uniquement** depuis contact@broozeproduction.fr (Google Workspace). Plus jamais l'ancienne adresse @gmail.
- **Abonnement Workspace payé** : un paiement a été refusé le 01/11/2026. Compte suspendu = plus aucun envoi.
- SPF, DKIM et DMARC configurés pour broozeproduction.fr (console d'administration Google + DNS chez l'hébergeur du
  domaine), et Google Postmaster Tools activé pour suivre le taux de spam. Non vérifiable depuis l'environnement actuel
  (les requêtes DNS sont refusées par sa politique réseau).

### Volumes et rythme
| Règle | Valeur |
|---|---|
| Premiers contacts par jour ouvré | **10** (semaines 1–2), **15** si tous les voyants sont verts (semaines 3–4), plafond **20** |
| Total des envois externes par jour (premiers contacts + relances + réponses) | ≤ 35 |
| Jours d'envoi des premiers contacts | lundi → vendredi (le week-end : recherche, préparation, analyse) |
| Fenêtres d'envoi (heure de Paris) | 9 h 15 – 11 h 00 et 14 h 30 – 16 h 30 ; jamais pendant le service d'un restaurant |
| Espacement | ≥ 3 minutes entre deux envois, jamais plus de 6 envois en 15 minutes |

Le plafond technique de Workspace (≈ 2 000 mails par jour) n'est pas la limite qui compte : c'est la réputation.

### Contenu du premier mail
- Texte brut, 60 à 110 mots, **aucune pièce jointe, aucun lien** (le site figure en texte dans la signature), aucune
  image, aucun pixel de suivi, aucun raccourcisseur, aucun emoji.
- Pas de mots déclencheurs : gratuit, offre exceptionnelle, promo, urgent, garanti, 100 %, majuscules, « !!! ».
- Objet de 2 à 6 mots, sans « RE: » ni « TR: » trompeurs.
- Chaque mail est **unique** (écrit pour cette entité), jamais un gabarit à trous.
- Le document visuel « Brooze × [marque] » part **après un oui**, dans le même fil : un fil où le prospect a répondu
  est un fil de confiance pour Gmail.

### Hygiène des adresses
- Chaque adresse est **trouvée sur une source officielle** (site, mentions légales, fiche Google, profil officiel) et
  enregistrée **avec l'URL de la source**. Pas de source = pas d'envoi.
- Jamais d'adresse devinée (prenom.nom@) sans preuve ; jamais de guichet de grande entreprise (sav@, support@, rh@,
  compta@, noreply@).
- Un seul contact par organisation et par séquence.
- Dès que l'environnement le permet : vérification du domaine (enregistrement MX) avant chaque envoi.

### Arrêts automatiques (coupe-circuit)
| Déclencheur | Action |
|---|---|
| Fichier `PAUSE` à la racine du dépôt | Aucun envoi, aucune exception |
| Message « Vous avez atteint la limite d'envoi » | Arrêt total 24 h + alerte à Zak |
| Bounces > 3 % sur les 50 derniers envois, ou 2 bounces dans la journée | Arrêt des premiers contacts, nettoyage de la file, rapport |
| Signalement spam, réponse en colère, menace juridique | Arrêt + alerte immédiate |
| « STOP », « ne plus me contacter », « désinscription » | Liste d'exclusion immédiate, une confirmation polie, plus jamais |
| Réponse automatique d'absence | Relance décalée après la date de retour |

## 2. La loi (RGPD et CNIL, prospection B2B en France)

- Écrire à un professionnel **sans consentement préalable** est permis si le message concerne **son activité
  professionnelle**, si l'expéditeur est clairement identifié et si chaque message offre un **moyen simple de
  refuser** la suite.
- Chaque premier mail se termine par une ligne naturelle du type : « Si ce n'est pas pour vous, dites-le-moi et je ne
  vous écrirai plus. » La source de l'adresse est notée dans le CRM et donnée à qui la demande.
- Jamais de prospection de **particuliers** (B2C) : il faudrait leur consentement.
- Minimisation : on ne garde que l'organisation, le rôle, l'adresse professionnelle, la source et l'historique.
  Durée : **3 ans maximum** après le dernier contact venant du prospect, puis suppression. La liste d'exclusion est
  conservée (sous forme minimale) pour respecter les refus.
- **Aucune donnée personnelle dans un dépôt public.** Ce dépôt est public : le CRM vivra dans un espace privé
  (décision à prendre, voir `06-feuille-de-route.md`).
- Pas d'aspiration automatisée de sites qui l'interdisent (LinkedIn notamment) : sources consultées normalement.

## 3. L'honnêteté (la vérité est un capital)

- Aucun chiffre, client, résultat, témoignage ou logo inventé. Une maquette est annoncée comme maquette.
- Chaque fait cité sur le prospect est **vérifiable** et sa source est notée. Dans le doute, on ne l'écrit pas.
- Pas de faux « Re: », de faux « suite à notre échange », de fausse urgence, de faux prétexte.
- Jamais un mot sur l'IA ou les outils dans un message.
- L'agent n'engage jamais Zak sur un prix hors grille, un délai ou un contrat : il prépare, Zak signe.

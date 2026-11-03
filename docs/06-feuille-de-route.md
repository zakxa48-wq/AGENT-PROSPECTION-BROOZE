# 06 · Feuille de route : la construction couche par couche

Règle : on ne passe à la couche suivante que sur le **feu vert de Zak**. Chaque couche a un critère de réussite
vérifiable. Rien n'est envoyé à un prospect avant la couche 5.

| Couche | Nom | Ce qu'elle livre | Critère de réussite |
|---|---|---|---|
| **1** | **Le socle** ✅ (validé le 03/11) | La constitution de l'agent : architecture, diagnostic chiffré, offre et cible, score, garde-fous, méthode, charte du Maître | Zak valide la direction |
| **2** | **La mémoire et le moteur** ✅ (livrée le 03/11) | CRM événementiel chiffré ; 211 entités déjà contactées importées depuis Gmail avec leurs issues (liste d'exclusion + base d'apprentissage) ; import de listes ; garde-fou codé ; vérification d'adresses ; score recalibrable ; tests A/B/C par Thompson ; diagnostic avec niveaux de preuve ; objectifs auto-ajustés ; comptes rendus ; 25 tests (`docs/07-moteur.md`) | Impossible de recontacter une entité par erreur ; un 11e premier contact est refusé par le code ✅ (testé) |
| 3 | L'Éclaireur | Sourcing sur signaux (agendas, presse locale, ouvertures, Bibliothèque publicitaire Meta, annuaires, HelloAsso…) et score /100 ; 20 entités notées par jour | 3 jours de files avec ≥ 80 % d'adresses à source officielle |
| 4 | Stratège, Plume, Sceptique | Dossiers entité, mails, relances, relecture adverse indépendante | 20 mails de test en **brouillons Gmail**, validés par Zak sans réécriture majeure |
| 5 | Facteur et Greffier | Envois réels au bon rythme, relances J+3 / J+7 / J+12, tri et réponses, alertes. Démarrage : 2 jours en brouillons validés par Zak, puis autonome | 1 semaine à 10 premiers contacts par jour ouvré, bounces < 2 %, toute réponse positive traitée en < 1 h ouvrée |
| 6 | Le Maître | Revue quotidienne et hebdomadaire, expériences, directives, bilans | 1er bilan hebdomadaire avec une directive appliquée et mesurée |
| 7 | L'autonomie | Tâches programmées (2 passages par jour ouvré, préparation le week-end, bilan du lundi), récap quotidien de 5 lignes à Zak | 2 semaines sans intervention, aucun voyant rouge non signalé |
| 8 | Multicanal et terrain | Tournées de visites, messages Instagram et LinkedIn prêts à envoyer, scripts d'appel, programme d'apporteurs d'affaires | 1 rendez-vous obtenu hors Gmail |
| 9 | Closing et récurrence | Fiches de rendez-vous, propositions visuelles « Brooze × [marque] » (avec brooze-direction), devis, passage à Brooze Continu, demandes de recommandation | 1er pilote signé, puis 1er client Brooze Continu |
| 10+ | L'intelligence cumulée | Mémoire des apprentissages par segment, recalibrage statistique du score, recherche de « jumeaux » des clients signés, saisonnalité apprise | Le taux de réponse positive progresse d'un mois sur l'autre |

## Décisions de Zak (03/11)

- Envois du lundi au vendredi ; le week-end : ajustement stratégique et récap.
- Mention « étudiant à l'EM Strasbourg » gardée dans toutes les approches ; d'autres approches testées en parallèle et
  renforcées progressivement selon leur conversion (réponse ET achat).
- Prix : ceux du site et des dernières propositions (`config/offre.json`).
- Zak fournit une première liste de 100 prospects, traitée progressivement sans jamais faire bloquer Gmail.
- Les brouillons existants peuvent servir d'inspiration, jamais de copie.

## Ce qui reste à trancher ou à débloquer

| # | Sujet | Pourquoi | Recommandation |
|---|---|---|---|
| 1 | **Paiement Google Workspace refusé le 01/11** | Compte suspendu = plus aucun envoi, ni prospection ni récaps | Mettre à jour la carte dans la console d'administration Google, cette semaine |
| 2 | **Ce dépôt est public** | Le CRM contient des données personnelles (RGPD) | Passer le dépôt en privé (GitHub → Settings → Danger Zone → Change visibility) |
| 3 | **Accès réseau de l'environnement** | La recherche web marche, mais la lecture des sites des entreprises est refusée (accès « limité »). Sans ça, pas d'analyse fine ni de vérification d'adresses | Passer l'accès réseau de l'environnement en accès complet (réglages de l'environnement cloud → Network access) |
| 4 | Prix de Brooze Continu | Le site dit « sur devis » ; le pilote est à 560 € TTC dans les dernières propositions | Une grille Continu (2 ou 3 formules) rendrait les propositions plus rapides |
| 5 | Démarrage | La première série engage la réputation de Brooze | 2 jours en brouillons validés par Zak, puis autonomie |
| 6 | Téléphone dans la signature | Rassure les commerçants (le WhatsApp est déjà public sur le site) | Oui, à confirmer (`config/offre.json` → `dans_signature`) |
| 7 | Zone | Le local répond 2,6 fois mieux que le national (14,7 % contre 5,6 %) | Strasbourg et Eurométropole d'abord, puis l'Alsace |
| 8 | DNS du domaine | SPF, DKIM et DMARC conditionnent la délivrabilité ; non vérifiables d'ici | Vérifier dans la console Google (Applications → Gmail → Authentifier les e-mails) |

# 06 · Feuille de route : la construction couche par couche

Règle : on ne passe à la couche suivante que sur le **feu vert de Zak**. Chaque couche a un critère de réussite
vérifiable. Rien n'est envoyé à un prospect avant la couche 5.

| Couche | Nom | Ce qu'elle livre | Critère de réussite |
|---|---|---|---|
| **1** | **Le socle** ✅ | La constitution de l'agent : architecture, diagnostic chiffré, offre et cible, score, garde-fous, méthode, charte du Maître | Zak valide la direction |
| 2 | La mémoire | CRM privé ; import des ≈ 220 entités déjà contactées (liste d'exclusion) et des leads tièdes (relances datées) ; outils `crm.py`, `garde_fou.py` (plafonds et coupe-circuit qui bloquent physiquement un envoi de trop), `verif.py` (adresses) ; labels Gmail normalisés | Impossible de recontacter une entité par erreur ; un 11e premier contact est refusé par le code |
| 3 | L'Éclaireur | Sourcing sur signaux (agendas, presse locale, ouvertures, Bibliothèque publicitaire Meta, annuaires, HelloAsso…) et score /100 ; 20 entités notées par jour | 3 jours de files avec ≥ 80 % d'adresses à source officielle |
| 4 | Stratège, Plume, Sceptique | Dossiers entité, mails, relances, relecture adverse indépendante | 20 mails de test en **brouillons Gmail**, validés par Zak sans réécriture majeure |
| 5 | Facteur et Greffier | Envois réels au bon rythme, relances J+3 / J+7 / J+12, tri et réponses, alertes. Démarrage : 2 jours en brouillons validés par Zak, puis autonome | 1 semaine à 10 premiers contacts par jour ouvré, bounces < 2 %, toute réponse positive traitée en < 1 h ouvrée |
| 6 | Le Maître | Revue quotidienne et hebdomadaire, expériences, directives, bilans | 1er bilan hebdomadaire avec une directive appliquée et mesurée |
| 7 | L'autonomie | Tâches programmées (2 passages par jour ouvré, préparation le week-end, bilan du lundi), récap quotidien de 5 lignes à Zak | 2 semaines sans intervention, aucun voyant rouge non signalé |
| 8 | Multicanal et terrain | Tournées de visites, messages Instagram et LinkedIn prêts à envoyer, scripts d'appel, programme d'apporteurs d'affaires | 1 rendez-vous obtenu hors Gmail |
| 9 | Closing et récurrence | Fiches de rendez-vous, propositions visuelles « Brooze × [marque] » (avec brooze-direction), devis, passage à Brooze Continu, demandes de recommandation | 1er pilote signé, puis 1er client Brooze Continu |
| 10+ | L'intelligence cumulée | Mémoire des apprentissages par segment, recalibrage statistique du score, recherche de « jumeaux » des clients signés, saisonnalité apprise | Le taux de réponse positive progresse d'un mois sur l'autre |

## Ce qui bloque ou doit être tranché avant la couche 2

| # | Sujet | Pourquoi | Recommandation |
|---|---|---|---|
| 1 | **Paiement Google Workspace refusé le 01/11** | Compte suspendu = plus aucun envoi, ni prospection ni récaps | Mettre à jour la carte dans la console d'administration Google, cette semaine |
| 2 | **Ce dépôt est public** | Le CRM contient des données personnelles (RGPD) | Passer le dépôt en privé (GitHub → Settings → Danger Zone → Change visibility) |
| 3 | **Accès réseau de l'environnement** | La recherche web marche, mais la lecture des sites des entreprises est refusée (accès « limité »). Sans ça, pas d'analyse fine ni de vérification d'adresses | Passer l'accès réseau de l'environnement en accès complet (réglages de l'environnement cloud → Network access) |
| 4 | Prix du pilote et de Brooze Continu | L'agent ne peut pas répondre à « combien ? » ni faire de proposition sans grille | Zak fixe un prix de pilote et 2 ou 3 formules Continu |
| 5 | Jours d'envoi | « Tous les jours » : les premiers contacts B2B le week-end répondent mal et font machinal | Envois du lundi au vendredi (≥ 10 par jour, soit ≥ 50 par semaine), préparation 7 jours sur 7 |
| 6 | Démarrage | La première série engage la réputation de Brooze | 2 jours en brouillons validés par Zak, puis autonomie |
| 7 | Signature | « Étudiant à l'EM Strasbourg » : effet inconnu ; un numéro de téléphone rassure les commerçants | Garder la mention pour un test A/B ; ajouter le téléphone si Zak est d'accord |
| 8 | Zone | Le local répond, le national non | Strasbourg et Eurométropole d'abord, puis l'Alsace |
| 9 | DNS du domaine | SPF, DKIM et DMARC conditionnent la délivrabilité ; non vérifiables d'ici | Vérifier dans la console Google (Applications → Gmail → Authentifier les e-mails) |

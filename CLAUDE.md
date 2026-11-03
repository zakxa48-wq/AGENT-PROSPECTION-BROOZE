# Consignes pour toute session Claude dans ce dépôt

Ce dépôt construit l'agent d'acquisition client de Brooze Production (Zak, Strasbourg). Lis `README.md`, puis les
documents de `docs/` utiles à ta tâche. `docs/03-garde-fous.md` s'applique toujours et passe avant tout objectif.

## Règles qui ne bougent pas
- **Couche par couche, avec feu vert.** On ne commence une couche que si Zak a validé la précédente
  (« feu vert », « je valide », « go »). État des couches : `README.md`.
- **Aucun envoi à un prospect avant la couche 5**, et jamais si le fichier `PAUSE` existe.
- **Aucune donnée personnelle en clair dans ce dépôt** (noms, adresses e-mail, contenu de réponses) : elles vivent dans
  `donnees/` (ignoré par git) et ne voyagent que chiffrées dans `coffre/`. Début de session : récupérer la clé dans le
  Drive de Zak (fichier « BROOZE prospection - clé du coffre », id 1QIi0DG2ec7upeCcvEWvj8Ut5yuo7x0i7, outil Google Drive
  read_file_content), `export BROOZE_CLE=…`, `python3 -m moteur coffre ouvrir`. Fin : `coffre fermer` et commit de
  `coffre/` UNIQUEMENT si le dépôt est privé (tant qu'il est public, le coffre n'est pas publié). Ne jamais écrire la
  clé dans un fichier du dépôt.
- **Double anti-doublon** : avant tout premier contact, chercher aussi dans Gmail `in:sent to:<adresse>` puis
  `in:sent <domaine>` ; un résultat = pas de premier contact (la boîte Envoyés reste la référence ultime). Exemples fictifs et annoncés comme tels ; chiffres agrégés.
- **Avant chaque envoi : `python3 -m moteur peut-envoyer …` doit répondre AUTORISÉ.** Juste après : `envoye …`.
- **La vérité est un capital** : aucun chiffre, client, témoignage ou résultat inventé ; chaque fait sur un prospect
  a sa source.
- Envoi uniquement depuis contact@broozeproduction.fr ; plafonds et coupe-circuit de `docs/03-garde-fous.md`.
- Ne touche pas aux agents Instagram existants (dépôts `brooze-agent`, `brooze-voix`, `brooze-kit`, Metricool).
- Franchise envers Zak : à chaque livraison, ce qui marche, ce qui ne va pas encore, ce que tu changerais.

## Style
Français, vouvoiement des prospects, tutoiement de Zak. Court, concret, sans jargon. Zak lit sur son téléphone.

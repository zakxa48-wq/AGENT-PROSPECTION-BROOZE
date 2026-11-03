# 07 · Le moteur : les outils de l'agent

Python standard, aucune dépendance. Tout passe par une commande : `python3 -m moteur <commande>`.
Tests : `python3 -m unittest discover -s tests -t .` (25 tests : garde-fou, import, tests A/B/C, diagnostic, DNS…).

## 1. Les briques et ce qu'elles garantissent

| Brique | Fichier | Ce qu'elle fait | Pourquoi c'est solide |
|---|---|---|---|
| CRM événementiel | `moteur/crm.py` | Une fiche par entité + un journal immuable de chaque action datée (importé, qualifié, rédigé, contrôlé, envoyé, bounce, réponse, rendez-vous, proposition, signé, récurrent, erreur, règle) | Rien n'est écrasé : on peut tout ré-analyser après coup, et l'état d'un prospect se déduit de son histoire |
| Anti-doublons | `crm.trouver_doublon` | Même adresse, même domaine pro, même téléphone, même Instagram, nom très proche dans la même ville | Une structure n'est jamais contactée deux fois, même par deux adresses différentes |
| Vérification d'adresse | `moteur/verif.py` | Syntaxe, guichets (sav@, rh@…), fautes de frappe (gmial.com), domaines jetables, requête DNS MX directe | Contrôle témoin : si le résolveur ne trouve même pas gmail.com, il est filtré et le moteur répond « non vérifiable » au lieu d'un faux verdict |
| Score /100 | `moteur/score.py` + `config/score.json` | Grille de `02-offre-cible.md`, exclusions, complétude de la recherche | `calibrer` : régression logistique sur les vraies réponses, mélangée à l'ancienne grille selon le nombre de réponses observées |
| Import de listes | `moteur/importer.py` | CSV, TSV, Excel, JSON ; reconnaît seul les colonnes (« Entreprise », « E-mail », « CP »…) ; segment deviné ; rapport complet | Doublons dans le fichier et contre le CRM, adresses bloquées, fiches sans source : tout est listé, rien n'est envoyé |
| **Garde-fou** | `moteur/garde_fou.py` + `config/garde_fous.json` | Autorise ou refuse CHAQUE envoi | Voir § 3 : les règles anti-blocage sont dans le code, pas dans une consigne |
| Tests A/B/C | `moteur/experiences.py` + `config/approches.json` | Échantillonnage de Thompson : les approches qui convertissent reçoivent progressivement plus d'envois | Correction du retard de réponse (un mail d'hier ne compte que pour une fraction d'essai), part minimale du témoin, champion déclaré seulement avec ≥ 40 essais et ≥ 95 % de probabilité |
| Diagnostic | `moteur/diagnostic.py` + `config/causes.json` | Entonnoir, goulot, scan automatique de toutes les caractéristiques, 33 causes testées, registre des erreurs | Niveaux de preuve corrigés du nombre de tests (on ne crie pas victoire sur un hasard) ; « non concluant » quand c'est le cas |
| Objectifs | `moteur/objectifs.py` | Relève une cible tenue 2 semaines d'un pas (+10 %), plafonnée | Une cible manquée n'est jamais baissée en douce : elle déclenche le diagnostic |
| File du jour | `moteur/planificateur.py` | Réponses à traiter, relances dues, nouveaux contacts (liste de Zak d'abord, puis score), fiches à compléter, leads tièdes | Le nombre de nouveaux contacts suit le plafond restant du garde-fou |
| Comptes rendus | `moteur/rapport.py` | Quotidien (4 lignes) et hebdomadaire (entonnoir, goulot, causes prouvées, ce qui marche, tests, erreurs, objectifs, directives) | Texte brut, lisible dans Gmail sur téléphone |
| Coffre | `moteur/coffre.py` | Chiffre `donnees/` en AES-256 (PBKDF2, 200 000 itérations) dans `coffre/` | Le dépôt peut rester public : sans la clé, le fichier est illisible ; une mauvaise clé est refusée |

## 2. Une journée de l'agent, commande par commande

```
export BROOZE_CLE=…            # lue dans le Drive privé de Zak (fichier « BROOZE prospection - clé du coffre »)
python3 -m moteur coffre ouvrir
python3 -m moteur etat          # voyants, palier, plafonds restants
python3 -m moteur file          # la liste de travail du jour
python3 -m moteur regles        # les règles apprises, à respecter
```

Pour chaque entité à contacter :

```
python3 -m moteur prospect voir ID
python3 -m moteur prospect maj ID --json '{"signaux": {...}, "email_source": "https://…/contact"}'   # recherche de l'Éclaireur
python3 -m moteur evenement dossier ID --json '{"douleur": "…", "angle": "…", "sources": ["…"]}'
python3 -m moteur evenement redige ID --json '{"etape": 1, "approche": "B", "objet": "…", "mots": 92}'
python3 -m moteur evenement controle ID --json '{"etape": 1, "note": 8.5, "defauts": []}'       # le Sceptique, agent séparé
python3 -m moteur peut-envoyer premier_contact ID     # code 0 = autorisé ; sinon, NE PAS ENVOYER
# envoi Gmail (send_message), puis immédiatement :
python3 -m moteur envoye ID --etape 1 --approche B --message MSG_ID --thread THREAD_ID --objet "…" --mots 92 \
        --dims '{"objet_type": "detail", "mention_em": true}'
```

Quand une réponse arrive : `evenement reponse ID --json '{"classe": "positive"}'` (classes : positive, question_prix,
redirection, deja_videaste, interne, pas_moment, pas_budget, pas_compris, pas_interesse, stop, autre), puis
`peut-envoyer reponse ID`, réponse Gmail, `envoye ID --type reponse --etape 0`. Un bounce : `evenement rebond ID --json
'{"nature": "bloque" | "adresse" | "rejet_destinataire"}'`. Une limite Gmail : `evenement limite_envoi` (arrêt 24 h).

Une erreur constatée (fait faux, adresse fausse, réponse lente…) : `evenement erreur ID --json '{"categorie": "…",
"description": "…", "cause": "…"}'`. Si elle se répète, le diagnostic exige une règle : `regle CATEGORIE "texte"`.

En fin de passage : `rapport quotidien` (envoyé à Zak), `coffre fermer`, copie du coffre dans le Drive, commit de
`config/` si le maître agent l'a modifié.

## 3. Ce que le garde-fou refuse (preuve à l'appui)

| Refus | Règle | Preuve |
|---|---|---|
| Fichier `PAUSE` | aucun envoi | — |
| Limite Gmail signalée | arrêt total 24 h | limite atteinte le 29/09 sur l'ancienne adresse |
| Week-end, jour férié (Alsace-Moselle comprise : Vendredi saint, 26 décembre) | pas de prospection | B2B |
| Hors 9 h 15 – 11 h et 14 h 30 – 16 h 30 | pas de prospection | — |
| 10 premiers contacts par jour (15 puis 20 si santé verte), 35 envois au total | plafonds par palier | — |
| Moins de 3 min depuis le dernier envoi, ou 6 envois en 15 min | espacement | **Historique (258 envois) : 1 à 2 % de messages bloqués par Google quand on envoie 1 à 5 mails en 10 minutes, 27 % à 6–9 et 42 % à 10 ou plus** |
| Bounces > 3 % sur les 50 derniers, ou 2 dans la journée | arrêt des nouveaux contacts | — |
| Structure déjà contactée (même adresse ou même domaine) depuis moins de 180 jours | doublon | — |
| Score < 60, exclusion, guichet, adresse bloquée, source absente | qualification | 0 réponse positive sur les guichets de marques nationales |
| Pas de texte rédigé enregistré, pas relu par le Sceptique, ou note < 8 | qualité | — |
| Relance avant J+3 / J+7 / J+12 ouvrés, ou prospect qui a déjà répondu | séquence | — |

Un envoi fait malgré un refus est enregistré comme **erreur** « envoi_non_autorise » : il apparaît dans le bilan.

## 4. Où vivent les données

- `donnees/` (jamais versionné) : `prospects.jsonl`, `evenements.jsonl`, `pilotage.json` (réglages du maître agent),
  `objectifs_courants.json`.
- `coffre/donnees.tar.gz.enc` (chiffré) + `coffre/empreinte.txt` (contrôle d'intégrité). Tant que le dépôt est
  public, le coffre n'est PAS versionné (le système de sécurité refuse, à juste titre, de publier des données issues de
  Gmail, même chiffrées) : il est copié dans le Drive privé de Zak. Une fois le dépôt privé, il sera versionné.
- La clé : un fichier texte dans le Google Drive de Zak (« BROOZE prospection - clé du coffre »). À défaut, une
  variable d'environnement `BROOZE_CLE` dans les réglages de l'environnement.
- Contenu actuel : 211 entités contactées entre le 14/09 et le 02/11/2026 (liste d'exclusion et base
  d'apprentissage), leurs issues lues dans Gmail, 6 leads tièdes, 3 incidents et 3 règles apprises.

## 5. Importer la liste de Zak

```
python3 -m moteur importer liste.xlsx --zak --simulation   # d'abord à blanc : lire le rapport
python3 -m moteur importer liste.xlsx --zak
```

Colonnes reconnues sans réglage : nom ou entreprise, e-mail, site, ville, CP, téléphone, contact ou décideur, poste,
secteur, Instagram, notes ou pourquoi, source. Les entités déjà contactées sont signalées (jamais recontactées sans
nouvelle raison). Les prospects importés sont « à qualifier » : l'Éclaireur complète leurs signaux avant qu'ils
entrent dans la file.

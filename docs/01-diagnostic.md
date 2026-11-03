# 01 · Diagnostic : ce que disent 7 semaines de vraie prospection

Source : la boîte Gmail de Brooze (contact@broozeproduction.fr et l'ancienne adresse broozeproduction@gmail.com),
relue fil par fil le 03/11/2026 et importée dans le moteur (210 premiers contacts, 258 envois, du 14/09 au 02/11/2026).
Chaque échec de remise a été lu un par un. Les chiffres ci-dessous sortent de `python3 -m moteur rapport hebdo`.

Ce dépôt est public : aucun nom de personne ni adresse e-mail ici, seulement des catégories. Le détail est chiffré
dans `coffre/`.

## Les chiffres de référence (baseline)

| Indicateur | Valeur mesurée | Objectif |
|---|---|---|
| Premiers contacts | 210 en 7 semaines (≈ 6 par jour ouvré) | ≥ 10 par jour ouvré |
| Délivrés | 187/210 = **89 %** | ≥ 98 % |
| dont messages **bloqués par Google** | 19 | 0 |
| dont adresses réellement invalides | 4 (1,9 %) | < 2 % |
| Limite d'envoi Gmail atteinte | 1 fois (29/09, ancienne adresse) | 0 |
| Réponses humaines | 19/187 = 10,2 % | ≥ 10 % |
| Réponses positives (intérêt, rendez-vous, demande de prix) | 5, soit 26 % des réponses | ≥ 30 % des réponses |
| Rendez-vous | 3 sur 5 réponses positives (+ 1 lead rencontré sur place) | — |
| Clients signés | 0 | 1er pilote sous 30 jours |

## Découverte n° 1 : ce ne sont pas les adresses, ce sont les rafales

19 des 23 échecs sont des « **Message bloqué** » (12 lus un par un, 7 déduits car partis dans la même minute que
deux blocages lus) : c'est Google qui refuse d'envoyer, parce que les mails partaient par paquets. Le moteur a recalculé, pour chacun des 258 envois, combien de mails étaient partis dans les 10 minutes
précédentes :

| Envois dans les 10 minutes | Envois | Bloqués par Google |
|---|---|---|
| 1 à 2 | 112 | 1 (1 %) |
| 3 à 5 | 93 | 2 (2 %) |
| 6 à 9 | 41 | 11 (27 %) |
| 10 et plus | 12 | 5 (42 %) |

Pire journée : le 29/09, 10 relances parties en 3 minutes, 9 bloquées, et la limite d'envoi atteinte sur l'ancienne
adresse. C'est exactement le blocage que Zak veut éviter. **Preuve : prouvé** (cause D3 du moteur). Le garde-fou impose
désormais 3 minutes minimum entre deux envois, soit 4 mails au plus en 10 minutes, dans la zone à 1 ou 2 %.

## Découverte n° 2 : la cible, plus que le texte

| Facteur | Ce que montrent les données | Niveau de preuve |
|---|---|---|
| Zone | Strasbourg 14,7 % de réponses (15/102), Alsace 8,3 % (1/12), reste de la France 5,6 % (3/54) | probable |
| Type de boîte | adresse perso (souvent lue par le patron) 16,7 %, contact@ 10,8 %, adresse nominative de marque 4,5 % | probable |
| Segment | lieux, artisans et associations locales 12 à 18 % ; marques nationales 5,8 % ; PME nommées 0 % | probable |
| Campagne | campagne locale d'octobre 19,4 % ; marques nationales avec PDF et prix : 10 % de réponses, **toutes des refus** | probable |
| Prix ou pièce jointe dans le 1er mail | 10,0 % contre 10,2 % de réponses : aucun effet mesurable sur le taux de réponse | non concluant |
| Relances | 0 des 19 réponses n'est arrivée après une relance | prouvé (mais relances faibles ou bloquées) |

Biais signalé honnêtement : zone et segment sont estimés d'après les noms et les campagnes. Ces conclusions orientent
le ciblage, elles seront confirmées ou démenties par les envois de l'agent, qui enregistre tout dès le départ.

## Ce qui a marché

- Les **indépendants strasbourgeois dont la boîte est lue par le patron** : toutes les réponses positives.
- Les mails courts avec une idée concrète et une question d'intérêt (« si ça vous parle, je vous envoie deux idées »).
- Le document visuel envoyé **après** un oui (« sincèrement je suis très impressionnée »).
- Le terrain : les rendez-vous se font facilement sur place à Strasbourg.

## Ce qui n'a pas marché

1. Les **rafales d'envois** (ci-dessus).
2. Les **marques nationales via leurs guichets** (contact@, bonjour@, sav@) : tickets automatiques, enquêtes de
   satisfaction, refus polis. Aucune réponse positive.
3. Le **timing** : en octobre, plusieurs commerces avaient déjà réservé leur vidéaste pour Noël.
4. L'**après-rendez-vous** : aucune proposition chiffrée envoyée vite, pas de suivi planifié. 6 leads tièdes
   attendent aujourd'hui une relance utile (liste dans `python3 -m moteur file`, section 5), dont une réponse
   « nous gardons vos coordonnées pour collaborer dans les prochains mois » restée sans suite depuis le 02/10.
5. Le **style perçu comme machinal** : une réponse commence par « Bonsoir IA (?) ».
6. Les **relances** sans élément nouveau (« je reviens vers vous ») : elles n'ont rien rapporté.

## Les objections entendues (19 réponses)

| Objection | Fois | Ce qu'elle révèle |
|---|---|---|
| « Pas intéressé » sans raison | 7 | Ciblage (surtout marques nationales et guichets) |
| « Déjà un vidéaste / tout en interne » | 5 | Ils croient à la vidéo et ont un budget : **signal de qualification** et angle « déclinaisons de vos rushes » |
| Intérêt, rencontre, demande de prix | 5 | — |
| « Pas le moment » | 1 | Calendrier |
| Redirection vers la bonne personne | 1 | À suivre jusqu'au décideur |

## Les 8 leçons qui fondent l'agent

- **L1.** Strasbourg et l'Eurométropole d'abord, boîte lue par le décideur.
- **L2.** « On a déjà un vidéaste » est un angle : nous transformons les rushes existants en formats courts.
- **L3.** Toujours viser le prochain pic du prospect, 6 à 10 semaines avant.
- **L4.** La fuite est après le rendez-vous : proposition sous 24 h, offre d'entrée claire, suivi planifié.
- **L5.** Jamais de rafale : 3 minutes minimum entre deux envois, codé dans le garde-fou (preuve ci-dessus).
- **L6.** Marques nationales : seulement avec un décideur nommé et un signal, jamais un guichet.
- **L7.** Écrire comme un humain qui a vraiment regardé : court, précis, une seule question.
- **L8.** Premier mail sans prix ni pièce jointe : aucun bénéfice mesuré, et un risque de délivrabilité.

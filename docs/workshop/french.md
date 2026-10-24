<!-- source: c1b2511ee47c687e -->

## Random New World

Un générateur de Nouveaux Mondes pour Europa Universalis V. Il refait les Amériques de fond en comble : continents, côtes, relief, climat, fleuves, végétation, ressources, provinces et peuples autochtones, et garde l'Ancien Monde tel que Paradox l'a fait. **Chaque monde qu'il crée est un mod de carte complet à part entière.** Il se joue seul : gardez autant de mondes que vous voulez, supprimez-les ou partagez le code d'un monde. Le monde se joue sans ce générateur, et toute personne qui a la même version du jeu obtient le même monde à partir de son code.

Inutile d'activer cet objet dans un playset. Il ne contient que le générateur.

## Pourquoi cet objet contient un programme

EU5 construit sa carte à partir de fichiers quand il charge les mods. Un mod, ce sont des données : il ne peut pas exécuter de code. Le script du jeu peut décider qui possède quoi au départ, mais il ne peut créer ni terres, ni montagnes, ni fleuves. EU5 n'offre aucun moyen officiel d'ajouter du code au jeu.

C'est donc un petit programme fourni avec cet objet qui crée le monde. Il lit votre installation d'EU5, crée un monde et l'enregistre comme un mod ordinaire. Il ne modifie pas le jeu, ne s'y attache pas et ne tourne pas à l'intérieur. Le contrat d'utilisation de Paradox compte les programmes parmi les contenus que les joueurs peuvent créer et partager gratuitement.

## Mode d'emploi

1. Dans la fenêtre **Mods**, cliquez sur **Ouvrir dans le dossier** pour Random New World, puis double-cliquez sur **Random New World Generator**.
2. Choisissez un type de monde : supercontinent, continents, petits continents, archipel ou îles éparses. Gardez la graine aléatoire, tapez-en une ou collez le code d'un monde. **L'essentiel** règle d'un mot les questions habituelles, comme le Nouveau Monde aléatoire d'EU4 : combien de terres, combien de peuples et d'États autochtones, à quelle fréquence se dresse un grand empire autochtone (jamais, rarement, parfois, souvent), et quelle richesse en or et en argent. Sous **Personnaliser**, chaque valeur se règle : les terres, les côtes, l'échelle de la carte et les peuples autochtones, des grands empires aux États isolés. Toute valeur proposée donne un monde jouable.
3. Cliquez sur **Créer**. En deux ou trois minutes, le monde apparaît comme un nouveau mod dans votre liste, sous un nom comme « RNW: Small continents 7K3Q » (type de monde et repère) ; vous pouvez le renommer dans le générateur. Tant que le Nouveau Monde est caché, son image dans la liste des mods porte le même repère en rouge, pour qu'on distingue les mondes.
4. Dans le jeu, cochez ce monde (un seul monde à la fois) et lancez une nouvelle partie. Si vous avez déjà joué une campagne depuis le lancement d'EU5, relancez d'abord EU5. Le générateur vous dit exactement quoi faire.

Le générateur garde chaque monde que vous avez créé, avec son code. Tant que vous ne choisissez pas de le montrer dans les **Paramètres**, le Nouveau Monde reste terra incognita partout avant que vous y jouiez : sur les images du générateur, dans la liste des mods du jeu et sur la carte de l'écran de nouvelle partie. Un seul réglage désactive tout cela. Le code d'un monde recrée le même monde, octet pour octet, sur n'importe quel ordinateur avec la même version du jeu.

Le générateur parle toutes les langues du jeu et démarre dans celle où Steam lance EU5.

## Ce que fait le programme, et ce qu'il ne fait pas

- Il lit votre installation d'EU5 et n'écrit qu'à deux endroits : dans les mondes qu'il crée (`mod/rnw_world_…` dans le dossier d'EU5 de vos Documents) et dans son propre dossier de données.
- Il n'utilise pas le réseau, ne demande pas les droits d'administrateur, ne touche pas au registre et ne modifie aucun fichier du jeu.
- Son code source est public, sous Mozilla Public License 2.0 : https://github.com/Sir-Starch/eu5-random-new-world. Chaque version est compilée automatiquement à partir d'un commit étiqueté, et la somme de contrôle SHA-256 de chaque fichier y est publiée.
- Faire confiance à un programme, c'est votre décision. Vous pouvez lire le code, comparer les sommes de contrôle ou le compiler vous-même.

## Avertissements de Windows

- Les fichiers que télécharge Steam ne sont pas marqués comme venant d'Internet : Windows SmartScreen ne devrait donc rien demander. [Confirm in 020.]
- Les antivirus signalent parfois les nouveaux programmes qu'ils ne connaissent pas encore. La page de chaque version renvoie vers une analyse VirusTotal.
- Le contrôle intelligent des applications de Windows 11 bloque les programmes sans signature connue, et Windows ne permet aucune exception pour un programme isolé. [Until signed:] Le générateur n'est pas encore signé : avec le contrôle intelligent des applications activé, il ne démarrera pas. [Once signed:] Le générateur et son module natif sont signés par [signer].

## Linux et Steam Deck

Le jeu tourne via Proton. « Ouvrir dans le dossier » ouvre alors l'explorateur de fichiers de Wine, et le même générateur s'y lance, dans le préfixe Proton du jeu lui-même. Rien à installer. [Steam Deck: confirm.]

## Limites

- **Nouvelles campagnes uniquement.** Un monde doit être créé avant le début de la campagne.
- **Créez avant de jouer, sinon relancez.** EU5 plante quand un autre monde démarre après une campagne dans la même session (le plantage vient du moteur du jeu). Créer un monde juste après le lancement d'EU5 ne demande pas de relance ; après une campagne, relancez EU5 avant le nouveau monde.
- **Mises à jour du jeu.** Après une mise à jour d'EU5, il se peut que le générateur refuse de fonctionner jusqu'à ce qu'il soit adapté à la nouvelle version. Il propose alors de recréer votre monde. Les anciennes sauvegardes ont besoin du monde sur lequel elles ont été jouées : recréez-le à partir de son code.
- **Un monde à la fois.** Ne cochez qu'un seul monde créé dans un playset.
- **Multijoueur.** Tous les joueurs utilisent le même code de monde et la même version du jeu.
- **Mémoire.** Environ 7,5 Go de mémoire libre pendant les deux minutes de création. Les 32 Go recommandés pour EU5 suffisent largement.
- **Succès.** Comme les autres mods qui modifient le jeu, il change la somme de contrôle du jeu. [Confirm what EU5 allows.]

## Désinstallation

Supprimez les mondes dans le générateur (**Supprimer le monde**) ou effacez vous-même leurs dossiers, puis désabonnez-vous. Les mondes que vous gardez restent jouables sans le générateur.

## Licence et crédits

Code et fichiers du mod : Mozilla Public License 2.0. Les mondes sont créés sur votre ordinateur à partir de votre copie d'EU5 et ne sont pas diffusés par le Workshop. Europa Universalis V est une marque de Paradox Interactive ; ce mod n'est pas affilié à Paradox Interactive.

# ES-FR Top 1000 Review

- Source file: `app/data/legacy_seed/words/es_fr_top1000.csv`
- Review scope: full pass over the legacy ES/FR seed list
- Result: 63 row updates and 46 duplicate-row removals
- Final data rows: 964 (down from 1010)
- Note: line numbers below refer to the original pre-cleanup CSV so the audit stays stable.

## Updated Rows

| Original line | Spanish | Changes |
| --- | --- | --- |
| 2 | solo | french synonyms: `uniquement` -> `uniquement;seul` |
| 23 | nombre | french synonyms: `prénom;appellation` -> `appellation;désignation` |
| 25 | hombre | french synonyms: `mâle` -> `individu` |
| 28 | sistema | spanish synonyms: `método` -> `método;conjunto`; french synonyms: `méthode;organisation` -> `méthode;organisation;dispositif` |
| 41 | agua | french synonyms: `liquide` -> `` |
| 53 | seguro | french synonyms: `` -> `certain` |
| 61 | seguridad | french synonyms: `` -> `certitude` |
| 75 | obra | french: `oeuvre` -> `œuvre` |
| 79 | música | french synonyms: `mélodie;son` -> `mélodie;chanson` |
| 107 | pequeño | french synonyms: `mince;réduit` -> `menu;réduit` |
| 130 | ropa | french: `vêtement` -> `vêtements`; spanish synonyms: `vestimenta` -> `vestimenta;indumentaria;atuendo` |
| 144 | mesa | french synonyms: `bureau` -> `bureau;comptoir` |
| 155 | memoria | french synonyms: `souvenir;mémoire` -> `souvenir` |
| 161 | hermana | french: `soeur` -> `sœur` |
| 165 | rojo | french synonyms: `roux` -> `rougeâtre` |
| 188 | piedra | french synonyms: `rocher` -> `rocher;caillou` |
| 190 | idioma | french synonyms: `langage` -> `idiome` |
| 195 | leche | french synonyms: `laitage` -> `` |
| 205 | cocina | french synonyms: `kitchenette` -> `` |
| 208 | dulce | french: `doux` -> `sucré`; french synonyms: `sucré` -> `doux` |
| 214 | pensamiento | french synonyms: `réflexion;pensée` -> `réflexion;idée` |
| 215 | claramente | french synonyms: `évidemment` -> `nettement;évidemment` |
| 230 | metro | french synonyms: `métropolitain` -> `` |
| 243 | clima | french synonyms: `météo` -> `` |
| 272 | ruido | spanish synonyms: `sonido` -> `sonido;estruendo`; french synonyms: `son` -> `vacarme;son` |
| 274 | jardín | spanish synonyms: `huerto` -> ``; french synonyms: `potager` -> `` |
| 281 | ventana | french synonyms: `vitre;lucarne` -> `baie vitrée` |
| 290 | huevo | french: `oeuf` -> `œuf` |
| 344 | patrón | french: `schéma;motif` -> `motif`; french synonyms: `` -> `schéma;modèle` |
| 346 | patrón | french: `motif` -> `modèle` |
| 367 | camiseta | spanish synonyms: `playera` -> `remera;playera;franela` |
| 382 | naranja | spanish synonyms: `` -> `anaranjado` |
| 395 | pesado | french synonyms: `` -> `pesant` |
| 412 | esquema | french: `plan;schéma` -> `schéma`; french synonyms: `schéma` -> `plan` |
| 415 | almuerzo | french synonyms: `dîner` -> `` |
| 422 | vaca | french synonyms: `bovin` -> `` |
| 437 | sombrero | spanish synonyms: `` -> `pamela` |
| 451 | nube | spanish synonyms: `cloud` -> `` |
| 456 | envidia | french synonyms: `convoitise` -> `envie` |
| 458 | cinturón | spanish synonyms: `correa;cincho` -> `correa;cincho;cinto` |
| 502 | volante | french synonyms: `guidon` -> `` |
| 511 | nostalgia | french synonyms: `mélancolie` -> `regret` |
| 521 | abrigo | spanish synonyms: `gabán;sobretodo` -> `gabán;sobretodo;tapado` |
| 523 | chaqueta | spanish synonyms: `cazadora;chamarra` -> `cazadora;chamarra;saco` |
| 531 | alfombra | spanish synonyms: `tapete;estera` -> `tapete;estera;moqueta` |
| 569 | toalla | french: `serviette` -> `serviette de toilette` |
| 678 | calabaza | spanish synonyms: `auyama;zapallo;calabacín` -> `auyama;zapallo` |
| 696 | lechuga | french synonyms: `salade` -> `` |
| 749 | enchufe | spanish synonyms: `conector` -> `conector;tomacorriente` |
| 760 | bufanda | spanish synonyms: `pañuelo` -> `pañuelo;chalina` |
| 765 | bombilla | spanish synonyms: `foco;lamparita` -> `foco;lamparita;bombillo` |
| 780 | credencial | french: `carte d'identité` -> `badge`; french synonyms: `` -> `carte d'identification` |
| 794 | enfermero | spanish synonyms: `enfermera` -> `` |
| 859 | trenza | spanish synonyms: `natté` -> ``; french synonyms: `` -> `natte` |
| 861 | bochorno | french: `canicule` -> `chaleur étouffante`; french synonyms: `chaleur étouffante` -> `canicule` |
| 878 | barandilla | french: `barrière de lit` -> `garde-corps`; french synonyms: `garde-corps` -> `rampe;main courante` |
| 886 | merluza | french: `colin` -> `merlu`; french synonyms: `` -> `colin` |
| 926 | lamina | spanish: `lamina` -> `lámina`; french: `lame` -> `feuille`; french synonyms: `feuille` -> `plaque` |
| 944 | plumón | french: `doudoune` -> `couette`; french synonyms: `` -> `édredon` |
| 976 | explicito | spanish: `explicito` -> `explícito`; spanish synonyms: `explícito` -> `` |
| 980 | pescadero | spanish synonyms: `pescador` -> `` |
| 996 | rotulo | spanish: `rotulo` -> `rótulo` |
| 1011 | espinillera | french: `protège-tibia` -> `protège-tibias` |

## Removed Rows

| Original line | Spanish | French | Notes |
| --- | --- | --- | --- |
| 29 | sistema | système | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 126 | isla | île | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 129 | ropa | vêtements | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 187 | piedra | pierre | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 207 | tren | train | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 212 | claramente | clairement | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 265 | vestido | robe | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 267 | ruido | bruit | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 271 | vestido | robe | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 273 | jardín | jardin | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 321 | espejo | miroir | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 326 | urbano | urbain | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 366 | camiseta | T-shirt | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 379 | naranja | orange | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 380 | seco | sec | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 383 | ácido | acide | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 391 | plástico | plastique | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 396 | pesado | lourd | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 409 | camisa | chemise | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 436 | sombrero | chapeau | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 447 | ligero | léger | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 461 | cinturón | ceinture | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 512 | pantalón | pantalon | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 522 | abrigo | manteau | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 524 | chaqueta | veste | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 532 | alfombra | tapis | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 537 | falda | jupe | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 544 | cajón | tiroir | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 556 | armario | armoire | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 563 | cortina | rideau | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 591 | lámpara | lampe | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 596 | gorra | casquette | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 601 | coral | corail | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 602 | gorra | casquette | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 630 | garaje | garage | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 632 | colchón | matelas | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 644 | sótano | sous-sol | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 750 | enchufe | prise | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 761 | bufanda | écharpe | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 766 | bombilla | ampoule | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 775 | narciso | narcisse | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 784 | narciso (flor) | narcisse | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 819 | estante | étagère | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 825 | maletero | coffre | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 863 | cojín | coussin | Removed duplicate or near-duplicate row after merging the surviving entry. |
| 866 | calcetín | chaussette | Removed duplicate or near-duplicate row after merging the surviving entry. |

# Localization (L1)

This document holds what was found about how EU5 writes its texts in its eleven official
languages, the rules the mod and the generator follow when they write theirs, the design of the
translation machinery, and where the work stands. It is written so that someone else can pick L1
up where it was left ([roadmap](roadmap.md) L1; owner's requirement of 2026-10-23, repeated on
2026-10-24: translate everything, improve the English while doing it, keep to the game's style,
and keep the texts free of the marks of machine-written prose).

Evidence is from the local installation: the 1.4.4 executable (Steam build 26142040) on the data
of 1.4.3 (build 26105915), read 2026-10-24 [V-LOCAL C268–C272]. Examples quote single names or a
few words; no game text is committed in bulk (see [legal](legal.md)). Scratch scripts that produced
the comparisons lived in the session's temporary folder and are described below so they can be
rewritten.

## 1. What a player sees

| Where | Source | State before L1 |
|---|---|---|
| Story events, their options, modifiers, privileges | `stories.py`, `stories_n4.py`, `stories_colonial.py` (`storymodel.event_keys`) | English in every language |
| Formable countries: description (`{name}`), founding modifier | `formations.py`, names in `eu5_formation.identities` (`"{seat} {suffix}"`) | English |
| Exceptional places (silver lodes, fishery) | `eu5_places.SPECS` | English |
| Colonial names | `colonial_names.TRADITIONS` (`Nueva {root}`, `New {root}`…) | founder's form in every language |
| Names of water | `seanames.TERMS`, `SECTORS`, `CENTRAL`, `FAR` | English |
| Wastelands, lakes | `eu5_natives.WASTELAND_SUFFIX`, `eu5_newworld.NAME_SUFFIX` (`" Highlands"`, `" Lake"`) | English |
| Proper names (locations, provinces, areas, regions, countries) | `names.NameGenerator`, `eu5_natives.PlaceNamer` (Markov chains over the game's American names) | Latin script in every language |
| Country adjectives `TAG_ADJ` | `eu5_natives.country_names`, `eu5_formation.texts` | the name itself in every language |
| The generator window | `gui/text.py` (about 470 strings), `progress.py` stage names | English only |
| Atlas: names shown in the window's maps | `eu5_atlas.py` (`atlas.json` keeps rendered English strings) | English |
| A world's title in the launcher's mod list | `worldname.py`, `.metadata` | English; whether the list can show another language is [UNKNOWN] |
| Steam Workshop text | `docs/workshop-description.md`, `docs/workshop/<language>.md` | Every language; `tests/test_workshop.py` |

Organizations and governments of the extraordinary societies use vanilla types and their vanilla
names, so they need nothing. Technical error details from deep in the export stay English (they
are for bug reports); what the window says around them is translated.

The amount of prose is modest: about 19,000 characters of game text (236 keys) and about 15,000
characters of window text [V-EXEC 2026-10-24, counted from the modules].

## 2. Observations from the installed game

### 2.1 Languages and files [V-LOCAL C268]

`game/main_menu/localization/` has eleven folders: `braz_por`, `english`, `french`, `german`,
`japanese`, `korean`, `polish`, `russian`, `simp_chinese`, `spanish`, `turkish`.
`languages.official_languages` already reads them from the installation. Files are UTF-8 with BOM,
`l_<language>:` header, ` key: "text"`; paragraph breaks are the two characters `\n`.

### 2.2 Which language the player uses [V-LOCAL C269]

The game's language is Steam's per-game language: `steamapps/appmanifest_3450310.acf`,
`"UserConfig" { "language" "english" }` (also `MountedConfig`). Steam names differ from the
game's folders: `brazilian` → `braz_por`, `schinese` → `simp_chinese`, `koreana` → `korean`,
`latam` → `spanish`; the others are equal. This answers the roadmap's open question of which
language the window starts in: the app manifest of the library the game is installed in (the
game folder's `../../appmanifest_3450310.acf`), else the system locale, and a manual choice in the
window that is remembered. `pdx_settings.json` does not hold it (roadmap, [V-LOCAL]).

### 2.3 Proper names are transliterated in four languages [V-LOCAL C270]

The game's own American location names are written in the script of the language in Russian
(Cyrillic), Japanese (katakana), Korean (hangul) and Simplified Chinese (characters chosen for
their sound), and kept in their Latin spelling in the other six (Turkish and Polish too, with
rare exceptions). Example: *Kangiqsualujjuaq* is `Кангиксуалуджуак`,
`カンギクスアルージュアック`, `캥그프샬루주악`, `康吉克苏阿卢朱瓦克`; *Tenōchtitlan* is
`Теночтитлан`, `テノチティトラン`, `테노치티틀란`, `特诺奇蒂特兰`. All 6,167 locations of the
continent `america` have a name in each of the four [V-LOCAL]. Our names are drawn from Markov
chains over exactly these names, so these pairs are the reference a transliterator is measured
against.

How to rebuild the reference: read `in_game/map_data/definitions.txt` with
`rnw.geography.read_locations`, keep `continent == "america"`, and pair the English
`location_names/*.yml` value of each key with the value in `russian`, `japanese`, `korean`,
`simp_chinese`. Keep the pairs under `local_data/` only.

Observed conventions:

- **Russian**: practical transcription, not letter-for-letter: `qu`/`c` → к, `x` (Nahuatl) → ш,
  `tl` → тль at the end (`Otomitl` → `Отомитль`), `ll` → ль/й, `j` → ж or х by the source language,
  `w` → у/в, doubled vowels collapse (`Niineniiniicie` → `Нинениничиэ`), final `-e` after a vowel →
  э, apostrophes and glottal stops vanish, diacritics drop (`Tōllān` → `Тольян`), ё is written.
- **Japanese**: katakana with long vowels as ー where the source has a doubled or accented vowel,
  `・` between words (`Utugo Kuri Doge` → `ウツゴ・クリ・ドージェ`), final consonants as ック/ト/ン/ル.
- **Korean**: hangul syllables with final consonants as batchim (`Tenochtitlan` → `테노치티틀란`),
  words separated by a space.
- **Chinese**: standard transliteration characters (Xinhua table style: 巴, 卡, 特, 纳, 马, 拉,
  萨, 塔, 尼, 科…), a final consonant as its own syllable (克, 特, 斯, 尔), no separator.

### 2.4 Geographic names [V-LOCAL C271]

The game writes a generic word with a proper name. The patterns, from its own names (sea, gulf,
bay, strait, channel, sound, coast, cape, island, islands, archipelago, ocean, lake, highlands):

| | Pattern for a foreign proper name | Notes |
|---|---|---|
| Russian | **term first, capitalised, name in the nominative**: `Море Лабрадор`, `Залив Джорджиан-Бей`, `Остров Санак`, `Озеро Виктория`, `Возвышенность Огоки` | established names use adjectives (`Гудзонов залив`); generated ones take the apposition. A part of a body: `Западная часть Сингапурского пролива`, `Северная часть Тихого океана` |
| German | compounds and `von`: `Labradorsee`, `Golf von Mexiko`, `Straße von Gibraltar`, `Kap Mount`, `Prinz-Eduard-Insel`, `Chumphon-Archipel`, `Hochland von Kamerun`, `Victoriasee` | a part: `Östliche Straße von Singapur`, `Ost-James-Bay`, `Meer von Westgrönland` |
| French | `Mer du Labrador`, `Golfe de Guinée`, `Baie d'Hudson`, `Île-du-Prince-Édouard`, `Lac Victoria`, `Hauts-Plateaux du Cameroun` | adjectives follow and agree: `Baie James orientale`, `Mer du Groenland occidental`; elision `d'` before a vowel |
| Spanish | `Mar de Labrador`, `Golfo de México`, `Bahía de Hudson`, `Isla del Príncipe Eduardo`, `Lago Victoria`, `Cabo Verde` | `Mar de Groenlandia Occidental`, `Costa Este`; Spanish compass adjectives agree only in number |
| Portuguese (Brazil) | `Mar do Labrador`, `Golfo do México`, `Baía de Hudson`, `Ilha …`, `Lago …`, `Litoral …`, `Planaltos de …` | `Atlântico Norte`, `Litoral Leste` |
| Polish | `Morze …`, `Zatoka …`, `Wyspa …`, `Jezioro …`, `Kanał …`, `Archipelag …`, `Wyżyny …` | adjectives precede and agree: `Zachodnie Morze Grenlandzkie`, `Wschodnia Zatoka Jamesa`; many names are left in English |
| Turkish | `… Denizi`, `… Körfezi`, `… Koyu`, `… Boğazı`, `… Kanalı`, `… Kıyısı`, `… Adası`, `… Adaları`, `… Takımadaları`, `… Okyanusu`, `… Gölü`, `… Yaylası` | compass words precede, invariable: `Batı Grönland Denizi`, `Kuzey Atlas Okyanusu`; many names left in English |
| Japanese | term glued after the name: `…海`, `…湾`, `…海峡`, `…海岸`, `…島`, `…諸島`, `…群島`, `…洋`, `…湖`, `…高地`/`…高原`, `…岬` | a part as a suffix: `ジェームズ湾東部`, `シンガポール海峡西部` |
| Korean | glued: `…해`, `…만`, `…섬`, `…곶`, `…호`, `…양`; spaced: `… 해협`, `… 해안`, `… 제도`, `… 군도`, `… 고원` | compass word before: `동부 제임스만`, `서대서양` |
| Chinese | glued: `…海`, `…湾`, `…海峡`, `…海岸`, `…岛`, `…群岛`/`…诸岛`, `…洋`, `…湖`, `…高地`, `…角` | `西格陵兰海` (prefix) or `新加坡海峡东段` (suffix) |

### 2.5 Country adjectives [V-LOCAL C272]

Vanilla `TAG_ADJ` is not the same kind of thing in every language, because the game's texts build
on it differently:

- **Russian**: a stem the text completes: `[COUNTRY.GetAdjectiveWithNoTooltip]ие революционеры`,
  `[...GetAdjective|l]ий народ`. For native names: consonant + `ск` (`Сакатлан` → `Сакатланск`,
  `Шиллук` → `Шиллукск`); `-и` → `-ийск` (`Осакиваки` → `Осакивакийск`); `-а`/`-о` after a consonant
  drop the vowel (`Сома` → `Сомск`, `Умохо` → `Умохск`); `-а` after a vowel → `-анск`
  (`Тоа` → `Тоанск`); `-я` → `-йск` (`Мия` → `Мийск`); `-у`, `-е`, `-э`, `-й` + `ск`. Vanilla is not
  fully regular; these are its majority rules.
- **Polish**: a stem that takes `-ki`/`-ka`/`-kie` (`#L [TARGET_COUNTRY.GetAdjective]ki#! naród`):
  `-n` → `-ńs` (`Zacatlańs`), a final vowel + `ńs` (`Mpanguńs`, `Umohońs`, `Eufaulańs`), `-k` → `-c`
  (`Shilluc`), other consonants + `s` (`Cocoms`).
- **German**: a full adjective in `-isch` that texts decline (`[...|U]e Freibeuter`): consonant +
  `isch`; `-a` mostly + `nisch` (`Sōmanisch`, `Nawanisch`); `-i` + `sch` (`Warsangalisch`);
  `-e` → `-isch` (`Tionontatisch`) but `-ee`/`-é` + `isch`; `-o`, `-u` + `isch`.
- **French, Spanish, Portuguese, Turkish**: the name itself (`Chén`, `Haudenosaunee`), as ours.
- **Japanese, Korean, Chinese**: the transliterated name.

### 2.6 Russian declension of country names [V-LOCAL]

Russian vanilla texts decline countries through customizable localization
(`in_game/common/customizable_localization/ru_EU5_custom_loc.txt`: `CL_GEN`, `CL_DAT`, `CL_ACC`,
`CL_INST`, `CL_PREP`, endings `end_fem` and others), one entry per vanilla tag and a fallback
(`default_RU_GEN_CL: "державы [ROOT.GetCountry.GetName]"`, `default_RU_end_fem_CL: "а"`). A
generated tag gets the fallback, which reads correctly: the generic noun is declined and the name
stays in the nominative. **Nothing needs to be written for it.** Our own Russian prose uses the
same device (`в городе [target_location.GetNameWithNoTooltip]`, `послы державы [target_country.GetName]`)
so that no generated name ever has to be declined.

### 2.7 Colonial names

Vanilla `scripted_country_names` translate the "new" of a colonial name into the language of the
interface: English `New Spain`, Russian `Новая Испания`, German `Neuspanien`, Spanish
`Nueva España`, Polish `Nowa Hiszpania`, Turkish `Yeni İspanya`; Japanese keeps the founder's form
in katakana (`ヌエバ・エスパーニャ`, `ニューヨーク`); established names stay (`Нью-Йорк`).

### 2.8 Event style per language

From the game's own events (economy and others):

- **English**: narration often in the country's voice (*we*, *our*), scripted names in brackets
  (`[ROOT.GetCountry.GetName]`, `[target_location.GetName]`), options short; some are commands
  (*Side with the university.*), many are lines spoken by the court (*That is why it is called free
  trade.*, *Luddites!*, *This will put Augsburg on the map!*). Titles are short noun phrases.
- **German**: options in the plural imperative (*Ermittelt und ersetzt die Schuldigen umgehend.*) or
  *Sollen sie …*; quotation marks „…“.
- **French**: first person plural (*Enquêtons et remplaçons…*, *laissons-les se retirer*); a space
  before `! ? : ;`.
- **Spanish**: first person plural subjunctive (*Investiguemos…*, *Dejemos que…*); «…».
- **Portuguese (Brazil)**: third person plural imperative (*Investiguem e substituam…*,
  *Deixem-nos…*). Avoid quotation marks: the game's own file shows `&quot;`.
- **Polish**: infinitives (*Rozpocząć śledztwo…*, *Pozwolić im…*); dash –.
- **Turkish**: jussive passive (*Soruşturma yapılsın…*) or plural imperative (*Bırakın…*).
- **Russian**: infinitive or imperative, often with an exclamation (*Немедленно выявить…!*,
  *Пусть себе уходят на покой.*); «…», —, ё.
- **Japanese**: narration in plain *da/dearu* style; options as plain commands or will
  (*…交代させろ。*, *見逃してやろう。*); 「…」.
- **Korean**: narration in the formal *-습니다* style; options in the plain command form
  (*…물갈이하라.*, *…물러나게 해라.*).
- **Chinese**: short, plain; full-width punctuation, “…”.

### 2.9 The game's own words for its interface [V-LOCAL]

Where the generator names a part of the game's interface, it uses the game's word in that
language (`MODS_GUI_TAB_MODS`, `MOD_OPEN_IN_FOLDER`, `SETTINGS_CATEGORY_PLAYSETS` and others):

| | Playset | Mods | Open in Folder |
|---|---|---|---|
| Russian | набор (модов) | Модификации | Открыть в папке |
| German | Gruppe | Mods | Ordner öffnen |
| French | playset | Mods | Ouvrir dans le dossier |
| Spanish | colección | Mods | Abrir en carpeta |
| Portuguese (Brazil) | Condição de Jogo | Mods | Abrir na pasta |
| Polish | zestaw modów | Mody | Otwórz w folderze |
| Turkish | oynanış seti | Modlar | Klasörde Aç |
| Japanese | プレイセット | MOD | フォルダで開く |
| Korean | 플레이세트 | 모드 | 폴더에서 열기 |
| Chinese | 播放集 | 模组 | 在文件夹中打开 |

## 3. Rules for writing

### 3.1 Every language

1. Write as the game writes (§2.8): concrete, a little dry, of its period; no modern words
   (*stakeholder*, *infrastructure*, *strategy*), no game mechanics in prose (*+10% tax*).
2. Never change scripted tokens: `[target_location.GetNameWithNoTooltip]`, `[target_country.GetName]`,
   `[other_location.GetNameWithNoTooltip]`, `[ROOT.GetCountry.GetFlavorRank]`, `$KEY$`, `{name}`.
   The check compares their sets with the English.
3. No straight double quote `"` inside a text (the file format); use the language's own marks.
4. Russian, Polish and other inflected languages: put a generic noun before a generated name so the
   name stays in the nominative (§2.6): *в городе X*, *w mieście X*, *послы державы X*.
5. A translation is a rewrite in the target language, not a calque: the sentence order, the idiom,
   the length follow the target language. If the English is weak, fix the English first.

### 3.2 Marks of machine-written prose to avoid

Collected from [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
(accessed 2026-10-24) and Russian guides ([Хабр, Bothub](https://habr.com/ru/companies/bothub/articles/1085684/),
[goodtarget](https://goodtarget.ru/proverka-teksta-na-ii/priznaki/), [Skillbox](https://skillbox.ru/media/education/kak-prepodavatelyu-ponyat-chto-tekst-sgenerirovan-neyrosetyu/)):

- inflated significance (*a testament to*, *pivotal*, *enduring legacy*, *rich tapestry*,
  *важную роль*, *уникальный*), and a closing clause that explains what the scene "means";
- the AI vocabulary: *delve*, *foster*, *bolster*, *showcase*, *underscore*, *vibrant*, *intricate*,
  *robust*, *crucial*, *Additionally* at the start; in Russian *стоит отметить*, *важно понимать*,
  *в современном мире*, *играет ключевую роль*;
- *serves as* / *stands as* instead of *is*;
- the rule of three everywhere, and negative parallelism (*not just X, but Y*; *не просто X, а Y*);
- the same rhetorical device in event after event (the draft repeated *They agree that … and agree
  on nothing else*; the *X say A. Y say B.* antithesis appeared five times);
- sentences of one length in a row; every paragraph built the same way;
- vague attribution (*some say*, *many believe*) where the text could name who says it;
- Title Case and bold where the game has none; curly quotes in English; emoji.

The test: read the text aloud as a line in the game. If it sounds like a brochure, a summary or a
moral, rewrite it.

### 3.3 Generated names in each language

Rules for the `Phrase` renderer (§4.2):

| Kind | en | ru | de | fr | es | pt | pl | tr | ja | ko | zh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sea | `{n} Sea` | `Море {n}` | `{n}-Meer` | `Mer de {n}` | `Mar de {n}` | `Mar de {n}` | `Morze {n}` | `{n} Denizi` | `{n}海` | `{n}해` | `{n}海` |
| ocean | `{n} Ocean` | `Океан {n}` | `{n}-Ozean` | `Océan {n}` | `Océano {n}` | `Oceano {n}` | `Ocean {n}` | `{n} Okyanusu` | `{n}洋` | `{n}양` | `{n}洋` |
| gulf | `Gulf of {n}` | `Залив {n}` | `Golf von {n}` | `Golfe de {n}` | `Golfo de {n}` | `Golfo de {n}` | `Zatoka {n}` | `{n} Körfezi` | `{n}湾` | `{n}만` | `{n}湾` |
| bay | `{n} Bay` | `Бухта {n}` | `{n}-Bucht` | `Baie de {n}` | `Bahía de {n}` | `Baía de {n}` | `Zatoka {n}` | `{n} Koyu` | `{n}湾` | `{n}만` | `{n}湾` |
| strait | `{n} Strait` | `Пролив {n}` | `Straße von {n}` | `Détroit de {n}` | `Estrecho de {n}` | `Estreito de {n}` | `Cieśnina {n}` | `{n} Boğazı` | `{n}海峡` | `{n} 해협` | `{n}海峡` |
| channel | `{n} Channel` | `Канал {n}` | `{n}-Kanal` | `Canal de {n}` | `Canal de {n}` | `Canal de {n}` | `Kanał {n}` | `{n} Kanalı` | `{n}水道` | `{n} 수로` | `{n}水道` |
| sound | `{n} Sound` | `Губа {n}` | `{n}-Sund` | `Passe de {n}` | `Paso de {n}` | `Passagem de {n}` | `Przesmyk {n}` | `{n} Geçidi` | `{n}入江` | `{n} 해협` | `{n}海湾` |
| coast | `{n} Coast` | `Побережье {n}` | `{n}-Küste` | `Côte de {n}` | `Costa de {n}` | `Costa de {n}` | `Wybrzeże {n}` | `{n} Kıyısı` | `{n}海岸` | `{n} 해안` | `{n}海岸` |
| cape | `Cape {n}` | `Мыс {n}` | `Kap {n}` | `Cap {n}` | `Cabo {n}` | `Cabo {n}` | `Przylądek {n}` | `{n} Burnu` | `{n}岬` | `{n}곶` | `{n}角` |
| island | `{n} Island` | `Остров {n}` | `Insel {n}` | `Île {n}` | `Isla {n}` | `Ilha {n}` | `Wyspa {n}` | `{n} Adası` | `{n}島` | `{n}섬` | `{n}岛` |
| islands | `{n} Islands` | `Острова {n}` | `{n}-Inseln` | `Îles {n}` | `Islas {n}` | `Ilhas {n}` | `Wyspy {n}` | `{n} Adaları` | `{n}諸島` | `{n} 제도` | `{n}诸岛` |
| archipelago | `{n} Archipelago` | `Архипелаг {n}` | `{n}-Archipel` | `Archipel de {n}` | `Archipiélago de {n}` | `Arquipélago de {n}` | `Archipelag {n}` | `{n} Takımadaları` | `{n}群島` | `{n} 군도` | `{n}群岛` |
| highlands | `{n} Highlands` | `Нагорье {n}` | `Hochland von {n}` | `Hautes Terres de {n}` | `Tierras Altas de {n}` | `Planalto de {n}` | `Wyżyna {n}` | `{n} Yaylası` | `{n}高地` | `{n} 고원` | `{n}高地` |
| lake | `Lake {n}` | `Озеро {n}` | `{n}-See` | `Lac {n}` | `Lago {n}` | `Lago {n}` | `Jezioro {n}` | `{n} Gölü` | `{n}湖` | `{n}호` | `{n}湖` |

`{n}` is the proper name as that language writes it (§2.3). French `de` becomes `d'` before a vowel
or `h`. German hyphenates the compound because generated names carry apostrophes and diacritics.

Parts of one body (`seanames._share_body`: eight compass points, *Central*, repeated *Far*):

- ru: `Северная часть моря {n}` (`часть` + the term in the genitive: моря, океана, залива,
  бухты); central `Центральная часть`, far `Дальняя северная часть`;
- de: a strong adjective agreeing with the term's gender, before it: `Nördliches {n}-Meer`,
  `Nördlicher Golf von {n}`, `Nördliche {n}-Bucht`; central `Mittleres/-er/-e`, far `Äußeres/-er/-e`
  before the compass adjective;
- fr: `… du Nord`, `du Nord-Est`, `de l'Est`, `du Sud-Est`, `du Sud`, `du Sud-Ouest`, `de l'Ouest`,
  `du Nord-Ouest`, central `du Centre`, far `de l'Extrême-Nord` etc.;
- es: `Mar de {n} Septentrional` (`Nororiental`, `Oriental`, `Suroriental`, `Meridional`,
  `Suroccidental`, `Occidental`, `Noroccidental`, `Central`; far adds `Exterior`), plural `-es`;
- pt: `Mar de {n} Norte` (`Nordeste`, `Leste`, `Sudeste`, `Sul`, `Sudoeste`, `Oeste`, `Noroeste`,
  `Central`, far `Exterior`);
- pl: an adjective agreeing with the term, before it: `Północne Morze {n}`, `Północna Zatoka {n}`,
  `Północny Kanał {n}`; `Wschodni/-ia/-ie`, `Zachodni/-ia/-ie`, `Południowy/-a/-e`,
  `Północno-Wschodni` …, central `Środkowy/-a/-e`, far `Daleki/-a/-ie`;
- tr: invariable before: `Kuzey`, `Kuzeydoğu`, `Doğu`, `Güneydoğu`, `Güney`, `Güneybatı`, `Batı`,
  `Kuzeybatı`, central `Orta`, far `Uzak`;
- ja: suffix `北部`, `北東部`, `東部`, `南東部`, `南部`, `南西部`, `西部`, `北西部`, central `中部`,
  far `最北部` etc.;
- ko: prefix `북부`, `북동부`, `동부`, `남동부`, `남부`, `남서부`, `서부`, `북서부`, central `중부`,
  far `외곽` before it;
- zh: suffix `北部`, `东北部`, `东部`, `东南部`, `南部`, `西南部`, `西部`, `西北部`, central `中部`,
  far `远` before the compass part.

Country adjectives follow §2.5. Formable names use the adjective where the language builds names
that way: ru `Кайрский союз` (stem + `ий`/`ая`/`ое`: союз m, конфедерация f, лига f,
содружество n, держава f, федерация f), de `Kairische Union` (adjective + `e`/`er`/`es`), pl
`Unia Kairska`; elsewhere a genitive or compound: fr `Union de Kaira`, es `Unión de Kaira`,
pt `União de Kaira`, tr `Kaira Birliği` (league `Kaira Ligi`, federation `Kaira Federasyonu`,
confederation `Kaira Konfederasyonu`, commonwealth `Kaira Topluluğu`, realm `Kaira Devleti`),
ja/zh glued (`…連合`, `…联盟`…), ko spaced.

Colonial names (§2.7): ru `Новая {n}` / `Новый {n}` by the name's ending (`-а`/`-я` feminine,
otherwise masculine), de `Neu-{n}`, fr `Nouvelle-{n}` (`-a`/`-e` endings) or `Nouveau-{n}`,
es `Nueva`/`Nuevo` (`-o` masculine), pt `Nova`/`Novo`, pl `Nowa`/`Nowy`, tr `Yeni {n}`, zh `新{n}`;
ja and ko keep the founder's word in their script (`ヌエバ・`, `ノヴァ・`, `ニュー・`,
`ヌーヴェル・`, `ニーウ・`; `누에바 `, `노바 `, `뉴 `, `누벨 `, `니우 `). English keeps the founder's
form (`Nueva {n}`, `New {n}`, `Nouvelle-{n}`), as N4c chose.

## 4. Design

### 4.1 Catalogs

- `src/rnw/locale/<language>/game.toml` (world mod) and `window.toml` (generator), one table per
  key: `source` is the first 16 hex digits of the SHA-256 of the English text, `text` the
  translation. English lives in the code, where it is written; the catalogs hold the other ten.
- `rnw.translations.translate(domain, language, sources)` returns the texts of a language and
  raises on a missing or stale entry; English returns the sources. A language the game ships but
  the generator has no catalog for is written in English and recorded in the export's statistics
  (`untranslated_languages`) and fails the local release check, so a patch that adds a language
  does not break generation but cannot be released past.
- The release check (`tests/test_translations.py`): every source key in every catalog language,
  every hash current, the same scripted tokens (`[...]`, `$...$`, `{...}`), no `"` in a text, no
  orphan keys; with `EU5_GAME_DIR`, every official language of the installation has catalogs.
- Packaging: the TOML files must reach the wheel (maturin includes package data) and the
  PyInstaller folder (`packaging/rnw.spec` datas); a test reads them through `importlib.resources`.

### 4.2 Phrases instead of English strings

Composed names are kept as data until the files are written:
`Phrase(term, word, sectors=())`, for example `Phrase("gulf", "Kaira", ("north",))`; a bare `str`
is a proper name. `seanames`, `eu5_newworld`, `eu5_natives` (wasteland), `eu5_formation` and
`colonial_names` return phrases; `eu5_nw_export._localization` and `eu5_story.build` render each
key once per language with `rnw.wording` (patterns of §3.3, transliteration of §2.3, adjectives
of §2.5). `$key$` references (the game's ocean areas) are a phrase of their own and render
unchanged. The atlas stores phrases in a structured form (format 2) so the window renders names in
its own language; format 1 atlases keep their English strings.

### 4.3 Transliteration

Rule-based, one function per script (`cyrillic`, `katakana`, `hangul`, `hanzi`) in
`rnw/translit.py`: normalise (strip diacritics, apostrophes, collapse doubled vowels as the game
does), segment into the source's digraphs (`tl`, `tz`, `ts`, `ch`, `sh`, `kw`, `qu`, `hu`+vowel,
`ll`, `ng`, `gg`…), then map syllables. Measured against the reference pairs of §2.3 for
agreement and, more importantly, read by eye for naturalness; the measured agreement is recorded
as a claim, not used as a gate.

## 5. Status and next steps

Done (2026-10-24):

- the inventory (§1), the observations (§2), the rules (§3), the design (§4);
- **the world's mod (0.11.5, epoch 29):** `translations.py` with catalogs for the ten languages
  besides English (`src/rnw/locale/<language>/game.toml`, 252 texts each) and the release check
  (`tests/test_translations.py`); the English of the stories, formables and places rewritten
  against §3.2 before translation (the repeated *agree on nothing else* device, five *X say A, Y
  say B* antitheses, vague *some/others*, the country's voice brought in as the game writes it;
  every option keeps its order and effects); `translit.py` (§2.3; agreement with the game's own
  spellings of 4,107 one-word American names: Russian 52 %, Japanese 49 %, Korean 58 %, Chinese
  49 %, C273); `wording.py` (§3.3): water, highlands, lakes, compass parts, country adjectives,
  formable names and colonial names in every language; the names travel as phrases through
  `seanames`, `eu5_newworld`, `eu5_natives`, `eu5_formation` and `colonial_names`, and
  `game_texts.localize` writes each key once per language. The token
  `[ROOT.GetCountry.GetFlavorRank]` left the English of *A Priesthood With a Seat*: its gender
  varies by rank and no Russian, German or Polish sentence could agree with it.

- **the window (0.11.6):** the window speaks the player's choice, else the game's language (Steam's
  app manifest, `discovery.game_language`), else the system's (`gui/text.py`: `choose_language`,
  `set_language`; a menu in Settings, effective at the next start); 441 strings in ten languages
  (`window.toml`: the window's strings, the export's stages, and the generator's messages to the
  player, `rnw/messages.py`, raised with `say(key)` so the command line and the log keep English
  and the window writes them in its language; a damaged world file or settings get a translated
  lead with the English detail); numbers grouped as each language groups them; the atlas in
  format 2 keeps names as phrases, and the window writes them in its language, with the game's
  own names of cultures, religions, materials and lands when the game is installed
  (`app/gamenames.py`; Russian and Polish culture stems completed as adjectives of *culture*).
  `tests/test_window.py` checks that every language fits the smallest supported window.

- **the Workshop description:** `docs/workshop/<language>.md` for the ten languages, each
  recording the fingerprint of the English below the line of `docs/workshop-description.md`;
  the window's words for its controls and the game's for its interface (§2.9); our bracketed
  notes stay English for whoever uploads. `tests/test_workshop.py` fails on a missing or
  outdated translation and on a lost note, link, path or section. Change the English, then every
  translation, then the fingerprints.
- **the metadata:** a mod's `metadata.json` holds one title and one description, with no field
  for another language (C276, interoperability R-003). The hub's and the worlds' stay English;
  the Workshop's own title and description per language are set at upload, and whether the game's
  list shows them is [UNKNOWN].

Next:

1. Owner review in game and in the window (roadmap gate), in a sitting held for other reasons;
   native readers for the Workshop texts before the upload, if any can be found.

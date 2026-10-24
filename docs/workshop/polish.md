<!-- source: c1b2511ee47c687e -->

## Random New World

Generator Nowych Światów do Europa Universalis V. Tworzy obie Ameryki od nowa: kontynenty, wybrzeża, rzeźbę terenu, klimat, rzeki, roślinność, surowce, prowincje i ludy tubylcze, a Stary Świat zostawia takim, jakim zrobił go Paradox. **Każdy stworzony świat to osobny, kompletny mod z mapą.** Działa sam: trzymaj tyle światów, ile chcesz, kasuj je albo udostępniaj kod świata. Do gry generator nie jest potrzebny, a każdy, kto ma tę samą wersję gry, dostanie z kodu ten sam świat.

Tego przedmiotu nie włączasz w żadnym zestawie modów. Zawiera tylko generator.

## Skąd w tym przedmiocie program

EU5 buduje mapę z plików, gdy wczytuje mody. Mod to dane: nie może uruchamiać kodu. Skrypt gry może ustalić, kto co posiada na początku, ale nie stworzy lądu, gór ani rzek. EU5 nie ma oficjalnego sposobu na dodanie do gry własnego kodu.

Dlatego świat tworzy mały program dołączony do tego przedmiotu. Czyta twoją instalację EU5, tworzy świat i zapisuje go jako zwykły mod. Nie zmienia gry, nie podłącza się do niej i nie działa w jej wnętrzu. Umowa użytkownika Paradoxu zalicza programy do treści, które gracze mogą tworzyć i udostępniać za darmo.

## Jak go używać

1. W oknie **Mody** kliknij **Otwórz w folderze** przy Random New World i kliknij dwukrotnie **Random New World Generator**.
2. Wybierz rodzaj świata: superkontynent, kontynenty, małe kontynenty, archipelag albo rozsiane wyspy. Zostaw losowe ziarno, wpisz własne albo wklej kod świata. **Podstawy** odpowiadają jednym słowem na zwykłe pytania, jak losowy Nowy Świat w EU4: ile lądu, ile ludów i państw tubylczych, jak często powstaje wielkie imperium tubylcze (nigdy, rzadko, czasem, często) i ile jest złota i srebra. W **Dostosuj** zmienisz każdą wartość: ląd, wybrzeża, skalę mapy i ludy tubylcze, od wielkich imperiów po samotne państwa. Każda proponowana wartość daje grywalny świat.
3. Kliknij **Utwórz**. Po dwóch, trzech minutach świat pojawi się jako nowy mod na twojej liście, pod nazwą w rodzaju „RNW: Small continents 7K3Q” (rodzaj świata i znacznik); w generatorze możesz zmienić mu nazwę. Dopóki Nowy Świat jest zakryty, jego obrazek na liście modów nosi ten sam znacznik na czerwono, żeby światy się nie myliły.
4. W grze zaznacz ten świat (tylko jeden świat naraz) i zacznij nową grę. Jeśli od uruchomienia EU5 rozegrano już kampanię, najpierw uruchom EU5 ponownie. Generator dokładnie podpowie, co zrobić.

Generator przechowuje każdy stworzony przez ciebie świat razem z kodem. Dopóki nie włączysz jego pokazywania w **Ustawieniach**, Nowy Świat przed grą wszędzie pozostaje terra incognita: na obrazkach generatora, na liście modów gry i na mapie ekranu nowej gry. Jedno ustawienie wyłącza to wszystko. Kod świata odtwarza ten sam świat, bajt w bajt, na każdym komputerze z tą samą wersją gry.

Generator mówi we wszystkich językach gry i uruchamia się w tym, w którym Steam uruchamia EU5.

## Co program robi, a czego nie

- Czyta twoją instalację EU5 i zapisuje tylko w dwóch miejscach: w tworzonych światach (`mod/rnw_world_…` w folderze EU5 w „Dokumentach”) i we własnym folderze danych.
- Nie łączy się z siecią, nie potrzebuje uprawnień administratora, nie rusza rejestru i nie zmienia żadnego pliku gry.
- Jego kod źródłowy jest publiczny, na licencji Mozilla Public License 2.0: https://github.com/Sir-Starch/eu5-random-new-world. Każde wydanie jest budowane automatycznie z oznaczonego commita, a suma kontrolna SHA-256 każdego pliku jest tam publikowana.
- Czy ufasz programowi, decydujesz ty. Możesz przeczytać kod, porównać sumy kontrolne albo zbudować go samodzielnie.

## Ostrzeżenia systemu Windows

- Pliki pobrane przez Steam nie są oznaczane jako pochodzące z internetu, więc Windows SmartScreen nie powinien o nic pytać. [Confirm in 020.]
- Programy antywirusowe czasem reagują na nowe programy, których jeszcze nie znają. Strona każdego wydania ma link do skanu VirusTotal.
- Inteligentna kontrola aplikacji w Windows 11 blokuje programy bez znanego podpisu, a Windows nie pozwala na wyjątek dla pojedynczego programu. [Until signed:] Generator nie jest jeszcze podpisany, więc przy włączonej inteligentnej kontroli aplikacji się nie uruchomi. [Once signed:] Generator i jego moduł natywny są podpisane przez [signer].

## Linux i Steam Deck

Gra działa przez Proton. „Otwórz w folderze” otwiera wtedy menedżer plików Wine, a ten sam generator działa tam, w prefiksie Protona samej gry. Nie trzeba niczego instalować. [Steam Deck: confirm.]

## Ograniczenia

- **Tylko nowe kampanie.** Świat trzeba stworzyć przed rozpoczęciem kampanii.
- **Najpierw stwórz świat albo uruchom grę ponownie.** EU5 się wysypuje, gdy w tej samej sesji po kampanii startuje inny świat (błąd leży w silniku gry). Świat stworzony zaraz po uruchomieniu EU5 nie wymaga restartu; po kampanii uruchom EU5 ponownie przed nowym światem.
- **Aktualizacje gry.** Po aktualizacji EU5 generator może odmówić działania, dopóki nie zostanie dostosowany do nowej wersji. Wtedy zaproponuje odtworzenie twojego świata. Stare zapisy potrzebują świata, na którym je grano: odtwórz go z kodu.
- **Jeden świat naraz.** W zestawie modów zaznacz tylko jeden stworzony świat.
- **Gra wieloosobowa.** Wszyscy gracze używają tego samego kodu świata i tej samej wersji gry.
- **Pamięć.** Około 7,5 GB wolnej pamięci na dwie minuty tworzenia świata. Zalecane dla EU5 32 GB wystarczają z zapasem.
- **Osiągnięcia.** Jak inne mody zmieniające grę, zmienia jej sumę kontrolną. [Confirm what EU5 allows.]

## Jak usunąć

Skasuj światy w generatorze (**Skasuj świat**) albo ręcznie usuń ich foldery, a potem anuluj subskrypcję. Światy, które zostawisz, da się grać bez generatora.

## Licencja i twórcy

Kod i pliki moda: Mozilla Public License 2.0. Światy powstają na twoim komputerze z twojej kopii EU5 i nie są rozpowszechniane przez Warsztat. Europa Universalis V jest znakiem towarowym Paradox Interactive; ten mod nie jest powiązany z Paradox Interactive.

<!-- source: c1b2511ee47c687e -->

## Random New World

Ein Generator für Neue Welten in Europa Universalis V. Er erschafft Amerika neu: Kontinente, Küsten, Relief, Klima, Flüsse, Vegetation, Rohstoffe, Provinzen und indigene Völker. Die Alte Welt bleibt, wie Paradox sie gebaut hat. **Jede Welt, die er erzeugt, ist ein eigener, vollständiger Karten-Mod.** Sie läuft für sich allein: Behalten Sie so viele Welten, wie Sie wollen, löschen Sie sie oder teilen Sie den Code einer Welt. Zum Spielen braucht die Welt den Generator nicht, und wer dieselbe Spielversion hat, erzeugt aus dem Code dieselbe Welt.

Diesen Workshop-Inhalt aktivieren Sie in keiner Gruppe. Er enthält nur den Generator.

## Warum hier ein Programm dabei ist

EU5 baut seine Karte beim Laden der Mods aus Dateien. Ein Mod besteht aus Daten: Er kann keinen Code ausführen. Das Skript des Spiels kann festlegen, wem zu Beginn was gehört, aber es kann kein Land, keine Gebirge und keine Flüsse erschaffen. Einen offiziellen Weg, dem Spiel Code hinzuzufügen, gibt es in EU5 nicht.

Deshalb erzeugt ein kleines Programm, das diesem Inhalt beiliegt, die Welt. Es liest Ihre EU5-Installation, erzeugt eine Welt und speichert sie als gewöhnlichen Mod. Es verändert das Spiel nicht, hängt sich nicht hinein und läuft nicht darin. Die Nutzungsvereinbarung von Paradox zählt Programme zu den Inhalten, die Spieler kostenlos erstellen und teilen dürfen.

## So geht's

1. Klicken Sie im Fenster **Mods** bei Random New World auf **Ordner öffnen** und doppelklicken Sie auf **Random New World Generator**.
2. Wählen Sie eine Weltart: Superkontinent, Kontinente, Kleine Kontinente, Archipel oder Verstreute Inseln. Behalten Sie den zufälligen Startwert, tippen Sie einen eigenen ein oder fügen Sie einen Weltcode ein. Die **Grundlagen** beantworten die üblichen Fragen mit einem Wort, wie die zufällige Neue Welt in EU4: wie viel Land, wie viele indigene Völker und Staaten, wie oft ein großes indigenes Imperium entsteht (nie, selten, manchmal, oft) und wie reich Gold und Silber sind. Unter **Anpassen** lässt sich jeder Wert ändern: Land, Küsten, Kartenmaßstab und die indigenen Völker, von großen Imperien bis zu einzelnen Staaten. Jeder angebotene Wert ergibt eine spielbare Welt.
3. Klicken Sie auf **Erstellen**. Nach zwei bis drei Minuten steht die Welt als neuer Mod in Ihrer Mod-Liste, mit einem Namen wie „RNW: Small continents 7K3Q“ (Weltart und Kennung); im Generator können Sie sie umbenennen. Solange die Neue Welt verdeckt ist, trägt ihr Bild in der Mod-Liste dieselbe Kennung in Rot, damit sich die Welten auseinanderhalten lassen.
4. Haken Sie diese Welt im Spiel an (immer nur eine Welt) und beginnen Sie ein neues Spiel. Haben Sie seit dem Start von EU5 schon eine Kampagne gespielt, starten Sie EU5 zuerst neu. Der Generator sagt Ihnen genau, was zu tun ist.

Der Generator bewahrt jede Welt auf, die Sie erzeugt haben, samt ihrem Code. Bis Sie sie in den **Einstellungen** sichtbar machen, bleibt die Neue Welt vor dem Spielen überall Terra incognita: auf den Bildern des Generators, in der Mod-Liste des Spiels und auf der Karte des Bildschirms für ein neues Spiel. Eine einzige Einstellung schaltet das alles ab. Ein Weltcode erzeugt dieselbe Welt Byte für Byte auf jedem Rechner mit derselben Spielversion.

Der Generator spricht jede Sprache des Spiels und startet in der, in der Steam EU5 ausführt.

## Was das Programm tut und was nicht

- Es liest Ihre EU5-Installation und schreibt nur an zwei Orte: in die erzeugten Welt-Mods (`mod/rnw_world_…` im EU5-Ordner unter „Dokumente“) und in seinen eigenen Datenordner.
- Es nutzt kein Netzwerk, braucht keine Administratorrechte, rührt die Registry nicht an und ändert keine Datei des Spiels.
- Sein Quellcode ist öffentlich, unter der Mozilla Public License 2.0: https://github.com/Sir-Starch/eu5-random-new-world. Jede Veröffentlichung wird automatisch aus einem markierten Commit gebaut, und dort steht auch die SHA-256-Prüfsumme jeder Datei.
- Ob Sie einem Programm vertrauen, entscheiden Sie. Sie können den Code lesen, die Prüfsummen vergleichen oder es selbst bauen.

## Warnungen von Windows

- Dateien, die Steam herunterlädt, werden nicht als aus dem Internet stammend markiert, daher sollte Windows SmartScreen nicht nachfragen. [Confirm in 020.]
- Virenscanner schlagen bei neuen, ihnen unbekannten Programmen manchmal an. Die Seite jeder Veröffentlichung verlinkt einen VirusTotal-Scan.
- Die intelligente App-Steuerung von Windows 11 blockiert Programme ohne bekannte Signatur, und Windows erlaubt keine Ausnahme für einzelne Programme. [Until signed:] Der Generator ist noch nicht signiert und startet daher nicht, solange die intelligente App-Steuerung aktiv ist. [Once signed:] Der Generator und sein natives Modul sind von [signer] signiert.

## Linux und Steam Deck

Das Spiel läuft über Proton. „Ordner öffnen“ öffnet dann den Dateimanager von Wine, und derselbe Generator läuft dort, im Proton-Präfix des Spiels selbst. Installieren müssen Sie nichts. [Steam Deck: confirm.]

## Grenzen

- **Nur neue Kampagnen.** Eine Welt muss vor Beginn der Kampagne erzeugt werden.
- **Erst erzeugen, dann spielen, sonst neu starten.** EU5 stürzt ab, wenn nach einer Kampagne in derselben Sitzung eine andere Welt startet (der Absturz liegt in der Engine des Spiels). Wer direkt nach dem Start von EU5 erzeugt, muss nicht neu starten; nach einer Kampagne starten Sie EU5 vor der neuen Welt neu.
- **Spiel-Updates.** Nach einem Update von EU5 verweigert der Generator unter Umständen den Dienst, bis er an den neuen Build angepasst ist. Dann bietet er an, Ihre Welt neu zu erzeugen. Ältere Spielstände brauchen die Welt, auf der sie gespielt wurden: Erzeugen Sie sie aus ihrem Code neu.
- **Eine Welt zur Zeit.** Haken Sie in einer Gruppe nur eine erzeugte Welt an.
- **Mehrspieler.** Alle Spieler nutzen denselben Weltcode und dieselbe Spielversion.
- **Arbeitsspeicher.** Etwa 7,5 GB freier Arbeitsspeicher für die zwei Minuten der Erzeugung. Die für EU5 empfohlenen 32 GB reichen reichlich.
- **Errungenschaften.** Wie andere Mods, die das Spiel verändern, ändert er die Prüfsumme des Spiels. [Confirm what EU5 allows.]

## Entfernen

Löschen Sie Welten im Generator (**Welt löschen**) oder entfernen Sie ihre Ordner selbst und kündigen Sie dann das Abonnement. Welten, die Sie behalten, bleiben ohne den Generator spielbar.

## Lizenz und Mitwirkende

Code und Mod-Dateien: Mozilla Public License 2.0. Die Welten entstehen auf Ihrem Rechner aus Ihrer Kopie von EU5 und werden nicht über den Workshop verbreitet. Europa Universalis V ist eine Marke von Paradox Interactive; dieser Mod steht in keiner Verbindung zu Paradox Interactive.

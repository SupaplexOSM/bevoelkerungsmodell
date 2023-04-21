# Bevölkerungsmodell mit QGIS aus Gebäudedaten interpolieren
## Statistische Punktwolke aller Bewohner:innen einer Stadt

Dieses Python-Script für QGIS erzeugt einen Bevölkerungsdatensatz in Form einer Punktwolke "individualisierter" Wohnorte auf Grundlage eines Gebäude- und eines Bevölkerungsdichte-Datensatzes. Die Bevölkerungsdichte wird auf die Gebäude entsprechend ihrer Gebäudeklasse, Stockwerkszahl und Grundfläche interpoliert und dadurch eine Bevölkerungszahl pro Gebäude abgeleitet. Diese Punktwolke kann mit statistischen Daten für das Gebiet verbunden werden, in dem jeder Person statistisch zugeordnet wird, ob ein Merkmal entsprechend seiner Häufigkeit für eine Person zutrifft oder nicht.

***Entstehungshintergrund:*** Wir haben das Modell in der Berliner OpenStreetMap-Community für die Generierung einer Parkraumdichteverteilung (in Verbindung mit Kfz-Meldedaten) entwickelt. Hintergründe zur Verwendung im OSM-Parkraumprojekt finden sich [in diesem Blogpost](https://parkraum.osm-verkehrswende.org/posts/2021-03-13-opendata/). Das Script kann bei Bedarf auch mit OSM-Gebäudedaten gefüttert werden, in Berlin haben wir aber vollständigere ALKIS-Daten genutzt.

## Welche Daten werden als Input benötigt?
- Datensatz aller Gebäude (Polygone) mit Anzahl der Gebäudestockwerke und Gebäudefunktion (zur Unterscheidung von Wohngebäuden von Gebäuden, die nicht zum Wohnen genutzt werden)

  **→ Beispiel für Berlin: [ALKIS-Gebäudedaten als WFS](https://fbinter.stadt-berlin.de/fb/wfs/data/senstadt/s_wfs_alkis_gebaeudeflaechen)**
- Datensatz mit Angaben der Bevölkerungszahl/Bevölkerungsdichte für (Teil-)Gebiete, möglichst kleinräumig

  **→ Beispiel für Berlin: [Einwohnerdichte auf Blockebene](https://fbinter.stadt-berlin.de/fb/wfs/data/senstadt/s06_06ewdichte2021)**

- Bei Bedarf: Datensatz zur statistischen Verknüpfung – jedem Punkt wird entsprechend der Häufigkeit eines Merkmals zugeordnet, ob es für eine Person zutrifft oder nicht (z.B. Besitzt die Person ein Auto? Ist die Person über 65 Jahre alt? etc.)

## Wie funktioniert die Generierung des Datensatzes?
- Über den Gebäudetyp werden zunächst alle Gebäude identifiziert, die sich zum Wohnen eignen und je nach Gebäudetyp Annahmen getroffen, wie viele Stockwerke des Gebäudes zum Wohnen verwendet werden (im Script können entsprechende Attribute/Werte angepasst werden). Bei einem reinen Wohngebäude wird beispielsweise angenommen, dass alle Stockwerke bewohnt sind, bei einer Mischnutzung (Gewerbe im Erdgeschoss) wird von einem Stockwerk weniger ausgegangen oder im etwas selteneren Fall von Gewerbegebäuden mit teilweiser Wohnnutzung von der Hälte aller Stockwerke. Daraus ergibt sich eine durchschnittliche Gesamtwohnfläche für jedes Gebäude (Grundfläche * zum Wohnen geeignete Stockwerke).
- Als nächstes wird die Angabe zur Bevölkerungszahl/-dichte einbezogen und jedem Gebäude eine statistisch erwartbare Anzahl Bewohner:innen zugeordnet – entsprechend seines Anteils an der "Gesamtwohnfläche" innerhalb des Raumes, für den eine Bevölkerungszahl vorliegt. Innerhalb jedes Gebäudes können nun genausoviele zufällige Punkte erzeugt werden, die jeweils ein Individuum statistisch repräsentieren.
- Bei Bedarf können auf die generierten "Bewohner:innen" statistische Angaben (z.B. soziodemographische Daten) übertragen werden. Dafür wird jedem Punkt eine Zufallszahl zugeordnet, die zur Übernahme eines statistischen Merkmals genutzt werden kann (z.B. trifft Attribut A auf 30% der Bevölkerung zu, dann bekommen alle Punkte mit Zufallszahl <= 30 einen entsprechenden Eintrag).

## Wie kann ich das Script ausführen?
- Es wird [QGIS](https://de.wikipedia.org/wiki/QGIS) benötigt. Öffne QGIS.
- Öffne die interne Python-Konsole über *Erweiterungen* → *Python-Konsole* (oder Shortcut Strg+Alt+P).
- Falls der Python-Editor in der Konsole ausgeblendet ist (also nicht als zweites, separates Fenster sichtbar ist), ihn mit "Editor anzeigen" einblenden.
- Das Script *population_building_scale.py* öffnen und bei Bedarf die Variablen und Einstellungen im oberen Bereich anpassen (Benennung der Datensätze, Attribute, Dateiformate etc.).
- Am Speicherort des Scripts einen Unterordner "data" anlegen und dort die Input-Datensätze bereithalten.
- Script ausführen (z.B. über den Konsolen-Button mit dem grünen Pfeil). Je nach Größe des Gebiets und Rechenleistung dauert es ein paar Sekunden (für einen Stadtteil) oder ein paar Stunden (z.B. für ganz Berlin mit mehreren Millionen Punkten und Gebäuden).

***Hinweis:*** Das Script ist bisher nicht sehr effizient geschreiben, sodass es bei großen Datensätzen/Städten länger dauern kann... Wer Lust/Wissen hat, kann es gern effektiver schreiben :) Eine bekannte Ungenauigkeit ist außerdem, dass ein kleiner Teil (<1%) der Bevölkerung "verschwinden" kann, also die Anzahl der Punkte am Ende nicht ganz der Gesamtbevölkerung aus dem Bevölkerungsdichtedatensatz entspricht. Könnte ein Rundungsproblem sein, habe ich mir noch nicht genauer angesehen, da es relativ vernachlässigbar ist.

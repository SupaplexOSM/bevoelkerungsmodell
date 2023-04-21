#--------------------------------------------------------------------#
#   Erzeugt einen Bevölkerungsdatensatz in Form einer Punktwolke     #
#   "individualisierter" Wohnorte auf Grundlage eines Gebäude- und   #
#   eines Bevölkerungsdichte-Datensatzes.                            #
#   Die Bevölkerungsdichte wird auf die Gebäude entsprechend ihrer   #
#   Gebäudeklasse, Stockwerkszahl und Grundfläche interpoliert und   #
#   dadurch eine Bevölkerungszahl pro Gebäude abgeleitet.            #
#   Diese Punktwolke kann mit statistischen Daten für das Gebiet     #
#   verbunden werden, in dem jeder Person statistisch zugeordnet     #
#   wird, ob ein Merkmal entsprechend seiner Häufigkeit für eine     #
#   Person zutrifft oder nicht.                                      #
#--------------------------------------------------------------------#
#   > version/date: 2023-03-07                                       #
#--------------------------------------------------------------------#
from qgis.core import *
from os.path import exists
import os, processing, math, random, time

#working directory, see https://stackoverflow.com/a/65543293/729221
from console.console import _console
dir = _console.console.tabEditorWidget.currentWidget().path.replace("population_building_scale.py","")

#-------------------------------------------------#
#   V a r i a b l e s   a n d   S e t t i n g s   #
#-------------------------------------------------#

# Notwendige Datensätze (als geojson im input-Ordner speichern):
# - Datensätze für 1) Gebäude und 2) Bevölkerungsdichte als WFS holen, auf Zielgebiet zuschneiden
# - bei Bedarf einen Datensatz mit Attributen zur statistischen Häufigkeit von Merkmalen im Zielgebiet

# 1) Gebäudedatensatz (ALKIS Berlin Gebäude, https://fbinter.stadt-berlin.de/fb/wfs/data/senstadt/s_wfs_alkis_gebaeudeflaechen)
input_buildings = dir + 'data/buildings.geojson'
# Filterausdruck, um nur passende Features des Datensatzes zu berücksichtigen
expr_filter_buildings = '\"bezeich\" = \'AX_Gebaeude\' and "bezzus" is NULL'
# Wie ist das Attribut mit der Anzahl der Gebäudestockwerke benannt?
attr_building_levels = 'aog'
# Wie ist das Attribut mit der Gebäudefunktion benannt?
attr_building_function = 'bezgfk'
# Wie heißen die Attribute, die ein Wohngebäude kennzeichnen? Wie viele Stockwerke dieser Gebäude werden berücksichtigt? (Ausdruck, der auf die Geschosszahl angewendet wird)
list_residential_buildings = [
['Gebäude für Gewerbe und Industrie mit Wohnen', '/2'], #Gewerbegebäude mit Wohnnutzung: Halbe Stockwerkszahl berücksichtigen
['Gebäude für Handel und Dienstleistung mit Wohnen', '/2'],
['Gebäude für öffentliche Zwecke mit Wohnen', '/2'],
['Gemischt genutztes Gebäude mit Wohnen', '/2'],
['Wohngebäude mit Gemeinbedarf', '-1'], #Wohngebäude mit Gewerbenutzung: Ein Stockwerk nicht berücksichtigen (meistens Erdgeschoss)
['Wohngebäude mit Gewerbe und Industrie', '-1'],
['Wohngebäude mit Handel und Dienstleistungen', '-1'],
['Wohnhaus', '-0'], #reine Wohngebäude: Alle Stockwerke berücksichtigen
['Wohngebäude', '-0'],
['Wohnheim', '-0'],
['Schwesternwohnheim', '-0'],
['Studenten-, Schülerwohnheim', '-0']]

# 2) Einwohnerdichte auf Blockebene (https://fbinter.stadt-berlin.de/fb/wfs/data/senstadt/s06_06ewdichte2021)
input_population_density = dir + 'data/population_density.geojson'
# Wie ist das Attribut mit der Bevölkerungszahl benannt?
attr_population = 'ew2021'
# Wie ist das Attribut mit der eindeutigen ID für jede Blockfläche benannt?
attr_block_id = 'schl5'

# 3) Bei Bedarf Datensatz zur statistischen Verknüpfung – jedem Punkt wird entsprechend der Häufigkeit zugeordnet, ob ein Merkmal zutrifft oder nicht
input_statistics = dir + 'data/Kfz-Bestand LOR-Planungsräume.geojson'
# Sollen statistische Merkmale übertragen werden?
adopt_statistics = True
# Wie sind die zu übertragenden Merkmale im statistischen Datensatz benannt?
attr_statistics = ['Kfz pro 1000 EW', 'Pkw pro 1000 EW']
# Wie sollen die übertragenden Merkmale im output-Datensatz benannt sein?
attr_statistics_output = ['Kfz', 'Pkw']
# Welche Skala haben die statistischen Werte / welcher Wert entspricht 100% (z.B. 100 oder 1)?
statistics_norm = 1000

output = dir + 'data/population_building_scale.geojson'
output_crs = "EPSG:25833"
output_file_format = 'GeoJSON'



def clearAttributes(layer, attributes):
#-------------------------------------------------------------------------------
# Deletes unnecessary attributes.
#-------------------------------------------------------------------------------
# > layer: The layer to be cleaned up.
# > attributes: List of attributes that should be kept.
#-------------------------------------------------------------------------------
    attr_count = len(layer.attributeList())
    delete_list = []
    for id in range(0, attr_count):
        if not layer.attributeDisplayName(id) in attributes:
            delete_list.append(layer.attributeDisplayName(id))
    layer = processing.run('qgis:deletecolumn', { 'INPUT' : layer, 'COLUMN' : delete_list, 'OUTPUT': 'memory:'})['OUTPUT']
    return(layer)



# Datensätze einlesen
print(time.strftime('%H:%M:%S', time.localtime()), 'Read datasets...')
if not exists(input_buildings):
    print(time.strftime('%H:%M:%S', time.localtime()), '[!] Error: Found no valid building dataset at "' + input_buildings + '".')
elif not exists(input_population_density):
    print(time.strftime('%H:%M:%S', time.localtime()), '[!] Error: Found no valid population density dataset at "' + input_population_density + '".')
else:
    layer_buildings = QgsVectorLayer(input_buildings + '|geometrytype=Polygon', 'buildings', 'ogr')
    population_density = QgsVectorLayer(input_population_density + '|geometrytype=Polygon', 'population density', 'ogr')

    print(time.strftime('%H:%M:%S', time.localtime()), 'Prepare datasets...')
    # doppelte Geometrien löschen
    layer_buildings = processing.run('native:deleteduplicategeometries', { 'INPUT' : layer_buildings, 'OUTPUT': 'memory:'})['OUTPUT']
    population_density = processing.run('native:deleteduplicategeometries', { 'INPUT' : population_density, 'OUTPUT': 'memory:'})['OUTPUT']
    # Filterbedingung auf Gebäude anwenden (Gebäudeteile und verfallene Gebäude ausschließen)
    layer_buildings = processing.run('qgis:extractbyexpression', { 'INPUT' : layer_buildings, 'EXPRESSION' : expr_filter_buildings, 'OUTPUT': 'memory:'})['OUTPUT']

    # zum Wohnen geeignete Gebäudestockwerke aus Gebäudekategorie ableiten und Wohngeschossfläche ermitteln (Wohnstockwerke * Grundfläche)
    print(time.strftime('%H:%M:%S', time.localtime()), 'Interpolate building population...')
    layer_buildings_provider = layer_buildings.dataProvider()
    layer_buildings_provider.addAttributes([
        QgsField("residential_levels", QVariant.Int),         # Wohnstockwerke
        QgsField("building_area", QVariant.Double),           # Gebäudegrundfläche
        QgsField("residential_level_area", QVariant.Double)]) # Wohngeschossfläche = Wohnstockwerke * Gebäudegrundfläche
    layer_buildings.updateFields()
    id_residential_levels = layer_buildings_provider.fields().indexOf('residential_levels')
    id_building_area = layer_buildings_provider.fields().indexOf('building_area')
    id_residential_level_area = layer_buildings_provider.fields().indexOf('residential_level_area')

    with edit(layer_buildings):
        for building in layer_buildings.getFeatures():
            residential_levels = 0
            building_levels = building.attribute(attr_building_levels)
            if not building_levels:
                building_levels = 0
            else:
                for building_class in list_residential_buildings:
                    if building_class[0] == building.attribute(attr_building_function):
                        residential_levels = int(eval(str(building_levels) + building_class[1]))
                        if building_levels == 1:
                            residential_levels = 1 # Mindestens ein Stockwerk zählt bei Wohngebäuden immer
            building_area = building.geometry().area()
            residential_level_area = residential_levels * building_area

            layer_buildings_provider.changeAttributeValues({building.id():{
            id_residential_levels:residential_levels,
            id_building_area:building_area,
            id_residential_level_area:residential_level_area}})

    # Blockbevölkerung und Block-ID auf Gebäude übertragen
    layer_buildings = processing.run('native:joinattributesbylocation', {'INPUT': layer_buildings, 'JOIN' : population_density, 'JOIN_FIELDS' : [attr_population, attr_block_id], 'METHOD' : 2, 'OUTPUT': 'memory:'})['OUTPUT']

    # Alle Wohngeschossflächen des gesamten Blocks summieren
    expr = 'sum("residential_level_area", group_by:="' + attr_block_id + '")'
    layer_buildings = processing.run('qgis:fieldcalculator', { 'INPUT': layer_buildings, 'FIELD_NAME': 'block_residential_level_area', 'FIELD_TYPE': 0, 'FIELD_LENGTH': 10, 'FIELD_PRECISION': 3, 'NEW_FIELD': True, 'FORMULA': expr, 'OUTPUT': 'memory:'})['OUTPUT']

    # Gebäudebevölkerung ableiten
    expr = 'max("' + attr_population + '" * ("residential_level_area" / "block_residential_level_area"), 0)' #max verhindert NULL-Werte
    layer_buildings = processing.run('qgis:fieldcalculator', { 'INPUT': layer_buildings, 'FIELD_NAME': 'building_residents', 'FIELD_TYPE': 1, 'NEW_FIELD': True, 'FORMULA': expr, 'OUTPUT': 'memory:'})['OUTPUT']

    # Zufallspunkte in Gebäudeumringen erzeugen
    print(time.strftime('%H:%M:%S', time.localtime()), 'Generate point cloud...')
    layer_residents_points = processing.run('native:randompointsinpolygons', { 'INPUT': layer_buildings, 'POINTS_NUMBER' : QgsProperty.fromExpression('"building_residents"'), 'OUTPUT': 'memory:'})['OUTPUT']

    # Zufallszahl für jeden Punkt erzeugen, der später für die Übernahme statistischer Annahmen genutzt werden kann (z.B. Attribut A trifft auf 30% der Bevölkerung zu -> wenn rand_num <= 30, dann trifft Attriut A auf diese Person zu)
    layer_residents_points = processing.run('qgis:fieldcalculator', { 'INPUT': layer_residents_points, 'FIELD_LENGTH' : 6, 'FIELD_NAME' : 'rand_num', 'FIELD_PRECISION' : 3, 'FIELD_TYPE' : 0, 'FORMULA' : 'round(randf(0, 100), 3)', 'NEW_FIELD': True, 'OUTPUT': 'memory:'})['OUTPUT']

    # Bei Bedarf statistische Merkmale übertragen
    print(time.strftime('%H:%M:%S', time.localtime()), 'Adopt statistics...')
    keep_attr = ['rand_num']
    if adopt_statistics:
        if not exists(input_statistics):
            print(time.strftime('%H:%M:%S', time.localtime()), '[!] Warning: Found no valid statistics dataset at "' + input_statistics + '". No statistical attributes were adopted.')
        else:
            print(time.strftime('%H:%M:%S', time.localtime()), '   Read statistical dataset...')
            layer_statistics = QgsVectorLayer(input_statistics + '|geometrytype=Polygon', 'statistics', 'ogr')
            print(time.strftime('%H:%M:%S', time.localtime()), '   Join statistical attributes...')
            layer_residents_points = processing.run('native:joinattributesbylocation', {'INPUT': layer_residents_points, 'JOIN' : layer_statistics, 'JOIN_FIELDS' : attr_statistics, 'METHOD' : 1, 'PREDICATE' : [5], 'OUTPUT': 'memory:'})['OUTPUT']
            print(time.strftime('%H:%M:%S', time.localtime()), '   Individualize statistics...')
            i = 0
            for attr in attr_statistics:
                if i + 1 > len(attr_statistics_output):
                    label = attr + '_'
                elif attr == attr_statistics_output[i]:
                    label = attr + '_'
                else:
                    label = attr_statistics_output[i]
                keep_attr.append(label)
                expr = 'if(\"' + attr + '\" / (' + str(statistics_norm) + ' / 100) >= \"rand_num\", 1, 0)'
                layer_residents_points = processing.run('qgis:fieldcalculator', { 'INPUT': layer_residents_points, 'FIELD_NAME': label, 'FIELD_TYPE': 1, 'FIELD_LENGTH' : 1, 'NEW_FIELD': True, 'FORMULA': expr, 'OUTPUT': 'memory:'})['OUTPUT']
                i += 1

    # Attributtabelle bereinigen
    print(time.strftime('%H:%M:%S', time.localtime()), 'Clean up dataset...')
    layer_residents_points = clearAttributes(layer_residents_points, keep_attr)

    # add output to map
    layer_buildings.setName('buildings')
    QgsProject.instance().addMapLayer(layer_buildings, True)
    layer_residents_points.setName('residents')
    QgsProject.instance().addMapLayer(layer_residents_points, True)

    print(time.strftime('%H:%M:%S', time.localtime()), 'Save output...')
    qgis.core.QgsVectorFileWriter.writeAsVectorFormat(layer_residents_points, output, 'utf-8', QgsCoordinateReferenceSystem(output_crs), output_file_format)

    # focus on output layer
    iface.mapCanvas().setExtent(layer_residents_points.extent())

    print(time.strftime('%H:%M:%S', time.localtime()), 'Completed.')
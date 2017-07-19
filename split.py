#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import tempfile
import os
import sys
import hashlib


def exportToNewDestination(newsvg, dist_file, extra_options=""):
    nt = ET.ElementTree(newsvg)
    dist_file_svg = dist_file + '.svg'
    sha256 = None
    os.makedirs(os.path.dirname(dist_file), exist_ok=True)
    if os.path.isfile(dist_file_svg):
        sha256 = hashlib.sha256(open(dist_file_svg, 'rb').read()).digest()
    nt.write(dist_file_svg,
             encoding='UTF-8',
             xml_declaration=True)
    if sha256 != hashlib.sha256(open(dist_file_svg, 'rb').read()).digest():
        print('Erstelle {} als PDF, ESP und PNG neu'.format(dist_file))
        for filetype in 'png eps pdf'.split():
            print(
                'inkscape {dist_file_svg} {extra_options} --export-{filetype} {dist_file}.{filetype}'.format(**vars()))
            os.system(
                'inkscape {dist_file_svg} {extra_options} --export-{filetype} {dist_file}.{filetype}'.format(**vars()))
    else:
        print('SVG {} ist unverändert...'.format(dist_file_svg))


def main(parcours_file):

    ET.register_namespace('', 'http://www.w3.org/2000/svg')

    plain_svg = tempfile.mktemp()

    if os.system('inkscape "{}" -l "{}"'.format(parcours_file, plain_svg)):
        exit(1)

    stege = []
    klassen = []

    tree = ET.parse(plain_svg)
    root = tree.getroot()
    for child in root:
        if child.attrib['id'].startswith('steg'):
            stege.append(child.attrib['id'])
        if child.attrib['id'].startswith('Klasse'):
            klassen.append(child.attrib['id'])
        print('{tag:<40}: {id}'.format(tag=child.tag, id=child.attrib['id']))

    stege.append('.')
    klassen.append('Parcours')

    splitParcours(stege, klassen, plain_svg)
    splitAlcatraz(klassen, plain_svg)
    os.remove(plain_svg)


def splitParcours(stege, klassen, plain_svg):
    for steg in stege:
        for klasse in klassen:
            newtree = ET.parse(plain_svg)
            newsvg = newtree.getroot()
            for style in newsvg.findall("[@style]"):
                del(style.attrib['style'])
            for child in list(newsvg):
                if (child.attrib['id'].startswith('Klasse')
                        and child.attrib['id'] != klasse):
                    newsvg.remove(child)
                if (child.attrib['id'].startswith('steg')
                        and child.attrib['id'] != steg):
                    newsvg.remove(child)
            labels = newsvg.findall(".//*[@id='Export_Area']")
            for label in labels:
                label.clear()
            labels = newsvg.findall(".//*[@id='bezeichnung_90']")
            for label in labels:
                label.clear()
            exportToNewDestination(newsvg, 'dist/{}/{}'.format(steg, klasse))


def splitAlcatraz(klassen, plain_svg):
    for alcatraz in [["I", [2]], ["II", [2]], ["Parcours", [1, 2]]]:
        for klasse in klassen:
            newtree = ET.parse(plain_svg)
            newsvg = newtree.getroot()
            for style in newsvg.findall("[@style]"):
                del(style.attrib['style'])
            for child in list(newsvg):
                if (child.attrib['id'].startswith('Klasse')
                        and child.attrib['id'] != klasse):
                    newsvg.remove(child)
                if child.attrib['id'].startswith('steg'):
                    newsvg.remove(child)
            labels = newsvg.findall(".//*[@id='abmessung']")
            labels.extend(newsvg.findall(".//*[@id='bezeichnung']"))
            for alc in alcatraz[1]:
                labels.extend(newsvg.findall(
                    ".//*[@id='Alcatraz_{}']".format(alc)))
            for label in labels:
                label.clear()
            exportToNewDestination(newsvg, 'dist/alcatraz_{}/{}'.format(
                alcatraz[0], klasse), '--export-id Export_Area -b FFFFFF')


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Bitte Parcours SVG angeben! {} parsours.svg'
              .format(sys.argv[0]), file=sys.stderr)
        exit(1)
    parcours_file = sys.argv[1]
    if not os.path.isfile(parcours_file):
        print('{} kann nicht gelesen werden!', file=sys.stderr)
        exit(1)
    main(parcours_file)

#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import tempfile
import os
import sys
import hashlib

if len(sys.argv) < 2:
    print('Bitte Parcours SVG angeben! {} parsours.svg'
          .format(sys.argv[0]), file=sys.stderr)
    exit(1)
else:
    parcours_file = sys.argv[1]
    if not os.path.isfile(parcours_file):
        print('{} kann nicht gelesen werden!', file=sys.stderr)
        exit(1)

ET.register_namespace('', 'http://www.w3.org/2000/svg')

plain_svg = tempfile.mktemp()

if os.system('inkscape "{}" -l "{}"'.format(parcours_file, plain_svg)):
    exit(1)

tree = ET.parse(plain_svg)
root = tree.getroot()
stege = []
klassen = []
for child in root:
    if child.attrib['id'].startswith('steg'):
        stege.append(child.attrib['id'])
    if child.attrib['id'].startswith('Klasse'):
        klassen.append(child.attrib['id'])
    print('{tag:<40}: {id}'.format(tag=child.tag, id=child.attrib['id']))

stege.append('.')
klassen.append('Parcours')
for steg in stege:
    for klasse in klassen:
        newtree = ET.parse(plain_svg)
        newsvg = newtree.getroot()
        for child in list(newsvg):
            if 'style' in child.attrib:
                del(child.attrib['style'])
            if (child.attrib['id'].startswith('Klasse')
               and child.attrib['id'] != klasse):
                newsvg.remove(child)
            if (child.attrib['id'].startswith('steg')
               and child.attrib['id'] != steg):
                newsvg.remove(child)
        nt = ET.ElementTree(newsvg)
        dist_file = 'dist/{}/{}'.format(steg, klasse)
        dist_file_svg = dist_file + '.svg'
        sha256 = None
        if os.path.isfile(dist_file_svg):
            sha256 = hashlib.sha256(open(dist_file_svg, 'rb').read()).digest()
        nt.write(dist_file_svg,
                 encoding='UTF-8',
                 xml_declaration=True)
        if sha256 != hashlib.sha256(open(dist_file_svg, 'rb').read()).digest():
            print('Erstelle {} als PDF, ESP und PNG neu'.format(dist_file))
            for filetype in 'png eps pdf'.split():
                os.system('inkscape {dist_file_svg} --export-{filetype} {dist_file}.{filetype}'.format(**vars()))

os.remove(plain_svg)

#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import tempfile
import os
import sys
import hashlib
import shutil
import subprocess
import base64
import mimetypes
from urllib.parse import unquote
from urllib.request import url2pathname

# Sprachkonfiguration:
#   prefix  – Prefix der Klassen-Layer in der SVG
#   dirs    – Mapping von SVG-Layer-ID → Ausgabeverzeichnis
# Neue Sprache hinzufügen: Layer in Inkscape anlegen (z.B. "Clase1", "ParcoursLabelES",
# "steg_untenES", "LogoES") und hier einen Eintrag ergänzen.
LANGUAGES = {
    "de": {
        "prefix": "Klasse",
        "dirs": {"": "", "steg_unten": "steg_unten", "steg_oben": "steg_oben"},
    },
    "en": {
        "prefix": "Class",
        "dirs": {"": "", "steg_unten": "pontoon_bottom", "steg_oben": "pontoon_top"},
    },
}


def embed_images(svg):
    xlink = "{http://www.w3.org/1999/xlink}href"
    for img in svg.iter("{http://www.w3.org/2000/svg}image"):
        href = img.get(xlink, "")
        if href.startswith("data:"):
            continue
        if href.startswith("file:///"):
            path = url2pathname(href[len("file://"):])
        else:
            path = unquote(href)
        if not os.path.isfile(path):
            print(f"Warnung: Bild nicht gefunden: {path}")
            continue
        mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        img.set(xlink, f"data:{mime};base64,{data}")


def export_to_destination(newsvg, dist_file, extra_options=""):
    export_types = ["pdf", "png", "eps"]
    if extra_options:
        export_types.append("svg")
    embed_images(newsvg)
    nt = ET.ElementTree(newsvg)
    dist_file_svg = f"{dist_file}.svg"
    os.makedirs(os.path.dirname(dist_file), exist_ok=True)

    fd, tmp_svg = tempfile.mkstemp(suffix=".svg")
    os.close(fd)
    nt.write(tmp_svg, encoding="UTF-8", xml_declaration=True)

    with open(tmp_svg, "rb") as f:
        new_sha = hashlib.sha256(f.read()).digest()
    sha_file = f"{dist_file}.sha256"
    old_sha = None
    if os.path.isfile(sha_file):
        with open(sha_file, "rb") as f:
            old_sha = f.read()

    if new_sha != old_sha:
        print(f"Erstelle {dist_file} als PDF und PNG neu")
        if not extra_options:
            shutil.move(tmp_svg, dist_file_svg)
            source_svg = dist_file_svg
        else:
            source_svg = tmp_svg
        for filetype in export_types:
            cmd = f"inkscape {source_svg} {extra_options} -o {dist_file}.{filetype}"
            print(cmd)
            subprocess.run(cmd, shell=True, check=False)
        if extra_options:
            os.remove(tmp_svg)
        with open(sha_file, "wb") as f:
            f.write(new_sha)
    else:
        os.remove(tmp_svg)
        print(f"SVG {dist_file_svg} ist unverändert...")


def main(parcours_file):
    fd, plain_svg = tempfile.mkstemp(suffix=".svg")
    os.close(fd)
    print(f'start: inkscape "{parcours_file}" -l --export-filename "{plain_svg}"')
    result = subprocess.run(
        f'inkscape "{parcours_file}" -l --export-filename "{plain_svg}"',
        shell=True,
    )
    if result.returncode:
        sys.exit(1)

    # Ausgabeverzeichnis vom Dateinamen ableiten
    base_name = os.path.splitext(os.path.basename(parcours_file))[0]
    dist_base = "dist" if base_name == "parcours" else f"dist/{base_name}"

    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    tree = ET.parse(plain_svg)
    root = tree.getroot()

    # Stege und Klassen dynamisch aus der SVG erkennen
    stege = [""]
    has_export_area = False
    infra_prefixes = ("steg_", "Parcours", "Logo", "arrows", "metadata",
                      "script", "Export_Area", "Speedboje")
    extra_layers = []
    klassen_per_lang = {lang: [] for lang in LANGUAGES}
    for child in root:
        cid = child.attrib.get("id", "")
        print(f"{child.tag:<40}: {cid}")
        if cid.startswith("steg_") and not any(c.isupper() for c in cid):
            stege.append(cid)
        if cid == "Export_Area":
            has_export_area = True
        matched = False
        for lang, conf in LANGUAGES.items():
            if cid.startswith(conf["prefix"]):
                klassen_per_lang[lang].append(cid)
                matched = True
        if not matched and not cid.startswith(infra_prefixes):
            extra_layers.append(cid)

    has_klassen = any(klassen for klassen in klassen_per_lang.values())

    if has_klassen:
        for lang, klassen in klassen_per_lang.items():
            if not klassen:
                continue
            klassen.append("Parcours")
            split_parcours(stege, klassen, plain_svg, lang,
                           LANGUAGES[lang]["dirs"], dist_base)
    else:
        # Keine Klassen gefunden (z.B. parallel.svg) — alle Extra-Layer
        # als einzelne "Klassen" behandeln, dazu den Gesamtparcours
        all_layers = extra_layers + ["Parcours"]
        # Sprache anhand vorhandener ParcoursLabel-Layer bestimmen
        for lang in LANGUAGES:
            lang_upper = lang.upper()
            label_id = f"ParcoursLabel{lang_upper}"
            if any(c.attrib.get("id") == label_id for c in root):
                split_parcours(stege, all_layers, plain_svg, lang,
                               LANGUAGES[lang]["dirs"], dist_base)

    # Alcatraz nur wenn Export_Area vorhanden und deutsche Klassen existieren
    if has_export_area and klassen_per_lang["de"]:
        split_alcatraz(klassen_per_lang["de"], plain_svg, dist_base)

    os.remove(plain_svg)


def split_parcours(stege, klassen, plain_svg, lang, dirs, dist_base):
    lang_upper = lang.upper()
    for steg in stege:
        out_dir = dirs.get(steg, steg)
        for klasse in klassen:
            include = {
                klasse,
                steg,
                "arrows",
                "metadata",
                f"Logo{lang_upper}",
                "Parcours",
                "ParcoursLabel",
                f"ParcoursLabel{lang_upper}",
                f"{steg}{lang_upper}",
            }
            if klasse.endswith("7"):
                include.add("SpeedbojeKlasse7")
            newtree = ET.parse(plain_svg)
            newsvg = newtree.getroot()
            for el in newsvg.findall(".//*[@style]"):
                el.attrib["style"] = el.attrib["style"].replace(
                    "display:none", "display:inline"
                )
            for child in list(newsvg):
                if child.attrib["id"] not in include:
                    newsvg.remove(child)

            export_to_destination(newsvg, f"{dist_base}/{lang}/{out_dir}/{klasse}")


def split_alcatraz(klassen, plain_svg, dist_base):
    for name, clear_ids in [("I", [2]), ("II", [1]), ("Parcours", [1, 2])]:
        for klasse in klassen:
            keep = {
                klasse,
                "arrows",
                "metadata",
                "Parcours",
                "Export_Area",
                "SpeedbojeKlasse7",
            }
            newtree = ET.parse(plain_svg)
            newsvg = newtree.getroot()
            for el in newsvg.findall(".//*[@style]"):
                el.attrib["style"] = el.attrib["style"].replace(
                    "display:none", "display:inline"
                )
            for child in list(newsvg):
                if child.attrib["id"] not in keep:
                    newsvg.remove(child)
            labels = newsvg.findall(".//*[@id='abmessung']")
            for alc_id in clear_ids:
                labels.extend(newsvg.findall(f".//*[@id='Alcatraz_{alc_id}']"))
            for label in labels:
                label.clear()
            export_to_destination(
                newsvg,
                f"{dist_base}/alcatraz_{name}/{klasse}",
                "--export-id Export_Area -b FFFFFF",
            )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            f"Bitte Parcours SVG angeben! {sys.argv[0]} parcours.svg",
            file=sys.stderr,
        )
        sys.exit(1)
    parcours_file = sys.argv[1]
    if not os.path.isfile(parcours_file):
        print(f"{parcours_file} kann nicht gelesen werden!", file=sys.stderr)
        sys.exit(1)
    main(parcours_file)

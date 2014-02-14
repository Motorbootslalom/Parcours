#!/bin/zsh
set -x
for i in export/Parcours.png export/Klasse*.png; do NAME=$(basename $i .png); echo $NAME;read; inkscape parcours.svg -e $NAME.png; inkscape parcours.svg -E $NAME.eps; inkscape parcours.svg -A $NAME.pdf; done

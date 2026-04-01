

all: dist/de/Parcours.svg dist/parallel/en/Parcours.svg

dist/de/Parcours.svg : parcours.svg split.py
	python3 split.py $<

dist/parallel/en/Parcours.svg : parallel.svg split.py
	python3 split.py $<


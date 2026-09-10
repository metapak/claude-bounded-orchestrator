.PHONY: validate test release

validate:
	python3 scripts/validate.py

test:
	python3 -m unittest discover -s tests -v

release:
	python3 scripts/build_release.py

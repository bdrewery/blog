all: venv/build-venv
	venv/bin/python blog.py build

venv:
	virtualenv venv

venv/build-venv: venv requirements.txt
	venv/bin/pip install -r requirements.txt
	touch venv/build-venv

# Contributing To This Project
Pull requests to contribute to this project are welcome, but should adhere to the following guidelines.

## Formatting
- All contributions should be formatted using [black](https://pypi.org/project/black/) with a maximum line length of 120 characters. Generally, just run `black -l 120 .` from the root of the repository.
- All contributions should be fully compliant with PEP-8 (pycodestyle, 120 char line length) and PEP-257 (pydocstyle). 

## Unit Tests
- Unit tests are run from the `smb_to_kodi` subfolder, in a virtualenv with all requirements installed, using `coverage run --source='.' manage.py test`.
- All unit tests must pass.
- All code under the `tv/` folder must have 100% coverage according to `coverage report`.
- Exclusions from coverage are allowed using `# pragma: no cover` in reasonable situations.

## Running Locally
It's much easier to run the server locally for development purposes if you skip the Docker container and do the following:
1. Create a `db` and `logs` folder in the same folder as manage.py.
2. Create a secret.key file in the same folder as manage.py.
3. Use `python manage.py runserver` to run the server, which will allow browsing at `http://localhost:8000/tv`.

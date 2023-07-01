# BoldiBackup – Backup scripts

## Setup

```shell
python -m venv .venv
. .venv/bin/activate
pip install --no-deps -r requirements.txt
pip install --no-deps --editable '.[dev]'
```

## Update dependencies

```shell
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install --upgrade --editable '.[dev]'
pip freeze --all --local --exclude-editable >requirements.txt
```

## `borg init`

```shell
python boldibackup.py borg -- init --encryption=ENCRYPTION ::
```
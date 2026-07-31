.PHONY: install test run seed demo migrate revision lint compose-up compose-down deploy

VENV ?= .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

install:               ## virtualenv va bog'liqliklar
	python3.12 -m venv $(VENV)
	$(PIP) install -q --upgrade pip
	$(PIP) install -r backend/requirements.txt

test:                  ## domen + bot testlari (majburiy!)
	cd backend && ../$(PY) -m pytest

run:                   ## lokal ishga tushirish (polling + API)
	cd backend && ../$(VENV)/bin/uvicorn app.main:app --reload --port 8000

seed:                  ## rollar, shablonlar, spravochniklar
	cd backend && ../$(PY) manage.py seed

demo:                  ## seed + namunaviy mashinalar
	cd backend && ../$(PY) manage.py demo

migrate:               ## alembic upgrade head
	cd backend && ../$(VENV)/bin/alembic upgrade head

revision:              ## yangi migratsiya: make revision M="izoh"
	cd backend && ../$(VENV)/bin/alembic revision --autogenerate -m "$(M)"

bot-info:              ## bot holati (getMe + webhook)
	cd backend && ../$(PY) manage.py bot-info

compose-up:
	docker compose up --build

compose-down:
	docker compose down

deploy:                ## fly.io
	fly deploy

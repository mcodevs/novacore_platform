.PHONY: install test run seed demo migrate revision compose-up compose-down deploy \
        miniapp-install miniapp-dev miniapp-build

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

miniapp-install:       ## Mini App bog'liqliklari
	cd miniapp && npm install --no-audit --no-fund

miniapp-dev:           ## Mini App dev-server (API → localhost:8000 ga proxy)
	cd miniapp && npm run dev

miniapp-build:         ## Mini App'ni yig'ib backend'ga qo'yish (/app yo'lida beriladi)
	cd miniapp && npm run build
	rm -rf backend/miniapp_dist && cp -r miniapp/dist backend/miniapp_dist

compose-up:
	docker compose up --build

compose-down:
	docker compose down

deploy:                ## fly.io
	fly deploy

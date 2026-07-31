.PHONY: bootstrap install test run seed demo migrate revision compose-up compose-down deploy \
        miniapp-install miniapp-dev miniapp-build

VENV ?= .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

bootstrap:             ## ⭐ Lokal muhitni noldan tayyorlaydi (venv + .env + npm + seed)
	@test -d $(VENV) || python3.12 -m venv $(VENV)
	@$(PIP) install -q --upgrade pip
	@$(PIP) install -q -r backend/requirements.txt
	@if [ ! -f backend/.env ]; then \
		sed -e "s|^JWT_SECRET=.*|JWT_SECRET=$$(openssl rand -hex 32)|" \
		    -e "s|^WEBHOOK_SECRET=.*|WEBHOOK_SECRET=$$(openssl rand -hex 16)|" \
		    backend/.env.example > backend/.env; \
		echo "✅ backend/.env yaratildi (kalitlar tasodifiy generatsiya qilindi)"; \
	else \
		echo "ℹ️  backend/.env allaqachon bor — tegilmadi"; \
	fi
	@cd miniapp && npm install --no-audit --no-fund --silent
	@$(MAKE) --no-print-directory demo
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Qoldi bitta qadam: backend/.env ichida BOT_TOKEN ni yozing."
	@echo "  ⚠️  LOKAL uchun ALOHIDA test bot oching (BotFather → /newbot),"
	@echo "      prod bot tokeni bilan ishlatmang — webhook bilan to'qnashadi."
	@echo ""
	@echo "So'ng o'zingizni reyestrga qo'shing va ishga tushiring:"
	@echo "  cd backend && ../$(PY) manage.py employee-add \"F.I.Sh.\" +998XXXXXXXXX admin"
	@echo "  make run"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

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

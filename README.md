# Insight

**Managed Network Portal** — ett internt verktyg för TERAFALK AB för att hantera kunder, övervaka nätverksintegrationer och automatiskt generera och skicka månadsrapporter.

---

## Funktioner

- **Kundhantering** — Lägg till, redigera och ta bort kunder med kontaktuppgifter
- **Integrationer** — Koppla och verifiera UniFi och Microsoft 365 per kund
- **Live-data** — Realtidsöverblick av WAN-status, ISP-mått, enheter och M365-hälsa
- **Rapporter** — Automatiska PDF-månadsrapporter skickade via Microsoft Graph
- **Schemaläggning** — Konfigurerbar cron-trigger (standard: 1:a varje månad, 08:00)
- **Rollbaserad åtkomst** — Admin (full åtkomst) och Kund (egen vy)

---

## Stack

| Lager | Teknik |
|---|---|
| Frontend | Vanilla JS · Nginx Alpine |
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 (async) |
| Databas | PostgreSQL 16 |
| PDF | WeasyPrint · Jinja2 |
| E-post | Microsoft Graph API |
| Auth | JWT (Bearer token) · bcrypt |
| Kryptering | Fernet AES-256 (API-nycklar i databasen) |
| Rate limiting | slowapi (5 inloggningsförsök/minut per IP) |
| Deploy | Docker Compose |

---

## Installation (första gången)

### Förutsättningar

- Docker + Docker Compose installerat på servern
- En domän med HTTPS (t.ex. via Nginx Proxy Manager)
- En Microsoft Azure-app för e-postutskick (se nedan)
- (Valfritt) En Microsoft Azure-app för M365-kundintegration (se nedan)

---

### Steg 1 — Klona repot

```bash
git clone https://github.com/terafalk/insight.git
cd insight
```

---

### Steg 2 — Skapa `.env`

```bash
cp .env.example .env
nano .env   # eller valfri editor
```

#### Generera säkra nycklar

**JWT-signeringsnyckel** (`SECRET_KEY`):
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Fernet-krypteringsnyckel** (`ENCRYPTION_KEY`):
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> **Viktigt:** Spara `ENCRYPTION_KEY` på ett säkert ställe. Om den tappas bort kan inte befintliga API-nycklar i databasen dekrypteras.

#### Minimal `.env` för uppstart

```env
# Databas
POSTGRES_DB=insight
POSTGRES_USER=insight
POSTGRES_PASSWORD=<starkt lösenord>

# Säkerhet
SECRET_KEY=<genererad JWT-nyckel>
ENCRYPTION_KEY=<genererad Fernet-nyckel>
ALLOWED_ORIGINS=https://insight.terafalk.com

# Första admin
FIRST_ADMIN_EMAIL=admin@terafalk.com
FIRST_ADMIN_PASSWORD=<tillfälligt lösenord — byt vid inloggning>

# Microsoft Graph e-post (krävs för att skicka rapporter)
GRAPH_TENANT_ID=<TERAFALK:s tenant-ID>
GRAPH_CLIENT_ID=<app client ID>
GRAPH_CLIENT_SECRET=<client secret>
GRAPH_SENDER=noreply@terafalk.com
```

Se [`.env.example`](.env.example) för fullständig beskrivning av alla variabler.

---

### Steg 3 — Starta

```bash
docker compose up -d
```

Första uppstarten bygger Docker-images och skapar databasen — kan ta 2–3 minuter. Kontrollera att allt startade korrekt:

```bash
docker compose logs -f backend
# Förväntat: "Application startup complete."
```

---

### Steg 4 — Konfigurera Nginx Proxy Manager

Skapa en proxy host som pekar på frontend-containern (port 80) och aktivera SSL. Se till att `ALLOWED_ORIGINS` i `.env` matchar din domän.

---

### Steg 5 — Logga in och byt lösenord

Öppna `https://insight.terafalk.com` och logga in med `FIRST_ADMIN_EMAIL` + `FIRST_ADMIN_PASSWORD`. Byt lösenord direkt under **Inställningar → Användare**.

---

## Uppdatera till ny version

```bash
git pull
docker compose up -d --build
```

Databasen och volymerna (`pg_data`, `report_output`) bevaras automatiskt.

---

## Microsoft Azure-appar

### App 1 — E-postutskick (single-tenant)

Registrera en app i **TERAFALK:s** Azure-tenant:

| Inställning | Värde |
|---|---|
| Typ | Single-tenant |
| Behörighet | `Mail.Send` (Application) |
| Admin consent | Krävs (Global Admin) |

Kopiera **Tenant ID**, **Client ID** och ett **Client Secret** till `.env` som `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`.

---

### App 2 — M365 kundintegration (multi-tenant)

Registrera en app i TERAFALK:s tenant med stöd för **multi-tenant**:

| Inställning | Värde |
|---|---|
| Typ | Multi-tenant |
| Redirect URI | `https://insight.terafalk.com/api/auth/microsoft/callback` |

Lägg till följande **Application permissions** (inte delegerade) och bevilja admin consent:

| Behörighet | Används till |
|---|---|
| `Organization.Read.All` | Tenant-information |
| `User.Read.All` | Användarlista och licenser |
| `UserAuthenticationMethod.Read.All` | MFA-status |
| `AuditLog.Read.All` | Inloggningsaktivitet |
| `Reports.Read.All` | OneDrive- och SharePoint-statistik |
| `RoleManagement.Read.Directory` | Admin-rolltilldelningar |
| `DeviceManagementManagedDevices.Read.All` | Intune-enheter |
| `SecurityEvents.Read.All` | Secure Score |

Kopiera **Client ID** och **Client Secret** till `.env` som `MS_APP_CLIENT_ID`, `MS_APP_CLIENT_SECRET`.

Kunder kopplas sedan via **Kunder → välj kund → Integrationer → Microsoft 365 → Koppla** — en admin consent-länk skickas till kundens IT-admin.

---

## Rapportschema

Standard: 1:a varje månad kl. 08:00 (Europe/Stockholm). Ändras i `.env`:

```env
REPORT_SCHEDULE_DAY=1        # Dag i månaden (1–28)
REPORT_SCHEDULE_HOUR=8       # Timme (0–23, 24h-format)
REPORT_SCHEDULE_MINUTE=0     # Minut (0–59)
```

Rapporter kan också köras manuellt per kund: **Kunder → välj kund → Generera rapport**.

---

## API-dokumentation

Swagger UI finns tillgänglig på:
```
https://insight.terafalk.com/api/docs
```
(Kräver inloggning — använd "Authorize"-knappen med din JWT-token.)

---

## Projektstruktur

```
insight/
├── backend/
│   └── app/
│       ├── api/           # REST-endpoints (auth, customers, reports, …)
│       ├── core/          # Config, säkerhet, scheduler, cache, limiter
│       ├── db/            # SQLAlchemy-modeller, init och seed
│       ├── integrations/  # Adaptrar per tjänst (unifi/, microsoft/)
│       ├── reports/       # PDF-generering (WeasyPrint) och rapport-runner
│       └── graph/         # Microsoft Graph e-postsändare
├── frontend/
│   ├── index.html         # Single-page app (Vanilla JS)
│   ├── assets/            # Logotyper och favicon
│   └── nginx.conf         # Reverse proxy till backend
├── .env.example           # Mall för miljövariabler
└── docker-compose.yml
```

---

## Felsökning

**Backend startar inte:**
```bash
docker compose logs backend --tail=50
```

**Kan inte ansluta till databasen:**
```bash
docker compose logs db --tail=20
# Kontrollera att POSTGRES_PASSWORD är satt i .env
```

**CORS-fel i webbläsaren:**
- Kontrollera att `ALLOWED_ORIGINS` i `.env` matchar exakt den URL du använder (inkl. `https://`)

**Rapporter skickas inte:**
- Kontrollera att `GRAPH_*`-variablerna är korrekt ifyllda
- Verifiera att admin consent är beviljat för Graph-appen i Azure

**Krypteringsfel ("Fernet key must be 32 url-safe base64-encoded bytes"):**
- `ENCRYPTION_KEY` är troligtvis en gammal okrypterad sträng — se [`.env.example`](.env.example) för hur en giltig nyckel genereras

---

## Licens

Intern mjukvara — © TERAFALK AB. Ej för distribution.

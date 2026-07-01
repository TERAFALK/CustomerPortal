# Databasmigrationer (Alembic)

Insight använder än så länge `app/db/database.py::init_db` (idempotent
`create_all` + `ALTER`) som körväg vid uppstart. Alembic är uppsatt bredvid och
redo att bli den enda schema-auktoriteten när du gjort en verifierad övergång.

## Engångsadoption på befintlig databas

Din produktions-DB har redan schemat, så baslinjen ska **markeras** som körd —
inte köras:

```bash
docker compose exec backend alembic stamp 0001_baseline
docker compose exec backend alembic current   # ska visa 0001_baseline
```

Att `alembic current` svarar korrekt bevisar att env.py + DB-anslutningen
fungerar i containern. (Ingen risk — `stamp` rör inte tabellerna.)

## Framtida schemaändringar

```bash
# 1. Ändra modellerna i app/db/models.py
# 2. Generera migration (jämför modeller mot DB):
docker compose exec backend alembic revision --autogenerate -m "beskrivning"
# 3. Granska filen i alembic/versions/
# 4. Applicera:
docker compose exec backend alembic upgrade head
```

## Övergång (valfritt, när du är trygg)

När `alembic current` fungerar och du vill göra Alembic till enda auktoritet:
byt uppstarten så att `alembic upgrade head` körs istället för `create_all`,
och ta bort ALTER-listan ur `init_db`. Hör av dig så gör vi den ändringen
tillsammans och verifierar den.

Tills dess är båda ofarligt samexisterande: `init_db` är idempotent och
baslinjen är stampad, så den återkörs aldrig.

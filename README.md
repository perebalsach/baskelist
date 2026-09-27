# Baskelist

Una agenda de bàsquet per organitzar els partits i desplaçaments de la família. Primera versió, en català, adaptable al mòbil.

## Dues formes de provar-la

### Demo a GitHub Pages

`docs/` és una aplicació estàtica independent, sense passos de compilació. Inclou dades fictícies, navegació setmanal, filtres, perfils editables, importació HTML FCBQ i enllaços a Maps. Les dades es guarden en localStorage només en aquest navegador. No hi ha autenticació, sincronització familiar ni còpies de seguretat; no introduïu dades sensibles en dispositius compartits.

Adreça prevista: https://perebalsach.github.io/baskelist/

El workflow `.github/workflows/pages.yml` publica `docs/`. Cal configurar **Settings → Pages → Source → GitHub Actions**. Si encara no està habilitat, feu aquest canvi i torneu a executar el workflow des d'Actions.

### Aplicació amb servidor i comptes familiars

Requereix [uv](https://docs.astral.sh/uv/getting-started/installation/). El projecte selecciona Python 3.12; `uv` gestiona Python, les dependències i l’entorn `.venv`. Comandes per a Linux/macOS, des de l’arrel del repositori:

```bash
uv sync --locked
uv run app.py
```

Obriu http://127.0.0.1:5000 i creeu un compte familiar. La contrasenya ha de tenir 12 caràcters o més. Base de dades SQLite i clau de sessió a `instance/`, exclosos del repositori. Per usar un altre port: `PORT=5001 uv run app.py`.

## Importar un equip

1. Creeu el perfil amb un nom o àlies, equip, competició i identificador FCBQ.
2. Obriu al navegador el calendari mensual o global de l’equip a la Federació.
3. Deseu el document HTML, o copieu la resposta HTML de Network a un `.txt` UTF-8.
4. A Jugadors, carregueu-lo al perfil corresponent. Màxim 2 MB.
5. Navegueu a la setmana dels partits. El servidor obre la setmana actual; la demo passa a la primera setmana importada.

L’importador llegeix taules de locals i visitants, data, hora, categoria, pavelló, adreça, estat i identificador del partit. Fa upsert per jugador i partit, i no elimina partits absents en una importació mensual. Per eliminar un partit retirat del calendari cal, de moment, eliminar/recrear el perfil i reimportar. Els canvis s’apliquen quan torneu a carregar el fitxer, no automàticament. Les hores es tracten com a hores locals de Catalunya; una hora publicada com 00:00 es conserva literalment i s’ha de verificar si significa pendent.

La font FCBQ provada des de l’entorn de desenvolupament ha retornat una verificació reCAPTCHA. No hi ha cap mecanisme per eludir-la. Cal validar una via estable i autoritzada abans d’implementar sincronització periòdica.

`examples/calendar.html` conté dos partits totalment ficticis de l’equip `10001`, el 26 i 27 de setembre de 2026. No conté dades personals.

## Què funciona

- Registre, inici/tancament de sessió amb contrasenyes hash scrypt al servidor.
- Aïllament dels perfils i partits per família, comprovacions d’autorització, CSRF, límit d’intents d’autenticació i límit d’importació.
- Crear, editar i eliminar jugadors amb color identificatiu.
- Agenda setmanal, filtre per jugador, indicació local/visitant i resum.
- Avís bàsic quan dos partits diferents comencen exactament alhora. No calcula durades ni trajectes.
- Importació manual idempotent d’HTML i enllaços externs a FCBQ/Google Maps.

## Verificació

```bash
uv sync --locked
uv run --locked python -m pytest -q
```

Proves d’importació, reimportació sense duplicats, importació invàlida atòmica, autenticació, CSRF i accés entre famílies. Les dues variants (Python i JavaScript) tenen importadors separats; manteniu-los alineats quan canviï l’HTML FCBQ.

## Abans d’obrir els comptes a altres famílies

Aquesta versió amb servidor és un MVP local, no un servei públic acabat. GitHub Pages no executa Flask ni SQLite. Per als comptes reals cal un backend separat amb HTTPS, servidor WSGI, `SECRET_KEY` gestionada i `HTTPS_ONLY=1`; també verificació de correu, recuperació de contrasenya, eliminació/exportació de compte, còpies de seguretat, monitoratge i revisió de privacitat. No publiqueu `instance/` ni HTML privats.

Vegeu `ROADMAP.md` per a les fases següents.

## Dependències amb uv

`pyproject.toml` declara les dependències i `uv.lock` en fixa la resolució. No cal activar manualment `.venv`. Les dependències de desenvolupament s’instal·len per defecte.

- Afegir una dependència: `uv add paquet`
- Afegir una eina de desenvolupament: `uv add --dev paquet`
- Actualitzar les dependències dins dels límits declarats: `uv lock --upgrade` i `uv sync --locked`
- Després d’un `git pull`: `uv sync --locked`

Versioneu sempre junts els canvis de `pyproject.toml` i `uv.lock`. Les dependències amb versió exacta s’actualitzen explícitament amb `uv add paquet==nova_versio`.

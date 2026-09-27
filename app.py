import json
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from flask import Flask, request, session, redirect, render_template, flash, g, abort
from werkzeug.security import generate_password_hash, check_password_hash
from importer import parse_calendar

ROOT = Path(__file__).parent
COLORS = ['violet', 'orange', 'green', 'blue', 'pink']

def create_app(test_config=None):
    app = Flask(__name__)
    instance = ROOT / 'instance'
    instance.mkdir(exist_ok=True)
    secret = instance / 'secret'
    if not secret.exists():
        try:
            fd = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f:
                f.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secret.read_text(), DATABASE=str(instance / 'app.db'),
        MAX_CONTENT_LENGTH=2*1024*1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('HTTPS_ONLY') == '1', PERMANENT_SESSION_LIFETIME=timedelta(days=7))
    if test_config:
        app.config.update(test_config)

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'])
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys=ON')
        return g.db

    @app.teardown_appcontext
    def close(error):
        if 'db' in g:
            g.db.close()

    with app.app_context():
        db().executescript('''
        CREATE TABLE IF NOT EXISTS families(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS players(id INTEGER PRIMARY KEY, family_id INTEGER NOT NULL REFERENCES families(id), name TEXT NOT NULL, color TEXT NOT NULL, team_id TEXT NOT NULL, team TEXT NOT NULL, competition TEXT NOT NULL, imported_at TEXT);
        CREATE TABLE IF NOT EXISTS games(player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE, source_id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(player_id,source_id));
        CREATE TABLE IF NOT EXISTS attempts(ip TEXT NOT NULL, at REAL NOT NULL);
        ''')

    @app.before_request
    def protect():
        session.setdefault('csrf', secrets.token_hex(32))
        if request.method == 'POST' and not secrets.compare_digest(session['csrf'], request.form.get('csrf', '')):
            abort(400, 'Formulari caducat. Recarrega la pàgina.')
        g.family = db().execute('SELECT * FROM families WHERE id=?', (session.get('family'),)).fetchone()
        if request.endpoint not in ('auth', 'static') and not g.family:
            return redirect('/login')

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.context_processor
    def context():
        return dict(csrf=session.get('csrf'), colors=COLORS)

    @app.route('/login', methods=['GET', 'POST'])
    @app.route('/register', methods=['GET', 'POST'])
    def auth():
        register = request.path == '/register'
        if request.method == 'POST':
            ip, now = request.remote_addr or 'local', time.time()
            db().execute('DELETE FROM attempts WHERE at < ?', (now - 900,))
            count = db().execute('SELECT count(*) FROM attempts WHERE ip=?', (ip,)).fetchone()[0]
            if count >= 15:
                abort(429, 'Massa intents. Torna-ho a provar d’aquí a 15 minuts.')
            db().execute('INSERT INTO attempts VALUES (?,?)', (ip, now)); db().commit()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            name = request.form.get('name', '').strip()
            if register:
                if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(email)>254 or not 12<=len(password)<=256 or not 1<=len(name)<=60:
                    flash('Revisa les dades. La contrasenya ha de tenir entre 12 i 256 caràcters.')
                    return render_template('auth.html', register=register), 400
                try:
                    db().execute('INSERT INTO families(name,email,password) VALUES (?,?,?)', (name,email,generate_password_hash(password)))
                    db().commit()
                except sqlite3.IntegrityError:
                    flash('No es pot crear aquest compte. Prova d’iniciar sessió.')
                    return render_template('auth.html', register=register), 400
            family = db().execute('SELECT * FROM families WHERE email=?', (email,)).fetchone()
            if not family or not check_password_hash(family['password'], password):
                flash('Correu o contrasenya incorrectes.')
                return render_template('auth.html', register=register), 401
            session.clear(); session['family']=family['id']; session['csrf']=secrets.token_hex(32); session.permanent=True
            return redirect('/')
        return render_template('auth.html', register=register)

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect('/login')

    def own_player(pid):
        p = db().execute('SELECT * FROM players WHERE id=? AND family_id=?', (pid,g.family['id'])).fetchone()
        if not p: abort(404)
        return p

    @app.route('/players', methods=['GET', 'POST'])
    def players():
        if request.method == 'POST':
            fields = {k:request.form.get(k,'').strip() for k in ['name','team','team_id','competition','color']}
            if not all(fields.values()) or not re.fullmatch(r'\d{1,12}',fields['team_id']) or fields['color'] not in COLORS or any(len(v)>150 for v in fields.values()):
                abort(400, 'Revisa els camps del jugador.')
            pid = request.form.get('id')
            if pid:
                old=own_player(pid)
                if old['team_id'] != fields['team_id']:
                    db().execute('DELETE FROM games WHERE player_id=?',(pid,))
                    db().execute('UPDATE players SET imported_at=NULL WHERE id=?',(pid,))
                db().execute('UPDATE players SET name=?,team=?,team_id=?,competition=?,color=? WHERE id=?',(*[fields[k] for k in ['name','team','team_id','competition','color']],pid))
            else:
                db().execute('INSERT INTO players(family_id,name,team,team_id,competition,color) VALUES (?,?,?,?,?,?)',(g.family['id'],*[fields[k] for k in ['name','team','team_id','competition','color']]))
            db().commit(); flash('Perfil desat.'); return redirect('/players')
        items=db().execute('SELECT * FROM players WHERE family_id=? ORDER BY id',(g.family['id'],)).fetchall()
        edit=own_player(request.args['edit']) if 'edit' in request.args else None
        return render_template('players.html',players=items,edit=edit)

    @app.post('/players/<int:pid>/delete')
    def delete(pid):
        own_player(pid); db().execute('DELETE FROM players WHERE id=?',(pid,)); db().commit()
        flash('Perfil eliminat.'); return redirect('/players')

    @app.post('/players/<int:pid>/import')
    def import_html(pid):
        player=own_player(pid)
        file=request.files.get('calendar')
        if not file:
            abort(400)
        try:
            games=parse_calendar(file.read().decode('utf-8-sig'),player['team_id'])
        except (ValueError,UnicodeError):
            flash('No s’ha importat: cal un HTML UTF-8 del calendari d’aquest equip amb dates i hores vàlides.'); return redirect('/players')
        changes=0
        for game in games:
            old=db().execute('SELECT payload FROM games WHERE player_id=? AND source_id=?',(pid,game['source_id'])).fetchone()
            if old and json.loads(old['payload']) != game: changes+=1
            db().execute('INSERT INTO games VALUES (?,?,?) ON CONFLICT(player_id,source_id) DO UPDATE SET payload=excluded.payload',(pid,game['source_id'],json.dumps(game,ensure_ascii=False)))
        stamp=datetime.now(ZoneInfo('Europe/Madrid')).strftime('%d/%m/%Y %H:%M')
        db().execute('UPDATE players SET imported_at=? WHERE id=?',(stamp,pid)); db().commit()
        flash(f'{len(games)} partits importats · {changes} actualitzats.'); return redirect('/')

    @app.get('/')
    def agenda():
        today=datetime.now(ZoneInfo('Europe/Madrid')).date()
        try: selected=datetime.strptime(request.args.get('week',today.isoformat()),'%Y-%m-%d').date()
        except ValueError: selected=today
        monday=selected-timedelta(days=selected.weekday()); sunday=monday+timedelta(days=6)
        players=db().execute('SELECT * FROM players WHERE family_id=? ORDER BY id',(g.family['id'],)).fetchall()
        chosen=request.args.get('player','')
        rows=db().execute('SELECT games.payload,players.id,players.name,players.color,players.imported_at FROM games JOIN players ON players.id=games.player_id WHERE players.family_id=?',(g.family['id'],)).fetchall()
        games=[]
        for row in rows:
            game=json.loads(row['payload'])
            if monday.isoformat()<=game['date']<=sunday.isoformat() and (not chosen or str(row['id'])==chosen):
                game.update(player=row['name'],color=row['color'],imported_at=row['imported_at'])
                game['date_label']=datetime.fromisoformat(game['date']).strftime('%d/%m')
                games.append(game)
        games.sort(key=lambda x:(x['date'],x['time']))
        for game in games:
            game['conflict']=any(other is not game and other['date']==game['date'] and other['time']==game['time'] and other['source_id']!=game['source_id'] for other in games)
        return render_template('agenda.html',players=players,games=games,chosen=chosen,monday=monday,sunday=sunday,previous=(monday-timedelta(days=7)).isoformat(),following=(monday+timedelta(days=7)).isoformat(),today=today)
    return app

if __name__ == '__main__':
    create_app().run(host='127.0.0.1',port=int(os.environ.get('PORT','5000')))

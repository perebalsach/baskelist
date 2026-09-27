import io
import sqlite3
from pathlib import Path
import pytest
from app import create_app
from importer import parse_calendar

FIXTURE=Path(__file__).parent.parent/'examples/calendar.html'

@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING':True,'DATABASE':str(tmp_path/'test.db'),'SECRET_KEY':'test-only'})

def post(client,url,data=None):
    client.get('/login')
    with client.session_transaction() as s: token=s['csrf']
    return client.post(url,data={**(data or {}),'csrf':token},follow_redirects=False)

def register(c,email):
    return post(c,'/register',dict(email=email,password='long-password-123',name='Test family'))

def player(c):
    post(c,'/players',dict(name='Player',team='Example',team_id='10001',competition='Cadet',color='violet'))

def test_parse():
    games=parse_calendar(FIXTURE.read_text(),'10001')
    assert len(games)==2
    assert {g['is_home'] for g in games}=={True,False}
    assert games[0]['time']=='10:30'
    assert games[0]['address']=='Carrer Exemple, 1'
    with pytest.raises(ValueError):parse_calendar(FIXTURE.read_text(),'999')

def test_auth_and_csrf(app):
    c=app.test_client()
    assert c.get('/').status_code==302
    assert c.post('/register',data={}).status_code==400
    assert register(c,'one@example.com').status_code==302
    assert c.get('/').status_code==200
    post(c,'/logout')
    assert post(c,'/login',dict(email='one@example.com',password='wrong')).status_code==401

def test_isolation_and_import(app):
    a,b=app.test_client(),app.test_client()
    register(a,'one@example.com');player(a)
    register(b,'two@example.com')
    assert b.get('/players?edit=1').status_code==404
    assert post(b,'/players/1/delete').status_code==404
    assert post(b,'/players/1/import').status_code==404
    for _ in range(2):
        response=post(a,'/players/1/import',{'calendar':(io.BytesIO(FIXTURE.read_bytes()),'calendar.html')})
        assert response.status_code==302
    assert b'BASQUET EXEMPLE' in a.get('/?week=2026-09-21').data
    assert b'BASQUET EXEMPLE' not in b.get('/?week=2026-09-21').data
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('select count(*) from games').fetchone()[0]==2
        assert not db.execute('select password from families').fetchone()[0].startswith('long-password')
    post(a,'/players/1/delete')
    with sqlite3.connect(app.config['DATABASE']) as db:
        assert db.execute('select count(*) from games').fetchone()[0]==0

def test_atomic_bad_import(app):
    c=app.test_client();register(c,'one@example.com');player(c)
    data=FIXTURE.read_text().replace('27/09/2026','99/09/2026')
    post(c,'/players/1/import',{'calendar':(io.BytesIO(data.encode()),'bad.html')})
    with sqlite3.connect(app.config['DATABASE']) as db:assert db.execute('select count(*) from games').fetchone()[0]==0

import re
from datetime import datetime
from bs4 import BeautifulSoup


def parse_calendar(html, team_id):
    soup = BeautifulSoup(html, 'html.parser')
    result = {}
    for row in soup.select('#calendar-team table tbody tr'):
        cells = row.find_all('td', recursive=False)
        if len(cells) < 7:
            continue
        teams = [cells[i].find('a', href=re.compile(r'^/equip/\d+$')) for i in (2, 3)]
        if not all(teams):
            continue
        ids = [a['href'].rsplit('/', 1)[-1] for a in teams]
        if str(team_id) not in ids:
            continue
        link = cells[6].find('a', href=re.compile(r'^/partits/llistatpartits/\d+$'))
        if not link:
            raise ValueError('Hi ha un partit sense identificador. No s’ha importat el fitxer.')
        date = datetime.strptime(cells[0].get_text(strip=True), '%d/%m/%Y').date().isoformat()
        hour = cells[1].get_text(strip=True)
        if hour:
            datetime.strptime(hour, '%H:%M')
        venue = list(cells[5].stripped_strings)
        key = link['href'].rsplit('/', 1)[-1]
        result[key] = dict(source_id=key, date=date, time=hour, home=teams[0].get_text(strip=True),
            away=teams[1].get_text(strip=True), is_home=ids[0] == str(team_id),
            competition=cells[4].get_text(' ', strip=True), venue=venue[0] if venue else '',
            address=' '.join(venue[1:]), source_changed=bool(cells[6].find('img', title='Canvis')),
            status='suspended' if cells[6].find('img', title='Suspès') else 'postponed' if cells[6].find('img', title='Ajornat') else 'scheduled')
    if not result:
        raise ValueError('No s’han trobat partits d’aquest equip. Comprova el fitxer i l’identificador de l’equip.')
    return list(result.values())

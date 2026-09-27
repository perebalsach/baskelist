# Pla de desenvolupament de Baskelist

## 1. MVP local i demo pública — implementat
Agenda adaptable, perfil de jugador, importació HTML, filtres, pavelló/Maps. Demo estàtica sense compte i backend Flask amb comptes familiars independents. Disseny verd fosc/crema, jerarquia clara d’horaris i colors per jugador.

## 2. Accés fiable a dades — dependència pendent
Validar API, exportació o accés acordat amb FCBQ. Identificar temporades i fases. No confondre calendari incomplet amb cancel·lació. Crear adaptador de font, reintents limitats, cua i indicació visible d’última sincronització/errada. Una importació per equip compartida per les famílies, amb separació de dades personals. Afegir fixtures per HTML global, ajornaments, hores pendents i canvis de temporada.

## 3. Comptes públics i model estable
Frontend únic connectat a API; retirar la duplicació demo/servidor. PostgreSQL amb migracions. Family → Player → TeamMembership(season, team, competition); entitats compartides Team, Competition, Venue, Match. El MVP vincula directament un equip a cada perfil: falta historial i múltiples equips per jugador. Completar correu verificat, recuperació de contrasenya, gestió del compte i invitacions opcionals; el primer requisit continua sent un compte compartit per família.

## 4. Planificació de desplaçaments
Lloc de sortida opcional, marge d’arribada per jugador, durada estimada del partit, geocodificació revisable, temps entre pavellons i assignació de conductor. Presentar estimacions i incertesa de trànsit; solapament calculat per intervals, no només hora d’inici.

## 5. Calendari i notificacions
Subscripció ICS privada revocable, historial real de canvis, avisos de data/hora/pavelló, preferències familiars i resum de cap de setmana. Evitar avisos duplicats. PWA i estratègia offline que no presenti dades antigues com a actuals.

## Criteris UX
Pantalla inicial amb agenda de cap de setmana i accés a tota la setmana. Diferenciar sense partits, sense dades i font no disponible. Disseny accessible amb text a més dels colors, teclat, focus visible, contrast i proves en mòbil. Confirmació d’eliminació i importació amb resultats clars. Cap dada personal de menors a la demo pública.

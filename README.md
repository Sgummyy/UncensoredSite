# Uncensored Runners – sito web

Sito della scuola di parkour **Uncensored Runners** (Padova), migrato da Jimdo.
È un sito statico: veloce, sicuro e ospitabile gratis. I contenuti si modificano da un pannello su `/admin`.

## Come è fatto

| Cartella / file | Cosa contiene |
|---|---|
| `content/settings.yml` | Telefono, email, social, menu, testi del piè di pagina |
| `content/home.yml` | Testi e foto della home |
| `content/pages/*.yml` | Le pagine (corsi, bambini, chi siamo…), composte a blocchi |
| `content/posts/*.md` | Gli articoli del blog |
| `static/` | Foto (`static/uploads`), PDF, logo, stile e script del sito |
| `admin/` | Il pannello di gestione (Sveltia CMS) |
| `build.py` | Genera il sito finito nella cartella `dist/` |

Gli indirizzi delle pagine sono identici a quelli del vecchio sito Jimdo, per non perdere il posizionamento su Google. I vecchi indirizzi `.html` sono reindirizzati (`_redirects`).

## Provarlo sul computer

```bash
pip install -r requirements.txt
python3 build.py                 # crea dist/
cd dist && python3 -m http.server 8000   # apri http://localhost:8000
```

`python3 build.py anteprima preview` crea una versione che si apre anche con un doppio clic sui file, senza server.

## Pubblicazione su Netlify (gratis)

1. Su [netlify.com](https://app.netlify.com) → **Add new site → Import an existing project → GitHub** → scegli questo repository.
2. Le impostazioni di build sono già in `netlify.toml`: non va cambiato nulla. Clicca **Deploy**.
3. **Modulo contatti:** in *Site configuration → Forms* abilita il rilevamento dei moduli (*Enable form detection*) e poi rifai il deploy. In *Forms → Form notifications* aggiungi una notifica email verso `info@uncensoredrunners.com`.
4. **Dominio:** in *Domain management* aggiungi `www.uncensoredrunners.com` e segui le istruzioni DNS. Fallo solo **dopo** aver trasferito il dominio da Jimdo.

Ogni modifica salvata dal pannello (o caricata su GitHub) ripubblica il sito da sola in 1–2 minuti.

## Il pannello di gestione (`/admin`)

Il cliente apre `https://www.uncensoredrunners.com/admin/` e trova:

- **Articoli del blog** – scrivere, modificare, salvare come bozza, aggiungere foto.
- **Pagine** – ogni pagina è una sequenza di blocchi (titolo, testo, foto, pulsante, video, colonne, PDF, modulo contatti) che si possono modificare, spostare, aggiungere o togliere.
- **Home e impostazioni** – testi e foto della home, telefono, email, social, voci del menu.

### Accesso

Chi usa il pannello deve avere un account GitHub con permesso di **scrittura** su questo repository
(*Settings → Collaborators → Add people*).

Ci sono due modi per entrare:

**A. Con un token (subito, senza configurare nulla).** Nella pagina di accesso si sceglie *Sign in with token* e si incolla un *personal access token* GitHub (fine-grained, limitato a questo repository, permesso *Contents: Read and write*). Il token resta salvato nel browser.

**B. Con il pulsante "Accedi con GitHub" (più comodo per il cliente).** Serve un piccolo servizio gratuito su Cloudflare:

1. Pubblica il [Sveltia CMS Authenticator](https://github.com/sveltia/sveltia-cms-auth) su Cloudflare Workers (piano gratuito), seguendo le istruzioni del suo README.
2. Su GitHub crea una *OAuth App* (*Settings → Developer settings → OAuth Apps*) con *Authorization callback URL* = `https://<nome-worker>.<account>.workers.dev/callback` e copia Client ID e Client Secret nelle variabili del worker.
3. In `admin/config.yml`, dentro `backend`, aggiungi `base_url: https://<nome-worker>.<account>.workers.dev`.

## Costi

| Voce | Costo |
|---|---|
| Hosting e modulo contatti (Netlify, piano gratuito) | 0 € |
| Pannello (Sveltia CMS) e accesso (Cloudflare Workers, gratuito) | 0 € |
| Dominio `.com` (es. Cloudflare Registrar) | circa 10 €/anno |

## Da completare prima del lancio

- [ ] Informativa privacy: il testo attuale arriva da Jimdo e descrive il vecchio hosting. Va aggiornata.
- [ ] PDF "Statuto": sul vecchio sito puntava allo stesso file dell'informativa privacy. Caricare lo statuto corretto.
- [ ] Link Instagram in *Home e impostazioni → Contatti*.
- [ ] Verificare la licenza dell'illustrazione nell'articolo "Programma di allenamento vacanze di Natale".

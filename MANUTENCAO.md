# Guia de Manutenção e Evolução — Sistema "Ponto Doméstico"

> **Como usar este guia:** ao abrir uma nova conversa para melhorar ou alterar o
> sistema, entregue este arquivo ao assistente logo no início. Ele contém tudo o
> que é necessário para entender a arquitetura, o ambiente de deploy e as regras
> de trabalho, sem depender de memória de conversas anteriores.

---

## 1. O que é o sistema

Aplicação web (PWA) para **registro interno de jornada** de empregados domésticos
e babá, com parâmetros da **LC 150/2015**. Uso interno, **não** destinado à
fiscalização.

- **Stack:** Flask + SQLite + Docker (servido por gunicorn).
- **Dois públicos:** painel administrativo (empregador) e tela mobile de registro
  (colaboradores), com botão único inteligente (1º toque = entrada, 2º = saída).
- **Recursos:** geofence, dashboard, exportação `.xlsx`, espelho em PDF, exceções
  (férias/folgas/feriados), auditoria de ajustes e relatório mensal automático por
  e-mail via n8n.

---

## 2. Onde está hospedado (produção)

| Item | Valor |
|---|---|
| Repositório | `github.com/rafaeljrocha/ponto-domestica` (branch **`main`**) |
| Deploy | EasyPanel, no VPS Hostinger (IP `72.61.42.105`), build por **Dockerfile** |
| Domínio | `https://ponto-domestik.rafaeljrocha.cloud` (porta **5000**, roteamento interno **HTTP**) |
| Volume persistente | montado em **`/app/data`** (contém `ponto.db` e a pasta `selfies`) |
| Painel admin | `/admin/login` — usuário `rafael` (senha na env `ADMIN_SENHA`) |
| Tela do colaborador | `/entrar` (login por PIN) e `/registro/` |

**Variáveis de ambiente (definidas no EasyPanel — os valores NÃO ficam no
repositório):** `SECRET_KEY`, `ADMIN_USUARIO`, `ADMIN_SENHA`,
`DB_PATH=/app/data/ponto.db`, `UPLOAD_DIR=/app/data/selfies`, `RELATORIO_EMAIL`.
(`N8N_WEBHOOK_URL` é opcional aqui — o webhook é configurado na tela
**Configurações** do próprio sistema, gravado no banco.)

---

## 3. Restrições operacionais — LEIA ANTES DE ALTERAR

1. **Rafael não usa Git no terminal.** Alterações chegam ao GitHub por **API**
   (com um token temporário que ele gera na hora) ou por **upload web**. Nunca
   oriente `git clone`/`git push` locais.
2. **O assistente não alcança a infraestrutura.** O ambiente do assistente só
   acessa domínios liberados (`github.com`, `api.github.com`, `pypi.org` etc.).
   **Não** alcança o EasyPanel, o VPS nem o n8n. Portanto, o fluxo é sempre:
   *assistente altera o código e sobe no GitHub → Rafael clica em Deploy no
   EasyPanel*.
3. Após **qualquer** push, é preciso **Deploy** no EasyPanel para aplicar.
4. Roteamento interno no EasyPanel é **HTTP**, não HTTPS.

---

## 4. Fluxo para fazer uma alteração (passo a passo do assistente)

1. **Obter os arquivos atuais.** Baixe do repositório os arquivos a editar
   (GitHub API: `GET /repos/rafaeljrocha/ponto-domestica/contents/{path}?ref=main`,
   campo `content` em base64) ou reconstrua o projeto a partir do repo.
2. **Editar e testar localmente** — ver seção 9 (padrão de teste).
3. **Pedir ao Rafael um token fine-grained** do GitHub: repositório
   `ponto-domestica`, permissão **Contents: Read and write**, validade curta.
4. **Subir a alteração** (ver snippets abaixo):
   - **Um arquivo:** `GET contents` para pegar o `sha` atual → `PUT contents`
     com o novo conteúdo em base64, o `sha` e `branch=main`.
   - **Vários arquivos em um único commit:** use a **Git Data API** — crie blobs,
     monte uma tree com `base_tree` = tree do commit atual, crie o commit com
     `parents=[commit_atual]` e atualize a ref `heads/main`.
5. **Rafael faz Deploy** no EasyPanel e valida no navegador/celular.
6. **Rafael revoga o token** ao final.

### Snippet — atualizar UM arquivo (Contents API)
```python
import base64, requests
API="https://api.github.com/repos/rafaeljrocha/ponto-domestica"
h={"Authorization":f"Bearer {TOKEN}","Accept":"application/vnd.github+json",
   "X-GitHub-Api-Version":"2022-11-28"}
path="blueprints/admin.py"
sha=requests.get(f"{API}/contents/{path}?ref=main",headers=h).json()["sha"]
content=base64.b64encode(open(path,"rb").read()).decode()
requests.put(f"{API}/contents/{path}",headers=h,json={
    "message":"descricao da mudanca","content":content,"sha":sha,"branch":"main"})
```

### Snippet — vários arquivos em UM commit (Git Data API)
```python
# 1) ref atual -> base_commit; 2) commit -> base_tree
# 3) POST /git/blobs (por arquivo) ; 4) POST /git/trees (com base_tree)
# 5) POST /git/commits (parents=[base_commit]) ; 6) PATCH /git/refs/heads/main
# Observação: se algum passo retornar 409 logo após uma escrita, repita após ~3s.
```
> O repositório já contém commits; **não** há mais o problema de "repo vazio"
> (que exige inicializar com um arquivo antes da Git Data API).

---

## 5. Estrutura de arquivos

```
app.py            factory Flask, inicializa DB, registra blueprints, agenda relatório (APScheduler)
config.py         leitura de variáveis de ambiente e defaults
tempo.py          horário local America/Sao_Paulo (ver seção 8) — USAR SEMPRE
models.py         entidades SQLAlchemy (ver seção 6)
jornada.py        motor de cálculo LC 150 + geofence (ver seção 7)
servico.py        agrega registros+regras+exceções+feriados por colaborador/mês
seed.py           semente inicial: admin, local base (Casa G23), feriados, config
blueprints/
  auth.py         login admin (usuário/senha) e colaborador (PIN); decorators admin_req/colab_req
  registro.py     tela mobile + POST /registro/marcar (geoloc, selfie, comprovante)
  admin.py        CRUD colaboradores/regras, locais/geofence, exceções, feriados, ajustes, config
  dashboard.py    painel de métricas, detalhe por colaborador, API de gráfico
  export.py       geração de .xlsx (openpyxl) e espelho PDF (WeasyPrint)
  report.py       monta o relatório e dispara o webhook do n8n
templates/        base + login + registro mobile + páginas admin + espelho_pdf.html
static/           css/style.css, js/registro.js, js/money.js, js/dashboard (inline), manifest.json, sw.js, icons/
n8n/              relatorio_mensal_ponto.json (workflow de envio)
Dockerfile        imagem (inclui libs de sistema do WeasyPrint e tzdata)
requirements.txt  dependências Python
```

---

## 6. Modelo de dados (models.py)

- **Admin**: usuário/senha (hash) do painel.
- **Local**: geofence editável (`latitude`, `longitude`, `raio_m`, `tolerancia_m`;
  propriedade `raio_efetivo` = raio + tolerância). Um colaborador aponta para um local.
- **Colaborador**: `nome`, `funcao`, `tipo` (mensalista|parcial|12x36), `pin_hash`,
  `salario_base`, `exige_selfie`, `ativo`, `local_id`, `criado_em`.
- **Regra**: jornada prevista, **uma linha por dia da semana** (0=segunda … 6=domingo):
  `trabalha`, `entrada_prevista`, `saida_prevista`, `intervalo_min` (pré-assinalado),
  `tolerancia_atraso_min`.
- **Registro**: cada marcação — `momento`, `tipo` (entrada|saida), `latitude`,
  `longitude`, `distancia_m`, `dentro_area`, `selfie_path`, `origem` (mobile|ajuste),
  `comprovante`.
- **Excecao**: férias/folgas por colaborador (`data_inicio`, `data_fim`, `abona`).
- **Feriado**: feriados globais (trabalho no feriado ⇒ HE 100%).
- **Ajuste**: trilha de auditoria de alterações manuais.
- **Config**: pares chave/valor (`Config.get`/`Config.set`).

---

## 7. Motor de cálculo (jornada.py) e premissas LC 150

Parâmetros conferidos com a LC 150/2015: jornada 8h/dia, 44h/sem, divisor 220;
HE mínimo 50%; domingo/feriado em dobro (100%); intervalo 1–2h (redutível a 30min);
banco de horas (40h/mês pagáveis, excedente compensável em até 1 ano); adicional
noturno 20% (22h–05h, hora reduzida 52'30"); DSR 24h + feriados.

**Premissas adotadas (ajustáveis) — validar juridicamente antes de mudar:**
1. **HE = tempo além do previsto na regra do dia.** Alternativa (estrito, acima de
   8h/dia) via `Config` chave `he_criterio_8h` = `on`. O limite **semanal de 44h
   não é apurado** separadamente (driver é a jornada diária).
2. **Intervalo pré-assinalado**, descontado do bruto quando a jornada comporta.
3. **Banco de horas apurado mês a mês** (saldo não acumulado entre meses).
4. **Adicional noturno** só é calculado se `Config` chave `adicional_noturno` = `on`.
5. **Faltas** contam apenas em dias úteis previstos, **da data de cadastro do
   colaborador até hoje** (não conta dias anteriores ao cadastro nem futuros).
   Parâmetro `conta_dia` em `calcula_dia`, alimentado por `servico.py`.

Funções-chave: `haversine_m`, `dentro_da_area`, `pares` (forma pares
entrada/saída; detecta jornada em aberto), `calcula_dia`, `calcula_mes`, `fmt_hm`.

---

## 8. Fuso horário (tempo.py) — REGRA CRÍTICA

O contêiner Docker roda em **UTC**; Maringá é **UTC−3**. Para evitar registros com
horário errado:

> **Use SEMPRE `tempo.agora()` (datetime) e `tempo.hoje()` (date) para qualquer
> data/hora do sistema. NUNCA use `datetime.now()`, `datetime.utcnow()` ou
> `date.today()` diretamente.**

`tempo.py` fixa `America/Sao_Paulo` via `zoneinfo` (o pacote `tzdata` está no
`requirements.txt` para o zoneinfo funcionar na imagem slim). Já aplicado em
models, registro, servico, report, dashboard e export.

---

## 9. Como testar localmente (padrão usado)

```bash
cd ponto-domestico
export DB_PATH=./data/ponto.db UPLOAD_DIR=./data/selfies SECRET_KEY=test
pip install -r requirements.txt --break-system-packages
python3 -c "from app import app; print('boot ok')"   # verifica imports/seed
```
Para exercitar rotas sem subir servidor, use `app.test_client()`:
login admin (`/admin/login`), criar colaborador (`/admin/colaboradores/novo` com
campos `dia_{0..6}_*`), login colaborador (`/entrar`), marcar (`POST /registro/marcar`
com JSON `{lat,lng}`), exportar (`/admin/export/xlsx`, `/admin/export/espelho/<id>`).
Defina `app.config["PROPAGATE_EXCEPTIONS"]=True` para ver o traceback real.

---

## 10. Integração n8n (relatório mensal)

- **Fluxo:** o Flask (`report.py`) monta a planilha do mês, converte em base64 e faz
  `POST` no **webhook do n8n**. O workflow (`n8n/relatorio_mensal_ponto.json`) tem:
  **Webhook** → **Code** (base64 → binário) → **Enviar e-mail (SMTP)**.
- **Envio:** SMTP da Hostinger — `smtp.hostinger.com` porta `465` (SSL), remetente
  `rochaecia@gruporc.net.br`. A senha SMTP fica **só na credencial do n8n**.
- **Webhook path:** `ponto-relatorio`. A **Production URL** do webhook é colada em
  **Configurações → Webhook do n8n** (gravada no banco).
- **Agendamento:** `APScheduler` em `app.py` dispara no dia configurado
  (`Config` chave `relatorio_dia`, padrão 1), referente ao mês anterior. gunicorn
  roda com **1 worker** justamente para o agendador não duplicar o envio.
- **Anexo:** o nó SMTP referencia a propriedade binária **`data`**.

---

## 11. Convenções técnicas estabelecidas

- **Campos monetários:** no HTML use `type="text" data-money=""` (+ `money.js`);
  no back-end converta com `_parse_money()` (em `admin.py`) — **nunca** `float()`
  direto (o valor chega como `R$ 1.234,56`).
- **gunicorn com 1 worker** (evita duplicar o relatório mensal).
- **Selfies e banco** no volume `/app/data` (não perder em redeploy).
- **WeasyPrint** exige libs de sistema (já no Dockerfile: pango/cairo/gdk-pixbuf).

---

## 12. Histórico de mudanças

- **v1** — build inicial completo (todos os módulos e extras).
- **fix** — `_parse_money`: criação/edição de colaborador quebrava quando o salário
  vinha com máscara (`R$ ...`).
- **feat** — exclusão de local (geofence) com trava: bloqueia se houver colaborador
  vinculado e não deixa excluir o único local.
- **fix** — fuso horário: marcações eram gravadas em UTC (+3h). Criado `tempo.py`;
  todo horário passou a usar `America/Sao_Paulo`.

---

## 13. Pendências e ideias (backlog)

- **LGPD:** redigir aviso de consentimento / autorização de geolocalização para
  anexar ao contrato das colaboradoras (reforça o valor probatório do espelho).
- **Fechamento não-calendário** (ex.: 21→20): hoje só há mês-calendário.
- **Banco de horas acumulado** entre meses (hoje é mês a mês).
- **Apuração semanal de 44h** (hoje o driver de HE é a jornada diária).
- **Data de admissão** própria (hoje as faltas contam a partir de `criado_em`).

---

## 14. Segurança

- **Nunca commitar segredos.** `SECRET_KEY`, `ADMIN_SENHA` e a senha SMTP vivem
  no EasyPanel / n8n, jamais no repositório.
- **Tokens do GitHub:** sempre fine-grained, restritos a este repositório, com
  validade curta; **revogar após o uso**.
- Recomendado manter o repositório **privado** (é um sistema interno).

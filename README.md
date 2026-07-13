# Ponto Doméstico — controle interno de jornada

Sistema web (PWA) para registro de ponto de empregados domésticos e babá, com
geofence, dashboard, exportação em `.xlsx`, espelho em PDF e relatório mensal
automático por e-mail via n8n. Uso **interno**, não destinado à fiscalização.

Stack: Flask + SQLite + Docker. Parâmetros de jornada seguem a **LC 150/2015**.

---

## 1. Como funciona (visão rápida)

- **Colaborador (celular):** faz login com PIN e toca em **um único botão** que
  alterna entrada/saída. O app captura a geolocalização, valida contra a área
  cadastrada (geofence) e emite um comprovante. Fora da área, **registra assim
  mesmo** e apenas sinaliza "fora da área".
- **Você (admin):** cadastra colaboradores e regras de jornada, lança férias/
  folgas/feriados (que abonam falta/atraso), acompanha o dashboard, exporta
  planilha/PDF e dispara/agenda o relatório mensal.

---

## 2. Deploy no EasyPanel (GitHub → EasyPanel)

1. **Suba este projeto para um repositório** na sua conta `rafaeljrocha`
   (pode ser privado). Mantenha a estrutura de pastas como está.
2. No **EasyPanel**, crie um serviço do tipo **App** apontando para esse
   repositório (build por **Dockerfile** — já incluído).
3. Em **Environment**, defina as variáveis:

   | Variável | Valor | Observação |
   |---|---|---|
   | `SECRET_KEY` | (uma senha longa aleatória) | obrigatório em produção |
   | `ADMIN_USUARIO` | `rafael` | usuário do painel |
   | `ADMIN_SENHA` | (senha forte) | **troque** o default `trocar123` |
   | `DB_PATH` | `/app/data/ponto.db` | fica no volume persistente |
   | `UPLOAD_DIR` | `/app/data/selfies` | selfies (se ativar) |
   | `N8N_WEBHOOK_URL` | (URL do webhook do n8n) | pode preencher depois, no painel |
   | `RELATORIO_EMAIL` | `rafaeljrocha@gmail.com` | destino do relatório |

4. Em **Volumes**, monte um volume persistente em **`/app/data`**
   (é onde ficam o banco e as selfies — não perca isso em redeploys).
5. Em **Domains/Proxy**, aponte para a **porta 5000**. Lembre: o roteamento
   **interno** do EasyPanel deve ser **HTTP** (não HTTPS); o HTTPS público o
   próprio EasyPanel resolve.
6. Faça o **deploy**. No primeiro boot o sistema cria o banco e já semeia:
   admin, o local base (Casa G23) e os feriados do ano.

**Primeiro acesso:** `https://seu-dominio/admin/login` (painel) e
`https://seu-dominio/registro/` (tela do celular; o colaborador entra em
`/entrar`). No celular, use "Adicionar à tela inicial" para virar atalho (PWA).

---

## 3. Configurar o relatório mensal (n8n)

1. Importe `n8n/relatorio_mensal_ponto.json` no seu n8n.
2. No nó **Gmail**, selecione sua credencial (o campo `credentials` vem com
   `SUBSTITUA` — reaponte para a sua conta Gmail já conectada).
3. Confira o nó **Webhook** e copie a **Production URL**.
4. No painel do sistema, em **Configurações**, cole essa URL em
   *Webhook do n8n* e confirme o *E-mail de destino* e o *Dia do envio*.
5. Ative o workflow no n8n.

O fluxo: o Flask gera a planilha do mês, converte em base64 e chama o webhook;
o n8n transforma em anexo e envia o e-mail. Você também pode disparar manualmente
em **Relatório mensal → Enviar agora**.

> Se, ao importar, o anexo do Gmail não vier vinculado, reabra o nó Gmail e
> selecione a propriedade binária **`data`** em anexos.

---

## 4. Configuração inicial recomendada

1. **Locais / Geofence** — o local base já vem cadastrado (Casa G23). Se mudar
   de endereço, no Google Maps toque e segure no ponto, copie as coordenadas
   (`-23.451737, -51.928168`) e cole no campo *Coordenadas*. Ajuste raio/tolerância.
2. **Colaboradores** — cadastre cada pessoa, defina o **PIN**, o **local** e as
   **regras de comparecimento** (dias, entrada/saída, intervalo pré-assinalado,
   tolerância de atraso).
3. **Feriados** — confira os pré-carregados; ajuste municipais/estaduais.
4. **Configurações** — dia do envio do relatório e critérios de cálculo.

---

## 5. Notas de cálculo — o que é exato e o que é premissa (LC 150/2015)

Para você validar como jurista. Os parâmetros conferem com a LC 150/2015:

- **Jornada 8h/dia, 44h/sem, divisor 220**, **HE mínimo 50%**, **domingo/feriado
  em dobro (100%)**, **intervalo 1–2h (redutível a 30min)**, **banco de horas**
  (primeiras 40h no mês pagáveis/compensáveis no mês; excedente em até 1 ano),
  **adicional noturno 20% (22h–05h, hora reduzida 52'30")**, **DSR 24h + feriados**.

Premissas/simplificações adotadas (ajustáveis):

1. **Definição de HE:** por padrão, HE = tempo **além do previsto na regra do dia**
   (o combinado). Em *Configurações* há a opção de usar o critério estrito
   **acima de 8h/dia**. O limite semanal de 44h **não** é apurado separadamente
   nesta versão — o driver é a jornada diária.
2. **Intervalo pré-assinalado:** descontado automaticamente do tempo bruto quando
   a jornada comporta, conforme a regra. Não há marcação de início/fim de intervalo.
3. **Banco de horas:** apurado **mês a mês**; o saldo **não** é acumulado
   automaticamente entre meses (apresentado por competência).
4. **Adicional noturno:** só é calculado se ligado em *Configurações*.
5. **Faltas:** contam apenas em dias úteis previstos, **a partir da data de
   cadastro** do colaborador e **até hoje** (não conta dias anteriores nem futuros).
   Férias/folgas/feriados abonam.

Se algum critério precisar mudar (ex.: apurar 44h semanais, fechamento 21→20,
saldo de banco acumulado), dá para evoluir — está tudo isolado em `jornada.py`.

---

## 6. Ponto de conformidade (LGPD)

O sistema captura geolocalização de trabalhadoras. Recomenda-se um **aviso de
consentimento** e uma **autorização escrita** anexa ao contrato. O espelho mensal
em PDF traz campos de assinatura das partes — um espelho assinado é boa prova
documental do controle interno.

---

## 7. Estrutura do projeto

```
app.py            factory, scheduler, blueprints
config.py         variáveis de ambiente
models.py         entidades (SQLAlchemy)
jornada.py        motor de cálculo LC 150 + geofence
servico.py        agregação mês/colaborador
seed.py           semente (admin, local, feriados)
blueprints/       auth, registro, admin, dashboard, export, report
templates/        painel + tela mobile + espelho PDF
static/           css, js, PWA (manifest, sw), ícones
n8n/              workflow do relatório mensal
Dockerfile        imagem (inclui libs do WeasyPrint)
```

---

## 8. Rodar localmente (opcional)

```bash
pip install -r requirements.txt
python app.py           # http://localhost:5000
```
Admin: `rafael` / `trocar123` (troque em produção).

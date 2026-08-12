# LoL Status Updater

App de bandeja (system tray) para Windows que mantém a *status message* do
League of Legends sincronizada com um arquivo de texto local, com detecção
automática da instalação do jogo, indicador visual de status, um override
cosmético de elo exibido no chat, e autoatualização via GitHub Releases.

## Funcionalidades

- **Status message automática** — mantém a mensagem de status do LoL sempre
  igual ao conteúdo de `message.txt`. Edita o arquivo, o client atualiza
  sozinho no próximo ciclo (a cada 5s), sem precisar reabrir nada.
- **Detecção automática da pasta do LoL** — lê
  `%PROGRAMDATA%\Riot Games\RiotClientInstalls.json` pra achar onde o jogo
  está instalado, mesmo em outro disco/pasta. Se falhar, dá pra apontar
  manualmente pelo menu da bandeja.
- **Ícone de status colorido** — a bolinha no ícone da bandeja indica o
  estado: 🟢 verde (sincronizando), 🟡 amarelo (aguardando o client abrir),
  🔴 vermelho (pasta não encontrada ou erro de comunicação com o client).
- **Elo customizado (cosmético)** — permite trocar o tier/divisão exibido
  no chat/hover card do client. **Isso é só visual** — não altera seu elo
  real de matchmaking nem nenhum dado da Riot, é o mesmo campo que aparece
  pro seus amigos no card de perfil.
- **Logs em arquivo** — opção pra gravar tudo (detecção da pasta, conexão
  com o client, atualizações de mensagem/elo, erros) em `logs.txt`, com
  data/hora em cada linha.
- **Iniciar com o Windows** — liga/desliga o autostart pelo próprio menu.
- **Autoatualização** — checa releases novas no GitHub automaticamente
  (a cada hora) e a cada uma encontrada, dá pra instalar com um clique
  direto pelo menu.

## Como funciona

Roda em segundo plano na bandeja do sistema, verificando a cada 5 segundos:

1. Resolve a pasta de instalação do LoL (override manual > auto-detecção).
2. Verifica se o client está aberto (lendo o `lockfile` que ele gera).
3. Se estiver, compara a status message atual com `message.txt` e o elo
   configurado (se o override estiver ativo) e atualiza via LCU API
   (`PUT /lol-chat/v1/me`) o que estiver diferente.

Dados do app (`message.txt`, `config.json`, `logs.txt`) ficam sempre em
`%TEMP%\LoLStatusUpdater`, independente de onde o `.exe` for executado —
não precisa manter os arquivos junto do executável.

## Uso

### Rodando o `.exe` (recomendado)

Baixe o `.exe` mais recente na aba [Releases](../../releases), execute, e
use o menu da bandeja pra tudo (editar mensagem, escolher elo, ativar
logs/autostart, etc). Nenhuma instalação é necessária.

### Rodando a partir do código-fonte

Requer Windows e Python 3.14+.

```bash
pip install -r requirements.txt
python main.py
```

## Gerando o `.exe`

```bash
pip install pyinstaller
pyinstaller --noconfirm LoLStatusUpdater.spec
```

O executável sai em `dist/LoLStatusUpdater.exe` — um único arquivo,
sem dependências externas.

## Publicando uma nova versão

1. Atualize a versão em `pyproject.toml` e em `APP_VERSION` (`updater.py`)
   pra bater com a tag que vai criar (ex: `1.1.0` → tag `v1.1.0`).
2. Gere o `.exe` (comando acima).
3. Crie uma tag e uma release no GitHub com essa tag, anexando o
   `LoLStatusUpdater.exe` gerado como asset.
4. Quem já tem uma versão mais antiga instalada recebe a notificação de
   atualização automaticamente e pode instalar direto pelo menu da bandeja.

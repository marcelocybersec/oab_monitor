# 🛡️ Bot de Monitoramento da OAB/FGV 📱

Este bot monitora as páginas da OAB e da FGV e envia mensagens automáticas no Telegram quando novas publicações são detectadas.

---

## 🚀 Como usar

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/oab_monitor.git
   cd oab_monitor
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Copie o `.env.example` e configure o seu `.env`:
   ```bash
   cp .env.example .env
   ```

   Edite o `.env` com suas informações reais:
   - TELEGRAM_BOT_TOKEN=seu_token_aqui  
   - TELEGRAM_CHAT_ID=seu_chat_id_aqui  

4. Execute o monitor:
   ```bash
   python monitor.py
   ```

---

## 📁 Estrutura esperada

```
oab_monitor/
├── monitor.py
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── publicacoes.json  ← (criado automaticamente)
```

---

## ⚠️ Segurança

- Nunca suba o arquivo `.env` com seu token real.
- O `.gitignore` já impede isso por padrão.
- O `.env.example` serve apenas como modelo de configuração.

---

## 📄 Variáveis do `.env`

- `TELEGRAM_BOT_TOKEN` — Token do seu bot (gerado no @BotFather)  
- `TELEGRAM_CHAT_ID` — ID do canal ou grupo (ex: -1001234567890)  
- `INTERVALO_SEGUNDOS` — Tempo entre as verificações (ex: 10)  
- `MAX_RETRIES` — Tentativas ao falhar envio (ex: 3)  
- `DELAY_ENTRE_ENVIOS` — Delay entre mensagens (ex: 1.0)  
- `LOG_LEVEL` — Nível de log (ex: INFO)  

---

## ✅ Requisitos

- Python 3.8 ou superior  
- Bibliotecas Python:

```text
requests
beautifulsoup4
python-dotenv
typing-extensions
soupsieve
```

Instale tudo com:

```bash
pip install -r requirements.txt
```

---

## 🧠 Autor

Criado por Marcelo Vale. Projeto pessoal e open-source.

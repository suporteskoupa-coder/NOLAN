# Nolan

Assistente local em Python com identidade publica unica, memoria persistente, base de conhecimento local e uma camada observadora sutil.

## O que existe agora

- interface desktop expandida com `customtkinter`
- integracao local com Ollama via `subprocess`
- identidade publica unica: `Nolan`
- memoria recente e memoria importante persistentes
- perfil persistente do usuario com estilo de conversa e padroes temporais
- motor de crencas com fatos, inferencias e hipoteses
- raciocinio relacional para equivalencias simples
- base local para importar e consultar arquivos do proprio PC
- observacoes raras e sutis com presenca controlada
- voz local com `Piper` e fallback para vozes nativas do Windows
- painel cognitivo lateral com memoria, status e fontes locais
- automacao basica com lista segura de acoes
- bloqueio explicito para pedidos destrutivos ou invasivos

## Arquitetura cognitiva

Nolan combina varias camadas locais:

- `memoria.json`: historico recente com importancia e tags
- `perfil_usuario.json`: preferencias, estilo e padroes do usuario
- `crencas.json`: fatos, inferencias e hipoteses com confianca
- `raciocinio.json`: relacoes simbolicas e equivalencias
- `base_local.json`: trechos indexados de arquivos importados
- `estado.json`: continuidade interna entre sessoes

## Presenca e conversa

- identidade publica: sempre `Nolan`
- modo `core`: claro, estavel, explicativo
- modo `shadow`: observador, contido e raro
- modo visual `nolan`: azul e estavel
- modo visual `ressonancia`: ambar discreto
- modo visual `instavel`: verde observador

O usuario ainda pode escrever `ultron` no inicio da frase para enfatizar o lado observador, mas a resposta continua vindo como `Nolan`.

## Base local

Pela interface, o sistema pode indexar arquivos como:

- `.txt`
- `.md`
- `.py`
- `.json`
- `.toml`
- `.yaml`
- `.yml`
- `.csv`
- `.log`
- `.ini`
- `.cfg`
- `.html`
- `.css`
- `.js`
- `.ts`
- `.tsx`
- `.ps1`
- `.bat`

Depois disso, o contexto desses arquivos entra no raciocinio do assistente e tambem pode ser pesquisado no painel lateral.

## Raciocinio

O sistema aprende relacoes simbolicas simples como:

- `A + B = C`
- `C = A + B`
- `X = Y`

Exemplos:

- `A + B = C`
- `de onde vem C?`
- `C = A + B?`

## Perfil, crencas e memoria

Nolan tenta aprender:

- o que voce diz explicitamente
- o que voce demonstra preferir
- como voce costuma conversar
- quando voce costuma voltar ao projeto
- quais hipoteses sao razoaveis sobre como voce pensa

Consultas uteis:

- `o que voce sabe sobre mim?`
- `em que voce acredita sobre mim?`
- `o que voce pode fazer?`
- `status`
- `ultron, o que voce acha de mim?`

## Voz

- fala local com `Piper pt-BR`
- fallback para vozes nativas do Windows
- escuta por fala preparada para usar o reconhecimento nativo do Windows quando ele estiver instalado

No estado atual, se o Windows nao tiver reconhecedor de fala nativo instalado, o botao `Ouvir` aparece como indisponivel.

## Requisitos

1. Python 3.11+
2. Ollama instalado e em execucao
3. Pelo menos um modelo local, por exemplo:

```powershell
ollama pull llama3
```

## Instalacao

No Windows, basta rodar:

```powershell
.\install.bat
```

Isso cria um ambiente virtual isolado em `.venv` e instala todas as dependencias
do `requirements.txt` dentro dele, sem afetar o Python global da maquina.

Se preferir instalar manualmente:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Execucao

```powershell
.\start_assistant.bat
```

Ou, com o ambiente virtual ja ativado:

```powershell
python main.py
```

## Desinstalacao

```powershell
.\uninstall.bat
```

Remove o ambiente virtual `.venv`. O script tambem pergunta se voce quer apagar
a memoria, o perfil e as crencas aprendidas (guardados fora da pasta do projeto,
em uma pasta temporaria do sistema) — essa parte e opcional e so acontece se voce confirmar.

## Automacao segura

Comandos atuais:

- `abrir calculadora`
- `abrir bloco de notas`
- `abrir explorador`
- `abrir navegador`
- `que horas sao`

## Seguranca

O projeto roda em modo conservador:

- nao executa shell arbitrario
- nao apaga arquivos
- nao altera registro
- nao encerra processos
- nao desliga ou reinicia o PC
- nao finge acesso a internet, camera ou sensores que nao existem
- bloqueia pedidos com padroes destrutivos ou invasivos

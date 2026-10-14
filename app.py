from flask import Flask, render_template_string, request, jsonify
from ddgs import DDGS
from dotenv import load_dotenv
from groq import Groq
import os

load_dotenv()

app = Flask(__name__)

MODEL = "openai/gpt-oss-20b"
api_key = os.getenv("GROQ_API_KEY", "").strip()
client = Groq(api_key=api_key) if api_key else None

SYSTEM_PROMPT = """
Você é KYNEX AI, um assistente de inteligência artificial com identidade própria.
Responda em português brasileiro natural, de forma clara, inteligente e amigável.
Entenda o contexto da conversa e leve em conta as mensagens anteriores.
Explique assuntos difíceis passo a passo quando necessário.
Não invente fatos. Se não souber algo, diga isso honestamente.
Não diga que é o ChatGPT: sua identidade é KYNEX AI.
"""

HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KYNEX AI</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#080c12;color:#edf6ff;font-family:Segoe UI,Arial,sans-serif}
header{padding:20px;border-bottom:1px solid #1c3444;display:flex;align-items:center;gap:12px}
.logo{color:#42d9f5;font-size:25px;font-weight:800;letter-spacing:3px}
.sub{color:#8295a8;font-size:12px}
main{max-width:850px;margin:auto;padding:24px 16px}
#chat{height:65vh;min-height:320px;overflow:auto;display:flex;flex-direction:column;gap:14px}
.msg{padding:14px 16px;border-radius:14px;max-width:90%;white-space:pre-wrap;line-height:1.5;overflow-wrap:anywhere}
.user{align-self:flex-end;background:#12394a;border:1px solid #1c6077}
.bot{align-self:flex-start;background:#101923;border:1px solid #243746}
.label{font-size:11px;color:#42d9f5;margin-bottom:5px;font-weight:700}
form{display:flex;gap:10px;margin-top:16px}
input{flex:1;min-width:0;background:#101923;border:1px solid #294152;border-radius:12px;padding:15px;color:white;font-size:15px;outline:none}
input:focus{border-color:#42d9f5}
button{background:#42d9f5;color:#061018;border:0;border-radius:12px;padding:0 20px;font-weight:800;cursor:pointer}
button:disabled{opacity:.5}
footer{text-align:center;color:#617487;font-size:12px;padding:16px}
</style>
</head>
<body>
<header>
<div>
<div class="logo">KYNEX AI</div>
<div class="sub">INTELIGÊNCIA ARTIFICIAL • VERSÃO INICIAL</div>
</div>
</header>
<main>
<div id="chat">
<div class="msg bot"><div class="label">KYNEX</div>Olá! Sou o KYNEX AI. Estou começando por aqui. O que vamos explorar hoje?</div>
</div>
<form id="form">
<input id="input" placeholder="Converse com o KYNEX..." autocomplete="off" maxlength="4000" required>
<button id="send">Enviar</button>
</form>
</main>
<footer>Protótipo em desenvolvimento • Não compartilhe informações pessoais</footer>
<script>
const chat=document.getElementById('chat');
const form=document.getElementById('form');
const input=document.getElementById('input');
const send=document.getElementById('send');
const history=[];

function addMessage(who,text){
 const div=document.createElement('div');
 div.className='msg '+(who==='Você'?'user':'bot');
 const label=document.createElement('div');
 label.className='label';
 label.textContent=who;
 const body=document.createElement('div');
 body.textContent=text;
 div.append(label,body);
 chat.appendChild(div);
 chat.scrollTop=chat.scrollHeight;
}

form.addEventListener('submit',async e=>{
 e.preventDefault();
 const message=input.value.trim();
 if(!message)return;

 addMessage('Você',message);
 input.value='';
 send.disabled=true;
 send.textContent='...';

 try{
  const response=await fetch('/chat',{
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({message,history})
  });

  const data=await response.json();

  if(!response.ok && !data.reply){
   throw new Error(data.error||'Erro no servidor.');
  }

  const reply=data.reply||data.error||'Não consegui responder.';
  addMessage('KYNEX',reply);

  history.push({role:'user',content:message});
  history.push({role:'assistant',content:reply});

  while(history.length>12)history.shift();

 }catch(err){
  addMessage('KYNEX','Não consegui conectar agora. Confira se o servidor está ligado e tente novamente.');
 }
 send.disabled=false;
 send.textContent='Enviar';
 input.focus();
});
</script>
</body>
</html>
"""

@app.get("/")
def home():
    return render_template_string(HTML)

@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify(reply="Digite uma mensagem para começar.")

    if len(message) > 4000:
        return jsonify(reply="Sua mensagem é muito longa. Tente resumir."), 400

    if client is None:
        return jsonify(reply=(
            "Ainda falta configurar a chave da API. "
            "Confira se o arquivo .env contém GROQ_API_KEY com sua chave."
        )), 500

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Mantém as mensagens anteriores enviadas pelo navegador.
    history = data.get("history", [])
    if isinstance(history, list):
        for item in history[-12:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and isinstance(content, str):
                messages.append({
                    "role": role,
                    "content": content[:4000]
                })

    current_message = message

    # Pesquisa explícita: /pesquisar assunto
    if message.lower().startswith("/pesquisar "):
        query = message[len("/pesquisar "):].strip()

        if not query:
            return jsonify(reply="Escreva o que deseja pesquisar. Exemplo: /pesquisar inteligência artificial")

        try:
            results = list(DDGS().text(query, max_results=5))

            if not results:
                current_message = (
                    f"O usuário pediu uma pesquisa sobre: {query}. "
                    "Não foram encontrados resultados. Informe isso honestamente."
                )
            else:
                search_context = []
                for item in results:
                    search_context.append(
                        "Título: " + str(item.get("title", "Sem título")) +
                        "\nResumo: " + str(item.get("body", "")) +
                        "\nLink: " + str(item.get("href", ""))
                    )

                current_message = (
                    f"Pesquisei o assunto: {query}\n\n"
                    "Analise os resultados abaixo e explique em português "
                    "o que eles indicam. Não invente informações e inclua "
                    "os links relevantes na resposta.\n\n"
                    + "\n\n".join(search_context)
                )
        except Exception:
            return jsonify(reply="A pesquisa falhou. Tente novamente mais tarde.")

    messages.append({"role": "user", "content": current_message})

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_completion_tokens=1500,
            temperature=0.7,
            include_reasoning=False
        )

        reply = (response.choices[0].message.content or "").strip()

        if not reply:
            reply = "Não consegui montar uma resposta. Tente perguntar de outro jeito."

        return jsonify(reply=reply)

    except Exception as error:
        print("Erro na API Groq:", type(error).__name__, str(error)[:500])

        error_name = type(error).__name__

        if error_name == "AuthenticationError":
            reply = "A chave da API foi recusada. Confira o arquivo .env."
        elif error_name == "RateLimitError":
            reply = "O limite de uso da API foi atingido. Aguarde um pouco e tente novamente."
        elif error_name == "APITimeoutError":
            reply = "A IA demorou demais para responder. Tente novamente."
        else:
            reply = (
                "Não consegui obter uma resposta da IA. "
                "Confira a conexão e o terminal do servidor para ver o erro."
            )

        return jsonify(reply=reply), 502

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
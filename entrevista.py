import sys
import os
import asyncio
import requests
import signal
import curses
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors

if sys.version_info < (3, 7):
    print("⚠️  Este script requer Python 3.7 ou superior. Atualize seu Python.")
    sys.exit(1)

PDF_FILE = "entrevista.pdf"
CONFIG_FILE = "modelo.txt"
POLLINATIONS_URL = "https://text.pollinations.ai/v1/chat/completions"

exit_requested = False
confirm_exit = False

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"

def handle_sigint(signum, frame):
    global confirm_exit, exit_requested
    if confirm_exit:
        print(f"{RED}\nSaindo...{RESET}")
        exit_requested = True
        os._exit(0)
    else:
        print(f"{YELLOW}\nPressione Ctrl+C novamente para confirmar a saída.{RESET}")
        confirm_exit = True

signal.signal(signal.SIGINT, handle_sigint)

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def read_job_description():
    print("Cole a descrição da vaga e pressione CTRL-D (ou CTRL-Z no Windows) para finalizar:")
    job_description = sys.stdin.read().strip()
    return job_description if job_description else read_job_description()

def split_questions(text):
    return [q.strip() for q in text.split("===PERGUNTA===") if q.strip()]

def list_models():
    url = "https://text.pollinations.ai/models"
    try:
        response = requests.get(url)
        response.raise_for_status()
        models = response.json()
        aliases = []
        for model in models:
            if model.get("aliases"):
                aliases.extend(model["aliases"])
            elif model.get("name"):
                aliases.append(model["name"])
        return aliases
    except Exception as e:
        print(f"Erro ao listar modelos: {e}")
        return []

def save_model(model_name):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(model_name)
    print(f"\nModelo selecionado: {model_name}\nSalvo em '{CONFIG_FILE}'")

def load_model():
    if os.path.exists(CONFIG_FILE):
        return open(CONFIG_FILE, "r", encoding="utf-8").read().strip()
    return "gpt-5-nano"

def interactive_model_menu(models):
    selected_index = 0

    def draw_menu(stdscr):
        nonlocal selected_index
        curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            stdscr.addstr(0, 2, "Use ↑/↓ para navegar e Enter para selecionar o modelo", curses.A_BOLD)
            for idx, model in enumerate(models):
                y = idx + 2
                if y >= h - 1:
                    break
                if idx == selected_index:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(y, 2, model[:w-4])
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(y, 2, model[:w-4])
            stdscr.refresh()
            key = stdscr.getch()
            if key == curses.KEY_UP and selected_index > 0:
                selected_index -= 1
            elif key == curses.KEY_DOWN and selected_index < len(models) - 1:
                selected_index += 1
            elif key in [10, 13]:
                return models[selected_index]

    try:
        return curses.wrapper(draw_menu)
    except KeyboardInterrupt:
        curses.endwin()
        print("\nMenu cancelado. Terminal restaurado.")
        return None

async def async_input(prompt: str = "") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))

def clean_ai_response(text: str) -> str:
    if not text:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="ignore")
    else:
        text = str(text)
    for sep in ["---", "**sponsor**"]:
        if sep in text:
            text = text.split(sep)[0].strip()
    return text

async def generate_response(conversation, prompt, model):
    loop = asyncio.get_event_loop()
    def call_api():
        payload = {
            "model": model,
            "messages": conversation + [{"role": "user", "content": prompt}],
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(POLLINATIONS_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        raw_text = response.json()['choices'][0]['message']['content']
        return clean_ai_response(raw_text)
    return await loop.run_in_executor(None, call_api)

async def ask_questions_live(conversation, questions):
    global confirm_exit, exit_requested
    for question in questions:
        if exit_requested:
            return
        confirm_exit = False
        clear_screen()
        print(f"\nSelecionilda: {question}\n")
        conversation.append({"role": "assistant", "content": question})
        try:
            answer = await async_input("Sua resposta: ")
        except KeyboardInterrupt:
            continue
        if exit_requested:
            return
        conversation.append({"role": "user", "content": answer})

async def test_connection(model):
    print("Testando conexão com IA, aguarde um momento...")
    conversation = [{"role": "system", "content": "Você é um assistente de teste."}]
    for attempt in range(1,4):
        if exit_requested:
            return False
        try:
            response = await generate_response(conversation, "Diga apenas: oi", model)
            if response.lower().strip() == "oi":
                print(f"{GREEN}Conexão com IA estabelecida!{RESET}\n")
                return True
        except Exception:
            pass
        await asyncio.sleep(1)
    print(f"{RED}Não foi possível obter conexão com a IA após 3 tentativas.{RESET}")
    print(f"{YELLOW}Verifique sua conexão com a internet ou troque o modelo com --config{RESET}")
    return False

async def generate_pdf(conversation, consolidated_report):
    doc = SimpleDocTemplate(PDF_FILE, pagesize=A4, rightMargin=15*mm,
                            leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
    elements = []

    styles = getSampleStyleSheet()
    normal = styles['Normal']
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=16,
        leading=18,
        textColor=colors.darkblue,
        spaceAfter=12
    )

    elements.append(Paragraph("Relatório da Entrevista", title_style))
    elements.append(Spacer(1, 12))

    lines = consolidated_report.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("• assunto:") or line.lower().startswith("- assunto:"):
            topico = line.split(":", 1)[-1].strip()
            elements.append(Paragraph(f"<b>Tópico: {topico}</b>", normal))
        elif line.lower().startswith("avaliação:"):
            avaliacao = line.split(":", 1)[-1].strip()
            elements.append(Paragraph(f"Avaliação: {avaliacao}", normal))
        else:
            elements.append(Paragraph(line, normal))
        elements.append(Spacer(1, 4))

    doc.build(elements)
    print(f"{GREEN}PDF gerado: {PDF_FILE}{RESET}")

async def main():
    if "--config" in sys.argv:
        models = list_models()
        if not models:
            print("Nenhum modelo disponível.")
            sys.exit(1)
        selected_model = interactive_model_menu(models)
        if selected_model is None:
            return
        save_model(selected_model)
        sys.exit(0)

    MODEL = load_model()
    clear_screen()
    if not await test_connection(MODEL) or exit_requested:
        return

    print("Olá, eu me chamo Selecionilda, serei sua entrevistadora nesta entrevista simulada.\n")

    job_description = read_job_description()
    if exit_requested:
        return
    clear_screen()

    conversation = [{"role": "system", "content": f"Você é um entrevistador para a seguinte vaga:\n{job_description}"}]

    initial_questions = [
        "Para começar, fale sobre você: trajetória profissional, principais conquistas e pontos fortes.",
        "Por que você escolheu se candidatar a esta vaga e o que mais lhe atrai na empresa ou função?"
    ]
    for question in initial_questions:
        if exit_requested:
            return
        clear_screen()
        print(f"\nSelecionilda: {question}\n")
        try:
            answer = await async_input("Sua resposta: ")
        except KeyboardInterrupt:
            continue
        if exit_requested:
            return
        conversation.append({"role": "assistant", "content": question})
        conversation.append({"role": "user", "content": answer})

    prompt_job_questions = (
        "Com base na descrição da vaga, gere 4 perguntas sobre hard skills e experiências relevantes. "
        "Cada pergunta deve começar verificando se o candidato possui a habilidade, por exemplo: "
        "'Você tem experiência com X? Se sim, explique como utilizou essa habilidade e em quais projetos.' "
        "Inclua toda a pergunta completa, já solicitando detalhes e exemplos. "
        "Use '===PERGUNTA===' como separador entre cada pergunta."
    )

    job_questions_task = asyncio.create_task(
        generate_response([{"role": "system", "content": job_description}], prompt_job_questions, MODEL)
    )

    prompt_behavioral_questions = (
        "Com base nas respostas iniciais do candidato, gere 3 perguntas comportamentais usando situações hipotéticas. "
        "O objetivo é avaliar como o candidato age em diferentes cenários profissionais, seu comportamento, tomada de decisão, "
        "capacidade de lidar com conflitos e trabalho em equipe, sem focar em habilidades técnicas. "
        "Use '===PERGUNTA===' como separador entre cada pergunta."
    )

    behavioral_questions_task = asyncio.create_task(
        generate_response(conversation, prompt_behavioral_questions, MODEL)
    )

    job_questions_text = await job_questions_task
    job_questions = split_questions(job_questions_text)
    await ask_questions_live(conversation, job_questions)
    if exit_requested:
        return

    behavioral_questions_text = await behavioral_questions_task
    behavioral_questions = split_questions(behavioral_questions_text)
    await ask_questions_live(conversation, behavioral_questions)
    if exit_requested:
        return

    clear_screen()
    print("Entrevista concluída! Obrigado por participar.\n")
    print("O PDF da sua entrevista está sendo gerado...")

    consolidated_prompt = (
        "Você é um avaliador de entrevistas. Abaixo estão todas as interações do candidato:\n"
        "Para cada pergunta, cite apenas o assunto e avalie de forma sincera o candidato como um todo, "
        "incluindo as respostas às perguntas iniciais. Formate a avaliação em parágrafos e bullets "
        "para facilitar leitura e cópia.\n\n"
    )
    for entry in conversation:
        if entry['role'] == 'assistant':
            consolidated_prompt += f"- Assunto: {entry['content']}\n"
        elif entry['role'] == 'user':
            consolidated_prompt += f"  Resposta: {entry['content']}\n"

    consolidated_report = await generate_response([], consolidated_prompt, MODEL)
    await generate_pdf(conversation, consolidated_report)

if __name__ == "__main__":
    asyncio.run(main())

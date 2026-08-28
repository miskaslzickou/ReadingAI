from google import genai
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import os
import re
import sys
import contextlib
import threading

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

WORKERS = 3

questions = [
    {"title": "Architektura osobního počítače, komponenty PC (PHW)", "points": """
- hardware osobního počítače, počítačové architektury
- case, napájecí zdroj, chlazení, základní deska
- CPU, GPU, RAM, úložiště HDD, SSD, M.2/NVMe, síťové a zvukové karty
- BIOS/UEFI, firmware, CMOS/RTC
- interní propojení komponent: PCI Express, SATA, M.2, USB interní konektory"""},

    {"title": "Počítačové periferie (PHW)", "points": """
- periferní zařízení počítače
- monitory, tiskárny, skenery, multifunkční zařízení
- klávesnice, myši, touchpady, grafické tablety
- webkamery, mikrofony, reproduktory, sluchátka
- USB-A, USB-C, HDMI, DisplayPort, audio konektory, možnosti bezdrátového připojení"""},

    {"title": "Mobilní, vestavěná a chytrá zařízení (PHW)", "points": """
- notebooky, tablety, chytré telefony
- SoC, ARM architektura, mobilní procesory
- senzory v mobilních zařízeních
- wearables, chytré hodinky, IoT zařízení
- chytrá domácnost, výhody a rizika propojených zařízení, správa zařízení, bezpečnost"""},

    {"title": "Bezpečnost informačních systémů (BEZ)", "points": """
- analýza rizik, aktiva, hrozby, rozdělení hrozeb
- ochrana před problémy v elektrické síti, zdroje nepřetržitého napájení
- malware, rozdělení, zranitelnosti v software, antiviry, detekce malwaru, hash
- autentizace, metody ověření, hesla, správci hesel, ukládání hesel v IS
- zálohování, pravidla zálohování, obnova dat, archivace, selhání hardware"""},

    {"title": "Informační bezpečnost uživatelů a kryptografie (BEZ)", "points": """
- zdravotní rizika při používání VT, dopady sociálních sítí
- dezinformace, hoaxy, deepfake, útoky na internetu, sociální inženýrství
- šifrování, kódování, historické a moderní šifry, steganografie
- princip digitálního podpisu, certifikáty, certifikační autorita
- osobní a citlivé údaje, digitální identita, digitální stopa, GDPR a cookies"""},

    {"title": "Operační systémy (SPS)", "points": """
- funkce a struktura operačního systému
- procesy, vlákna, multitasking, správa paměti, soubory, ovladače, registry
- bootování, UEFI, zavaděč systému
- souborové systémy, uživatelská oprávnění
- nejznámější zástupci operačních systémů"""},

    {"title": "Správa OS, příkazový interpret a skriptování (SPS)", "points": """
- operační systémy Windows a Linux
- instalace a konfigurace OS, správa uživatelů a oprávnění
- příkazový řádek ve Windows
- terminál v Linuxu
- skriptování"""},

    {"title": "Internet, webové služby a digitální komunikace (PVY)", "points": """
- internet, jeho služby a základní principy, WWW, URL, HTTP/HTTPS
- webové prohlížeče a jejich nastavení
- e-mail, chat, videokonference
- cloudové služby, sdílení dokumentů a online spolupráce
- vyhledávání, ověřování a zpracování informací, důvěryhodnost zdrojů"""},

    {"title": "Software, licence a distribuce aplikací (PVY)", "points": """
- software, vývojový cyklus, metody vývoje
- rozdělení software, příklady aplikací a platforem
- softwarové licence, EULA, právní aspekty používání
- modely financování a poskytování software
- distribuce, instalace, aktualizace, údržba"""},

    {"title": "Teorie informace a informační systémy (PVY)", "points": """
- data, informace a informační systémy
- reprezentace dat v počítači, číselné soustavy
- převody mezi číselnými soustavami
- komprese dat, archivační formáty
- kódování dat, znakové sady, multimediální formáty"""},

    {"title": "Kancelářské aplikace a online spolupráce (PVY)", "points": """
- kancelářské balíky, cloudové aplikace
- textové editory, formátování, tvorba strukturovaných dokumentů
- tabulkové procesory, vzorce, filtrování, vizualizace dat
- prezentační software, multimédia, online prezentování
- e-mailový klient, plánování, digitální komunikace"""},

    {"title": "Počítačová grafika, média a 3D technologie (PCG)", "points": """
- rastrová a vektorová grafika, jejich vlastnosti a využití
- rozlišení, barevné modely, barevná hloubka, komprese, grafické formáty
- digitální fotografie, práce s fotoaparátem a expoziční trojúhelník
- 3D grafika, modelování a texturování objektů, 3D tisk
- virtuální a rozšířená realita"""},

    {"title": "Zpracování videa a zvuku (PCG)", "points": """
- digitální video, jeho parametry, formáty a kodeky
- záznam, střih a export videa, titulky, efekty a animace
- zvuk, jeho fyzikální podstata a digitalizace
- zvukové formáty, komprese, záznam, úprava a mixování zvuku
- software pro tvorbu/editaci videa a zvuku a jejich propojení"""},

    {"title": "Architektura a technologie počítačové sítě (SPS)", "points": """
- možné dělení počítačových sítí
- technické prostředky sítí, aktivní a pasivní síťové prvky
- síťové modely ISO/OSI a TCP/IP, jejich srovnání
- základní síťové protokoly
- způsoby připojení k Internetu"""},

    {"title": "Servery a služby počítačových sítí (SPS)", "points": """
- historie sítě Internet
- základní pojmy síťových služeb: server, klient, p2p, administrátor, protokol
- HTTP, HTTPS, FTP, SFTP, DNS, DHCP
- IMAP, POP3, SMTP, VoIP, streaming
- DNS záznamy, URL adresy síťových služeb, jejich části"""},

    {"title": "Adresace, směrování a zabezpečení sítě (SPS)", "points": """
- adresování na fyzické, síťové a transportní vrstvě
- třídy adres, beztřídní adresování, výchozí brány a masky, tvorba podsítí
- IPv4 a IPv6, porty TCP/UDP
- směrování, jeho protokoly a principy
- Firewall, VPN, zabezpečení Wi-Fi"""},

    {"title": "HTML, CSS a JavaScript (WEB)", "points": """
- princip vzniku a fungování WWW, protokoly, architektura
- struktura HTML, značky, sémantické prvky HTML
- stylování webu pomocí CSS, selektory, layout, responzivní design
- jazyk JS, proměnné, funkce, události a DOM
- webdesign, UX/UI principy, frameworky a moderní trendy"""},

    {"title": "Redakční systémy a systémy pro správu verzí (WEB)", "points": """
- principy a využití redakčních systémů, zástupci
- webhosting, domény a požadavky na provoz webu
- instalace, konfigurace a zabezpečení, výhody, nevýhody
- šablony, pluginy, aktualizace systému, zálohování
- systém pro správu verzí, principy verzování, základní příkazy"""},

    {"title": "Programování v PHP a databáze (WEB)", "points": """
- skriptování na straně serveru, vlastnosti, využití jazyka PHP
- datové typy, proměnné, podmínky, operátory
- logické operace, cykly, funkce, vkládání dat
- formuláře v PHP, validace dat, PHP a databáze, propojení a komunikace
- databáze, klíče, datové typy, základní příkazy jazyka SQL"""},

    {"title": "Algoritmizace a programovací jazyky (PVA)", "points": """
- instrukce, instrukční sada, princip zpracování instrukce a dat
- algoritmizace, etapy algoritmizace, algoritmus
- základní vlastnosti algoritmů, možnosti zápisu algoritmů
- program, programovací jazyky, dělení a historie, syntaxe, sémantika
- zdrojový text v programu, strojový kód, chyby a varování"""},

    {"title": "Strukturované programování a jazyky (PVA)", "points": """
- základy strukturovaného programování
- proměnné, datové typy, deklarace, inicializace, výraz, přiřazovací příkaz
- podmíněný příkaz, cykly
- funkce, pole, řetězce, knihovny
- základní konstrukce vybraného strukturovaného programovacího jazyka"""},

    {"title": "Objektové programování a tvorba GUI (PVA)", "points": """
- základy objektově-orientovaného přístupu, výhody, jazyky, principy OOP
- třída, objekt, konstruktor, destruktor, metoda, vlastnost
- přístupová práva, dědičnost, šablony a přetěžování funkcí, výjimky
- základní prvky grafických uživatelských rozhraní, grafické knihovny
- základní konstrukce vybraného objektového programovacího jazyka"""},
]


@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, 'w') as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr


def web_search_and_scrape(query, num_results=5):
    results = []
    with DDGS() as ddgs:
        hits = list(ddgs.text(query, max_results=num_results))
    for hit in hits:
        try:
            html = requests.get(hit["href"], timeout=5, headers={"User-Agent": "Mozilla/5.0"}).text
            soup = BeautifulSoup(html, "html.parser")
            text = " ".join(p.get_text() for p in soup.find_all("p"))[:2000]
            if len(text) > 200:
                results.append(text)
        except:
            continue
    if not results:
        results = [h.get("body", "") for h in hits if h.get("body")]
    return "\n\n".join(results)


def generate_report(title, points, context):
    config = {"max_output_tokens": 8192}

    with suppress_stderr():
        response = client.models.generate_content(
            model="gemma-4-26b-a4b-it",
            config=config,
            contents=f"""
            Piš výhradně česky, nepoužívej cyrilici ani cizí písma.
            Každý bod vysvětli podrobně na samostatném odstavci s prázdným řádkem mezi nimi.
            Používej striktně tento formát pro nadpisy bodů: **Název bodu:** Vysvětlení
            Nikdy nepiš "neuvádí se" — vždy doplň ze svých znalostí.

            Téma maturitní otázky: {title}

            Podklady z webu:
            {context}

            Vypracuj podrobnou odpověď na maturitní otázku podle těchto bodů:
            {points}

            Formát výstupu:
            # {title}

            Pro každý bod z osnovy vytvoř sekci:
            ## Název bodu
            Podrobné vysvětlení v několika větách. Uveď konkrétní příklady, technické detaily a praktické využití.
            """
        )

    text = response.text
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[а-яА-ЯёЁ]+', '', text)
    text = re.sub(r'[\u0980-\u09FF]+', '', text)
    text = text.replace('&amp;', '&')
    return text


def add_to_pdf(pdf, content):
    content = re.sub(r'<[^>]+>', '', content)
    content = re.sub(r'[а-яА-ЯёЁ]+', '', content)
    content = re.sub(r'[\u0980-\u09FF]+', '', content)
    content = content.replace('&amp;', '&')

    pdf.add_page()

    for line in content.split("\n"):
        if line.startswith("# "):
            pdf.set_font("Arial", "B", 16)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(pdf.epw, 10, line[2:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        elif line.startswith("## "):
            pdf.set_font("Arial", "B", 12)
            pdf.set_text_color(60, 60, 150)
            pdf.ln(4)
            pdf.multi_cell(pdf.epw, 8, line[3:], new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(60, 60, 150)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + pdf.epw, pdf.get_y())
            pdf.ln(3)
            pdf.set_text_color(0, 0, 0)

        elif line.strip() == "":
            pdf.ln(2)

        else:
            bold_match = re.match(r'\*\*(.+?):\*\*\s*(.*)', line)
            if bold_match:
                label = bold_match.group(1) + ":"
                rest = bold_match.group(2)
                pdf.set_font("Arial", "B", 10)
                pdf.multi_cell(pdf.epw, 6, label, new_x="LMARGIN", new_y="NEXT")
                if rest:
                    pdf.set_font("Arial", "", 10)
                    pdf.multi_cell(pdf.epw, 6, rest, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
            else:
                clean = re.sub(r'\*+', '', line)
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(pdf.epw, 6, clean, new_x="LMARGIN", new_y="NEXT")


def process_question(question):
    title = question["title"]
    points = question["points"]
    tqdm.write(f"[START] {title}")
    context = web_search_and_scrape(f"{title} maturita informatika vysvětlení")
    if not context:
        context = "Žádné informace, použij vlastní znalosti."
    report = generate_report(title, points, context)
    tqdm.write(f"[HOTOVO] {title}")
    return title, report


# zpracování
results = {}

with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    futures = {executor.submit(process_question, q): q for q in questions}
    with tqdm(total=len(questions), desc="Celkový progress", unit="otázka") as pbar:
        for future in as_completed(futures):
            q = futures[future]
            try:
                title, report = future.result()
                results[title] = report
            except Exception as e:
                tqdm.write(f"[CHYBA] {q['title']}: {e}")
            finally:
                pbar.update(1)

# sestavení PDF ve správném pořadí
pdf = FPDF()
pdf.set_margins(20, 20, 20)
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_font("Arial", "", "C:/Windows/Fonts/arial.ttf")
pdf.add_font("Arial", "B", "C:/Windows/Fonts/arialbd.ttf")

for question in questions:
    title = question["title"]
    if title in results:
        add_to_pdf(pdf, results[title])
    else:
        tqdm.write(f"[CHYBÍ] {title} — přeskočeno")

os.makedirs("reports", exist_ok=True)
pdf.output("reports/maturita_IT.pdf")
print("\nUloženo: reports/maturita_IT.pdf")
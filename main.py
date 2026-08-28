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

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# kolik knih se zpracovává paralelně
WORKERS = 4

#názvy knih v češtině!!
books = [
    {"title": "Zvířecí farma", "author": "George Orwell"},
    {"title": "1984", "author": "George Orwell"},
    {"title": "Malý princ", "author": "Antoine de Saint-Exupéry"},
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
    
    tqdm.write(f"  Search našel {len(hits)} výsledků pro: {query[:50]}")
    
    for hit in hits:
        try:
            html = requests.get(hit["href"], timeout=5, headers={"User-Agent": "Mozilla/5.0"}).text
            soup = BeautifulSoup(html, "html.parser")
            text = " ".join(p.get_text() for p in soup.find_all("p"))[:2000]
            if len(text) > 200:
                results.append(text)
                tqdm.write(f"  ✓ Scraped: {hit['href'][:60]}")
            else:
                tqdm.write(f"  ✗ Příliš málo textu: {hit['href'][:60]}")
        except Exception as e:
            tqdm.write(f"  ✗ Chyba: {hit['href'][:60]} — {e}")
            continue
    
    if not results:
        tqdm.write(f"  ! Fallback na snippety ({len(hits)} kusů)")
        results = [h.get("body", "") for h in hits if h.get("body")]
    
    tqdm.write(f"  Celkem textu: {sum(len(r) for r in results)} znaků")
    return "\n\n".join(results)

def generate_report(title, author, context):
    config = {"max_output_tokens": 8192}

    with suppress_stderr():
        response1 = client.models.generate_content(
            model="gemma-4-26b-a4b-it",
            config=config,
            contents=f"""
            Piš výhradně česky, nepoužívej cyrilici ani cizí písma.
            Každou položku uveď na samostatném řádku s prázdným řádkem mezi nimi.
            Pokud podklady neobsahují informaci, doplň ze svých znalostí. Nikdy nepiš "neuvádí se".
            Používej striktně tento formát: **Název položky:** Text
            Mezi každou položkou jeden prázdný řádek.

            Kniha: {title}, Autor: {author}
            Podklady: {context}

            Vypracuj POUZE tyto sekce:

            # {title} — {author}

            **Nakladatelství, rok vydání:** [doplň]
            **Překladatel:** [doplň pokud překlad]

            ## I) Informace o celém díle

            **Děj celého díla:** [podrobné shrnutí]

            **Námět (inspirace):** [co autora inspirovalo]

            **Téma:** [hlavní myšlenka]

            **Časoprostor:** [kde a kdy]

            **Kompozice vnitřní:** [způsob vyprávění]

            **Kompozice vnější textu:** [složení textu]

            **Kompozice vnější celého díla:** [kapitoly, části]

            **Literární druh:** [epika/lyrika/drama; próza/poezie]

            **Literární žánr:** [konkrétní žánr]

            **Vypravěč / lyrický subjekt:** [typ a popis]

            **Vyprávěcí pásmo:** [převažující pásmo]

            **Formy řeči:** [er/ich/wir-forma]

            **Postavy v díle a jejich charakteristika:** [každá postava na samostatném řádku, min. 2-3 věty]

            **Literární typ:** [typy postav]

            **Typy promluv postav:** [přímá/nepřímá řeč]

            **Jazykové prostředky, spisovnost, vrstvy slovní zásoby:** [popis jazyka]

            **Figury a tropy v díle:** [konkrétní příklady z díla]
            """
        )

    with suppress_stderr():
        response2 = client.models.generate_content(
            model="gemma-4-26b-a4b-it",
            config=config,
            contents=f"""
            Piš výhradně česky, nepoužívej cyrilici ani cizí písma.
            Každou položku uveď na samostatném řádku s prázdným řádkem mezi nimi.
            Pokud podklady neobsahují informaci, doplň ze svých znalostí. Nikdy nepiš "neuvádí se".
            Používej striktně tento formát: **Název položky:** Text
            Mezi každou položkou jeden prázdný řádek.

            Kniha: {title}, Autor: {author}

            Vypracuj POUZE tyto sekce:

            ## III) Vztah autora k dílu

            **Autorovy sympatie:** [ke které postavě autor sympatizuje]

            **Ztotožnění:** [s kterou postavou se autor ztotožňuje]

            **Co chtěl autor dílem sdělit:** [hlavní poselství]

            ## V) Literárněhistorický kontext

            **Je toto dílo pro autora typické nebo netypické? Čím?:** [zhodnocení]

            **Zařazení do kontextu autorovy tvorby:** [typ tvorby, období]

            **Další autorova díla:** [výčet minimálně 5 děl]

            **Literární směr / sloh / období:** [konkrétní směr]

            **Století, půlstoletí, stát:** [kdy a kde žil]

            **Literární skupina nebo proud:** [skupina nebo proud]

            **Další autoři a díla:**
            - dějově podobná: [minimálně 3 příklady]
            - stejný literární směr: [minimálně 3 příklady]
            - autorovi současníci: [minimálně 3 příklady]
            """
        )

    text = response1.text + "\n\n" + response2.text
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[а-яА-ЯёЁ]+', '', text)
    text = re.sub(r'[\u0980-\u09FF]+', '', text)
    text = text.replace('&amp;', '&')
    return text


def save_report(title, author, content):
    os.makedirs("reports", exist_ok=True)
    safe_name = f"{title.replace(' ', '_')}_{author.replace(' ', '_')}"

    content = re.sub(r'<[^>]+>', '', content)
    content = re.sub(r'[а-яА-ЯёЁ]+', '', content)
    content = re.sub(r'[\u0980-\u09FF]+', '', content)
    content = content.replace('&amp;', '&')

    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.add_font("Arial", "", "C:/Windows/Fonts/arial.ttf")
    pdf.add_font("Arial", "B", "C:/Windows/Fonts/arialbd.ttf")

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

    pdf_path = f"reports/{safe_name}.pdf"
    pdf.output(pdf_path)


def process_book(book):
    title = book["title"]
    author = book["author"]
    tqdm.write(f"[START] {title} - {author}")
    context = web_search_and_scrape(f"{title} {author} rozbor témata postavy literární kontext")
    if not context:
        context = "Žádné informace, použij vlastní znalosti."
    report = generate_report(title, author, context)
    save_report(title, author, report)
    tqdm.write(f"[HOTOVO] {title}")


with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    futures = {executor.submit(process_book, book): book for book in books}
    with tqdm(total=len(books), desc="Celkový progress", unit="kniha") as pbar:
        for future in as_completed(futures):
            book = futures[future]
            try:
                future.result()
            except Exception as e:
                tqdm.write(f"[CHYBA] {book['title']}: {e}")
            finally:
                pbar.update(1)

print("\nVšechno hotovo!")
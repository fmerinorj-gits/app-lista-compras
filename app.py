# === APLICATIVO LISTA DE COMPRAS & MERCADO - VERSÃO v.1.20.1 ===
import base64
import json
import math
import time
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
import gspread
from google.oauth2.service_account import Credentials

VERSAO_APP = "v.1.20.1"

# Configuração de página idêntica ao padrão mobile/centered do App Luz & Água
st.set_page_config(
    page_title="Lista de Compras",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilo visual customizado (Tons de Azul/Verde, divisores do esboço e controles Verdes quando marcados)
st.markdown("""
<style>
    :root {
        --primary-color: #2ECC71 !important;
    }
    /* Cartões de resumo e alertas */
    .card-azul {
        background-color: rgba(30, 136, 229, 0.12);
        border-left: 5px solid #1E88E5;
        padding: 12px 14px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .card-verde {
        background-color: rgba(46, 125, 50, 0.14);
        border-left: 5px solid #2E7D32;
        padding: 12px 14px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .card-farmacia {
        background-color: rgba(156, 39, 176, 0.12);
        border-left: 5px solid #AB47BC;
        padding: 12px 14px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .card-alerta-caixa {
        background-color: rgba(255, 152, 0, 0.15);
        border: 1px solid #FF9800;
        border-left: 6px solid #FF9800;
        padding: 12px 14px;
        border-radius: 8px;
        margin-top: 8px;
        margin-bottom: 12px;
    }
    .setor-header {
        background: linear-gradient(90deg, rgba(30,136,229,0.20) 0%, rgba(30,136,229,0.02) 100%);
        padding: 8px 12px;
        border-radius: 6px;
        font-weight: 700;
        margin-top: 14px;
        margin-bottom: 6px;
        border-left: 4px solid #4FC3F7;
    }
    .item-sub {
        color: #778DA9;
        font-size: 0.85rem;
    }
    /* Divisores visuais horizontais em tom azul-escuro suave (igual ao esboço) */
    .divisor-secao {
        border: 0;
        height: 2px;
        background: linear-gradient(90deg, rgba(65, 90, 119, 0.15) 0%, rgba(65, 90, 119, 0.65) 50%, rgba(65, 90, 119, 0.15) 100%);
        margin: 14px 0px;
    }
    /* Logos de bancos alinhados com os rótulos de pagamento */
    .bank-label {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        font-size: 0.92rem;
        margin-bottom: 4px;
        margin-top: 6px;
    }
    /* Transforma o Vermelho nativo (#FF4B4B) do Streamlit em VERDE (#2ECC71) nos Checkboxes ("Comprado") */
    div[data-testid="stCheckbox"] {
        filter: hue-rotate(125deg) saturate(1.5) brightness(1.1) !important;
    }
    /* Transforma o Vermelho nativo (#FF4B4B) do Streamlit em VERDE (#2ECC71) apenas na 2ª opção ("Comprar") do Radio, mantendo "— Não" em Vermelho! */
    div[role="radiogroup"] > *:nth-child(2) {
        filter: hue-rotate(125deg) saturate(1.5) brightness(1.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# === LOGOTIPOS VETORIAIS EM BASE64 (PROPORÇÕES FIÉIS ÀS IMAGENS ANEXADAS) ===
def _svg_to_base64(svg_str):
    b64 = base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"

# Bradesco: Fundo branco arredondado com o símbolo vermelho oficial em alta nitidez
LOGO_BRADESCO = _svg_to_base64("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#FFFFFF" stroke="#E0E0E0" stroke-width="2"/>
  <path d="M12 36 C12 18, 34 10, 50 22 C38 16, 20 21, 19 36 C25 27, 42 25, 53 34 C53 41, 48 47, 41 49 C46 43, 44 33, 31 33 C22 33, 17 39, 17 45" stroke="#CC092F" stroke-width="5" fill="none" stroke-linecap="round"/>
  <rect x="27" y="40" width="4.8" height="15" rx="1.5" fill="#CC092F"/>
  <rect x="34.5" y="36" width="4.8" height="19" rx="1.5" fill="#CC092F"/>
</svg>
""")

# Mercado Pago: Elipse azul-celeste com borda azul-marinho e aperto de mãos branco no centro
LOGO_MERCADOPAGO = _svg_to_base64("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <ellipse cx="32" cy="32" rx="29" ry="22" fill="#00B1EA" stroke="#002B7F" stroke-width="3.8"/>
  <path d="M7 27 C16 27, 21 19, 32 19 C43 19, 48 27, 57 27" stroke="#FFFFFF" stroke-width="5.5" fill="none"/>
  <path d="M17 33 L27 24 C31 21, 37 22, 41 28 L48 35 C44 42, 34 45, 24 41 Z" fill="#FFFFFF" stroke="#002B7F" stroke-width="3.2" stroke-linejoin="round"/>
  <circle cx="22" cy="38" r="3.2" fill="#FFFFFF" stroke="#002B7F" stroke-width="2.5"/>
  <circle cx="27.5" cy="40.5" r="3.2" fill="#FFFFFF" stroke="#002B7F" stroke-width="2.5"/>
  <circle cx="33" cy="42" r="3.2" fill="#FFFFFF" stroke="#002B7F" stroke-width="2.5"/>
</svg>
""")

# Nubank: Fundo roxo oficial (#820AD1) com as letras "nu" brancas centralizadas
LOGO_NUBANK = _svg_to_base64("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#820AD1"/>
  <path d="M12 43 V27 C12 20.5, 16.5 17, 22 17 C27.5 17, 31 20.5, 31 27 V43" stroke="#FFFFFF" stroke-width="5.8" fill="none" stroke-linecap="round"/>
  <path d="M35 19 V35 C35 41.5, 39.5 45, 45 45 C50.5 45, 54 41.5, 54 35 V19" stroke="#FFFFFF" stroke-width="5.8" fill="none" stroke-linecap="round"/>
</svg>
""")

def label_banco_html(logo_uri, nome_banco, modalidade):
    cor_mod = "#4FC3F7" if "DÉBITO" in modalidade.upper() else "#FFB74D"
    return f"""
    <div class="bank-label">
        <img src="{logo_uri}" width="26" height="26" style="border-radius:6px; box-shadow: 0 1px 4px rgba(0,0,0,0.45);">
        <span>{nome_banco} — <span style="color:{cor_mod};">{modalidade}</span> (R$)</span>
    </div>
    """

# === FUSO HORÁRIO DE BRASÍLIA (UTC-3) ===
FUSO_BR = timezone(timedelta(hours=-3))

def agora_br():
    return datetime.now(FUSO_BR)

def hoje_br():
    return agora_br().date()

# === FUNÇÕES UTILITÁRIAS DE NÚMEROS, FORMATAÇÃO E PROTEÇÃO CONTRA #ERROR! ===
def arredondar_moeda(valor, casas=2):
    try:
        d = Decimal(str(valor))
        formato = "0." + ("0" * casas) if casas > 0 else "0"
        return float(d.quantize(Decimal(formato), rounding=ROUND_HALF_UP))
    except Exception:
        return round(float(valor or 0.0), casas)

def safe_float(val):
    if pd.isna(val) or val is None or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip().replace("R$", "").strip()
    if "," in val_str:
        if "." in val_str:
            val_str = val_str.replace(".", "")
        val_str = val_str.replace(",", ".")
    try:
        return float(val_str)
    except Exception:
        return 0.0

def safe_bool(val):
    if isinstance(val, bool):
        return val
    return str(val).strip().upper() in ["TRUE", "1", "SIM", "S", "X", "COMPRAR", "OK"]

def formatar_num_planilha(valor_float, casas=2):
    v = arredondar_moeda(safe_float(valor_float), casas)
    if casas == 3 and abs(v - round(v)) < 1e-6:
        return str(int(round(v)))
    return f"{v:.{casas}f}".replace(".", ",")

def formatar_moeda_br(valor_float):
    v = arredondar_moeda(safe_float(valor_float), 2)
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def formatar_qtd_br(valor_float):
    v = safe_float(valor_float)
    if abs(v - round(v)) < 1e-5:
        return str(int(round(v)))
    return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")

def escapar_texto_sheets(val_str):
    """
    Evita que textos iniciados com '+' ou '=' (como '+Forte Reforçado - 50 Lts.')
    sejam interpretados pelo Google Sheets como fórmula matemática (#ERROR!).
    """
    s = str(val_str or "").strip()
    if s.startswith("+") or s.startswith("="):
        return "'" + s
    return s

def limpar_marca_lida(marca_str, cod_str=""):
    """Remove eventual apóstrofo inicial e repara automaticamente '#ERROR!' nos Sacos de Lixo."""
    m = str(marca_str or "").strip().lstrip("'")
    c = str(cod_str or "").strip()
    if "ERROR" in m.upper():
        if c == "#22A":
            return "+Forte Reforçado - 50 Lts."
        if c == "#22B":
            return "+Forte Reforçado - 100 Lts."
    return m

def exibir_marca_limpa(marca_str, cod_str=""):
    m = limpar_marca_lida(marca_str, cod_str)
    if m in ["", "-", "--", "nan", "None"]:
        return "Sem marca específica"
    return m

def eh_unidade_fracionada(unid_str):
    """Retorna True apenas para itens vendidos a granel/peso (Kg). Unidades fechadas (Pacote, Saco, Lata, etc.) usam inteiros sem '.00'."""
    return str(unid_str or "").strip().lower() == "kg"

def data_padrao_dia_5(mes_ano_str):
    """Retorna o dia 05 do Mês/Ano ativo como data padrão de compra (5º dia útil / pagamento)."""
    try:
        partes = str(mes_ano_str).strip().split(" ")
        m = int(partes[0])
        a = int(partes[1])
        return date(a, m, 5)
    except Exception:
        h = hoje_br()
        return date(h.year, h.month, 5)

# === LISTA OFICIAL DOS DEPARTAMENTOS E DOS 88 PRODUTOS (CIRCUITO DO MERCADO) ===
SETORES_OFICIAIS = [
    "💊 Antes do Mercado: Farmácia",
    "🥩 Setor A: Açougue/Salgados/Congelados",
    "🧀 Setor B: Laticínios/Frios",
    "🍞 Setor C: Padaria",
    "☕ Setor D: Farelos, Café",
    "🧄 Setor E: Hortifruti",
    "🍪 Setor F: Doces, Complementos e Biscoitos",
    "🪥 Setor G: Higiene Pessoal e Perfumaria",
    "🧻 Setor H: Sacos, Papéis e Descartáveis",
    "🧼 Setor I: Limpeza",
    "🥫 Setor J: Mercearia (Latas e Condimentos)",
    "🌾 Setor K: Mercearia (Grãos)",
    "➕ Setor L: Extras"
]

# Tuplas: (Ordem, Codigo, Setor, Produto, Marca1, Marca2_Obs, QtdPadrao, Unidade)
CATALOGO_INICIAL = [
    # 💊 ANTES DO MERCADO: FARMÁCIA
    (1, "F1", "💊 Antes do Mercado: Farmácia", "Neosoro", "--", "-", 9.0, "Unidade"),
    (2, "F2", "💊 Antes do Mercado: Farmácia", "Alprazolam 0,5mg", "--", "Caixa 30 Comprimidos", 1.0, "Caixa (30 Comprimidos)"),
    (3, "F3", "💊 Antes do Mercado: Farmácia", "Bupropiona 150mg - 12H", "--", "Caixa 30 Comprimidos", 1.0, "Caixa (30 Comprimidos)"),

    # 🥩 SETOR A: AÇOUGUE / SALGADOS / CONGELADOS
    (4, "#62", "🥩 Setor A: Açougue/Salgados/Congelados", "Peito de Frango sem osso", "Sadia", "-", 4.0, "Kg"),
    (5, "#64", "🥩 Setor A: Açougue/Salgados/Congelados", "Patinho ou Chã MOÍDO", "Magro", "No máximo 2,5Kg", 2.5, "Kg"),
    (6, "#65", "🥩 Setor A: Açougue/Salgados/Congelados", "Costela Magra", "--", "Ref. 1,5Kg", 1.5, "Kg"),
    (7, "#63", "🥩 Setor A: Açougue/Salgados/Congelados", "Alcatra", "2 Bifes com 3cm de espessura", "-", 2.0, "Bifes"),
    (8, "#61", "🥩 Setor A: Açougue/Salgados/Congelados", "Sal fino", "Lebre", "Ita", 1.0, "Kg"),
    (9, "#70", "🥩 Setor A: Açougue/Salgados/Congelados", "Batata Pré Frita", "--", "-", 2.0, "Kg"),

    # 🧀 SETOR B: LATICÍNIOS / FRIOS
    (10, "#58", "🧀 Setor B: Laticínios/Frios", "Requeijão Light", "Itambé", "200gr", 4.0, "Unidade"),
    (11, "#59", "🧀 Setor B: Laticínios/Frios", "Requeijão Zero lactose", "Itambé", "200gr", 8.0, "Unidade"),
    (12, "#60", "🧀 Setor B: Laticínios/Frios", "Iogurte Natural", "--", "-", 2.0, "Unidade"),
    (13, "#9", "🧀 Setor B: Laticínios/Frios", "Leite Molico ou Desnatado", "--", "-", 14.0, "Litro"),
    (14, "#10", "🧀 Setor B: Laticínios/Frios", "Leite de sem Lactose ou de Soja", "--", "-", 12.0, "Litro"),

    # 🍞 SETOR C: PADARIA
    (15, "#67", "🍞 Setor C: Padaria", "Pão de forma milho ou leite", "--", "-", 2.0, "Saco"),
    (16, "#68", "🍞 Setor C: Padaria", "Pão de forma Integral 67%", "Wickbold", "-", 2.0, "Saco"),

    # ☕ SETOR D: FARELOS, CAFÉ
    (17, "#44", "☕ Setor D: Farelos, Café", "Aveia em flocos ou farinha", "Quaker", "-", 2.0, "Caixa"),
    (18, "#35", "☕ Setor D: Farelos, Café", "Farinha Láctea", "Nestlé", "Genérica", 1.0, "Saco"),
    (19, "#39", "☕ Setor D: Farelos, Café", "Ovomaltine", "--", "-", 1.0, "Saco"),
    (20, "#71", "☕ Setor D: Farelos, Café", "Amido", "--", "-", 1.0, "Caixa Pequena"),
    (21, "#72", "☕ Setor D: Farelos, Café", "Leite em pó integral", "--", "-", 1.0, "Saco / Unidade"),
    (22, "#73", "☕ Setor D: Farelos, Café", "Café solúvel", "Matinal", "-", 1.0, "Saco / Unidade"),
    (23, "#33", "☕ Setor D: Farelos, Café", "Pó de café", "Evoluto Premium", "Pacote 0,5 Kg", 1.0, "Pacote (0,5Kg)"),
    (24, "#34", "☕ Setor D: Farelos, Café", "Filtro de café - 102", "Melitta", "Pimpinela", 1.0, "Caixa"),
    (25, "#36", "☕ Setor D: Farelos, Café", "Erva Mate", "Leão", "Gr", 1.0, "Caixa"),

    # 🧄 SETOR E: HORTIFRUTI
    (26, "#69", "🧄 Setor E: Hortifruti", "Alho", "Cabeça", "-", 4.0, "Unidade"),

    # 🍪 SETOR F: DOCES, COMPLEMENTOS E BISCOITOS
    (27, "#74", "🍪 Setor F: Doces, Complementos e Biscoitos", "Fermento em pó", "Royal", "-", 1.0, "Pote"),
    (28, "#42", "🍪 Setor F: Doces, Complementos e Biscoitos", "Geleia - Uva - Pêssego - Morango - Damasco", "Ritter", "Predilecta", 3.0, "Unidade"),
    (29, "#43", "🍪 Setor F: Doces, Complementos e Biscoitos", "Goiabada Fina – Não cascão", "Predilecta", "-", 1.0, "Unidade"),
    (30, "#40", "🍪 Setor F: Doces, Complementos e Biscoitos", "Creme de Leite SEM LACTOSE", "--", "-", 1.0, "Caixa"),
    (31, "#41", "🍪 Setor F: Doces, Complementos e Biscoitos", "Leite Condensado SEM LACTOSE", "--", "-", 1.0, "Caixa"),
    (32, "#75", "🍪 Setor F: Doces, Complementos e Biscoitos", "Coco ralado", "Sococo", "-", 1.0, "Saco"),
    (33, "#37", "🍪 Setor F: Doces, Complementos e Biscoitos", "Biscoito Cristal", "Marilan", "(3X Econômico)", 1.0, "Pacote"),
    (34, "#38", "🍪 Setor F: Doces, Complementos e Biscoitos", "Biscoito Maisena", "--", "-", 1.0, "Pacote"),

    # 🪥 SETOR G: HIGIENE PESSOAL E PERFUMARIA (6 VARIAÇÕES SHAMPOO / CONDICIONADOR / KIT)
    (35, "#28", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Creme dental", "Sensodyne “Original”", "-", 1.0, "Tubo"),
    (36, "#29A", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Shampoo", "Seda \"Roxo\"", "Individual", 1.0, "Unidade"),
    (37, "#30A", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Condicionador", "Seda \"Roxo\"", "Individual", 1.0, "Unidade"),
    (38, "#29K", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Kit Shampoo + Condicionador", "Seda \"Roxo\"", "Embalagem Econômica", 1.0, "Unidade"),
    (39, "#29B", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Shampoo", "Pantene Liso Extremo", "Individual", 1.0, "Unidade"),
    (40, "#30B", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Condicionador", "Pantene Liso Extremo", "Individual", 1.0, "Unidade"),
    (41, "#30K", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Kit Shampoo + Condicionador", "Pantene Liso Extremo", "Embalagem Econômica", 1.0, "Unidade"),
    (42, "#31", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Sabonete", "Protex", "Erva Doce", 6.0, "Unidade"),
    (43, "#32", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Cotonetes", "Johnson’s", "-", 1.0, "Caixa"),
    (44, "#76", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Desodorante Sem perfume", "--", "-", 1.0, "Lata"),
    (45, "#77", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Escova Dental", "--", "-", 1.0, "Unidade"),

    # 🧻 SETOR H: SACOS, PAPÉIS E DESCARTÁVEIS
    (46, "#78", "🧻 Setor H: Sacos, Papéis e Descartáveis", "Pastilhas Pato Purific", "Limão", "-", 1.0, "Caixa"),
    (47, "#23", "🧻 Setor H: Sacos, Papéis e Descartáveis", "Rolo de Sacos", "29cm", "-", 1.0, "Rolo"),
    (48, "#24", "🧻 Setor H: Sacos, Papéis e Descartáveis", "Papel Toalha", "Snob", "Social", 1.0, "Pacote"),
    (49, "#25", "🧻 Setor H: Sacos, Papéis e Descartáveis", "Filme PVC - 30 mts - Sem picotes", "--", "-", 1.0, "Rolo"),
    (50, "#26", "🧻 Setor H: Sacos, Papéis e Descartáveis", "Papel Hig. – Personal VIP - Mimmo (Urso Bege c/Lilás)", "--", "-", 16.0, "Rolo"),

    # 🧼 SETOR I: LIMPEZA
    (51, "#13", "🧼 Setor I: Limpeza", "Cloro (não água sanitária)", "Pró Water", "-", 2.0, "Litro"),
    (52, "#14", "🧼 Setor I: Limpeza", "“Cheirinho” para chão", "Casa & Perfume", "-", 1.0, "Vidro"),
    (53, "#16", "🧼 Setor I: Limpeza", "Sabão de coco neutro", "Ypê", "Palmeira", 1.0, "Unidade"),
    (54, "#17", "🧼 Setor I: Limpeza", "Desengordurante", "Veja", "Cif", 1.0, "Refil"),
    (55, "#18", "🧼 Setor I: Limpeza", "Sapólio Radium – Cloro pó", "--", "-", 1.0, "Unidade"),
    (56, "#27", "🧼 Setor I: Limpeza", "Álcool com Eucalipto", "--", "-", 1.0, "Litro"),
    (57, "#15", "🧼 Setor I: Limpeza", "Detergente - Transparente", "Ypê", "-", 3.0, "Unidade"),
    (58, "#11", "🧼 Setor I: Limpeza", "Sabão em pó AZUL", "Ypê", "-", 2.0, "Kg"),
    (59, "#12", "🧼 Setor I: Limpeza", "Amaciante Confort Concent.", "Bebê Hipoalergênico", "Frasco 0,5 Litro", 1.0, "Frasco (0,5 Litro)"),
    (60, "#19", "🧼 Setor I: Limpeza", "Bombril", "--", "-", 1.0, "Saquinho"),
    (61, "#20", "🧼 Setor I: Limpeza", "Pano de Pia - Amarelo", "3M", "-", 1.0, "Saquinho"),
    (62, "#21", "🧼 Setor I: Limpeza", "Esponja 3 ou 4 unidades", "Ypê", "3M", 1.0, "Saquinho"),
    (63, "#22A", "🧼 Setor I: Limpeza", "Saco de Lixo", "+Forte Reforçado - 50 Lts.", "-", 1.0, "Pacote"),
    (64, "#22B", "🧼 Setor I: Limpeza", "Saco de Lixo", "+Forte Reforçado - 100 Lts.", "-", 1.0, "Pacote"),

    # 🥫 SETOR J: MERCEARIA (LATAS E CONDIMENTOS)
    (65, "#66", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Colorau", "--", "-", 1.0, "Saquinho"),
    (66, "#45", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Maionese (com bico)", "Hellmann's", "Heinz (2 Pequenas / 1 Grande / Pote)", 1.0, "Unidade"),
    (67, "#46", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Atum – Água (Light) - Sólido", "Gomes da Costa", "-", 2.0, "Lata"),
    (68, "#47", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Óleo de soja", "--", "-", 1.0, "Litro"),
    (69, "#48", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Vinagre de Maçã", "--", "-", 1.0, "Litro"),
    (70, "#49", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Azeite de Oliva 0,2% ou 0,5%", "Andorinha", "Gallo", 1.0, "Vidro"),
    (71, "#50", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Milho em lata", "Pramesa", "Predilecta", 2.0, "Lata"),
    (72, "#51", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Molho Shoyo Premium", "Sakura", "Ajinoshoyo", 1.0, "Pote"),
    (73, "#52", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Ketchup - Sem pimenta", "Pramesa", "Hellmann's", 1.0, "Unidade"),
    (74, "#53", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Mostarda", "Pramesa", "Hellmann's", 1.0, "Unidade"),
    (75, "#54", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Champignon", "Pramesa", "1 Pequeno", 1.0, "Vidro"),
    (76, "#55", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Batata Palha – não fina", "Elma Chips", "Sacos Grandes", 3.0, "Saquinho"),
    (77, "#56", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Macarrão de Arroz", "Urbano", "-", 1.0, "Kg"),
    (78, "#57", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Queijo ralado", "Vigor", "Président (100g)", 1.0, "Unidade (100g)"),

    # 🌾 SETOR K: MERCEARIA (GRÃOS)
    (79, "#1", "🌾 Setor K: Mercearia (Grãos)", "Arroz Branco", "Tio João", "Tio Mingote", 1.0, "Pacote (5Kg)"),
    (80, "#2", "🌾 Setor K: Mercearia (Grãos)", "Feijão manteiga ou vermelho", "--", "Pacote 0,5 Kg", 1.0, "Pacote (0,5Kg)"),
    (81, "#3", "🌾 Setor K: Mercearia (Grãos)", "Feijão Branco", "--", "Pacote 0,5 Kg", 1.0, "Pacote (0,5Kg)"),
    (82, "#4", "🌾 Setor K: Mercearia (Grãos)", "Feijão preto", "Tio João", "Máximo", 1.0, "Pacote (1Kg)"),
    (83, "#5", "🌾 Setor K: Mercearia (Grãos)", "Farinha de Mesa Fina Torrada", "Granfino", "Pacote 0,5 Kg", 1.0, "Pacote (0,5Kg)"),
    (84, "#6", "🌾 Setor K: Mercearia (Grãos)", "Farinha de Trigo (sem fermento)", "D. Benta", "Boa Sorte", 1.0, "Pacote (1Kg)"),
    (85, "#7", "🌾 Setor K: Mercearia (Grãos)", "Milharina ou Fubá Mimoso", "Granfino", "Pacote 0,5 Kg", 1.0, "Pacote (0,5Kg)"),
    (86, "#8", "🌾 Setor K: Mercearia (Grãos)", "Açúcar", "União", "Neve", 3.0, "Pacote (1Kg)"),

    # ➕ SETOR L: EXTRAS (SOMADOS AO MERCADO)
    (87, "#E1", "➕ Setor L: Extras", "Soja clara pequena - PTS", "--", "-", 1.0, "Kg"),
    (88, "#E2", "➕ Setor L: Extras", "Refil Filtro Cozinha", "--", "-", 2.0, "Unidade")
]

# Grupos de Equivalência Inteligente (Shampoo + Condicionador Avulsos <-> Kit Econômico)
GRUPOS_SHAMPOO_EQUIV = [
    {"avulsos": ["#29A", "#30A"], "kit": "#29K", "todos": {"#29A", "#30A", "#29K"}},
    {"avulsos": ["#29B", "#30B"], "kit": "#30K", "todos": {"#29B", "#30B", "#30K"}}
]

COLUNAS_CATALOGO = [
    "Ordem", "Codigo", "Setor", "Produto", "Marca1", "Marca2",
    "QtdPadrao", "Unidade", "PrecoRef", "Ativo"
]

COLUNAS_MES = [
    "Ordem", "Codigo", "Setor", "Produto", "Marca1", "Marca2", "Unidade",
    "Planejado", "QtdPlanejada", "PrecoUnit", "SubtotalPlanejado",
    "Comprado", "QtdComprada", "PrecoRealUnit", "SubtotalReal", "ObsMes"
]

COLUNAS_RESUMO = [
    "MesAno", "DataCompra", "TotalMercadoPlanejado", "TotalMercadoReal",
    "TotalFarmaciaPlanejado", "TotalFarmaciaReal",
    "Dinheiro", "BradescoDebito", "BradescoCredito",
    "MercadoPagoDebito", "MercadoPagoCredito", "NubankDebito", "NubankCredito",
    "PagamentoFarmacia", "ObsFechamento",
    "TranspIdaPag", "TranspIdaVal", "TranspVoltaPag", "TranspVoltaVal",
    "DescontoClube"
]

# === CONEXÃO COM GOOGLE SHEETS (GSPREAD) COM CACHE E PROTEÇÃO ANTI-QUOTA ===
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)

def executar_com_retry(func, *args, **kwargs):
    """Evita queda por limite de requisições por minuto (APIError 429) do Google Sheets."""
    ultimo_erro = None
    for tentativa in range(4):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ultimo_erro = e
            time.sleep(1.2 * (tentativa + 1))
    raise ultimo_erro

@st.cache_resource(ttl=600)
def get_spreadsheet_por_ano(ano_str=None):
    client = get_gspread_client()
    if not ano_str:
        ano_str = agora_br().strftime("%Y")
    nome_alvo = f"Compras {ano_str}"
    try:
        return executar_com_retry(client.open, nome_alvo)
    except gspread.SpreadsheetNotFound:
        return executar_com_retry(client.open, "Compras 2026")

@st.cache_data(ttl=600, show_spinner=False)
def listar_anos_disponiveis_gdrive():
    """
    Descobre automaticamente todos os arquivos 'Compras AAAA' criados na pasta do Google Drive.
    Se você criar 'Compras 2031', 'Compras 2032', etc., a lista de Mês/Ano cresce sozinha!
    """
    anos = set(range(2026, max(2031, int(agora_br().strftime("%Y")) + 2)))
    try:
        client = get_gspread_client()
        arquivos = executar_com_retry(client.list_spreadsheet_files)
        for arq in arquivos:
            nome = str(arq.get("name", "")).strip()
            if nome.startswith("Compras "):
                partes = nome.split(" ")
                if len(partes >= 2) and partes[-1].isdigit() and len(partes[-1]) == 4:
                    anos.add(int(partes[-1]))
    except Exception:
        pass
    return sorted(list(anos))

def limpar_cache_dados():
    """Limpa o cache em memória sempre que algum dado é salvo na planilha."""
    st.cache_data.clear()

def criar_aba_no_inicio(spreadsheet, titulo, linhas="150", colunas="20"):
    try:
        return executar_com_retry(spreadsheet.add_worksheet, title=titulo, rows=linhas, cols=colunas, index=0)
    except TypeError:
        return executar_com_retry(spreadsheet.add_worksheet, title=titulo, rows=linhas, cols=colunas)

def obter_aba_config(ano_str=None):
    sp = get_spreadsheet_por_ano(ano_str)
    try:
        sheet = executar_com_retry(sp.worksheet, "Configuracoes")
    except gspread.WorksheetNotFound:
        sheet = executar_com_retry(sp.add_worksheet, title="Configuracoes", rows="200", cols="2")
        mes_atual = "11 2026"
        executar_com_retry(
            sheet.append_rows,
            [
                ["Chave", "Valor"],
                ["mes_ano_ativo", mes_atual],
                ["data_compra_ativa", "05/11/2026"]
            ],
            value_input_option="USER_ENTERED"
        )
    return sheet

@st.cache_data(ttl=180, show_spinner=False)
def carregar_config_dict(ano_str=None):
    try:
        raw = executar_com_retry(obter_aba_config(ano_str).get_values)
        cfg = {}
        if len(raw) > 1:
            for r in raw[1:]:
                if len(r) >= 2:
                    cfg[str(r[0]).strip()] = str(r[1]).strip()
        return cfg
    except Exception:
        return {}

def salvar_configs(novas_configs_dict, ano_str=None):
    sheet = obter_aba_config(ano_str)
    existente = carregar_config_dict(ano_str).copy()
    existente.update({str(k): str(v) for k, v in novas_configs_dict.items()})
    linhas = [["Chave", "Valor"]]
    for k, v in existente.items():
        linhas.append([str(k), str(v)])
    executar_com_retry(sheet.clear)
    executar_com_retry(sheet.append_rows, linhas, value_input_option="USER_ENTERED")
    limpar_cache_dados()

def obter_aba_catalogo(ano_str=None):
    sp = get_spreadsheet_por_ano(ano_str)
    try:
        sheet = executar_com_retry(sp.worksheet, "Catalogo")
        vals = executar_com_retry(sheet.get_values)
        if len(vals) <= 1:
            raise gspread.WorksheetNotFound("Catálogo vazio")
        # Migração automática para v.1.20.1 (repara #ERROR! de '+Forte', mantém 6 variações de Shampoo e preserva preços/quantidades)
        codigos_atuais = {str(r[1]).strip() for r in vals[1:] if len(r) > 1}
        mapa_unid_atuais = {str(r[1]).strip(): (r[7] if len(r) > 7 else "") for r in vals[1:] if len(r) > 1}
        tem_erro_formula = any(
            (len(r) > 4 and "ERROR" in str(r[4]).upper()) or (len(r) > 5 and "ERROR" in str(r[5]).upper())
            for r in vals[1:]
        )
        precisa_migrar_v1201 = (
            tem_erro_formula
            or "#22A" not in codigos_atuais
            or "#29A" not in codigos_atuais
            or "#30K" not in codigos_atuais
            or mapa_unid_atuais.get("#1") != "Pacote (5Kg)"
            or mapa_unid_atuais.get("#4") != "Pacote (1Kg)"
            or mapa_unid_atuais.get("#6") != "Pacote (1Kg)"
            or mapa_unid_atuais.get("#8") != "Pacote (1Kg)"
            or any(len(r) > 7 and r[7] in ["Un", "Lt", "Pct", "Cx", "Sc", "Sq", "Vd", "Tb", "Rol"] for r in vals[1:])
        )
        if precisa_migrar_v1201:
            precos_antigos = {str(r[1]).strip(): (r[8] if len(r) > 8 else "0,00") for r in vals[1:] if len(r) > 1}
            qtds_antigas = {str(r[1]).strip(): safe_float(r[6]) for r in vals[1:] if len(r) > 6}
            if "#22" in precos_antigos and "#22A" not in precos_antigos:
                precos_antigos["#22A"] = precos_antigos["#22"]
                precos_antigos["#22B"] = precos_antigos["#22"]
            if "#29" in precos_antigos and "#29A" not in precos_antigos:
                precos_antigos["#29A"] = precos_antigos["#29"]
            if "#30" in precos_antigos and "#30A" not in precos_antigos:
                precos_antigos["#30A"] = precos_antigos["#30"]
            linhas_mig = [COLUNAS_CATALOGO]
            cods_oficiais = {it[1] for it in CATALOGO_INICIAL}
            for item in CATALOGO_INICIAL:
                ordem, cod, setor, prod, m1, m2, qtd_p, unid = item
                pr_salvo = precos_antigos.get(cod, "0,00")
                qtd_usar = qtds_antigas.get(cod, qtd_p) if (cod in qtds_antigas and qtds_antigas[cod] > 0 and cod != "#1") else qtd_p
                linhas_mig.append([
                    str(ordem), cod, setor, prod,
                    escapar_texto_sheets(m1), escapar_texto_sheets(m2),
                    formatar_num_planilha(qtd_usar, 3), unid, pr_salvo, "TRUE"
                ])
            for r in vals[1:]:
                if len(r) > 1 and str(r[1]).strip() not in cods_oficiais and str(r[1]).strip() not in ["#22", "#29", "#30"]:
                    r_copia = list(r[:len(COLUNAS_CATALOGO)])
                    if len(r_copia) > 4:
                        r_copia[4] = escapar_texto_sheets(limpar_marca_lida(r_copia[4], r_copia[1]))
                    linhas_mig.append(r_copia)
            executar_com_retry(sheet.clear)
            executar_com_retry(sheet.append_rows, linhas_mig, value_input_option="USER_ENTERED")
        return sheet
    except gspread.WorksheetNotFound:
        try:
            sheet = executar_com_retry(sp.worksheet, "Catalogo")
            executar_com_retry(sheet.clear)
        except gspread.WorksheetNotFound:
            sheet = executar_com_retry(sp.add_worksheet, title="Catalogo", rows="200", cols="12")
        linhas_init = [COLUNAS_CATALOGO]
        for item in CATALOGO_INICIAL:
            ordem, cod, setor, prod, m1, m2, qtd_p, unid = item
            linhas_init.append([
                str(ordem), cod, setor, prod,
                escapar_texto_sheets(m1), escapar_texto_sheets(m2),
                formatar_num_planilha(qtd_p, 3), unid, "0,00", "TRUE"
            ])
        executar_com_retry(sheet.append_rows, linhas_init, value_input_option="USER_ENTERED")
        return sheet

@st.cache_data(ttl=180, show_spinner=False)
def carregar_df_catalogo(ano_str=None):
    sheet = obter_aba_catalogo(ano_str)
    vals = executar_com_retry(sheet.get_values)
    if len(vals) > 1:
        df = pd.DataFrame(vals[1:], columns=vals[0])
    else:
        df = pd.DataFrame(columns=COLUNAS_CATALOGO)
    for c in COLUNAS_CATALOGO:
        if c not in df.columns:
            df[c] = ""
    df["Marca1"] = [limpar_marca_lida(m, c) for m, c in zip(df["Marca1"], df["Codigo"])]
    df["Marca2"] = [limpar_marca_lida(m, c) for m, c in zip(df["Marca2"], df["Codigo"])]
    df["Ordem_num"] = df["Ordem"].apply(lambda x: int(safe_float(x)) if safe_float(x) > 0 else 999)
    df["QtdPadrao_num"] = df["QtdPadrao"].apply(safe_float)
    df["PrecoRef_num"] = df["PrecoRef"].apply(safe_float)
    df["Ativo_bool"] = df["Ativo"].apply(lambda x: True if str(x).strip() == "" else safe_bool(x))
    df = df.sort_values("Ordem_num").reset_index(drop=True)
    return df

def obter_aba_resumo_mensal(ano_str=None):
    sp = get_spreadsheet_por_ano(ano_str)
    try:
        sheet = executar_com_retry(sp.worksheet, "Resumo_Mensal")
        vals = executar_com_retry(sheet.get_values)
        if len(vals) == 0:
            executar_com_retry(sheet.append_row, COLUNAS_RESUMO, value_input_option="USER_ENTERED")
        return sheet
    except gspread.WorksheetNotFound:
        sheet = executar_com_retry(sp.add_worksheet, title="Resumo_Mensal", rows="100", cols="20")
        executar_com_retry(sheet.append_row, COLUNAS_RESUMO, value_input_option="USER_ENTERED")
        return sheet

def obter_aba_mes(mes_ano_str, ano_str=None):
    if not ano_str:
        ano_str = mes_ano_str.split(" ")[-1] if " " in mes_ano_str else agora_br().strftime("%Y")
    sp = get_spreadsheet_por_ano(ano_str)
    titulo_aba = f"{mes_ano_str} Compras"
    try:
        sheet = executar_com_retry(sp.worksheet, titulo_aba)
        vals = executar_com_retry(sheet.get_values)
        if len(vals) > 1:
            return sheet, vals
    except gspread.WorksheetNotFound:
        sheet = criar_aba_no_inicio(sp, titulo_aba, linhas="160", colunas="18")

    # Se a aba do mês acabou de ser criada (ou estava vazia), popula com o Catálogo Oficial em 1 única chamada
    df_cat = carregar_df_catalogo(ano_str)
    df_cat_ativos = df_cat[df_cat["Ativo_bool"]].copy()
    linhas_mes = [COLUNAS_MES]
    for _, r in df_cat_ativos.iterrows():
        qtd_p = safe_float(r["QtdPadrao_num"])
        preco_ref = safe_float(r["PrecoRef_num"])
        linhas_mes.append([
            str(int(r["Ordem_num"])),
            str(r["Codigo"]),
            str(r["Setor"]),
            str(r["Produto"]),
            escapar_texto_sheets(r["Marca1"]),
            escapar_texto_sheets(r["Marca2"]),
            str(r["Unidade"]),
            "FALSE",  # Planejado
            formatar_num_planilha(qtd_p, 3),
            formatar_num_planilha(preco_ref, 2),
            "0,00",   # Subtotal Planejado
            "FALSE",  # Comprado
            formatar_num_planilha(qtd_p, 3),
            formatar_num_planilha(preco_ref, 2),
            "0,00",   # Subtotal Real
            ""        # ObsMes
        ])
    executar_com_retry(sheet.clear)
    executar_com_retry(sheet.append_rows, linhas_mes, value_input_option="USER_ENTERED")
    return sheet, linhas_mes

@st.cache_data(ttl=300, show_spinner=False)
def ler_dados_aba_mes_cached(mes_ano_str, ano_str=None):
    sheet, vals = obter_aba_mes(mes_ano_str, ano_str)
    if len(vals) > 1:
        df = pd.DataFrame(vals[1:], columns=vals[0])
    else:
        df = pd.DataFrame(columns=COLUNAS_MES)
    for c in COLUNAS_MES:
        if c not in df.columns:
            df[c] = ""

    # Sincroniza nomes/unidades/ordem/quantidades padrão do Catálogo e repara eventual #ERROR! nas marcas
    df_cat = carregar_df_catalogo(ano_str)
    cods_obsoletos = {"#22", "#29", "#30"}
    if any(c in df["Codigo"].astype(str).str.strip().values for c in cods_obsoletos):
        df = df[~df["Codigo"].astype(str).str.strip().isin(cods_obsoletos)].copy()

    mapa_cat_meta = {str(rc["Codigo"]).strip(): rc for _, rc in df_cat.iterrows()}
    mapa_qtd_fabrica = {str(it[1]).strip(): float(it[6]) for it in CATALOGO_INICIAL}
    precisa_salvar_migracao = False
    for idx_m, rm in df.iterrows():
        c_m = str(rm["Codigo"]).strip()
        m1_limpa = limpar_marca_lida(rm["Marca1"], c_m)
        if m1_limpa != str(rm["Marca1"]):
            df.at[idx_m, "Marca1"] = m1_limpa
            precisa_salvar_migracao = True

        if c_m in mapa_cat_meta:
            rc_ref = mapa_cat_meta[c_m]
            qtd_cat_atual = safe_float(rc_ref["QtdPadrao_num"])
            qtd_plan_mes = safe_float(rm["QtdPlanejada"])
            qtd_fab = mapa_qtd_fabrica.get(c_m, qtd_cat_atual)
            plan_b_atual = safe_bool(rm["Planejado"])
            comp_b_atual = safe_bool(rm["Comprado"])

            # Se o Arroz (#1) estava com unidade antiga "Kg" e Qtd 5, migra para 1 Pacote (5Kg)
            if c_m == "#1" and str(rm["Unidade"]) == "Kg" and qtd_plan_mes == 5.0:
                df.at[idx_m, "QtdPlanejada"] = "1"
                df.at[idx_m, "QtdComprada"] = "1"
                precisa_salvar_migracao = True

            # Sincroniza QtdPlanejada se o item ainda não foi marcado OU se foi alterado no Cadastro de Produtos em relação ao padrão inicial
            if qtd_cat_atual > 0 and abs(qtd_plan_mes - qtd_cat_atual) > 1e-4:
                if (not plan_b_atual and not comp_b_atual) or (abs(qtd_cat_atual - qtd_fab) > 1e-4 and abs(qtd_plan_mes - qtd_fab) < 1e-4):
                    df.at[idx_m, "QtdPlanejada"] = formatar_num_planilha(qtd_cat_atual, 3)
                    if not comp_b_atual:
                        df.at[idx_m, "QtdComprada"] = formatar_num_planilha(qtd_cat_atual, 3)
                    precisa_salvar_migracao = True

            if (str(rm["Produto"]) != str(rc_ref["Produto"]) or
                str(rm["Unidade"]) != str(rc_ref["Unidade"]) or
                str(df.at[idx_m, "Marca1"]) != str(rc_ref["Marca1"]) or
                str(rm["Marca2"]) != str(rc_ref["Marca2"]) or
                str(rm["Ordem"]) != str(int(rc_ref["Ordem_num"]))):
                df.at[idx_m, "Ordem"] = str(int(rc_ref["Ordem_num"]))
                df.at[idx_m, "Setor"] = str(rc_ref["Setor"])
                df.at[idx_m, "Produto"] = str(rc_ref["Produto"])
                df.at[idx_m, "Marca1"] = str(rc_ref["Marca1"])
                df.at[idx_m, "Marca2"] = str(rc_ref["Marca2"])
                df.at[idx_m, "Unidade"] = str(rc_ref["Unidade"])
                precisa_salvar_migracao = True

    codigos_mes = set(df["Codigo"].astype(str).str.strip().tolist())
    novas_linhas = []
    for _, rc in df_cat[df_cat["Ativo_bool"]].iterrows():
        cod_c = str(rc["Codigo"]).strip()
        if cod_c and cod_c not in codigos_mes:
            qtd_p = safe_float(rc["QtdPadrao_num"])
            pr_p = safe_float(rc["PrecoRef_num"])
            nova = {
                "Ordem": str(int(rc["Ordem_num"])),
                "Codigo": cod_c,
                "Setor": str(rc["Setor"]),
                "Produto": str(rc["Produto"]),
                "Marca1": str(rc["Marca1"]),
                "Marca2": str(rc["Marca2"]),
                "Unidade": str(rc["Unidade"]),
                "Planejado": "FALSE",
                "QtdPlanejada": formatar_num_planilha(qtd_p, 3),
                "PrecoUnit": formatar_num_planilha(pr_p, 2),
                "SubtotalPlanejado": "0,00",
                "Comprado": "FALSE",
                "QtdComprada": formatar_num_planilha(qtd_p, 3),
                "PrecoRealUnit": formatar_num_planilha(pr_p, 2),
                "SubtotalReal": "0,00",
                "ObsMes": ""
            }
            novas_linhas.append(nova)
            precisa_salvar_migracao = True
    if novas_linhas:
        df = pd.concat([df, pd.DataFrame(novas_linhas)], ignore_index=True)

    df["Ordem_num"] = df["Ordem"].apply(lambda x: int(safe_float(x)) if safe_float(x) > 0 else 999)
    df["Planejado_bool"] = df["Planejado"].apply(safe_bool)
    df["Comprado_bool"] = df["Comprado"].apply(safe_bool)
    df["QtdPlanejada_num"] = df["QtdPlanejada"].apply(safe_float)
    df["PrecoUnit_num"] = df["PrecoUnit"].apply(safe_float)
    df["QtdComprada_num"] = df["QtdComprada"].apply(safe_float)
    df["PrecoRealUnit_num"] = df["PrecoRealUnit"].apply(safe_float)
    df = df.sort_values("Ordem_num").reset_index(drop=True)

    if precisa_salvar_migracao:
        try:
            salvar_df_mes(mes_ano_str, df, ano_str, atualizar_preco_catalogo=False)
        except Exception:
            pass

    return df

def carregar_df_mes(mes_ano_str, ano_str=None):
    """Retorna uma cópia rápida em memória (0 chamadas extras de API durante a navegação)."""
    df = ler_dados_aba_mes_cached(mes_ano_str, ano_str).copy()
    return df, mes_ano_str

def salvar_df_mes(sheet_ou_mes_ano, df_mes, ano_str=None, atualizar_preco_catalogo=True):
    if isinstance(sheet_ou_mes_ano, str):
        mes_ano_ref = sheet_ou_mes_ano
        if not ano_str:
            ano_str = mes_ano_ref.split(" ")[-1] if " " in mes_ano_ref else agora_br().strftime("%Y")
        sp = get_spreadsheet_por_ano(ano_str)
        sheet = executar_com_retry(sp.worksheet, f"{mes_ano_ref} Compras")
    else:
        sheet = sheet_ou_mes_ano

    linhas_salvar = [COLUNAS_MES]
    mapa_precos_ref = {}
    for _, r in df_mes.sort_values("Ordem_num").iterrows():
        plan_b = bool(r["Planejado_bool"])
        comp_b = bool(r["Comprado_bool"])
        qtd_pl = safe_float(r["QtdPlanejada_num"])
        pr_pl = safe_float(r["PrecoUnit_num"])
        qtd_co = safe_float(r["QtdComprada_num"])
        pr_co = safe_float(r["PrecoRealUnit_num"])
        if pr_co <= 0 and pr_pl > 0:
            pr_co = pr_pl
        if pr_pl <= 0 and pr_co > 0:
            pr_pl = pr_co

        sub_pl = arredondar_moeda(qtd_pl * pr_pl, 2) if plan_b else 0.0
        sub_co = arredondar_moeda(qtd_co * pr_co, 2) if comp_b else 0.0

        cod_str = str(r["Codigo"]).strip()
        if pr_co > 0:
            mapa_precos_ref[cod_str] = pr_co
        elif pr_pl > 0:
            mapa_precos_ref[cod_str] = pr_pl

        m1_limpa = limpar_marca_lida(r["Marca1"], cod_str)
        m2_limpa = limpar_marca_lida(r["Marca2"], cod_str)

        linhas_salvar.append([
            str(int(safe_float(r["Ordem_num"]))),
            cod_str,
            str(r["Setor"]),
            str(r["Produto"]),
            escapar_texto_sheets(m1_limpa),
            escapar_texto_sheets(m2_limpa),
            str(r["Unidade"]),
            "TRUE" if plan_b else "FALSE",
            formatar_num_planilha(qtd_pl, 3),
            formatar_num_planilha(pr_pl, 2),
            formatar_num_planilha(sub_pl, 2),
            "TRUE" if comp_b else "FALSE",
            formatar_num_planilha(qtd_co, 3),
            formatar_num_planilha(pr_co, 2),
            formatar_num_planilha(sub_co, 2),
            escapar_texto_sheets(str(r.get("ObsMes", "") or ""))
        ])

    executar_com_retry(sheet.clear)
    executar_com_retry(sheet.append_rows, linhas_salvar, value_input_option="USER_ENTERED")

    # Atualiza PrecoRef no Catálogo para já servir de base nos próximos meses
    if atualizar_preco_catalogo and mapa_precos_ref:
        try:
            sh_cat = obter_aba_catalogo(ano_str)
            vals_cat = executar_com_retry(sh_cat.get_values)
            if len(vals_cat) > 1:
                novas_cat = [vals_cat[0]]
                for row_c in vals_cat[1:]:
                    while len(row_c) < len(COLUNAS_CATALOGO):
                        row_c.append("")
                    cod_c = str(row_c[1]).strip()
                    row_c[4] = escapar_texto_sheets(limpar_marca_lida(row_c[4], cod_c))
                    row_c[5] = escapar_texto_sheets(limpar_marca_lida(row_c[5], cod_c))
                    if cod_c in mapa_precos_ref and mapa_precos_ref[cod_c] > 0:
                        row_c[8] = formatar_num_planilha(mapa_precos_ref[cod_c], 2)
                    novas_cat.append(row_c[:len(COLUNAS_CATALOGO)])
                executar_com_retry(sh_cat.clear)
                executar_com_retry(sh_cat.append_rows, novas_cat, value_input_option="USER_ENTERED")
        except Exception:
            pass
    limpar_cache_dados()

def salvar_resumo_pagamento(mes_ano_str, dados_resumo_dict, ano_str=None):
    sh_res = obter_aba_resumo_mensal(ano_str)
    vals = executar_com_retry(sh_res.get_values)
    cabecalho = COLUNAS_RESUMO
    linhas = [cabecalho]
    encontrou = False

    nova_linha = [
        mes_ano_str,
        str(dados_resumo_dict.get("DataCompra", hoje_br().strftime("%d/%m/%Y"))),
        formatar_num_planilha(dados_resumo_dict.get("TotalMercadoPlanejado", 0.0), 2),
        formatar_num_planilha(dados_resumo_dict.get("TotalMercadoReal", 0.0), 2),
        formatar_num_planilha(dados_resumo_dict.get("TotalFarmaciaPlanejado", 0.0), 2),
        formatar_num_planilha(dados_resumo_dict.get("TotalFarmaciaReal", 0.0), 2),
        formatar_num_planilha(dados_resumo_dict.get("Dinheiro", 0.0), 2),
        formatar_num_planilha(dados_resumo_dict.get("BradescoDebito", 0.0), 2),
        formatar_num_planilha(dados_resumo_dict.get("BradescoCredito", 0.0), 2),
        formatar_num_planilha(dados_resumo_dict.get("MercadoPagoDebito", 0.0), 2),
        formatar_num_planilha(dados_resumo_dict.get("MercadoPagoCredito", 0.0), 2),
        formatar_num_planilha(dados_resumo_dict.get("NubankDebito", 0.0), 2),
        formatar_num_planilha(dados_resumo_dict.get("NubankCredito", 0.0), 2),
        str(dados_resumo_dict.get("PagamentoFarmacia", "Dinheiro")),
        str(dados_resumo_dict.get("ObsFechamento", "")),
        str(dados_resumo_dict.get("TranspIdaPag", "Não houve")),
        formatar_num_planilha(dados_resumo_dict.get("TranspIdaVal", 0.0), 2),
        str(dados_resumo_dict.get("TranspVoltaPag", "Não houve")),
        formatar_num_planilha(dados_resumo_dict.get("TranspVoltaVal", 0.0), 2),
        formatar_num_planilha(dados_resumo_dict.get("DescontoClube", 0.0), 2)
    ]

    if len(vals) > 1:
        for r in vals[1:]:
            if len(r) > 0 and str(r[0]).strip() == mes_ano_str:
                linhas.append(nova_linha)
                encontrou = True
            else:
                linhas.append(r)
    if not encontrou:
        linhas.append(nova_linha)

    executar_com_retry(sh_res.clear)
    executar_com_retry(sh_res.append_rows, linhas, value_input_option="USER_ENTERED")
    limpar_cache_dados()

@st.cache_data(ttl=180, show_spinner=False)
def obter_resumo_mes(mes_ano_str, ano_str=None):
    try:
        sh_res = obter_aba_resumo_mensal(ano_str)
        vals = executar_com_retry(sh_res.get_values)
        if len(vals) > 1:
            for r in vals[1:]:
                if len(r) >= 13 and str(r[0]).strip() == mes_ano_str:
                    return {
                        "MesAno": r[0],
                        "DataCompra": r[1] if len(r) > 1 else "",
                        "TotalMercadoPlanejado": safe_float(r[2]) if len(r) > 2 else 0.0,
                        "TotalMercadoReal": safe_float(r[3]) if len(r) > 3 else 0.0,
                        "TotalFarmaciaPlanejado": safe_float(r[4]) if len(r) > 4 else 0.0,
                        "TotalFarmaciaReal": safe_float(r[5]) if len(r) > 5 else 0.0,
                        "Dinheiro": safe_float(r[6]) if len(r) > 6 else 0.0,
                        "BradescoDebito": safe_float(r[7]) if len(r) > 7 else 0.0,
                        "BradescoCredito": safe_float(r[8]) if len(r) > 8 else 0.0,
                        "MercadoPagoDebito": safe_float(r[9]) if len(r) > 9 else 0.0,
                        "MercadoPagoCredito": safe_float(r[10]) if len(r) > 10 else 0.0,
                        "NubankDebito": safe_float(r[11]) if len(r) > 11 else 0.0,
                        "NubankCredito": safe_float(r[12]) if len(r) > 12 else 0.0,
                        "PagamentoFarmacia": r[13] if len(r) > 13 and r[13] else "Dinheiro",
                        "ObsFechamento": r[14] if len(r) > 14 else "",
                        "TranspIdaPag": r[15] if len(r) > 15 and r[15] else "Não houve",
                        "TranspIdaVal": safe_float(r[16]) if len(r) > 16 else 0.0,
                        "TranspVoltaPag": r[17] if len(r) > 17 and r[17] else "Não houve",
                        "TranspVoltaVal": safe_float(r[18]) if len(r) > 18 else 0.0,
                        "DescontoClube": safe_float(r[19]) if len(r) > 19 else 0.0
                    }
    except Exception:
        pass
    return {}

def calcular_totais_df(df_mes):
    eh_farmacia = df_mes["Setor"].astype(str).str.contains("Farmácia", case=False, na=False)
    df_farm = df_mes[eh_farmacia]
    df_merc = df_mes[~eh_farmacia]

    tot_farm_plan = sum(
        arredondar_moeda(r["QtdPlanejada_num"] * r["PrecoUnit_num"], 2)
        for _, r in df_farm[df_farm["Planejado_bool"]].iterrows()
    )
    tot_farm_real = sum(
        arredondar_moeda(r["QtdComprada_num"] * (r["PrecoRealUnit_num"] if r["PrecoRealUnit_num"] > 0 else r["PrecoUnit_num"]), 2)
        for _, r in df_farm[df_farm["Comprado_bool"]].iterrows()
    )

    tot_merc_plan = sum(
        arredondar_moeda(r["QtdPlanejada_num"] * r["PrecoUnit_num"], 2)
        for _, r in df_merc[df_merc["Planejado_bool"]].iterrows()
    )
    tot_merc_real = sum(
        arredondar_moeda(r["QtdComprada_num"] * (r["PrecoRealUnit_num"] if r["PrecoRealUnit_num"] > 0 else r["PrecoUnit_num"]), 2)
        for _, r in df_merc[df_merc["Comprado_bool"]].iterrows()
    )

    qtd_itens_plan_merc = int(df_merc["Planejado_bool"].sum())
    qtd_itens_comp_merc = int(df_merc["Comprado_bool"].sum())
    qtd_itens_plan_farm = int(df_farm["Planejado_bool"].sum())
    qtd_itens_comp_farm = int(df_farm["Comprado_bool"].sum())

    return {
        "farm_plan": arredondar_moeda(tot_farm_plan, 2),
        "farm_real": arredondar_moeda(tot_farm_real, 2),
        "merc_plan": arredondar_moeda(tot_merc_plan, 2),
        "merc_real": arredondar_moeda(tot_merc_real, 2),
        "itens_plan_merc": qtd_itens_plan_merc,
        "itens_comp_merc": qtd_itens_comp_merc,
        "itens_plan_farm": qtd_itens_plan_farm,
        "itens_comp_farm": qtd_itens_comp_farm
    }

def codigos_visiveis_conferencia(df_mes):
    """
    Retorna o conjunto de códigos que devem aparecer na Conferência quando 'Mostrar só itens planejados' está ativo.
    Se qualquer item de um grupo Shampoo/Condicionador/Kit (Seda ou Pantene) estiver planejado, exibe as 3 opções do grupo!
    """
    planejados_ou_comprados = set(
        df_mes[df_mes["Planejado_bool"] | df_mes["Comprado_bool"]]["Codigo"].astype(str).str.strip().tolist()
    )
    visiveis = set(planejados_ou_comprados)
    for grp in GRUPOS_SHAMPOO_EQUIV:
        if visiveis.intersection(grp["todos"]):
            visiveis.update(grp["todos"])
    return visiveis

def aplicar_equivalencia_kits_shampoo(df_mes):
    """
    Substituição automática inteligente entre Kit (Shampoo + Condicionador) e Unidades Avulsas:
    - Se o usuário planejou os avulsos (#29A/#30A ou #29B/#30B) mas no mercado comprou o Kit (#29K ou #30K),
      transfere o planejamento para o Kit e desmarca o planejamento dos avulsos não comprados (para não caírem em 'Faltou Comprar').
    - Se planejou o Kit mas comprou os avulsos, transfere o planejamento do Kit para os avulsos comprados.
    """
    idx_por_cod = {str(r["Codigo"]).strip(): idx for idx, r in df_mes.iterrows()}
    for grp in GRUPOS_SHAMPOO_EQUIV:
        cod_kit = grp["kit"]
        cods_av = grp["avulsos"]
        if cod_kit not in idx_por_cod:
            continue
        i_kit = idx_por_cod[cod_kit]
        kit_comp = bool(df_mes.at[i_kit, "Comprado_bool"])
        kit_plan = bool(df_mes.at[i_kit, "Planejado_bool"])

        av_comprados = [c for c in cods_av if c in idx_por_cod and bool(df_mes.at[idx_por_cod[c], "Comprado_bool"])]
        av_planejados = [c for c in cods_av if c in idx_por_cod and bool(df_mes.at[idx_por_cod[c], "Planejado_bool"])]

        if kit_comp and av_planejados:
            df_mes.at[i_kit, "Planejado_bool"] = True
            for c_av in cods_av:
                if c_av in idx_por_cod and not bool(df_mes.at[idx_por_cod[c_av], "Comprado_bool"]):
                    df_mes.at[idx_por_cod[c_av], "Planejado_bool"] = False
        elif av_comprados and kit_plan and not kit_comp:
            df_mes.at[i_kit, "Planejado_bool"] = False
            for c_av in av_comprados:
                df_mes.at[idx_por_cod[c_av], "Planejado_bool"] = True
    return df_mes

# === GERADOR DO APLICATIVO HTML 100% OFFLINE E SINCRONIZADOR DE RETORNO (.JSON) ===
def gerar_html_offline_mercado(mes_ano_str, df_mes, resumo_dict, data_padrao_str):
    """
    Gera um arquivo HTML 100% autônomo (zero internet necessária) contendo todos os itens,
    setores retráteis ('cortinas'), equivalência Kit/Avulso, adição de item extra,
    cancelamento de item planejado, calculadora de caixa (Clube de Descontos + Dinheiro + Cartões)
    e salvamento automático em localStorage.
    """
    itens_json = []
    for _, r in df_mes.sort_values("Ordem_num").iterrows():
        unid_str = str(r["Unidade"])
        cod_str = str(r["Codigo"]).strip()
        m2_limpa = limpar_marca_lida(r["Marca2"], cod_str)
        itens_json.append({
            "ordem": int(safe_float(r["Ordem_num"])),
            "codigo": cod_str,
            "setor": str(r["Setor"]),
            "produto": str(r["Produto"]),
            "marca1": exibir_marca_limpa(r["Marca1"], cod_str),
            "marca2": m2_limpa if m2_limpa not in ["-", "--", "nan"] else "",
            "unidade": unid_str,
            "fracionado": eh_unidade_fracionada(unid_str),
            "planejado": bool(r["Planejado_bool"]),
            "qtd_plan": safe_float(r["QtdPlanejada_num"]),
            "preco_plan": safe_float(r["PrecoUnit_num"]),
            "comprado": bool(r["Comprado_bool"]),
            "qtd_comp": safe_float(r["QtdComprada_num"]) if safe_float(r["QtdComprada_num"]) > 0 else safe_float(r["QtdPlanejada_num"]),
            "preco_comp": safe_float(r["PrecoRealUnit_num"]) if safe_float(r["PrecoRealUnit_num"]) > 0 else safe_float(r["PrecoUnit_num"]),
            "obs": str(r.get("ObsMes", "") or "")
        })

    fechamento_init = {
        "data_compra": str(resumo_dict.get("DataCompra") or data_padrao_str),
        "desconto_clube": safe_float(resumo_dict.get("DescontoClube", 0.0)),
        "dinheiro": safe_float(resumo_dict.get("Dinheiro", 0.0)),
        "bradesco_deb": safe_float(resumo_dict.get("BradescoDebito", 0.0)),
        "bradesco_cred": safe_float(resumo_dict.get("BradescoCredito", 0.0)),
        "mp_deb": safe_float(resumo_dict.get("MercadoPagoDebito", 0.0)),
        "mp_cred": safe_float(resumo_dict.get("MercadoPagoCredito", 0.0)),
        "nubank_deb": safe_float(resumo_dict.get("NubankDebito", 0.0)),
        "nubank_cred": safe_float(resumo_dict.get("NubankCredito", 0.0)),
        "pag_farmacia": str(resumo_dict.get("PagamentoFarmacia") or "Dinheiro"),
        "transp_ida_pag": str(resumo_dict.get("TranspIdaPag") or "Não houve"),
        "transp_ida_val": safe_float(resumo_dict.get("TranspIdaVal", 0.0)),
        "transp_volta_pag": str(resumo_dict.get("TranspVoltaPag") or "Não houve"),
        "transp_volta_val": safe_float(resumo_dict.get("TranspVoltaVal", 0.0)),
        "obs_fechamento": str(resumo_dict.get("ObsFechamento") or "")
    }

    payload_inicial = {
        "versao": VERSAO_APP,
        "mes_ano": mes_ano_str,
        "setores": SETORES_OFICIAIS,
        "itens": itens_json,
        "fechamento": fechamento_init
    }
    json_embutido = json.dumps(payload_inicial, ensure_ascii=False)
    chave_storage = f"compras_offline_v120_{mes_ano_str.replace(' ', '_')}"
    nome_arq_retorno = f"{mes_ano_str} Compras Retorno.json"

    html_doc = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>{mes_ano_str} Compras (Offline)</title>
<style>
  :root {{
    --bg: #0E1117;
    --card: #1A202C;
    --border: #2D3748;
    --text: #E2E8F0;
    --sub: #90CDF4;
    --muted: #A0AEC0;
    --green: #2ECC71;
    --blue: #1E88E5;
    --purple: #AB47BC;
    --orange: #FF9800;
    --red: #E53E3E;
  }}
  * {{ box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  body {{ background: var(--bg); color: var(--text); margin: 0; padding: 10px; padding-bottom: 60px; }}
  h2 {{ text-align: center; margin: 6px 0 4px 0; font-size: 1.25rem; }}
  .sub-top {{ text-align: center; font-size: 0.80rem; color: var(--green); margin-bottom: 10px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }}
  .card-resumo {{ padding: 10px; border-radius: 8px; font-size: 0.85rem; line-height: 1.35; }}
  .card-farm {{ background: rgba(156,39,176,0.15); border-left: 4px solid var(--purple); }}
  .card-merc {{ background: rgba(46,125,50,0.18); border-left: 4px solid var(--green); }}
  .card-caixa {{ background: rgba(255,152,0,0.14); border: 1px solid var(--orange); border-left: 5px solid var(--orange); padding: 10px; border-radius: 8px; font-size: 0.86rem; line-height: 1.4; margin: 10px 0; }}
  .toolbar {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }}
  .btn {{ border: 1px solid var(--border); background: var(--card); color: var(--text); padding: 8px 10px; border-radius: 6px; font-size: 0.84rem; font-weight: 600; cursor: pointer; flex: 1; text-align: center; }}
  .btn-active {{ background: var(--blue); border-color: #63B3ED; color: #FFF; }}
  .btn-green {{ background: #2E7D32; border-color: var(--green); color: #FFF; font-size: 0.95rem; padding: 12px; width: 100%; margin-top: 8px; }}
  .btn-orange {{ background: #C05621; border-color: var(--orange); color: #FFF; font-size: 0.88rem; padding: 10px; width: 100%; margin-top: 6px; }}
  select, input[type="text"], input[type="number"] {{
    background: #141821; color: #FFF; border: 1px solid var(--border); border-radius: 6px; padding: 7px 8px; font-size: 0.90rem; width: 100%;
  }}
  details.setor-box {{ background: rgba(26,32,44,0.65); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 10px; overflow: hidden; }}
  details.setor-box > summary {{
    background: linear-gradient(90deg, rgba(30,136,229,0.25) 0%, rgba(30,136,229,0.05) 100%);
    padding: 10px 12px; font-weight: 700; font-size: 0.92rem; cursor: pointer; border-left: 4px solid #4FC3F7; list-style: none; display: flex; justify-content: space-between; align-items: center;
  }}
  .item-card {{ padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.07); }}
  .item-card.comprado-bg {{ background: rgba(46, 204, 113, 0.08); }}
  .item-title {{ font-size: 0.93rem; font-weight: 700; margin-bottom: 3px; }}
  .item-meta {{ font-size: 0.78rem; color: var(--muted); margin-bottom: 8px; }}
  .item-controls {{ display: grid; grid-template-columns: 1.1fr 0.9fr 1fr; gap: 6px; align-items: end; }}
  .chk-wrap {{ display: flex; flex-direction: column; gap: 5px; }}
  .chk-label {{ display: flex; align-items: center; gap: 6px; font-weight: 700; font-size: 0.88rem; cursor: pointer; user-select: none; padding: 5px 6px; border-radius: 6px; background: rgba(255,255,255,0.04); }}
  .chk-label input {{ width: 20px; height: 20px; accent-color: var(--green); }}
  .btn-cancel-plan {{ background: rgba(229,62,62,0.18); border: 1px solid var(--red); color: #FEB2B2; font-size: 0.72rem; padding: 3px 6px; border-radius: 4px; cursor: pointer; text-align: center; }}
  .btn-add-plan {{ background: rgba(30,136,229,0.18); border: 1px solid var(--blue); color: #90CDF4; font-size: 0.72rem; padding: 3px 6px; border-radius: 4px; cursor: pointer; text-align: center; }}
  .lbl-mini {{ font-size: 0.72rem; color: var(--muted); margin-bottom: 2px; display: block; }}
  .bank-row {{ display: flex; align-items: center; gap: 6px; font-size: 0.84rem; font-weight: 600; margin-top: 6px; margin-bottom: 3px; }}
  .bank-row img {{ width: 22px; height: 22px; border-radius: 4px; }}
</style>
</head>
<body>

<h2>🛒 {mes_ano_str} Compras (Offline)</h2>
<div class="sub-top" id="status_salvo">💾 100% Offline — Tudo é salvo automaticamente no celular</div>

<div class="grid-2">
  <div class="card-resumo card-farm" id="card_farm"></div>
  <div class="card-resumo card-merc" id="card_merc"></div>
</div>

<div class="toolbar">
  <button type="button" class="btn btn-active" id="btn_modo_plan" onclick="mudarModoFiltro(true)">🎯 Só Planejados</button>
  <button type="button" class="btn" id="btn_modo_todos" onclick="mudarModoFiltro(false)">📋 Todos (Cadastrar Preços)</button>
</div>

<div class="toolbar">
  <select id="sel_setor_filtro" onchange="renderizarLista()" style="flex:2;">
    <option value="TODOS">📋 Todos os Setores (Circuito A → L)</option>
  </select>
  <button type="button" class="btn" onclick="alternarCortinas(true)">📂 Abrir</button>
  <button type="button" class="btn" onclick="alternarCortinas(false)">📁 Fechar</button>
</div>

<details class="setor-box" style="margin-bottom:12px;">
  <summary>➕ Adicionar Item Extra de Última Hora</summary>
  <div style="padding:10px;">
    <div class="grid-2">
      <div>
        <label class="lbl-mini">Nome do Produto</label>
        <input type="text" id="ex_nome" placeholder="Ex: Pilha Alcalina">
      </div>
      <div>
        <label class="lbl-mini">Setor</label>
        <select id="ex_setor"></select>
      </div>
      <div>
        <label class="lbl-mini">Marca</label>
        <input type="text" id="ex_marca" value="Sem marca específica">
      </div>
      <div>
        <label class="lbl-mini">Unidade</label>
        <input type="text" id="ex_unid" value="Unidade">
      </div>
      <div>
        <label class="lbl-mini">Quantidade</label>
        <input type="number" id="ex_qtd" value="1" step="0.5">
      </div>
      <div>
        <label class="lbl-mini">Preço Unit. (R$)</label>
        <input type="number" id="ex_preco" value="0.00" step="0.50">
      </div>
    </div>
    <button type="button" class="btn btn-green" onclick="adicionarItemExtraOffline()">➕ Incluir no Carrinho (Já Comprado ✅)</button>
  </div>
</details>

<div id="container_setores"></div>

<details class="setor-box" open>
  <summary>🧾 Fechamento do Caixa, Clube de Descontos e Pagamentos</summary>
  <div style="padding:10px;">
    <div class="grid-2">
      <div>
        <label class="lbl-mini">Data Real da Compra</label>
        <input type="text" id="f_data" onchange="atualizarFechamento()">
      </div>
      <div>
        <label class="lbl-mini">🏷️ Clube de Descontos (R$)</label>
        <input type="number" id="f_clube" step="0.50" onchange="atualizarFechamento()">
      </div>
      <div>
        <label class="lbl-mini">💵 1º Pago em Dinheiro (R$)</label>
        <input type="number" id="f_dinheiro" step="10.0" onchange="atualizarFechamento()">
      </div>
      <div>
        <label class="lbl-mini">💊 Pago na Farmácia com</label>
        <select id="f_pag_farm" onchange="atualizarFechamento()">
          <option>Dinheiro</option>
          <option>Bradesco - Débito</option>
          <option>Bradesco - Crédito</option>
          <option>Mercado Pago - Débito</option>
          <option>Mercado Pago - Crédito</option>
          <option>Nubank - Débito</option>
          <option>Nubank - Crédito</option>
        </select>
      </div>
    </div>

    <div class="card-caixa" id="box_resumo_caixa"></div>

    <div class="grid-2">
      <div>
        <div class="bank-row"><img src="{LOGO_BRADESCO}"> Bradesco DÉB</div>
        <input type="number" id="f_bd" step="10" onchange="atualizarFechamento()">
        <div class="bank-row"><img src="{LOGO_MERCADOPAGO}"> Mercado Pago DÉB</div>
        <input type="number" id="f_md" step="10" onchange="atualizarFechamento()">
        <div class="bank-row"><img src="{LOGO_NUBANK}"> Nubank DÉB</div>
        <input type="number" id="f_nd" step="10" onchange="atualizarFechamento()">
      </div>
      <div>
        <div class="bank-row"><img src="{LOGO_BRADESCO}"> Bradesco CRÉD</div>
        <input type="number" id="f_bc" step="10" onchange="atualizarFechamento()">
        <div class="bank-row"><img src="{LOGO_MERCADOPAGO}"> Mercado Pago CRÉD</div>
        <input type="number" id="f_mc" step="10" onchange="atualizarFechamento()">
        <div class="bank-row"><img src="{LOGO_NUBANK}"> Nubank CRÉD</div>
        <input type="number" id="f_nc" step="10" onchange="atualizarFechamento()">
      </div>
    </div>

    <hr style="border:0;height:1px;background:var(--border);margin:12px 0;">
    <div style="font-weight:700;font-size:0.88rem;margin-bottom:6px;">🚕 Transporte (Ida e Volta)</div>
    <div class="grid-2">
      <div>
        <label class="lbl-mini">🚕 Ida — Pago com</label>
        <select id="f_ti_pag" onchange="atualizarFechamento()">
          <option>Não houve</option><option>Dinheiro</option>
          <option>Bradesco - Débito</option><option>Bradesco - Crédito</option>
          <option>Mercado Pago - Débito</option><option>Mercado Pago - Crédito</option>
          <option>Nubank - Débito</option><option>Nubank - Crédito</option>
        </select>
        <label class="lbl-mini" style="margin-top:4px;">🚕 Ida — Valor (R$)</label>
        <input type="number" id="f_ti_val" step="5" onchange="atualizarFechamento()">
      </div>
      <div>
        <label class="lbl-mini">🚕 Volta — Pago com</label>
        <select id="f_tv_pag" onchange="atualizarFechamento()">
          <option>Não houve</option><option>Dinheiro</option>
          <option>Bradesco - Débito</option><option>Bradesco - Crédito</option>
          <option>Mercado Pago - Débito</option><option>Mercado Pago - Crédito</option>
          <option>Nubank - Débito</option><option>Nubank - Crédito</option>
        </select>
        <label class="lbl-mini" style="margin-top:4px;">🚕 Volta — Valor (R$)</label>
        <input type="number" id="f_tv_val" step="5" onchange="atualizarFechamento()">
      </div>
    </div>
    <div style="margin-top:8px;">
      <label class="lbl-mini">📝 Observação Geral da Compra</label>
      <input type="text" id="f_obs" onchange="atualizarFechamento()">
    </div>
  </div>
</details>

<div style="margin-top:14px;">
  <button type="button" class="btn btn-green" onclick="baixarArquivoRetorno()">💾 Baixar Retorno ({nome_arq_retorno})</button>
  <button type="button" class="btn btn-orange" onclick="copiarJsonRetorno()">📋 Copiar Código de Retorno (Caso prefira colar no App)</button>
  <button type="button" class="btn" style="margin-top:12px;width:100%;font-size:0.75rem;opacity:0.7;" onclick="resetarParaPlanilhaOriginal()">🔄 Restaurar Dados Originais de Saída</button>
</div>

<script>
const CHAVE_STORAGE = "{chave_storage}";
const NOME_ARQ_RETORNO = "{nome_arq_retorno}";
const DADOS_ORIGINAIS = {json_embutido};

let estado = null;
let apenasPlanejados = true;
let cortinasAbertas = {{}};

const GRUPOS_SHAMPOO = [
  {{ avulsos: ["#29A", "#30A"], kit: "#29K", todos: ["#29A", "#30A", "#29K"] }},
  {{ avulsos: ["#29B", "#30B"], kit: "#30K", todos: ["#29B", "#30B", "#30K"] }}
];

function numSeguro(v) {{
  if (v === null || v === undefined || v === "") return 0;
  let s = String(v).replace("R$", "").trim().replace(",", ".");
  let n = parseFloat(s);
  return isNaN(n) ? 0 : n;
}}

function moedaBR(v) {{
  let n = Math.round((numSeguro(v) + Number.EPSILON) * 100) / 100;
  return "R$ " + n.toFixed(2).replace(".", ",");
}}

function repararMarcasSacoLixo(est) {{
  if (!est || !est.itens) return;
  est.itens.forEach(it => {{
    if (it.codigo === "#22A" && (!it.marca1 || it.marca1.toUpperCase().includes("ERROR"))) {{
      it.marca1 = "+Forte Reforçado - 50 Lts.";
    }}
    if (it.codigo === "#22B" && (!it.marca1 || it.marca1.toUpperCase().includes("ERROR"))) {{
      it.marca1 = "+Forte Reforçado - 100 Lts.";
    }}
  }});
}}

function carregarEstado() {{
  try {{
    let salvo = localStorage.getItem(CHAVE_STORAGE);
    if (salvo) {{
      estado = JSON.parse(salvo);
    }} else {{
      estado = JSON.parse(JSON.stringify(DADOS_ORIGINAIS));
    }}
  }} catch (e) {{
    estado = JSON.parse(JSON.stringify(DADOS_ORIGINAIS));
  }}
  repararMarcasSacoLixo(estado);
  estado.setores.forEach(s => {{
    if (cortinasAbertas[s] === undefined) cortinasAbertas[s] = true;
  }});
}}

function salvarEstado() {{
  try {{
    localStorage.setItem(CHAVE_STORAGE, JSON.stringify(estado));
    let agora = new Date();
    let h = String(agora.getHours()).padStart(2, '0') + ":" + String(agora.getMinutes()).padStart(2, '0') + ":" + String(agora.getSeconds()).padStart(2, '0');
    document.getElementById("status_salvo").innerText = "✅ Salvo na memória do celular às " + h;
  }} catch (e) {{}}
}}

function aplicarEquivalenciaKits() {{
  GRUPOS_SHAMPOO.forEach(grp => {{
    let itemKit = estado.itens.find(i => i.codigo === grp.kit);
    let itensAv = estado.itens.filter(i => grp.avulsos.includes(i.codigo));
    if (!itemKit) return;
    let algumAvPlan = itensAv.some(i => i.planejado);
    let algumAvComp = itensAv.some(i => i.comprado);
    if (itemKit.comprado && algumAvPlan) {{
      itemKit.planejado = true;
      itensAv.forEach(i => {{ if (!i.comprado) i.planejado = false; }});
    }} else if (algumAvComp && itemKit.planejado && !itemKit.comprado) {{
      itemKit.planejado = false;
      itensAv.forEach(i => {{ if (i.comprado) i.planejado = true; }});
    }}
  }});
}}

function codigosVisiveisModoPlanejado() {{
  let vis = new Set();
  estado.itens.forEach(i => {{
    if (i.planejado || i.comprado) vis.add(i.codigo);
  }});
  GRUPOS_SHAMPOO.forEach(grp => {{
    if (grp.todos.some(c => vis.has(c))) {{
      grp.todos.forEach(c => vis.add(c));
    }}
  }});
  return vis;
}}

function atualizarResumosTopoECaixa() {{
  let farmPlan = 0, farmReal = 0, fItensP = 0, fItensC = 0;
  let mercPlan = 0, mercReal = 0, mItensP = 0, mItensC = 0;

  estado.itens.forEach(it => {{
    let ehFarm = it.setor.toLowerCase().includes("farmácia");
    let subP = it.planejado ? (numSeguro(it.qtd_plan) * numSeguro(it.preco_plan)) : 0;
    let prUsar = numSeguro(it.preco_comp) > 0 ? numSeguro(it.preco_comp) : numSeguro(it.preco_plan);
    let subC = it.comprado ? (numSeguro(it.qtd_comp) * prUsar) : 0;
    if (ehFarm) {{
      farmPlan += subP; farmReal += subC;
      if (it.planejado) fItensP++;
      if (it.comprado) fItensC++;
    }} else {{
      mercPlan += subP; mercReal += subC;
      if (it.planejado) mItensP++;
      if (it.comprado) mItensC++;
    }}
  }});

  let clube = numSeguro(estado.fechamento.desconto_clube);
  let mercLiq = Math.max(0, mercReal - clube);

  document.getElementById("card_farm").innerHTML =
    `<b>💊 Farmácia</b><br>Carrinho: <b>${{fItensC}}/${{fItensP}}</b><br>Real: <b>${{moedaBR(farmReal)}}</b> <span style="color:#A0AEC0;font-size:0.75rem;">(Prev: ${{moedaBR(farmPlan)}})</span>`;

  let txtClube = clube > 0 ? `<br><span style="color:#2ECC71;">🏷️ Clube: -${{moedaBR(clube)}} → <b>Líq: ${{moedaBR(mercLiq)}}</b></span>` : "";
  document.getElementById("card_merc").innerHTML =
    `<b>🛒 Mercado (+ Extras)</b><br>Carrinho: <b>${{mItensC}}/${{mItensP}}</b><br>Bruto: <b>${{moedaBR(mercReal)}}</b>${{txtClube}}`;

  let baseCaixa = mercReal > 0 ? mercReal : mercPlan;
  let alvoLiq = Math.max(0, baseCaixa - clube);
  let din = numSeguro(estado.fechamento.dinheiro);
  let restaCartoes = Math.max(0, alvoLiq - din);
  let somaPag = din + numSeguro(estado.fechamento.bradesco_deb) + numSeguro(estado.fechamento.bradesco_cred)
                    + numSeguro(estado.fechamento.mp_deb) + numSeguro(estado.fechamento.mp_cred)
                    + numSeguro(estado.fechamento.nubank_deb) + numSeguro(estado.fechamento.nubank_cred);
  let dif = alvoLiq - somaPag;
  let statusDif = Math.abs(dif) < 0.05
    ? `<span style="color:#2ECC71;">✅ Pagamento 100% fechado!</span>`
    : `<span style="color:#FBD38D;">⚠️ Falta alocar nos cartões: <b>${{moedaBR(dif)}}</b></span>`;

  document.getElementById("box_resumo_caixa").innerHTML =
    `<b>📢 RESUMO DE CAIXA (MERCADO):</b><br>` +
    `• Subtotal Bruto: <b>${{moedaBR(baseCaixa)}}</b> | 🏷️ Clube: <b style="color:#2ECC71;">- ${{moedaBR(clube)}}</b><br>` +
    `• <b>(=) Valor Líquido a Pagar: ${{moedaBR(alvoLiq)}}</b><br>` +
    `• 1º Entregar em <b>💵 Dinheiro</b>: <b>${{moedaBR(din)}}</b> → <b>Resta p/ Cartões: ${{moedaBR(restaCartoes)}}</b><br>` +
    `• Total Lançado: <b>${{moedaBR(somaPag)}}</b> (${{statusDif}})`;
}}

function renderizarLista() {{
  const cont = document.getElementById("container_setores");
  cont.innerHTML = "";
  const filtroSetor = document.getElementById("sel_setor_filtro").value;
  const visiveis = codigosVisiveisModoPlanejado();

  estado.setores.forEach((nomeSetor, idxSetor) => {{
    if (filtroSetor !== "TODOS" && filtroSetor !== nomeSetor) return;
    let itensSetor = estado.itens.filter(i => i.setor === nomeSetor);
    if (apenasPlanejados) {{
      itensSetor = itensSetor.filter(i => visiveis.has(i.codigo));
    }}
    if (itensSetor.length === 0) return;

    let qtdComp = itensSetor.filter(i => i.comprado).length;
    let totSet = itensSetor.length;
    let badgeSetor = (qtdComp === totSet && totSet > 0) ? "✅ Concluído" : `${{qtdComp}}/${{totSet}} no carrinho`;

    let det = document.createElement("details");
    det.className = "setor-box";
    det.open = cortinasAbertas[nomeSetor] !== false;
    det.addEventListener("toggle", () => {{ cortinasAbertas[nomeSetor] = det.open; }});

    let sum = document.createElement("summary");
    sum.innerHTML = `<span>${{nomeSetor}}</span><span id="badge_set_${{idxSetor}}" style="font-size:0.80rem;color:#90CDF4;">(${{badgeSetor}})</span>`;
    det.appendChild(sum);

    let ehFarm = nomeSetor.toLowerCase().includes("farmácia");

    itensSetor.forEach(it => {{
      let div = document.createElement("div");
      div.className = "item-card" + (it.comprado ? " comprado-bg" : "");
      div.id = "card_" + it.codigo;

      let m2Txt = it.marca2 ? ` | <b>${{it.marca2}}</b>` : "";
      let stepQtd = it.fracionado ? "0.1" : "1";
      let prExib = numSeguro(it.preco_comp) > 0 ? numSeguro(it.preco_comp) : numSeguro(it.preco_plan);
      let subItem = it.comprado ? (numSeguro(it.qtd_comp) * prExib) : 0;

      let btnPlanHtml = it.planejado
        ? `<button type="button" class="btn-cancel-plan" onclick="alternarPlanejadoItem('${{it.codigo}}', false)">🚫 Cancelar Plan.</button>`
        : `<button type="button" class="btn-add-plan" onclick="alternarPlanejadoItem('${{it.codigo}}', true)">➕ Planejar</button>`;

      let obsHtml = ehFarm ? "" : `
        <div style="margin-top:6px;">
          <input type="text" placeholder="Obs (Ex: Kit / Pote / Peso)" value="${{it.obs || ''}}"
            onchange="atualizarItem('${{it.codigo}}', 'obs', this.value)">
        </div>`;

      div.innerHTML = `
        <div class="item-title">${{it.produto}}</div>
        <div class="item-meta">Marca: <b>${{it.marca1}}</b>${{m2Txt}} | Planejado: <b>${{it.qtd_plan}} ${{it.unidade}}</b> <span id="sub_${{it.codigo}}" style="float:right;color:#2ECC71;font-weight:700;">${{it.comprado ? moedaBR(subItem) : ''}}</span></div>
        <div class="item-controls">
          <div class="chk-wrap">
            <label class="chk-label">
              <input type="checkbox" ${{it.comprado ? 'checked' : ''}} onchange="atualizarItem('${{it.codigo}}', 'comprado', this.checked)">
              <span>Comprado</span>
            </label>
            ${{btnPlanHtml}}
          </div>
          <div>
            <span class="lbl-mini">${{it.unidade}}</span>
            <input type="number" step="${{stepQtd}}" value="${{it.qtd_comp}}"
              onchange="atualizarItem('${{it.codigo}}', 'qtd_comp', this.value)">
          </div>
          <div>
            <span class="lbl-mini">Preço Unit. (R$)</span>
            <input type="number" step="0.10" value="${{prExib.toFixed(2)}}"
              onchange="atualizarItem('${{it.codigo}}', 'preco_comp', this.value)">
          </div>
        </div>
        ${{obsHtml}}
      `;
      det.appendChild(div);
    }});

    cont.appendChild(det);
  }});
  atualizarResumosTopoECaixa();
}}

function atualizarItem(cod, campo, valor) {{
  let it = estado.itens.find(x => x.codigo === cod);
  if (!it) return;
  if (campo === "comprado") {{
    it.comprado = Boolean(valor);
    aplicarEquivalenciaKits();
  }} else if (campo === "qtd_comp") {{
    it.qtd_comp = numSeguro(valor);
  }} else if (campo === "preco_comp") {{
    let p = numSeguro(valor);
    it.preco_comp = p;
    if (p > 0) it.preco_plan = p;
  }} else if (campo === "obs") {{
    it.obs = String(valor || "");
  }}
  salvarEstado();
  renderizarLista();
}}

function alternarPlanejadoItem(cod, novoStatus) {{
  let it = estado.itens.find(x => x.codigo === cod);
  if (!it) return;
  it.planejado = Boolean(novoStatus);
  if (!novoStatus) it.comprado = false;
  salvarEstado();
  renderizarLista();
}}

function mudarModoFiltro(soPlan) {{
  apenasPlanejados = soPlan;
  document.getElementById("btn_modo_plan").className = soPlan ? "btn btn-active" : "btn";
  document.getElementById("btn_modo_todos").className = !soPlan ? "btn btn-active" : "btn";
  renderizarLista();
}}

function alternarCortinas(abrir) {{
  estado.setores.forEach(s => {{ cortinasAbertas[s] = abrir; }});
  renderizarLista();
}}

function adicionarItemExtraOffline() {{
  let nome = document.getElementById("ex_nome").value.trim();
  if (!nome) {{
    document.getElementById("status_salvo").innerText = "⚠️ Digite o nome do produto extra antes de incluir.";
    return;
  }}
  let setor = document.getElementById("ex_setor").value;
  let marca = document.getElementById("ex_marca").value.trim() || "--";
  let unid = document.getElementById("ex_unid").value.trim() || "Unidade";
  let qtd = numSeguro(document.getElementById("ex_qtd").value) || 1;
  let preco = numSeguro(document.getElementById("ex_preco").value) || 0;
  let novoCod = "#AV" + Math.floor(Date.now() % 100000);

  estado.itens.push({{
    ordem: 900 + estado.itens.length,
    codigo: novoCod,
    setor: setor,
    produto: nome,
    marca1: marca,
    marca2: "Extra Offline",
    unidade: unid,
    fracionado: unid.toLowerCase() === "kg",
    planejado: true,
    qtd_plan: qtd,
    preco_plan: preco,
    comprado: true,
    qtd_comp: qtd,
    preco_comp: preco,
    obs: "Adicionado no mercado (Offline)"
  }});
  document.getElementById("ex_nome").value = "";
  salvarEstado();
  renderizarLista();
}}

function carregarCamposFechamento() {{
  const f = estado.fechamento;
  document.getElementById("f_data").value = f.data_compra || "";
  document.getElementById("f_clube").value = numSeguro(f.desconto_clube).toFixed(2);
  document.getElementById("f_dinheiro").value = numSeguro(f.dinheiro).toFixed(2);
  document.getElementById("f_pag_farm").value = f.pag_farmacia || "Dinheiro";
  document.getElementById("f_bd").value = numSeguro(f.bradesco_deb).toFixed(2);
  document.getElementById("f_bc").value = numSeguro(f.bradesco_cred).toFixed(2);
  document.getElementById("f_md").value = numSeguro(f.mp_deb).toFixed(2);
  document.getElementById("f_mc").value = numSeguro(f.mp_cred).toFixed(2);
  document.getElementById("f_nd").value = numSeguro(f.nubank_deb).toFixed(2);
  document.getElementById("f_nc").value = numSeguro(f.nubank_cred).toFixed(2);
  document.getElementById("f_ti_pag").value = f.transp_ida_pag || "Não houve";
  document.getElementById("f_ti_val").value = numSeguro(f.transp_ida_val).toFixed(2);
  document.getElementById("f_tv_pag").value = f.transp_volta_pag || "Não houve";
  document.getElementById("f_tv_val").value = numSeguro(f.transp_volta_val).toFixed(2);
  document.getElementById("f_obs").value = f.obs_fechamento || "";
}}

function atualizarFechamento() {{
  const f = estado.fechamento;
  f.data_compra = document.getElementById("f_data").value;
  f.desconto_clube = numSeguro(document.getElementById("f_clube").value);
  f.dinheiro = numSeguro(document.getElementById("f_dinheiro").value);
  f.pag_farmacia = document.getElementById("f_pag_farm").value;
  f.bradesco_deb = numSeguro(document.getElementById("f_bd").value);
  f.bradesco_cred = numSeguro(document.getElementById("f_bc").value);
  f.mp_deb = numSeguro(document.getElementById("f_md").value);
  f.mp_cred = numSeguro(document.getElementById("f_mc").value);
  f.nubank_deb = numSeguro(document.getElementById("f_nd").value);
  f.nubank_cred = numSeguro(document.getElementById("f_nc").value);
  f.transp_ida_pag = document.getElementById("f_ti_pag").value;
  f.transp_ida_val = numSeguro(document.getElementById("f_ti_val").value);
  f.transp_volta_pag = document.getElementById("f_tv_pag").value;
  f.transp_volta_val = numSeguro(document.getElementById("f_tv_val").value);
  f.obs_fechamento = document.getElementById("f_obs").value;
  salvarEstado();
  atualizarResumosTopoECaixa();
}}

async function baixarArquivoRetorno() {{
  atualizarFechamento();
  const conteudoJson = JSON.stringify(estado, null, 2);

  // Tenta abrir o seletor de pastas nativo ("Salvar como") caso o navegador suporte
  if (window.showSaveFilePicker) {{
    try {{
      const handle = await window.showSaveFilePicker({{
        suggestedName: NOME_ARQ_RETORNO,
        types: [{{
          description: "Arquivo JSON de Retorno",
          accept: {{ "application/json": [".json"] }}
        }}]
      }});
      const writable = await handle.createWritable();
      await writable.write(conteudoJson);
      await writable.close();
      document.getElementById("status_salvo").innerText = "💾 Arquivo '" + NOME_ARQ_RETORNO + "' salvo na pasta escolhida!";
      return;
    }} catch (err) {{
      if (err && err.name === "AbortError") return;
    }}
  }}

  const blob = new Blob([conteudoJson], {{ type: "application/json" }});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = NOME_ARQ_RETORNO;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  document.getElementById("status_salvo").innerText = "💾 Arquivo '" + NOME_ARQ_RETORNO + "' gerado! Salve na pasta Download/Compras.";
}}

function copiarJsonRetorno() {{
  atualizarFechamento();
  navigator.clipboard.writeText(JSON.stringify(estado)).then(() => {{
    document.getElementById("status_salvo").innerText = "📋 Código de retorno copiado! Basta colar no App quando chegar no Wi-Fi.";
  }});
}}

function resetarParaPlanilhaOriginal() {{
  localStorage.removeItem(CHAVE_STORAGE);
  carregarEstado();
  carregarCamposFechamento();
  renderizarLista();
  document.getElementById("status_salvo").innerText = "🔄 Dados restaurados conforme a saída de casa.";
}}

window.onload = function() {{
  carregarEstado();
  const selFiltro = document.getElementById("sel_setor_filtro");
  const selExtra = document.getElementById("ex_setor");
  estado.setores.forEach(s => {{
    let op1 = document.createElement("option"); op1.value = s; op1.text = s; selFiltro.appendChild(op1);
    let op2 = document.createElement("option"); op2.value = s; op2.text = s; selExtra.appendChild(op2);
  }});
  selExtra.value = estado.setores[estado.setores.length - 1];
  carregarCamposFechamento();
  renderizarLista();
}};
</script>
</body>
</html>"""
    return html_doc

def sincronizar_retorno_offline(dados_json, df_mes, sheet_mes, mes_ano_ativo, ano_ativo):
    """
    Recebe o JSON vindo do aplicativo HTML Offline (via arquivo .json ou texto colado),
    atualiza todos os produtos comprados, preços cadastrados na gôndola, itens extras,
    equivalência de Kits de Shampoo e fechamento financeiro na planilha do Google Drive!
    """
    itens_off = dados_json.get("itens", [])
    fech_off = dados_json.get("fechamento", {})

    idx_por_cod = {str(r["Codigo"]).strip(): idx for idx, r in df_mes.iterrows()}
    novas_linhas_extras = []

    for it in itens_off:
        cod = str(it.get("codigo", "")).strip()
        if not cod:
            continue
        plan_b = bool(it.get("planejado", False))
        comp_b = bool(it.get("comprado", False))
        qtd_c = safe_float(it.get("qtd_comp", 0.0))
        pr_c = safe_float(it.get("preco_comp", 0.0))
        pr_p = safe_float(it.get("preco_plan", 0.0))
        obs_c = str(it.get("obs", "") or "")

        if cod in idx_por_cod:
            idx = idx_por_cod[cod]
            df_mes.at[idx, "Planejado_bool"] = plan_b
            df_mes.at[idx, "Comprado_bool"] = comp_b
            if qtd_c > 0:
                df_mes.at[idx, "QtdComprada_num"] = qtd_c
            if pr_c > 0:
                df_mes.at[idx, "PrecoRealUnit_num"] = pr_c
                df_mes.at[idx, "PrecoUnit_num"] = pr_c
            elif pr_p > 0:
                df_mes.at[idx, "PrecoUnit_num"] = pr_p
            df_mes.at[idx, "ObsMes"] = obs_c
        else:
            # Item extra criado dentro do HTML Offline
            sub_ex = arredondar_moeda(qtd_c * pr_c, 2)
            novas_linhas_extras.append({
                "Ordem": str(int(safe_float(it.get("ordem", 950)))),
                "Codigo": cod,
                "Setor": str(it.get("setor", SETORES_OFICIAIS[-1])),
                "Produto": str(it.get("produto", "Item Extra")),
                "Marca1": str(it.get("marca1", "--")),
                "Marca2": "Extra Offline",
                "Unidade": str(it.get("unidade", "Unidade")),
                "Planejado": "TRUE" if plan_b else "FALSE",
                "QtdPlanejada": formatar_num_planilha(qtd_c, 3),
                "PrecoUnit": formatar_num_planilha(pr_c, 2),
                "SubtotalPlanejado": formatar_num_planilha(sub_ex, 2),
                "Comprado": "TRUE" if comp_b else "FALSE",
                "QtdComprada": formatar_num_planilha(qtd_c, 3),
                "PrecoRealUnit": formatar_num_planilha(pr_c, 2),
                "SubtotalReal": formatar_num_planilha(sub_ex if comp_b else 0.0, 2),
                "ObsMes": obs_c,
                "Ordem_num": int(safe_float(it.get("ordem", 950))),
                "Planejado_bool": plan_b,
                "Comprado_bool": comp_b,
                "QtdPlanejada_num": qtd_c,
                "PrecoUnit_num": pr_c,
                "QtdComprada_num": qtd_c,
                "PrecoRealUnit_num": pr_c
            })

    if novas_linhas_extras:
        df_mes = pd.concat([df_mes, pd.DataFrame(novas_linhas_extras)], ignore_index=True)

    df_mes = aplicar_equivalencia_kits_shampoo(df_mes)
    salvar_df_mes(sheet_mes, df_mes, ano_ativo, atualizar_preco_catalogo=True)

    novos_tot = calcular_totais_df(df_mes)
    dt_str = str(fech_off.get("data_compra") or hoje_br().strftime("%d/%m/%Y")).strip()
    salvar_configs({f"data_compra_{mes_ano_ativo}": dt_str}, ano_ativo)

    salvar_resumo_pagamento(mes_ano_ativo, {
        "DataCompra": dt_str,
        "TotalMercadoPlanejado": novos_tot["merc_plan"],
        "TotalMercadoReal": novos_tot["merc_real"],
        "TotalFarmaciaPlanejado": novos_tot["farm_plan"],
        "TotalFarmaciaReal": novos_tot["farm_real"],
        "Dinheiro": safe_float(fech_off.get("dinheiro", 0.0)),
        "BradescoDebito": safe_float(fech_off.get("bradesco_deb", 0.0)),
        "BradescoCredito": safe_float(fech_off.get("bradesco_cred", 0.0)),
        "MercadoPagoDebito": safe_float(fech_off.get("mp_deb", 0.0)),
        "MercadoPagoCredito": safe_float(fech_off.get("mp_cred", 0.0)),
        "NubankDebito": safe_float(fech_off.get("nubank_deb", 0.0)),
        "NubankCredito": safe_float(fech_off.get("nubank_cred", 0.0)),
        "PagamentoFarmacia": str(fech_off.get("pag_farmacia") or "Dinheiro"),
        "ObsFechamento": str(fech_off.get("obs_fechamento") or ""),
        "TranspIdaPag": str(fech_off.get("transp_ida_pag") or "Não houve"),
        "TranspIdaVal": safe_float(fech_off.get("transp_ida_val", 0.0)),
        "TranspVoltaPag": str(fech_off.get("transp_volta_pag") or "Não houve"),
        "TranspVoltaVal": safe_float(fech_off.get("transp_volta_val", 0.0)),
        "DescontoClube": safe_float(fech_off.get("desconto_clube", 0.0))
    }, ano_ativo)
    return novos_tot, safe_float(fech_off.get("desconto_clube", 0.0))

# === CARREGAMENTO INICIAL DE CONFIGURAÇÃO DO MÊS ATIVO ===
ano_corrente = agora_br().strftime("%Y")
mes_padrao_inicial = "11 2026"

try:
    config_dict = carregar_config_dict(ano_corrente)
except Exception as e:
    st.error(f"⚠️ Não foi possível conectar à planilha 'Compras {ano_corrente}'. Verifique se o e-mail do robô foi compartilhado na pasta 'mercado' e se o Secrets está configurado. Detalhe: {e}")
    st.stop()

if "mes_ano_ativo_mem" not in st.session_state:
    mes_cfg = config_dict.get("mes_ano_ativo", mes_padrao_inicial)
    if not mes_cfg or " " not in mes_cfg or mes_cfg == "10 2026":
        mes_cfg = mes_padrao_inicial
    st.session_state["mes_ano_ativo_mem"] = mes_cfg

mes_ano_ativo = st.session_state["mes_ano_ativo_mem"]
ano_ativo = mes_ano_ativo.split(" ")[-1]

# Lista de meses dinâmica: cresce automaticamente conforme novos arquivos "Compras AAAA" existam no GDrive!
anos_disponiveis = listar_anos_disponiveis_gdrive()
opcoes_meses = []
for a in anos_disponiveis:
    for m in range(1, 13):
        if a == 2026 and m < 11:
            continue
        opcoes_meses.append(f"{m:02d} {a}")
if "10 2026" not in opcoes_meses:
    opcoes_meses.append("10 2026")
if mes_ano_ativo not in opcoes_meses:
    opcoes_meses.insert(0, mes_ano_ativo)

# === MENU LATERAL COM RECOLHIMENTO AUTOMÁTICO (SEM SELETOR DUPLICADO DE MÊS) ===
if "recolher_menu" not in st.session_state:
    st.session_state["recolher_menu"] = 0
if "fechar_menu_agora" not in st.session_state:
    st.session_state["fechar_menu_agora"] = False

def acionar_fechamento_menu():
    st.session_state["recolher_menu"] += 1
    st.session_state["fechar_menu_agora"] = True

st.sidebar.markdown("### 🛒 Compras")
st.sidebar.caption(f"📅 Mês Ativo: **{mes_ano_ativo}**")

menu = st.sidebar.radio(
    "Navegação",
    [
        "Planejamento (Casa)",
        "Conferência (Mercado)",
        "O que Faltou Comprar",
        "Tabela de Preços do Mês",
        "Relatório / Histórico",
        "Cadastro de Produtos"
    ],
    on_change=acionar_fechamento_menu
)
st.sidebar.caption(f"📌 Versão {VERSAO_APP}")

if st.session_state.get("fechar_menu_agora", False):
    st.session_state["fechar_menu_agora"] = False
    components.html(
        f"""
        <!-- Gatilho de recolhimento #{st.session_state["recolher_menu"]} -->
        <script>
        (function() {{
            function tentarFecharMenu() {{
                try {{
                    const doc = window.parent.document;
                    const sidebar = doc.querySelector('[data-testid="stSidebar"], .stSidebar');
                    if (sidebar && sidebar.getBoundingClientRect().width > 100) {{
                        const btn = doc.querySelector('[data-testid="stSidebarCollapseButton"] button')
                                 || doc.querySelector('button[data-testid="stSidebarCollapseButton"]')
                                 || sidebar.querySelector('[data-testid="stSidebarHeader"] button')
                                 || sidebar.querySelector('button[kind="headerNoPadding"]')
                                 || sidebar.querySelector('button[kind="header"]')
                                 || sidebar.querySelector('button');
                        if (btn) {{
                            btn.click();
                            return true;
                        }}
                    }}
                }} catch (e) {{}}
                return false;
            }}
            if (!tentarFecharMenu()) {{
                setTimeout(tentarFecharMenu, 100);
                setTimeout(tentarFecharMenu, 250);
            }}
        }})();
        </script>
        """,
        height=0
    )

# Garante via JS no documento pai que o filtro Verde esteja aplicado exatamente no 2º botão ("Comprar") e nos Checkboxes ("Comprado")
components.html(
    f"""
    <!-- Filtro Verde v{VERSAO_APP} - #{st.session_state["recolher_menu"]} -->
    <script>
    (function() {{
        try {{
            const doc = window.parent.document;
            const filtroVerde = 'hue-rotate(125deg) saturate(1.5) brightness(1.1)';

            function aplicarFiltroVerde() {{
                doc.querySelectorAll('div[data-testid="stCheckbox"]').forEach(el => {{
                    el.style.setProperty('filter', filtroVerde, 'important');
                }});
                doc.querySelectorAll('div[role="radiogroup"]').forEach(rg => {{
                    if (rg.children && rg.children.length >= 2) {{
                        rg.children[0].style.removeProperty('filter');
                        rg.children[1].style.setProperty('filter', filtroVerde, 'important');
                    }}
                }});
            }}

            aplicarFiltroVerde();
            setTimeout(aplicarFiltroVerde, 100);
            setTimeout(aplicarFiltroVerde, 300);

            if (!doc._intervaloVerdeV117) {{
                doc._intervaloVerdeV117 = setInterval(aplicarFiltroVerde, 400);
            }}
        }} catch (e) {{}}
    }})();
    </script>
    """,
    height=0
)

# Carrega os dados do mês ativo (em cache rápido)
df_mes, sheet_mes = carregar_df_mes(mes_ano_ativo, ano_ativo)
totais_atuais = calcular_totais_df(df_mes)
resumo_salvo = obter_resumo_mes(mes_ano_ativo, ano_ativo)

# Data padrão da compra do mês ativo (sempre Dia 05 do mês selecionado, salvo se já alterada pelo usuário)
data_compra_padrao_mes = data_padrao_dia_5(mes_ano_ativo)
if resumo_salvo.get("DataCompra"):
    try:
        dt_salva = datetime.strptime(str(resumo_salvo["DataCompra"]).strip(), "%d/%m/%Y").date()
        if dt_salva.strftime("%m %Y") == mes_ano_ativo:
            data_compra_padrao_mes = dt_salva
    except Exception:
        pass
elif config_dict.get(f"data_compra_{mes_ano_ativo}"):
    try:
        data_compra_padrao_mes = datetime.strptime(config_dict[f"data_compra_{mes_ano_ativo}"], "%d/%m/%Y").date()
    except Exception:
        pass

# ==============================================================================
# GUIA 1: PLANEJAMENTO (CASA - PRÉ-COMPRA)
# ==============================================================================
if menu == "Planejamento (Casa)":
    st.markdown('<h2 style="text-align: center; margin-bottom: 10px;">📝 Planejamento (Pré-Compra)</h2>', unsafe_allow_html=True)

    def ao_trocar_mes_planejamento():
        novo_m = st.session_state.get("sel_mes_topo_plan", mes_ano_ativo)
        if novo_m and novo_m != st.session_state.get("mes_ano_ativo_mem"):
            st.session_state["mes_ano_ativo_mem"] = novo_m
            try:
                salvar_configs({"mes_ano_ativo": novo_m}, novo_m.split(" ")[-1])
            except Exception:
                pass

    # Cabeçalho centralizado exatamente como no esboço: Mês/Ano Ativo + Data Real da Compra (padrão dia 05)
    _, col_centro_hdr, _ = st.columns([0.3, 2.4, 0.3])
    with col_centro_hdr:
        col_hdr_mes, col_hdr_dt = st.columns(2)
        with col_hdr_mes:
            st.selectbox(
                "📅 Mês/Ano Ativo:",
                opcoes_meses,
                index=opcoes_meses.index(mes_ano_ativo),
                key="sel_mes_topo_plan",
                on_change=ao_trocar_mes_planejamento
            )
        with col_hdr_dt:
            dt_topo_plan = st.date_input(
                "Data Real da Compra",
                value=data_compra_padrao_mes,
                format="DD/MM/YYYY",
                key=f"dt_topo_plan_{mes_ano_ativo}"
            )

    st.markdown('<hr class="divisor-secao">', unsafe_allow_html=True)

    if "msg_sucesso_plan" in st.session_state:
        st.success(st.session_state.pop("msg_sucesso_plan"))

    # Painel de Resumo Rápido no Topo (sem bolinha desnecessária)
    c_top1, c_top2 = st.columns(2)
    with c_top1:
        st.markdown(f"""
        <div class="card-farmacia">
            <b>💊 Farmácia (Separado)</b><br>
            Itens marcados: <b>{totais_atuais['itens_plan_farm']}</b><br>
            Previsto Farmácia: <b>{formatar_moeda_br(totais_atuais['farm_plan'])}</b>
        </div>
        """, unsafe_allow_html=True)
    with c_top2:
        st.markdown(f"""
        <div class="card-azul">
            <b>🛒 Mercado (+ Extras)</b><br>
            Itens marcados: <b>{totais_atuais['itens_plan_merc']}</b><br>
            Previsto Mercado: <b>{formatar_moeda_br(totais_atuais['merc_plan'])}</b>
        </div>
        """, unsafe_allow_html=True)

    # Central Offline no Planejamento: permite gerar o arquivo HTML logo após planejar em casa
    with st.expander("📴 Modo Offline (Baixar Lista p/ Usar Sem Internet no Mercado)"):
        st.caption(
            f"Salve o arquivo **`{mes_ano_ativo} Compras.html`** na sua pasta **`Download/Compras`** do Android antes de sair do Wi-Fi.\n\n"
            "💡 **Para o celular sempre perguntar onde salvar (e você escolher a pasta `Compras` tanto no `.html` quanto no `.json`):** "
            "no Chrome do Android, toque nos **3 pontinhos (`⋮`)** $\\rightarrow$ **Configurações** $\\rightarrow$ **Downloads** $\\rightarrow$ ative **'Perguntar onde salvar os arquivos'**."
        )
        html_offline_str = gerar_html_offline_mercado(
            mes_ano_ativo, df_mes, resumo_salvo, dt_topo_plan.strftime("%d/%m/%Y")
        )
        st.download_button(
            label=f"📲 Baixar Aplicativo Offline ({mes_ano_ativo} Compras.html)",
            data=html_offline_str.encode("utf-8"),
            file_name=f"{mes_ano_ativo} Compras.html",
            mime="text/html",
            use_container_width=True
        )

    st.markdown('<hr class="divisor-secao">', unsafe_allow_html=True)

    # Filtro opcional de setor + controles de expandir/recolher todos os setores
    col_flt1, col_flt2, col_flt3 = st.columns([2.2, 0.9, 0.9])
    with col_flt1:
        opcoes_filtro_setor = ["📋 Todos os Setores (Circuito Completo)"] + SETORES_OFICIAIS
        filtro_setor = st.selectbox("Filtrar por Departamento / Setor:", opcoes_filtro_setor, index=0)
    with col_flt2:
        st.write("")
        if st.button("📂 Abrir Setores", use_container_width=True):
            st.session_state["exp_plan_todos"] = True
    with col_flt3:
        st.write("")
        if st.button("📁 Encolher Todos", use_container_width=True):
            st.session_state["exp_plan_todos"] = False

    with st.expander("➕ Adicionar Item Avulso Rápido para este Mês"):
        with st.form("form_item_avulso_mes", clear_on_submit=True):
            ca1, ca2 = st.columns(2)
            with ca1:
                av_prod = st.text_input("Nome do Produto Avulso")
                av_setor = st.selectbox("Setor no Circuito", SETORES_OFICIAIS, index=len(SETORES_OFICIAIS)-1)
                av_m1 = st.text_input("Marca 1 (ou deixe em branco p/ Sem marca)", value="--")
            with ca2:
                av_qtd = st.number_input("Quantidade", min_value=0.1, value=1.0, step=0.5, format="%.2f")
                av_unid = st.text_input("Unidade (Unidade, Kg, Pacote, Caixa, Litro...)", value="Unidade")
                av_preco = st.number_input("Preço Unit. Estimado (R$)", min_value=0.0, value=0.0, step=0.5, format="%.2f")
            if st.form_submit_button("Inserir Item Avulso já Marcado para Compra", use_container_width=True):
                if av_prod.strip():
                    df_set_av = df_mes[df_mes["Setor"] == av_setor]
                    nova_ordem = int(df_set_av["Ordem_num"].max() + 1) if not df_set_av.empty else int(df_mes["Ordem_num"].max() + 1)
                    novo_cod = f"#AV{int(time.time()) % 10000}"
                    sub_av = arredondar_moeda(av_qtd * av_preco, 2)
                    nova_linha_av = pd.DataFrame([{
                        "Ordem": str(nova_ordem),
                        "Codigo": novo_cod,
                        "Setor": av_setor,
                        "Produto": av_prod.strip(),
                        "Marca1": av_m1.strip() or "--",
                        "Marca2": "Avulso do Mês",
                        "Unidade": av_unid.strip() or "Unidade",
                        "Planejado": "TRUE",
                        "QtdPlanejada": formatar_num_planilha(av_qtd, 3),
                        "PrecoUnit": formatar_num_planilha(av_preco, 2),
                        "SubtotalPlanejado": formatar_num_planilha(sub_av, 2),
                        "Comprado": "FALSE",
                        "QtdComprada": formatar_num_planilha(av_qtd, 3),
                        "PrecoRealUnit": formatar_num_planilha(av_preco, 2),
                        "SubtotalReal": "0,00",
                        "ObsMes": "Item avulso",
                        "Ordem_num": nova_ordem,
                        "Planejado_bool": True,
                        "Comprado_bool": False,
                        "QtdPlanejada_num": float(av_qtd),
                        "PrecoUnit_num": float(av_preco),
                        "QtdComprada_num": float(av_qtd),
                        "PrecoRealUnit_num": float(av_preco)
                    }])
                    df_mes_novo = pd.concat([df_mes, nova_linha_av], ignore_index=True)
                    salvar_df_mes(sheet_mes, df_mes_novo, ano_ativo, atualizar_preco_catalogo=False)
                    st.session_state["msg_sucesso_plan"] = f"✅ Item avulso '{av_prod}' adicionado em '{av_setor}' e já marcado como Planejado (aparecerá na Conferência)!"
                    st.rerun()

    st.caption("💡 **Dica:** Você pode clicar no título de qualquer **Setor** abaixo para **encolher (recolher)** os setores que você já revisou, sem perder nenhuma marcação!")

    setores_exibir = SETORES_OFICIAIS if filtro_setor.startswith("📋") else [filtro_setor]
    expandir_padrao_plan = st.session_state.get("exp_plan_todos", True)

    with st.form("form_planejamento_casa", clear_on_submit=False):
        valores_plan = {}
        for setor_nome in setores_exibir:
            df_setor = df_mes[df_mes["Setor"] == setor_nome]
            if df_setor.empty:
                continue

            qtd_marcados_setor = int(df_setor["Planejado_bool"].sum())
            total_itens_setor = len(df_setor)
            titulo_exp = f"{setor_nome}  —  ({qtd_marcados_setor}/{total_itens_setor} marcados)"

            with st.expander(titulo_exp, expanded=expandir_padrao_plan):
                for idx_row, row in df_setor.iterrows():
                    cod = str(row["Codigo"]).strip()
                    prod = str(row["Produto"])
                    m1 = exibir_marca_limpa(row["Marca1"], cod)
                    m2 = limpar_marca_lida(row["Marca2"], cod)
                    m2_txt = f" | <b>{m2}</b>" if m2 not in ["", "-", "--", "nan"] else ""
                    unid = str(row["Unidade"])
                    plan_atual = bool(row["Planejado_bool"])
                    qtd_atual = float(row["QtdPlanejada_num"]) if row["QtdPlanejada_num"] > 0 else 1.0
                    pr_atual = float(row["PrecoUnit_num"])

                    st.markdown(
                        f"**{prod}** <span class='item-sub'>— Marca: <b>{m1}</b>{m2_txt} | Unid: <b>{unid}</b></span>",
                        unsafe_allow_html=True
                    )
                    c1, c2, c3 = st.columns([1.4, 1.1, 1.2])
                    with c1:
                        escolha_az = st.radio(
                            f"Marcar {cod}",
                            options=["— Não", "Comprar"],
                            index=1 if plan_atual else 0,
                            horizontal=True,
                            label_visibility="collapsed",
                            key=f"pl_rad_{mes_ano_ativo}_{idx_row}"
                        )
                    with c2:
                        if eh_unidade_fracionada(unid):
                            nova_qtd = float(st.number_input(
                                f"{unid}",
                                min_value=0.0,
                                value=float(qtd_atual),
                                step=0.5,
                                format="%.2f",
                                key=f"pl_qtd_{mes_ano_ativo}_{idx_row}"
                            ))
                        else:
                            nova_qtd = float(st.number_input(
                                f"{unid}",
                                min_value=0,
                                value=int(round(qtd_atual)),
                                step=1,
                                key=f"pl_qtd_{mes_ano_ativo}_{idx_row}"
                            ))
                    with c3:
                        novo_pr = st.number_input(
                            "Preço Unit. (R$)",
                            min_value=0.0,
                            value=pr_atual,
                            step=0.50,
                            format="%.2f",
                            key=f"pl_pr_{mes_ano_ativo}_{idx_row}"
                        )
                    valores_plan[idx_row] = (escolha_az == "Comprar", nova_qtd, novo_pr)
                    st.markdown('<hr style="margin: 6px 0px; opacity: 0.2;">', unsafe_allow_html=True)

        st.markdown('<hr class="divisor-secao">', unsafe_allow_html=True)
        st.markdown("### 💵 Planejamento de Pagamento para o Caixa (Mercado)")
        st.caption("Lembrete: pagar **1º em Dinheiro** no caixa e dividir o restante entre Débito ou Crédito (Bradesco, Mercado Pago ou Nubank):")

        c_din_pl, c_desc_pl = st.columns(2)
        with c_din_pl:
            din_prev = st.number_input(
                "💵 1º Dinheiro em Espécie no Caixa (R$)",
                min_value=0.0,
                value=safe_float(resumo_salvo.get("Dinheiro", 0.0)),
                step=10.0,
                format="%.2f"
            )
        with c_desc_pl:
            desc_clube_prev = st.number_input(
                "🏷️ Clube de Descontos (Abater no Caixa R$)",
                min_value=0.0,
                value=safe_float(resumo_salvo.get("DescontoClube", 0.0)),
                step=1.0,
                format="%.2f"
            )
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.markdown(label_banco_html(LOGO_BRADESCO, "Bradesco", "DÉBITO"), unsafe_allow_html=True)
            brad_deb = st.number_input("Bradesco Débito", min_value=0.0, value=safe_float(resumo_salvo.get("BradescoDebito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="pl_bd")

            st.markdown(label_banco_html(LOGO_MERCADOPAGO, "Mercado Pago", "DÉBITO"), unsafe_allow_html=True)
            mp_deb = st.number_input("Mercado Pago Débito", min_value=0.0, value=safe_float(resumo_salvo.get("MercadoPagoDebito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="pl_md")

            st.markdown(label_banco_html(LOGO_NUBANK, "Nubank", "DÉBITO"), unsafe_allow_html=True)
            nu_deb = st.number_input("Nubank Débito", min_value=0.0, value=safe_float(resumo_salvo.get("NubankDebito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="pl_nd")

        with col_b2:
            st.markdown(label_banco_html(LOGO_BRADESCO, "Bradesco", "CRÉDITO"), unsafe_allow_html=True)
            brad_cred = st.number_input("Bradesco Crédito", min_value=0.0, value=safe_float(resumo_salvo.get("BradescoCredito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="pl_bc")

            st.markdown(label_banco_html(LOGO_MERCADOPAGO, "Mercado Pago", "CRÉDITO"), unsafe_allow_html=True)
            mp_cred = st.number_input("Mercado Pago Crédito", min_value=0.0, value=safe_float(resumo_salvo.get("MercadoPagoCredito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="pl_mc")

            st.markdown(label_banco_html(LOGO_NUBANK, "Nubank", "CRÉDITO"), unsafe_allow_html=True)
            nu_cred = st.number_input("Nubank Crédito", min_value=0.0, value=safe_float(resumo_salvo.get("NubankCredito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="pl_nc")

        opcoes_pag_farm_pl = ["Dinheiro", "Bradesco - Débito", "Bradesco - Crédito", "Mercado Pago - Débito", "Mercado Pago - Crédito", "Nubank - Débito", "Nubank - Crédito"]
        idx_pf_pl = opcoes_pag_farm_pl.index(resumo_salvo.get("PagamentoFarmacia")) if resumo_salvo.get("PagamentoFarmacia") in opcoes_pag_farm_pl else 0
        pag_farm_str = st.selectbox(
            "💊 Forma de Pagamento na Farmácia (Antes do Mercado):",
            opcoes_pag_farm_pl,
            index=idx_pf_pl
        )

        st.markdown("#### 🚕 Transporte (Ida e Volta)")
        opcoes_transp = ["Não houve", "Dinheiro", "Bradesco - Débito", "Bradesco - Crédito", "Mercado Pago - Débito", "Mercado Pago - Crédito", "Nubank - Débito", "Nubank - Crédito"]
        ct1, ct2 = st.columns(2)
        with ct1:
            idx_ti = opcoes_transp.index(resumo_salvo.get("TranspIdaPag")) if resumo_salvo.get("TranspIdaPag") in opcoes_transp else 0
            tr_ida_pag_pl = st.selectbox("🚕 Ida — Forma de Pagamento:", opcoes_transp, index=idx_ti, key="pl_ti_p")
            tr_ida_val_pl = st.number_input("🚕 Ida — Valor (R$):", min_value=0.0, value=safe_float(resumo_salvo.get("TranspIdaVal", 0.0)), step=5.0, format="%.2f", key="pl_ti_v")
        with ct2:
            idx_tv = opcoes_transp.index(resumo_salvo.get("TranspVoltaPag")) if resumo_salvo.get("TranspVoltaPag") in opcoes_transp else 0
            tr_volta_pag_pl = st.selectbox("🚕 Volta — Forma de Pagamento:", opcoes_transp, index=idx_tv, key="pl_tv_p")
            tr_volta_val_pl = st.number_input("🚕 Volta — Valor (R$):", min_value=0.0, value=safe_float(resumo_salvo.get("TranspVoltaVal", 0.0)), step=5.0, format="%.2f", key="pl_tv_v")

        btn_salvar_plan = st.form_submit_button("💾 Salvar Planejamento do Mês", use_container_width=True)

    if btn_salvar_plan:
        for idx_r, (b_plan, q_pl, p_pl) in valores_plan.items():
            df_mes.at[idx_r, "Planejado_bool"] = b_plan
            df_mes.at[idx_r, "QtdPlanejada_num"] = q_pl
            df_mes.at[idx_r, "PrecoUnit_num"] = p_pl
            if not df_mes.at[idx_r, "Comprado_bool"]:
                df_mes.at[idx_r, "QtdComprada_num"] = q_pl
                df_mes.at[idx_r, "PrecoRealUnit_num"] = p_pl

        salvar_df_mes(sheet_mes, df_mes, ano_ativo, atualizar_preco_catalogo=True)
        novos_tot = calcular_totais_df(df_mes)
        dt_plan_str = dt_topo_plan.strftime("%d/%m/%Y")
        salvar_configs({f"data_compra_{mes_ano_ativo}": dt_plan_str, "mes_ano_ativo": mes_ano_ativo}, ano_ativo)
        salvar_resumo_pagamento(mes_ano_ativo, {
            "DataCompra": dt_plan_str,
            "TotalMercadoPlanejado": novos_tot["merc_plan"],
            "TotalMercadoReal": novos_tot["merc_real"],
            "TotalFarmaciaPlanejado": novos_tot["farm_plan"],
            "TotalFarmaciaReal": novos_tot["farm_real"],
            "Dinheiro": din_prev,
            "BradescoDebito": brad_deb,
            "BradescoCredito": brad_cred,
            "MercadoPagoDebito": mp_deb,
            "MercadoPagoCredito": mp_cred,
            "NubankDebito": nu_deb,
            "NubankCredito": nu_cred,
            "PagamentoFarmacia": pag_farm_str,
            "ObsFechamento": resumo_salvo.get("ObsFechamento", ""),
            "TranspIdaPag": tr_ida_pag_pl,
            "TranspIdaVal": tr_ida_val_pl,
            "TranspVoltaPag": tr_volta_pag_pl,
            "TranspVoltaVal": tr_volta_val_pl,
            "DescontoClube": desc_clube_prev
        }, ano_ativo)
        st.session_state["msg_sucesso_plan"] = f"✅ Planejamento de {mes_ano_ativo} salvo com sucesso! Previsto Mercado: {formatar_moeda_br(novos_tot['merc_plan'])} | Farmácia: {formatar_moeda_br(novos_tot['farm_plan'])}"
        st.rerun()

    # Simulador visual imediato do saldo após o Clube de Descontos e o Dinheiro
    desc_clube_salvo_pl = safe_float(resumo_salvo.get("DescontoClube", 0.0))
    merc_liq_prev = max(0.0, arredondar_moeda(totais_atuais["merc_plan"] - desc_clube_salvo_pl, 2))
    saldo_apos_dinheiro = max(0.0, arredondar_moeda(merc_liq_prev - safe_float(resumo_salvo.get("Dinheiro", 0.0)), 2))
    linha_desc_pl = f"🏷️ (-) Clube de Descontos: <b>- {formatar_moeda_br(desc_clube_salvo_pl)}</b> → Líquido: <b>{formatar_moeda_br(merc_liq_prev)}</b><br>" if desc_clube_salvo_pl > 0 else ""
    st.markdown(f"""
    <div class="card-alerta-caixa">
        <b>📢 LEMBRETE P/ HORA DE PASSAR NO CAIXA (MERCADO):</b><br>
        {linha_desc_pl}1º Entregar em <b>💵 Dinheiro</b>: <b>{formatar_moeda_br(resumo_salvo.get('Dinheiro', 0.0))}</b><br>
        2º Saldo Restante p/ passar nos Cartões (Débito/Crédito): <b>{formatar_moeda_br(saldo_apos_dinheiro)}</b>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# GUIA 2: CONFERÊNCIA (NO MERCADO / RETORNO - COM TICK VERDE)
# ==============================================================================
elif menu == "Conferência (Mercado)":
    st.markdown('<h2 style="text-align: center; margin-bottom: 10px;">✅ Conferência (Mercado / Retorno)</h2>', unsafe_allow_html=True)

    if "msg_sucesso_conf" in st.session_state:
        st.success(st.session_state.pop("msg_sucesso_conf"))

    desc_clube_topo = safe_float(resumo_salvo.get("DescontoClube", 0.0))
    merc_liq_topo = max(0.0, arredondar_moeda(totais_atuais["merc_real"] - desc_clube_topo, 2))
    txt_desc_topo = f"<br>🏷️ Clube Descontos: <b>- {formatar_moeda_br(desc_clube_topo)}</b> → Líquido: <b>{formatar_moeda_br(merc_liq_topo)}</b>" if desc_clube_topo > 0 else ""

    c_res1, c_res2 = st.columns(2)
    with c_res1:
        st.markdown(f"""
        <div class="card-farmacia">
            <b>💊 Farmácia</b><br>
            Comprados: <b>{totais_atuais['itens_comp_farm']} / {totais_atuais['itens_plan_farm']}</b><br>
            Gasto Real: <b>{formatar_moeda_br(totais_atuais['farm_real'])}</b> <span class="item-sub">(Prev: {formatar_moeda_br(totais_atuais['farm_plan'])})</span>
        </div>
        """, unsafe_allow_html=True)
    with c_res2:
        st.markdown(f"""
        <div class="card-verde">
            <b>🛒 Mercado no Carrinho (✅)</b><br>
            Comprados: <b>{totais_atuais['itens_comp_merc']} / {totais_atuais['itens_plan_merc']}</b><br>
            Gasto Real: <b>{formatar_moeda_br(totais_atuais['merc_real'])}</b> <span class="item-sub">(Prev: {formatar_moeda_br(totais_atuais['merc_plan'])})</span>{txt_desc_topo}
        </div>
        """, unsafe_allow_html=True)

    # Central Completa do Modo Offline (Ida: Baixar HTML | Volta no Wi-Fi: Sincronizar Retorno .json)
    with st.expander("📴 Modo Offline (Baixar Lista p/ Mercado ou Sincronizar Retorno no Wi-Fi)", expanded=False):
        aba_off_ida, aba_off_volta = st.tabs([
            f"📲 1. Antes de Sair ({mes_ano_ativo} Compras.html)",
            f"📤 2. Na Volta no Wi-Fi (Sincronizar Retorno)"
        ])
        with aba_off_ida:
            st.caption(
                f"Toque abaixo para salvar **`{mes_ano_ativo} Compras.html`** na pasta **`Download/Compras`** do celular.\n\n"
                "💡 **Como salvar direto na pasta `Download/Compras`:** no navegador Chrome do Android, toque nos **3 pontinhos (`⋮`)** $\\rightarrow$ **Configurações** $\\rightarrow$ **Downloads** $\\rightarrow$ ative **'Perguntar onde salvar os arquivos'**. Assim, tanto no `.html` quanto no `.json` de retorno ele abre a janelinha para você escolher a pasta `Compras`!"
            )
            html_off_conf = gerar_html_offline_mercado(
                mes_ano_ativo, df_mes, resumo_salvo, data_compra_padrao_mes.strftime("%d/%m/%Y")
            )
            st.download_button(
                label=f"📲 Baixar Aplicativo Offline ({mes_ano_ativo} Compras.html)",
                data=html_off_conf.encode("utf-8"),
                file_name=f"{mes_ano_ativo} Compras.html",
                mime="text/html",
                use_container_width=True,
                key="dl_html_off_conf"
            )
        with aba_off_volta:
            st.caption(
                f"De volta ao Wi-Fi de casa, selecione o arquivo **`{mes_ano_ativo} Compras Retorno.json`** (salvo em `Download/Compras`) "
                "ou cole o código copiado. *(Seus arquivos locais jamais são apagados automaticamente!)*"
            )
            arq_retorno = st.file_uploader(
                f"Selecionar arquivo '{mes_ano_ativo} Compras Retorno.json'",
                type=["json"],
                key=f"up_json_{mes_ano_ativo}"
            )
            texto_retorno = st.text_input(
                "Ou cole aqui o Código de Retorno copiado do App Offline:",
                placeholder="Cole aqui caso tenha usado o botão 'Copiar Código de Retorno'...",
                key=f"txt_json_{mes_ano_ativo}"
            )
            if st.button("🚀 Sincronizar Compra Offline com a Planilha", type="primary", use_container_width=True):
                try:
                    dados_sync = None
                    if arq_retorno is not None:
                        dados_sync = json.loads(arq_retorno.getvalue().decode("utf-8"))
                    elif texto_retorno.strip():
                        dados_sync = json.loads(texto_retorno.strip())
                    else:
                        st.warning("⚠️ Selecione o arquivo `.json` ou cole o código de retorno antes de sincronizar.")

                    if dados_sync:
                        novos_tot_off, desc_off = sincronizar_retorno_offline(
                            dados_sync, df_mes, sheet_mes, mes_ano_ativo, ano_ativo
                        )
                        liq_off = max(0.0, arredondar_moeda(novos_tot_off["merc_real"] - desc_off, 2))
                        st.session_state["msg_sucesso_conf"] = (
                            f"✅ Compra Offline sincronizada com sucesso! "
                            f"Mercado Líquido: {formatar_moeda_br(liq_off)} | Farmácia: {formatar_moeda_br(novos_tot_off['farm_real'])}"
                        )
                        st.rerun()
                except Exception as e:
                    st.error(f"⚠️ Erro ao processar o arquivo de retorno: {e}")

    st.markdown('<hr class="divisor-secao">', unsafe_allow_html=True)

    col_f1, col_f2, col_f3, col_f4 = st.columns([1.3, 1.5, 0.6, 0.6])
    with col_f1:
        apenas_planejados = st.checkbox("Mostrar só itens planejados", value=True)
    with col_f2:
        setor_conf_sel = st.selectbox("Ir direto ao Setor:", ["📋 Circuito Completo (A → L)"] + SETORES_OFICIAIS, index=0)
    with col_f3:
        st.write("")
        if st.button("📂 Abrir", use_container_width=True, help="Expandir todos os setores"):
            st.session_state["exp_conf_todos"] = True
    with col_f4:
        st.write("")
        if st.button("📁 Fechar", use_container_width=True, help="Recolher todos os setores"):
            st.session_state["exp_conf_todos"] = False

    # Também permite adicionar item avulso de última hora direto na Conferência (no meio do mercado)
    with st.expander("➕ Adicionar Item Avulso Rápido no Carrinho"):
        with st.form("form_item_avulso_conf", clear_on_submit=True):
            ca1, ca2 = st.columns(2)
            with ca1:
                avc_prod = st.text_input("Nome do Produto")
                avc_setor = st.selectbox("Setor", SETORES_OFICIAIS, index=len(SETORES_OFICIAIS)-1)
                avc_m1 = st.text_input("Marca", value="--")
            with ca2:
                avc_qtd = st.number_input("Quantidade", min_value=0.1, value=1.0, step=0.5, format="%.2f")
                avc_unid = st.text_input("Unidade", value="Unidade")
                avc_preco = st.number_input("Preço Unit. (R$)", min_value=0.0, value=0.0, step=0.5, format="%.2f")
            if st.form_submit_button("Inserir já como Planejado e Comprado (✅)", use_container_width=True):
                if avc_prod.strip():
                    df_set_av = df_mes[df_mes["Setor"] == avc_setor]
                    nova_ordem = int(df_set_av["Ordem_num"].max() + 1) if not df_set_av.empty else int(df_mes["Ordem_num"].max() + 1)
                    novo_cod = f"#AV{int(time.time()) % 10000}"
                    sub_av = arredondar_moeda(avc_qtd * avc_preco, 2)
                    nova_linha_av = pd.DataFrame([{
                        "Ordem": str(nova_ordem),
                        "Codigo": novo_cod,
                        "Setor": avc_setor,
                        "Produto": avc_prod.strip(),
                        "Marca1": avc_m1.strip() or "--",
                        "Marca2": "Avulso do Mês",
                        "Unidade": avc_unid.strip() or "Unidade",
                        "Planejado": "TRUE",
                        "QtdPlanejada": formatar_num_planilha(avc_qtd, 3),
                        "PrecoUnit": formatar_num_planilha(avc_preco, 2),
                        "SubtotalPlanejado": formatar_num_planilha(sub_av, 2),
                        "Comprado": "TRUE",
                        "QtdComprada": formatar_num_planilha(avc_qtd, 3),
                        "PrecoRealUnit": formatar_num_planilha(avc_preco, 2),
                        "SubtotalReal": formatar_num_planilha(sub_av, 2),
                        "ObsMes": "Avulso no mercado",
                        "Ordem_num": nova_ordem,
                        "Planejado_bool": True,
                        "Comprado_bool": True,
                        "QtdPlanejada_num": float(avc_qtd),
                        "PrecoUnit_num": float(avc_preco),
                        "QtdComprada_num": float(avc_qtd),
                        "PrecoRealUnit_num": float(avc_preco)
                    }])
                    df_mes_novo = pd.concat([df_mes, nova_linha_av], ignore_index=True)
                    salvar_df_mes(sheet_mes, df_mes_novo, ano_ativo, atualizar_preco_catalogo=False)
                    st.session_state["msg_sucesso_conf"] = f"✅ Item '{avc_prod}' incluído no carrinho!"
                    st.rerun()

    setores_conf = SETORES_OFICIAIS if setor_conf_sel.startswith("📋") else [setor_conf_sel]
    expandir_padrao_conf = st.session_state.get("exp_conf_todos", True)
    codigos_visiveis_conf = codigos_visiveis_conferencia(df_mes)

    with st.form("form_conferencia_mercado", clear_on_submit=False):
        valores_conf = {}
        algum_item_exibido = False

        for setor_nome in setores_conf:
            df_setor = df_mes[df_mes["Setor"] == setor_nome]
            if apenas_planejados:
                df_setor = df_setor[df_setor["Codigo"].astype(str).str.strip().isin(codigos_visiveis_conf)]
            if df_setor.empty:
                continue

            algum_item_exibido = True
            eh_setor_farmacia = "Farmácia" in setor_nome
            qtd_comp_set = int(df_setor["Comprado_bool"].sum())
            tot_set = len(df_setor)
            status_setor = "✅ Concluído" if (tot_set > 0 and qtd_comp_set == tot_set) else f"{qtd_comp_set}/{tot_set} no carrinho"

            with st.expander(f"{setor_nome}  —  ({status_setor})", expanded=expandir_padrao_conf):
                for idx_row, row in df_setor.iterrows():
                    cod = str(row["Codigo"]).strip()
                    prod = str(row["Produto"])
                    m1 = exibir_marca_limpa(row["Marca1"], cod)
                    m2 = limpar_marca_lida(row["Marca2"], cod)
                    m2_txt = f" | {m2}" if m2 not in ["", "-", "--", "nan"] else ""
                    unid = str(row["Unidade"])
                    comp_atual = bool(row["Comprado_bool"])
                    plan_atual_conf = bool(row["Planejado_bool"])
                    qtd_c_atual = float(row["QtdComprada_num"]) if row["QtdComprada_num"] > 0 else float(row["QtdPlanejada_num"])
                    pr_c_atual = float(row["PrecoRealUnit_num"]) if row["PrecoRealUnit_num"] > 0 else float(row["PrecoUnit_num"])
                    obs_atual = str(row.get("ObsMes", "") or "")

                    st.markdown(
                        f"**{prod}** <span class='item-sub'>— Marca: <b>{m1}{m2_txt}</b> | Planejado: <b>{formatar_qtd_br(row['QtdPlanejada_num'])} {unid}</b></span>",
                        unsafe_allow_html=True
                    )

                    # Na Farmácia não exibe o campo "Obs (Kit/Pote/Peso)"
                    if eh_setor_farmacia:
                        cc1, cc2, cc3 = st.columns([1.2, 1.1, 1.2])
                        with cc1:
                            chk_verde = st.checkbox(
                                "Comprado",
                                value=comp_atual,
                                key=f"cf_chk_{mes_ano_ativo}_{idx_row}"
                            )
                            manter_plan = st.checkbox(
                                "Manter Planejado",
                                value=plan_atual_conf,
                                help="Desmarque se desistir de comprar este item para ele não ir para 'O que Faltou Comprar'.",
                                key=f"cf_pl_{mes_ano_ativo}_{idx_row}"
                            )
                        with cc2:
                            qtd_real = float(st.number_input(
                                f"{unid}",
                                min_value=0,
                                value=int(round(qtd_c_atual)),
                                step=1,
                                key=f"cf_qtd_{mes_ano_ativo}_{idx_row}"
                            ))
                        with cc3:
                            pr_real = st.number_input(
                                "Preço Unit. (R$)",
                                min_value=0.0,
                                value=pr_c_atual,
                                step=0.50,
                                format="%.2f",
                                key=f"cf_pr_{mes_ano_ativo}_{idx_row}"
                            )
                        obs_in = obs_atual
                    else:
                        cc1, cc2, cc3, cc4 = st.columns([1.15, 0.95, 1.1, 1.25])
                        with cc1:
                            chk_verde = st.checkbox(
                                "Comprado",
                                value=comp_atual,
                                key=f"cf_chk_{mes_ano_ativo}_{idx_row}"
                            )
                            manter_plan = st.checkbox(
                                "Planejado",
                                value=plan_atual_conf,
                                help="Desmarque caso desista de levar este item na hora (evita que vá para 'O que Faltou Comprar').",
                                key=f"cf_pl_{mes_ano_ativo}_{idx_row}"
                            )
                        with cc2:
                            if eh_unidade_fracionada(unid):
                                qtd_real = float(st.number_input(
                                    f"{unid}",
                                    min_value=0.0,
                                    value=float(qtd_c_atual),
                                    step=0.1,
                                    format="%.2f",
                                    key=f"cf_qtd_{mes_ano_ativo}_{idx_row}"
                                ))
                            else:
                                qtd_real = float(st.number_input(
                                    f"{unid}",
                                    min_value=0,
                                    value=int(round(qtd_c_atual)),
                                    step=1,
                                    key=f"cf_qtd_{mes_ano_ativo}_{idx_row}"
                                ))
                        with cc3:
                            pr_real = st.number_input(
                                "Preço Unit. (R$)",
                                min_value=0.0,
                                value=pr_c_atual,
                                step=0.50,
                                format="%.2f",
                                key=f"cf_pr_{mes_ano_ativo}_{idx_row}"
                            )
                        with cc4:
                            obs_in = st.text_input(
                                "Obs (Kit/Pote/Peso)",
                                value=obs_atual,
                                placeholder="Ex: Kit / Pote",
                                key=f"cf_obs_{mes_ano_ativo}_{idx_row}"
                            )

                    valores_conf[idx_row] = (chk_verde, manter_plan, qtd_real, pr_real, obs_in)
                    st.markdown('<hr style="margin: 6px 0px; opacity: 0.2;">', unsafe_allow_html=True)

        if not algum_item_exibido:
            st.warning("Nenhum item planejado para este filtro. Desmarque a opção 'Mostrar só itens planejados' acima ou vá na guia Planejamento (Casa).")

        st.markdown('<hr class="divisor-secao">', unsafe_allow_html=True)
        st.markdown("### 🧾 Fechamento do Caixa (Como foi pago)")

        dt_compra_in = st.date_input("Data Real da Compra", value=data_compra_padrao_mes, format="DD/MM/YYYY")

        c_desc_cf, c_din_cf = st.columns(2)
        with c_desc_cf:
            desc_clube_real = st.number_input(
                "🏷️ Clube de Descontos (Abatido no fim da conta R$)",
                min_value=0.0,
                value=safe_float(resumo_salvo.get("DescontoClube", 0.0)),
                step=1.0,
                format="%.2f",
                help="Valor total de descontos do App do Mercado debitado no fechamento do cupom fiscal (exclusivo do Mercado)."
            )
        with c_din_cf:
            din_real = st.number_input(
                "💵 1º Pago em DINHEIRO (R$)",
                min_value=0.0,
                value=safe_float(resumo_salvo.get("Dinheiro", 0.0)),
                step=10.0,
                format="%.2f"
            )

        cp1, cp2 = st.columns(2)
        with cp1:
            st.markdown(label_banco_html(LOGO_BRADESCO, "Bradesco", "DÉBITO"), unsafe_allow_html=True)
            b_deb_r = st.number_input("Bradesco Débito Real", min_value=0.0, value=safe_float(resumo_salvo.get("BradescoDebito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="cf_bd")

            st.markdown(label_banco_html(LOGO_MERCADOPAGO, "Mercado Pago", "DÉBITO"), unsafe_allow_html=True)
            m_deb_r = st.number_input("Mercado Pago Débito Real", min_value=0.0, value=safe_float(resumo_salvo.get("MercadoPagoDebito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="cf_md")

            st.markdown(label_banco_html(LOGO_NUBANK, "Nubank", "DÉBITO"), unsafe_allow_html=True)
            n_deb_r = st.number_input("Nubank Débito Real", min_value=0.0, value=safe_float(resumo_salvo.get("NubankDebito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="cf_nd")
        with cp2:
            st.markdown(label_banco_html(LOGO_BRADESCO, "Bradesco", "CRÉDITO"), unsafe_allow_html=True)
            b_cred_r = st.number_input("Bradesco Crédito Real", min_value=0.0, value=safe_float(resumo_salvo.get("BradescoCredito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="cf_bc")

            st.markdown(label_banco_html(LOGO_MERCADOPAGO, "Mercado Pago", "CRÉDITO"), unsafe_allow_html=True)
            m_cred_r = st.number_input("Mercado Pago Crédito Real", min_value=0.0, value=safe_float(resumo_salvo.get("MercadoPagoCredito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="cf_mc")

            st.markdown(label_banco_html(LOGO_NUBANK, "Nubank", "CRÉDITO"), unsafe_allow_html=True)
            n_cred_r = st.number_input("Nubank Crédito Real", min_value=0.0, value=safe_float(resumo_salvo.get("NubankCredito", 0.0)), step=10.0, format="%.2f", label_visibility="collapsed", key="cf_nc")

        opcoes_pag_farm = ["Dinheiro", "Bradesco - Débito", "Bradesco - Crédito", "Mercado Pago - Débito", "Mercado Pago - Crédito", "Nubank - Débito", "Nubank - Crédito"]
        idx_pf = opcoes_pag_farm.index(resumo_salvo.get("PagamentoFarmacia")) if resumo_salvo.get("PagamentoFarmacia") in opcoes_pag_farm else 0
        pag_farm_r = st.selectbox("💊 Pago na Farmácia com:", opcoes_pag_farm, index=idx_pf)

        st.markdown("#### 🚕 Transporte (Ida e Volta)")
        opcoes_transp_cf = ["Não houve", "Dinheiro", "Bradesco - Débito", "Bradesco - Crédito", "Mercado Pago - Débito", "Mercado Pago - Crédito", "Nubank - Débito", "Nubank - Crédito"]
        ct_cf1, ct_cf2 = st.columns(2)
        with ct_cf1:
            idx_ti_cf = opcoes_transp_cf.index(resumo_salvo.get("TranspIdaPag")) if resumo_salvo.get("TranspIdaPag") in opcoes_transp_cf else 0
            tr_ida_pag_cf = st.selectbox("🚕 Ida — Pago com:", opcoes_transp_cf, index=idx_ti_cf, key="cf_ti_p")
            tr_ida_val_cf = st.number_input("🚕 Ida — Valor (R$):", min_value=0.0, value=safe_float(resumo_salvo.get("TranspIdaVal", 0.0)), step=5.0, format="%.2f", key="cf_ti_v")
        with ct_cf2:
            idx_tv_cf = opcoes_transp_cf.index(resumo_salvo.get("TranspVoltaPag")) if resumo_salvo.get("TranspVoltaPag") in opcoes_transp_cf else 0
            tr_volta_pag_cf = st.selectbox("🚕 Volta — Pago com:", opcoes_transp_cf, index=idx_tv_cf, key="cf_tv_p")
            tr_volta_val_cf = st.number_input("🚕 Volta — Valor (R$):", min_value=0.0, value=safe_float(resumo_salvo.get("TranspVoltaVal", 0.0)), step=5.0, format="%.2f", key="cf_tv_v")

        obs_fech_r = st.text_input("Observação geral da compra do mês:", value=str(resumo_salvo.get("ObsFechamento", "")))

        btn_salvar_conf = st.form_submit_button("✅ Salvar Conferência e Fechamento", use_container_width=True)

    if btn_salvar_conf:
        for idx_r, (chk_v, m_plan, q_r, p_r, ob_r) in valores_conf.items():
            df_mes.at[idx_r, "Comprado_bool"] = chk_v
            df_mes.at[idx_r, "Planejado_bool"] = True if chk_v else bool(m_plan)
            df_mes.at[idx_r, "QtdComprada_num"] = q_r
            df_mes.at[idx_r, "PrecoRealUnit_num"] = p_r
            if p_r > 0:
                df_mes.at[idx_r, "PrecoUnit_num"] = p_r
            df_mes.at[idx_r, "ObsMes"] = ob_r

        df_mes = aplicar_equivalencia_kits_shampoo(df_mes)
        salvar_df_mes(sheet_mes, df_mes, ano_ativo, atualizar_preco_catalogo=True)
        novos_tot = calcular_totais_df(df_mes)
        dt_c_str = dt_compra_in.strftime("%d/%m/%Y")
        salvar_configs({f"data_compra_{mes_ano_ativo}": dt_c_str}, ano_ativo)
        salvar_resumo_pagamento(mes_ano_ativo, {
            "DataCompra": dt_c_str,
            "TotalMercadoPlanejado": novos_tot["merc_plan"],
            "TotalMercadoReal": novos_tot["merc_real"],
            "TotalFarmaciaPlanejado": novos_tot["farm_plan"],
            "TotalFarmaciaReal": novos_tot["farm_real"],
            "Dinheiro": din_real,
            "BradescoDebito": b_deb_r,
            "BradescoCredito": b_cred_r,
            "MercadoPagoDebito": m_deb_r,
            "MercadoPagoCredito": m_cred_r,
            "NubankDebito": n_deb_r,
            "NubankCredito": n_cred_r,
            "PagamentoFarmacia": pag_farm_r,
            "ObsFechamento": obs_fech_r,
            "TranspIdaPag": tr_ida_pag_cf,
            "TranspIdaVal": tr_ida_val_cf,
            "TranspVoltaPag": tr_volta_pag_cf,
            "TranspVoltaVal": tr_volta_val_cf,
            "DescontoClube": desc_clube_real
        }, ano_ativo)
        liq_msg = max(0.0, arredondar_moeda(novos_tot["merc_real"] - desc_clube_real, 2))
        st.session_state["msg_sucesso_conf"] = f"✅ Conferência salva! Mercado Líquido: {formatar_moeda_br(liq_msg)} (Bruto: {formatar_moeda_br(novos_tot['merc_real'])} | Clube: -{formatar_moeda_br(desc_clube_real)}) | Farmácia: {formatar_moeda_br(novos_tot['farm_real'])}"
        st.rerun()

    # Conferência matemática entre Soma dos Pagamentos e Total Líquido do Carrinho do Mercado (após Clube de Descontos)
    soma_pagamentos_merc = (
        safe_float(resumo_salvo.get("Dinheiro", 0.0)) +
        safe_float(resumo_salvo.get("BradescoDebito", 0.0)) +
        safe_float(resumo_salvo.get("BradescoCredito", 0.0)) +
        safe_float(resumo_salvo.get("MercadoPagoDebito", 0.0)) +
        safe_float(resumo_salvo.get("MercadoPagoCredito", 0.0)) +
        safe_float(resumo_salvo.get("NubankDebito", 0.0)) +
        safe_float(resumo_salvo.get("NubankCredito", 0.0))
    )
    bruto_caixa = totais_atuais["merc_real"] if totais_atuais["merc_real"] > 0 else totais_atuais["merc_plan"]
    desc_clube_caixa = safe_float(resumo_salvo.get("DescontoClube", 0.0))
    alvo_caixa = max(0.0, arredondar_moeda(bruto_caixa - desc_clube_caixa, 2))
    falta_alocar = arredondar_moeda(alvo_caixa - soma_pagamentos_merc, 2)
    saldo_pos_din = max(0.0, arredondar_moeda(alvo_caixa - safe_float(resumo_salvo.get("Dinheiro", 0.0)), 2))

    st.markdown(f"""
    <div class="card-alerta-caixa">
        <b>📢 RESUMO DE CAIXA (MERCADO):</b><br>
        • Subtotal Bruto dos Produtos: <b>{formatar_moeda_br(bruto_caixa)}</b><br>
        • 🏷️ (-) Clube de Descontos (App): <b style="color:#2ECC71;">- {formatar_moeda_br(desc_clube_caixa)}</b><br>
        • <b>(=) Valor Líquido a Pagar no Caixa: {formatar_moeda_br(alvo_caixa)}</b><br>
        • 1º Pagamento em <b>💵 Dinheiro</b>: <b>{formatar_moeda_br(resumo_salvo.get('Dinheiro', 0.0))}</b> → <b>Resta p/ Cartões: {formatar_moeda_br(saldo_pos_din)}</b><br>
        • Soma total lançada (Dinheiro + Cartões): <b>{formatar_moeda_br(soma_pagamentos_merc)}</b>
        {"✅ <i>(Pagamento 100% fechado!)</i>" if abs(falta_alocar) < 0.05 else f"⚠️ <i>(Diferença p/ alocar nos cartões: {formatar_moeda_br(falta_alocar)})</i>"}
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# GUIA 3: O QUE FALTOU COMPRAR (PENDÊNCIAS DO MÊS)
# ==============================================================================
elif menu == "O que Faltou Comprar":
    st.markdown('<h2 style="margin-bottom: 0px;">⚠️ O que Faltou Comprar</h2>', unsafe_allow_html=True)
    st.caption(f"Itens marcados no planejamento de **{mes_ano_ativo}** que não foram comprados ou vieram em quantidade menor.")

    if "msg_faltou" in st.session_state:
        st.success(st.session_state.pop("msg_faltou"))

    cond_faltou = df_mes["Planejado_bool"] & ((~df_mes["Comprado_bool"]) | (df_mes["QtdComprada_num"] + 1e-4 < df_mes["QtdPlanejada_num"]))
    df_faltou = df_mes[cond_faltou].copy()

    if df_faltou.empty:
        st.success("🎉 Parabéns! Todos os itens planejados para este mês já foram comprados!")
    else:
        eh_farm_f = df_faltou["Setor"].astype(str).str.contains("Farmácia", case=False, na=False)

        def calc_custo_faltante(row_f):
            qtd_f = row_f["QtdPlanejada_num"] if not row_f["Comprado_bool"] else max(0.0, row_f["QtdPlanejada_num"] - row_f["QtdComprada_num"])
            pr_f = row_f["PrecoRealUnit_num"] if row_f["PrecoRealUnit_num"] > 0 else row_f["PrecoUnit_num"]
            return qtd_f, arredondar_moeda(qtd_f * pr_f, 2)

        tot_faltou_farm = 0.0
        tot_faltou_merc = 0.0
        for _, rf in df_faltou.iterrows():
            _, c_f = calc_custo_faltante(rf)
            if "Farmácia" in str(rf["Setor"]):
                tot_faltou_farm += c_f
            else:
                tot_faltou_merc += c_f

        cf1, cf2 = st.columns(2)
        with cf1:
            st.metric("💊 Faltou na Farmácia", formatar_moeda_br(tot_faltou_farm), f"{int(eh_farm_f.sum())} item(ns)")
        with cf2:
            st.metric("🛒 Faltou no Mercado", formatar_moeda_br(tot_faltou_merc), f"{int((~eh_farm_f).sum())} item(ns)")

        with st.form("form_dar_baixa_faltantes"):
            st.write("Se você comprou algum destes itens depois em outro mercado, marque abaixo para atualizar:")
            baixas_faltantes = {}
            for setor_nome in SETORES_OFICIAIS:
                df_sf = df_faltou[df_faltou["Setor"] == setor_nome]
                if df_sf.empty:
                    continue
                st.markdown(f'<div class="setor-header">{setor_nome}</div>', unsafe_allow_html=True)
                for idx_f, rf in df_sf.iterrows():
                    qtd_falta, custo_falta = calc_custo_faltante(rf)
                    m1 = exibir_marca_limpa(rf["Marca1"], rf["Codigo"])
                    pr_base = rf["PrecoRealUnit_num"] if rf["PrecoRealUnit_num"] > 0 else rf["PrecoUnit_num"]
                    chk_f = st.checkbox(
                        f"Dar baixa: **{rf['Produto']}** ({m1}) — Faltam **{formatar_qtd_br(qtd_falta)} {rf['Unidade']}** | Estimado: **{formatar_moeda_br(custo_falta)}** (Unit: {formatar_moeda_br(pr_base)})",
                        value=False,
                        key=f"flt_{mes_ano_ativo}_{idx_f}"
                    )
                    baixas_faltantes[idx_f] = chk_f

            if st.form_submit_button("✔️ Confirmar Compra dos Itens Selecionados", use_container_width=True):
                alterou = False
                for idx_f, marcou in baixas_faltantes.items():
                    if marcou:
                        df_mes.at[idx_f, "Comprado_bool"] = True
                        df_mes.at[idx_f, "QtdComprada_num"] = df_mes.at[idx_f, "QtdPlanejada_num"]
                        alterou = True
                if alterou:
                    salvar_df_mes(sheet_mes, df_mes, ano_ativo, atualizar_preco_catalogo=True)
                    novos_tot = calcular_totais_df(df_mes)
                    res_atu = obter_resumo_mes(mes_ano_ativo, ano_ativo)
                    res_atu["TotalMercadoReal"] = novos_tot["merc_real"]
                    res_atu["TotalFarmaciaReal"] = novos_tot["farm_real"]
                    salvar_resumo_pagamento(mes_ano_ativo, res_atu, ano_ativo)
                    st.session_state["msg_faltou"] = "✅ Itens atualizados como comprados!"
                    st.rerun()

# ==============================================================================
# GUIA 4: TABELA DE PREÇOS DO MÊS (EDIÇÃO RÁPIDA EM GRADE)
# ==============================================================================
elif menu == "Tabela de Preços do Mês":
    st.markdown('<h2 style="margin-bottom: 0px;">💲 Tabela de Preços do Mês</h2>', unsafe_allow_html=True)
    st.caption(f"Edite rapidamente os preços unitários de **{mes_ano_ativo}** (aceita números inteiros como `5`, com vírgula `35,00` ou ponto `35.00`).")

    if "msg_precos" in st.session_state:
        st.success(st.session_state.pop("msg_precos"))

    df_grade_precos = pd.DataFrame({
        "Setor": df_mes["Setor"],
        "Produto": df_mes["Produto"],
        "Marca": [exibir_marca_limpa(m, c) for m, c in zip(df_mes["Marca1"], df_mes["Codigo"])],
        "Unidade": df_mes["Unidade"],
        "Qtd_Planejada": df_mes["QtdPlanejada_num"].apply(formatar_qtd_br),
        "Preco_Unit_RS": df_mes["PrecoUnit_num"].apply(lambda x: f"{safe_float(x):.2f}".replace(".", ","))
    })

    grade_editada = st.data_editor(
        df_grade_precos,
        hide_index=True,
        use_container_width=True,
        disabled=["Setor", "Produto", "Marca", "Unidade", "Qtd_Planejada"],
        column_config={
            "Setor": st.column_config.TextColumn("Setor"),
            "Produto": st.column_config.TextColumn("Produto"),
            "Marca": st.column_config.TextColumn("Marca"),
            "Unidade": st.column_config.TextColumn("Unidade"),
            "Qtd_Planejada": st.column_config.TextColumn("Qtd"),
            "Preco_Unit_RS": st.column_config.TextColumn("Preço Unit. (R$)")
        },
        key=f"ed_precos_{mes_ano_ativo}"
    )

    if st.button("💾 Salvar Tabela de Preços do Mês", type="primary", use_container_width=True):
        for idx_p, r_ed in grade_editada.iterrows():
            pr_novo = safe_float(r_ed["Preco_Unit_RS"])
            df_mes.at[idx_p, "PrecoUnit_num"] = pr_novo
            if not df_mes.at[idx_p, "Comprado_bool"] or df_mes.at[idx_p, "PrecoRealUnit_num"] <= 0:
                df_mes.at[idx_p, "PrecoRealUnit_num"] = pr_novo
        salvar_df_mes(sheet_mes, df_mes, ano_ativo, atualizar_preco_catalogo=True)
        novos_tot = calcular_totais_df(df_mes)
        res_atu = obter_resumo_mes(mes_ano_ativo, ano_ativo)
        if res_atu:
            res_atu["TotalMercadoPlanejado"] = novos_tot["merc_plan"]
            res_atu["TotalFarmaciaPlanejado"] = novos_tot["farm_plan"]
            salvar_resumo_pagamento(mes_ano_ativo, res_atu, ano_ativo)
        st.session_state["msg_precos"] = f"✅ Preços de {mes_ano_ativo} atualizados com sucesso!"
        st.rerun()

# ==============================================================================
# GUIA 5: RELATÓRIO / COFRE HISTÓRICO (LAYOUT FIEL AO ESBOÇO DO USUÁRIO)
# ==============================================================================
elif menu == "Relatório / Histórico":
    col_t_rel, col_s_rel, _ = st.columns([1.35, 1.0, 0.8])
    with col_t_rel:
        st.markdown('<h2 style="margin-top: 2px; margin-bottom: 0px;">📅 Resumo Mensal</h2>', unsafe_allow_html=True)
    with col_s_rel:
        mes_rel_sel = st.selectbox(
            "Mês do Resumo",
            opcoes_meses,
            index=opcoes_meses.index(mes_ano_ativo) if mes_ano_ativo in opcoes_meses else 0,
            label_visibility="collapsed",
            key="sel_mes_relatorio"
        )

    ano_rel_sel = mes_rel_sel.split(" ")[-1]
    res_mes_rel = obter_resumo_mes(mes_rel_sel, ano_rel_sel)

    if mes_rel_sel == mes_ano_ativo:
        df_rel_mes = df_mes
    else:
        df_rel_mes, _ = carregar_df_mes(mes_rel_sel, ano_rel_sel)
    tot_rel = calcular_totais_df(df_rel_mes)

    dt_exib = res_mes_rel.get("DataCompra") or data_padrao_dia_5(mes_rel_sel).strftime("%d/%m/%Y")
    merc_prev_exib = safe_float(res_mes_rel.get("TotalMercadoPlanejado", tot_rel["merc_plan"])) or tot_rel["merc_plan"]
    merc_real_bruto = safe_float(res_mes_rel.get("TotalMercadoReal", tot_rel["merc_real"])) or tot_rel["merc_real"]
    desc_clube_exib = safe_float(res_mes_rel.get("DescontoClube", 0.0))
    merc_real_exib = max(0.0, arredondar_moeda(merc_real_bruto - desc_clube_exib, 2))

    farm_real_exib = safe_float(res_mes_rel.get("TotalFarmaciaReal", tot_rel["farm_real"]))
    if farm_real_exib <= 0 and tot_rel["farm_plan"] > 0:
        farm_real_exib = tot_rel["farm_plan"]

    din_merc_exib = safe_float(res_mes_rel.get("Dinheiro", 0.0))
    brad_deb_exib = safe_float(res_mes_rel.get("BradescoDebito", 0.0))
    brad_cred_exib = safe_float(res_mes_rel.get("BradescoCredito", 0.0))
    mp_deb_exib = safe_float(res_mes_rel.get("MercadoPagoDebito", 0.0))
    mp_cred_exib = safe_float(res_mes_rel.get("MercadoPagoCredito", 0.0))
    nu_deb_exib = safe_float(res_mes_rel.get("NubankDebito", 0.0))
    nu_cred_exib = safe_float(res_mes_rel.get("NubankCredito", 0.0))

    tot_cartoes_merc = arredondar_moeda(
        brad_deb_exib + brad_cred_exib + mp_deb_exib + mp_cred_exib + nu_deb_exib + nu_cred_exib, 2
    )

    tr_ida_pag = str(res_mes_rel.get("TranspIdaPag", "Não houve"))
    tr_ida_val = safe_float(res_mes_rel.get("TranspIdaVal", 0.0))
    tr_volta_pag = str(res_mes_rel.get("TranspVoltaPag", "Não houve"))
    tr_volta_val = safe_float(res_mes_rel.get("TranspVoltaVal", 0.0))

    base_merc_geral = (din_merc_exib + tot_cartoes_merc) if (din_merc_exib + tot_cartoes_merc) > 0 else merc_real_exib
    total_geral_exib = arredondar_moeda(farm_real_exib + base_merc_geral + tr_ida_val + tr_volta_val, 2)
    badge_clube_rel = f'<br><span style="color:#2ECC71;font-size:0.75rem;font-weight:500;">(🏷️ -{formatar_moeda_br(desc_clube_exib)})</span>' if desc_clube_exib > 0 else ""

    pag_farm_metodo = str(res_mes_rel.get("PagamentoFarmacia", "Dinheiro") or "Dinheiro")
    if "Bradesco" in pag_farm_metodo:
        icone_farm_pag = f'<img src="{LOGO_BRADESCO}" width="20" style="vertical-align:middle;border-radius:4px;margin-right:6px;"> <b>Bradesco</b>'
    elif "Mercado Pago" in pag_farm_metodo:
        icone_farm_pag = f'<img src="{LOGO_MERCADOPAGO}" width="20" style="vertical-align:middle;border-radius:4px;margin-right:6px;"> <b>Mercado Pago</b>'
    elif "Nubank" in pag_farm_metodo:
        icone_farm_pag = f'<img src="{LOGO_NUBANK}" width="20" style="vertical-align:middle;border-radius:4px;margin-right:6px;"> <b>Nubank</b>'
    else:
        icone_farm_pag = '💵 <b>Dinheiro</b>'

    farm_deb_str = formatar_moeda_br(farm_real_exib) if "Débito" in pag_farm_metodo else ("-" if "Dinheiro" in pag_farm_metodo else "R$ 0,00")
    farm_cred_str = formatar_moeda_br(farm_real_exib) if "Crédito" in pag_farm_metodo else ("-" if "Dinheiro" in pag_farm_metodo else "R$ 0,00")

    def montar_dados_transporte(chave_banco):
        usou_ida = tr_ida_pag.startswith(chave_banco) and tr_ida_val > 0
        usou_volta = tr_volta_pag.startswith(chave_banco) and tr_volta_val > 0

        bolinha_ida = '<span style="display:inline-block;width:13px;height:13px;border-radius:50%;background:#2ECC71;border:2px solid #E0E0E0;vertical-align:middle;margin-right:3px;"></span>' if usou_ida else '<span style="display:inline-block;width:13px;height:13px;border-radius:50%;background:transparent;border:2px solid #90A4AE;vertical-align:middle;margin-right:3px;"></span>'
        bolinha_volta = '<span style="display:inline-block;width:13px;height:13px;border-radius:50%;background:#2ECC71;border:2px solid #E0E0E0;vertical-align:middle;margin-right:3px;"></span>' if usou_volta else '<span style="display:inline-block;width:13px;height:13px;border-radius:50%;background:transparent;border:2px solid #90A4AE;vertical-align:middle;margin-right:3px;"></span>'
        html_ida_volta = f'<span style="margin-left:10px;font-size:0.82rem;color:#CFD8DC;">{bolinha_ida}Ida &nbsp; {bolinha_volta}Volta</span>'

        if chave_banco == "Dinheiro":
            sub_t = (tr_ida_val if usou_ida else 0.0) + (tr_volta_val if usou_volta else 0.0)
            return html_ida_volta, "-", "-", formatar_moeda_br(sub_t)

        val_deb = 0.0
        val_cred = 0.0
        if usou_ida:
            if "Débito" in tr_ida_pag:
                val_deb += tr_ida_val
            else:
                val_cred += tr_ida_val
        if usou_volta:
            if "Débito" in tr_volta_pag:
                val_deb += tr_volta_val
            else:
                val_cred += tr_volta_val
        sub_t = val_deb + val_cred
        return html_ida_volta, formatar_moeda_br(val_deb), formatar_moeda_br(val_cred), formatar_moeda_br(sub_t)

    iv_din, td_din, tc_din, ts_din = montar_dados_transporte("Dinheiro")
    iv_bra, td_bra, tc_bra, ts_bra = montar_dados_transporte("Bradesco")
    iv_mp, td_mp, tc_mp, ts_mp = montar_dados_transporte("Mercado Pago")
    iv_nu, td_nu, tc_nu, ts_nu = montar_dados_transporte("Nubank")

    st.markdown(f"""
    <style>
        .tbl-resumo {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            margin-bottom: 18px;
            font-size: 0.90rem;
            background-color: rgba(25, 32, 42, 0.55);
            border-radius: 8px;
            overflow: hidden;
        }}
        .tbl-resumo th {{
            text-align: center;
            padding: 8px 6px;
            border-bottom: 1px solid rgba(255,255,255,0.12);
            color: #E0E6ED;
            font-weight: 700;
            line-height: 1.25;
        }}
        .tbl-resumo td {{
            text-align: center;
            padding: 10px 6px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            color: #FFFFFF;
        }}
        .tbl-det {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 8px;
            font-size: 0.92rem;
            background-color: rgba(25, 32, 42, 0.55);
            border-radius: 8px;
            overflow: hidden;
        }}
        .tbl-det th {{
            text-align: left;
            padding: 10px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.14);
            color: #E0E6ED;
            font-weight: 700;
            background-color: rgba(255,255,255,0.03);
        }}
        .tbl-det td {{
            padding: 9px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            color: #E0E6ED;
        }}
    </style>

    <table class="tbl-resumo">
        <thead>
            <tr>
                <th><br>Data</th>
                <th>🛒<br>Mercado<br><span style="font-weight:400;font-size:0.80rem;">(Prev.)</span></th>
                <th>🛒<br>Mercado<br><span style="font-weight:400;font-size:0.80rem;">(Real)</span></th>
                <th>💊<br>Farmácia<br><span style="font-weight:400;font-size:0.80rem;">(Real)</span></th>
                <th>💵 🛒<br>Dinheiro</th>
                <th>💳 🛒<br>Total<br>Cartões</th>
                <th>💵 💳<br>Total<br><span style="font-weight:400;font-size:0.80rem;">Geral</span></th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>{dt_exib}</td>
                <td>{formatar_moeda_br(merc_prev_exib)}</td>
                <td><b>{formatar_moeda_br(merc_real_exib)}</b>{badge_clube_rel}</td>
                <td><b>{formatar_moeda_br(farm_real_exib)}</b></td>
                <td>{formatar_moeda_br(din_merc_exib)}</td>
                <td>{formatar_moeda_br(tot_cartoes_merc)}</td>
                <td><b>{formatar_moeda_br(total_geral_exib)}</b></td>
            </tr>
        </tbody>
    </table>

    <h3 style="margin-top: 8px; margin-bottom: 6px;">🗒️ Detalhamento</h3>

    <table class="tbl-det">
        <thead>
            <tr>
                <th>Forma de Pagamento <span style="font-weight:400;">(Farmácia)</span></th>
                <th>Débito</th>
                <th>Crédito</th>
                <th>Subtotal</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>{icone_farm_pag}</td>
                <td>{farm_deb_str}</td>
                <td>{farm_cred_str}</td>
                <td><b>{formatar_moeda_br(farm_real_exib)}</b></td>
            </tr>
            <tr>
                <th colspan="4">Forma de Pagamento (Mercado)</th>
            </tr>
            <tr>
                <td>🏷️ <b>Clube de Descontos</b> <span style="font-size:0.80rem;color:#90A4AE;">(Bruto: {formatar_moeda_br(merc_real_bruto)})</span></td>
                <td>-</td>
                <td>-</td>
                <td><b style="color:#2ECC71;">- {formatar_moeda_br(desc_clube_exib)}</b></td>
            </tr>
            <tr>
                <td>💵 <b>Dinheiro</b></td>
                <td>-</td>
                <td>-</td>
                <td><b>{formatar_moeda_br(din_merc_exib)}</b></td>
            </tr>
            <tr>
                <td><img src="{LOGO_BRADESCO}" width="20" style="vertical-align:middle;border-radius:4px;margin-right:6px;"> <b>Bradesco</b></td>
                <td>{formatar_moeda_br(brad_deb_exib)}</td>
                <td>{formatar_moeda_br(brad_cred_exib)}</td>
                <td><b>{formatar_moeda_br(brad_deb_exib + brad_cred_exib)}</b></td>
            </tr>
            <tr>
                <td><img src="{LOGO_MERCADOPAGO}" width="20" style="vertical-align:middle;border-radius:4px;margin-right:6px;"> <b>Mercado Pago</b></td>
                <td>{formatar_moeda_br(mp_deb_exib)}</td>
                <td>{formatar_moeda_br(mp_cred_exib)}</td>
                <td><b>{formatar_moeda_br(mp_deb_exib + mp_cred_exib)}</b></td>
            </tr>
            <tr>
                <td><img src="{LOGO_NUBANK}" width="20" style="vertical-align:middle;border-radius:4px;margin-right:6px;"> <b>Nubank</b></td>
                <td>{formatar_moeda_br(nu_deb_exib)}</td>
                <td>{formatar_moeda_br(nu_cred_exib)}</td>
                <td><b>{formatar_moeda_br(nu_deb_exib + nu_cred_exib)}</b></td>
            </tr>
            <tr>
                <th colspan="4">Forma de Pagamento <span style="font-weight:400;">(Transporte)</span></th>
            </tr>
            <tr>
                <td>💵 <b>Dinheiro</b> {iv_din}</td>
                <td>{td_din}</td>
                <td>{tc_din}</td>
                <td><b>{ts_din}</b></td>
            </tr>
            <tr>
                <td><img src="{LOGO_BRADESCO}" width="20" style="vertical-align:middle;border-radius:4px;margin-right:6px;"> <b>Bradesco</b> {iv_bra}</td>
                <td>{td_bra}</td>
                <td>{tc_bra}</td>
                <td><b>{ts_bra}</b></td>
            </tr>
            <tr>
                <td><img src="{LOGO_MERCADOPAGO}" width="20" style="vertical-align:middle;border-radius:4px;margin-right:6px;"> <b>Mercado Pago</b> {iv_mp}</td>
                <td>{td_mp}</td>
                <td>{tc_mp}</td>
                <td><b>{ts_mp}</b></td>
            </tr>
            <tr>
                <td><img src="{LOGO_NUBANK}" width="20" style="vertical-align:middle;border-radius:4px;margin-right:6px;"> <b>Nubank</b> {iv_nu}</td>
                <td>{td_nu}</td>
                <td>{tc_nu}</td>
                <td><b>{ts_nu}</b></td>
            </tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)

    if res_mes_rel.get("ObsFechamento"):
        st.caption(f"📝 **Observações do fechamento ({mes_rel_sel}):** {res_mes_rel.get('ObsFechamento')}")

# ==============================================================================
# GUIA 6: CADASTRO DE PRODUTOS E DEPARTAMENTOS (CATÁLOGO FIXO)
# ==============================================================================
elif menu == "Cadastro de Produtos":
    st.markdown('<h2 style="margin-bottom: 0px;">🗂️ Cadastro de Produtos e Circuito</h2>', unsafe_allow_html=True)
    st.caption("Adicione novos produtos fixos escolhendo em qual Departamento/Setor do seu circuito eles entram (a Ordem é calculada automaticamente no final do Setor escolhido!).")

    if "msg_cat" in st.session_state:
        st.success(st.session_state.pop("msg_cat"))

    df_cat_atual = carregar_df_catalogo(ano_ativo)

    with st.expander("➕ Cadastrar Novo Produto Fixo no Catálogo", expanded=False):
        with st.form("form_novo_produto_catalogo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                np_setor = st.selectbox("Departamento / Setor no Circuito:", SETORES_OFICIAIS)
                np_prod = st.text_input("Nome do Produto:")
                np_m1 = st.text_input("Marca 1 (use '--' para Sem marca específica):", value="--")
                np_m2 = st.text_input("Marca 2 / Observação:", value="-")
            with c2:
                np_qtd = st.number_input("Quantidade Padrão Mensal:", min_value=0.1, value=1.0, step=0.5, format="%.2f")
                np_unid = st.selectbox(
                    "Unidade / Métrica:",
                    [
                        "Unidade", "Kg", "Pacote (1Kg)", "Pacote (5Kg)", "Pacote (0,5Kg)",
                        "Litro", "Lata", "Pacote", "Caixa", "Caixa Pequena",
                        "Saco", "Saco / Unidade", "Vidro", "Refil", "Rolo",
                        "Saquinho", "Tubo", "Pote", "Bifes",
                        "Caixa (30 Comprimidos)", "Frasco (0,5 Litro)", "Unidade (100g)", "Unidade / Kit"
                    ]
                )
                np_preco = st.number_input("Preço Unitário de Referência (R$):", min_value=0.0, value=0.0, step=0.50, format="%.2f")

            if st.form_submit_button("➕ Salvar Novo Produto no Catálogo e no Mês Ativo", use_container_width=True):
                if not np_prod.strip():
                    st.warning("⚠️ Informe o nome do produto.")
                else:
                    df_set_sel = df_cat_atual[df_cat_atual["Setor"] == np_setor]
                    if not df_set_sel.empty:
                        ordem_insercao = float(df_set_sel["Ordem_num"].max()) + 0.5
                    else:
                        ordem_insercao = float(df_cat_atual["Ordem_num"].max() + 1) if not df_cat_atual.empty else 1.0

                    novo_id_num = int(df_cat_atual["Ordem_num"].max() + 1) if not df_cat_atual.empty else 85
                    nova_row_cat = pd.DataFrame([{
                        "Ordem_num": ordem_insercao,
                        "Codigo": f"#{novo_id_num}",
                        "Setor": np_setor,
                        "Produto": np_prod.strip(),
                        "Marca1": np_m1.strip() or "--",
                        "Marca2": np_m2.strip() or "-",
                        "QtdPadrao_num": float(np_qtd),
                        "Unidade": np_unid,
                        "PrecoRef_num": float(np_preco),
                        "Ativo_bool": True
                    }])
                    df_cat_reord = pd.concat([df_cat_atual, nova_row_cat], ignore_index=True).sort_values("Ordem_num").reset_index(drop=True)

                    sh_cat = obter_aba_catalogo(ano_ativo)
                    linhas_c = [COLUNAS_CATALOGO]
                    for idx_novo, rc in df_cat_reord.iterrows():
                        linhas_c.append([
                            str(idx_novo + 1),
                            str(rc["Codigo"]),
                            str(rc["Setor"]),
                            str(rc["Produto"]),
                            escapar_texto_sheets(rc["Marca1"]),
                            escapar_texto_sheets(rc["Marca2"]),
                            formatar_num_planilha(safe_float(rc["QtdPadrao_num"]), 3),
                            str(rc["Unidade"]),
                            formatar_num_planilha(safe_float(rc["PrecoRef_num"]), 2),
                            "TRUE" if safe_bool(rc["Ativo_bool"]) else "FALSE"
                        ])
                    executar_com_retry(sh_cat.clear)
                    executar_com_retry(sh_cat.append_rows, linhas_c, value_input_option="USER_ENTERED")
                    limpar_cache_dados()
                    st.session_state["msg_cat"] = f"✅ Produto '{np_prod}' cadastrado automaticamente no final do '{np_setor}'!"
                    st.rerun()

    st.markdown("### 📋 Editar Produtos Existentes (Ordem, Setor, Marcas, Quantidade Padrão)")
    st.caption("Dica: dê dois cliques em qualquer célula abaixo para editar e depois clique em **Salvar Alterações do Catálogo**.")

    df_ed_cat = pd.DataFrame({
        "Ordem": df_cat_atual["Ordem_num"],
        "Codigo": df_cat_atual["Codigo"],
        "Setor": df_cat_atual["Setor"],
        "Produto": df_cat_atual["Produto"],
        "Marca1": df_cat_atual["Marca1"],
        "Marca2": df_cat_atual["Marca2"],
        "QtdPadrao": df_cat_atual["QtdPadrao_num"],
        "Unidade": df_cat_atual["Unidade"],
        "PrecoRef": df_cat_atual["PrecoRef_num"],
        "Ativo": df_cat_atual["Ativo_bool"]
    })

    cat_editado = st.data_editor(
        df_ed_cat,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Codigo": None,
            "Ordem": st.column_config.NumberColumn("Ordem", min_value=1, step=1),
            "Setor": st.column_config.SelectboxColumn("Setor", options=SETORES_OFICIAIS, required=True),
            "QtdPadrao": st.column_config.NumberColumn("Qtd Padrão", min_value=0.1, step=0.5),
            "PrecoRef": st.column_config.NumberColumn("Preço Ref (R$)", min_value=0.0, step=0.10, format="R$ %.2f"),
            "Ativo": st.column_config.CheckboxColumn("Ativo?")
        }
    )

    if st.button("💾 Salvar Alterações do Catálogo", type="primary", use_container_width=True):
        mapa_qtd_antiga = {str(r["Codigo"]).strip(): safe_float(r["QtdPadrao_num"]) for _, r in df_cat_atual.iterrows()}
        mapa_pr_antigo = {str(r["Codigo"]).strip(): safe_float(r["PrecoRef_num"]) for _, r in df_cat_atual.iterrows()}
        mudancas_qtd = {}
        mudancas_pr = {}

        sh_cat = obter_aba_catalogo(ano_ativo)
        linhas_c = [COLUNAS_CATALOGO]
        cat_ord = cat_editado.sort_values("Ordem").reset_index(drop=True)
        for idx_c, rc in cat_ord.iterrows():
            if not str(rc.get("Produto", "")).strip():
                continue
            cod_c = str(rc.get("Codigo", f"#{idx_c+1}")).strip()
            nova_q = safe_float(rc.get("QtdPadrao", 1.0))
            novo_p = safe_float(rc.get("PrecoRef", 0.0))
            if cod_c in mapa_qtd_antiga and abs(nova_q - mapa_qtd_antiga[cod_c]) > 1e-4:
                mudancas_qtd[cod_c] = nova_q
            if cod_c in mapa_pr_antigo and abs(novo_p - mapa_pr_antigo[cod_c]) > 1e-4:
                mudancas_pr[cod_c] = novo_p

            m1_c = limpar_marca_lida(rc.get("Marca1", "--"), cod_c) or "--"
            m2_c = limpar_marca_lida(rc.get("Marca2", "-"), cod_c) or "-"

            linhas_c.append([
                str(int(safe_float(rc.get("Ordem", idx_c + 1)))),
                cod_c,
                str(rc.get("Setor", SETORES_OFICIAIS[-1])),
                str(rc.get("Produto", "")).strip(),
                escapar_texto_sheets(m1_c),
                escapar_texto_sheets(m2_c),
                formatar_num_planilha(nova_q, 3),
                str(rc.get("Unidade", "Unidade")).strip() or "Unidade",
                formatar_num_planilha(novo_p, 2),
                "TRUE" if safe_bool(rc.get("Ativo", True)) else "FALSE"
            ])
        executar_com_retry(sh_cat.clear)
        executar_com_retry(sh_cat.append_rows, linhas_c, value_input_option="USER_ENTERED")

        # Propaga imediatamente alterações de Qtd Padrão ou Preço Ref para a aba do Mês Ativo
        if mudancas_qtd or mudancas_pr:
            alterou_mes = False
            for idx_m, rm in df_mes.iterrows():
                c_m = str(rm["Codigo"]).strip()
                if c_m in mudancas_qtd:
                    df_mes.at[idx_m, "QtdPlanejada_num"] = mudancas_qtd[c_m]
                    if not df_mes.at[idx_m, "Comprado_bool"]:
                        df_mes.at[idx_m, "QtdComprada_num"] = mudancas_qtd[c_m]
                    alterou_mes = True
                if c_m in mudancas_pr and mudancas_pr[c_m] > 0:
                    df_mes.at[idx_m, "PrecoUnit_num"] = mudancas_pr[c_m]
                    if not df_mes.at[idx_m, "Comprado_bool"]:
                        df_mes.at[idx_m, "PrecoRealUnit_num"] = mudancas_pr[c_m]
                    alterou_mes = True
            if alterou_mes:
                salvar_df_mes(sheet_mes, df_mes, ano_ativo, atualizar_preco_catalogo=False)

        limpar_cache_dados()
        st.session_state["msg_cat"] = "✅ Catálogo de produtos atualizado e sincronizado com o mês ativo!"
        st.rerun()
# === FIM DO CÓDIGO - VERSÃO v.1.20.1 ===

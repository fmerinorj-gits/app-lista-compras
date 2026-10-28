# === APLICATIVO LISTA DE COMPRAS & MERCADO - VERSÃO v.1.1 ===
import math
import time
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
import gspread
from google.oauth2.service_account import Credentials

VERSAO_APP = "v.1.1"

# Configuração de página idêntica ao padrão mobile/centered do App Luz & Água
st.set_page_config(
    page_title="Lista de Compras",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilo visual customizado (Tons de Azul para Planejamento e Verde para Conferência)
st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

# === FUSO HORÁRIO DE BRASÍLIA (UTC-3) ===
FUSO_BR = timezone(timedelta(hours=-3))

def agora_br():
    return datetime.now(FUSO_BR)

def hoje_br():
    return agora_br().date()

# === FUNÇÕES UTILITÁRIAS DE NÚMEROS E FORMATAÇÃO ===
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
    # Se for quantidade inteira exata (ex: 2.00), formata sem casas desnecessárias quando casas=3
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

def exibir_marca_limpa(marca_str):
    m = str(marca_str or "").strip()
    if m in ["", "-", "--", "nan", "None"]:
        return "Sem marca específica"
    return m

# === LISTA OFICIAL DOS DEPARTAMENTOS E DOS 83 PRODUTOS (CIRCUITO DO MERCADO) ===
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
    (1, "F1", "💊 Antes do Mercado: Farmácia", "Neosoro", "--", "-", 9.0, "Un"),
    (2, "F2", "💊 Antes do Mercado: Farmácia", "Alprazolam 0,5mg", "--", "Cx 30 Comp", 1.0, "Cx (30 Comp)"),
    (3, "F3", "💊 Antes do Mercado: Farmácia", "Bupropiona 150mg - 12H", "--", "Cx 30 Comp", 1.0, "Cx (30 Comp)"),

    # 🥩 SETOR A: AÇOUGUE / SALGADOS / CONGELADOS
    (4, "#62", "🥩 Setor A: Açougue/Salgados/Congelados", "Peito de Frango sem osso", "Sadia", "-", 4.0, "Kg"),
    (5, "#64", "🥩 Setor A: Açougue/Salgados/Congelados", "Patinho ou Chã MOÍDO", "Magro", "No máximo 2,5Kg", 2.5, "Kg"),
    (6, "#65", "🥩 Setor A: Açougue/Salgados/Congelados", "Costela Magra", "--", "Ref. 1,5Kg", 1.5, "Kg"),
    (7, "#63", "🥩 Setor A: Açougue/Salgados/Congelados", "Alcatra", "2 Bifes com 3cm de espessura", "-", 2.0, "Bifes"),
    (8, "#61", "🥩 Setor A: Açougue/Salgados/Congelados", "Sal fino", "Lebre", "Ita", 1.0, "Kg"),
    (9, "#70", "🥩 Setor A: Açougue/Salgados/Congelados", "Batata Pré Frita", "--", "-", 2.0, "Kg"),

    # 🧀 SETOR B: LATICÍNIOS / FRIOS
    (10, "#58", "🧀 Setor B: Laticínios/Frios", "Requeijão Light", "Itambé", "200gr", 4.0, "Un"),
    (11, "#59", "🧀 Setor B: Laticínios/Frios", "Requeijão Zero lactose", "Itambé", "200gr", 8.0, "Un"),
    (12, "#60", "🧀 Setor B: Laticínios/Frios", "Iogurte Natural", "--", "-", 2.0, "Un"),
    (13, "#9", "🧀 Setor B: Laticínios/Frios", "Leite Molico ou Desnatado", "--", "-", 14.0, "Lt"),
    (14, "#10", "🧀 Setor B: Laticínios/Frios", "Leite sem Lactose – OU ADES sem sabor", "--", "-", 12.0, "Lt"),

    # 🍞 SETOR C: PADARIA
    (15, "#67", "🍞 Setor C: Padaria", "Pão de forma milho ou leite", "--", "-", 2.0, "Sc"),
    (16, "#68", "🍞 Setor C: Padaria", "Pão de forma Integral 67%", "Wickbold", "-", 2.0, "Sc"),

    # ☕ SETOR D: FARELOS, CAFÉ
    (17, "#44", "☕ Setor D: Farelos, Café", "Aveia em flocos ou farinha", "Quaker", "-", 2.0, "Cx"),
    (18, "#35", "☕ Setor D: Farelos, Café", "Farinha Láctea", "Nestlé", "Genérica", 1.0, "Sc"),
    (19, "#39", "☕ Setor D: Farelos, Café", "Ovomaltine", "--", "-", 1.0, "Sc"),
    (20, "#71", "☕ Setor D: Farelos, Café", "Amido", "--", "-", 1.0, "Cx Pq"),
    (21, "#72", "☕ Setor D: Farelos, Café", "Leite em pó integral", "--", "-", 1.0, "Sc/Un"),
    (22, "#73", "☕ Setor D: Farelos, Café", "Café solúvel", "Matinal", "-", 1.0, "Sc/Un"),
    (23, "#33", "☕ Setor D: Farelos, Café", "Pó de café", "Evoluto Premium", "pct 0,5 Kg", 1.0, "Pct (0,5Kg)"),
    (24, "#34", "☕ Setor D: Farelos, Café", "Filtro de café - 102", "Melitta", "Pimpinela", 1.0, "Cx"),
    (25, "#36", "☕ Setor D: Farelos, Café", "Erva Mate", "Leão", "Gr", 1.0, "Cx"),

    # 🧄 SETOR E: HORTIFRUTI
    (26, "#69", "🧄 Setor E: Hortifruti", "Alho", "Cabeça", "-", 4.0, "Un"),

    # 🍪 SETOR F: DOCES, COMPLEMENTOS E BISCOITOS
    (27, "#74", "🍪 Setor F: Doces, Complementos e Biscoitos", "Fermento em pó", "Royal", "-", 1.0, "Pote"),
    (28, "#42", "🍪 Setor F: Doces, Complementos e Biscoitos", "Geleia - Uva - Pêssego - Morango - Damasco", "Ritter", "Predilecta", 3.0, "Un"),
    (29, "#43", "🍪 Setor F: Doces, Complementos e Biscoitos", "Goiabada Fina – Não cascão", "Predilecta", "-", 1.0, "Un"),
    (30, "#40", "🍪 Setor F: Doces, Complementos e Biscoitos", "Creme de Leite SEM LACTOSE", "--", "-", 1.0, "Cx"),
    (31, "#41", "🍪 Setor F: Doces, Complementos e Biscoitos", "Leite Condensado SEM LACTOSE", "--", "-", 1.0, "Cx"),
    (32, "#75", "🍪 Setor F: Doces, Complementos e Biscoitos", "Coco ralado", "Sococo", "-", 1.0, "Sc"),
    (33, "#37", "🍪 Setor F: Doces, Complementos e Biscoitos", "Biscoito Cristal", "Marilan", "(3X Econômico)", 1.0, "Pct"),
    (34, "#38", "🍪 Setor F: Doces, Complementos e Biscoitos", "Biscoito Maisena", "--", "-", 1.0, "Pct"),

    # 🪥 SETOR G: HIGIENE PESSOAL E PERFUMARIA
    (35, "#28", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Creme dental", "Sensodyne “Original”", "-", 1.0, "Tb"),
    (36, "#29", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Shampoo Seda roxo", "Individual", "Kit?", 1.0, "Un/Kit"),
    (37, "#30", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Condicionador Seda roxo", "Individual", "Kit?", 1.0, "Un"),
    (38, "#31", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Sabonete", "Protex", "Erva Doce", 8.0, "Un"),
    (39, "#32", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Cotonetes", "Johnson’s", "-", 1.0, "Cx"),
    (40, "#76", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Desodorante Sem perfume", "--", "-", 1.0, "Lt"),
    (41, "#77", "🪥 Setor G: Higiene Pessoal e Perfumaria", "Escova Dental", "--", "-", 1.0, "Un"),

    # 🧻 SETOR H: SACOS, PAPÉIS E DESCARTÁVEIS
    (42, "#78", "🧻 Setor H: Sacos, Papéis e Descartáveis", "Pastilhas Pato Purific", "Limão", "-", 1.0, "Cx"),
    (43, "#23", "🧻 Setor H: Sacos, Papéis e Descartáveis", "Rolo de Sacos", "29cm", "-", 1.0, "Rol"),
    (44, "#24", "🧻 Setor H: Sacos, Papéis e Descartáveis", "Papel Toalha", "Snob", "Social", 1.0, "Pct"),
    (45, "#25", "🧻 Setor H: Sacos, Papéis e Descartáveis", "Filme PVC - 30 mts - Sem picotes", "--", "-", 1.0, "Rolo"),
    (46, "#26", "🧻 Setor H: Sacos, Papéis e Descartáveis", "Papel Hig. – Personal VIP - Mimmo (Urso Bege c/Lilás)", "--", "-", 16.0, "Rolo"),

    # 🧼 SETOR I: LIMPEZA
    (47, "#13", "🧼 Setor I: Limpeza", "Cloro (não água sanitária)", "Pró Water", "-", 2.0, "Lt"),
    (48, "#14", "🧼 Setor I: Limpeza", "“Cheirinho” para chão", "Casa & Perfume", "-", 1.0, "Vd"),
    (49, "#16", "🧼 Setor I: Limpeza", "Sabão de coco neutro", "Ypê", "Palmeira", 1.0, "Un"),
    (50, "#17", "🧼 Setor I: Limpeza", "Desengordurante", "Veja", "Cif", 1.0, "Refil"),
    (51, "#18", "🧼 Setor I: Limpeza", "Sapólio Radium – Cloro pó", "--", "-", 1.0, "Un"),
    (52, "#27", "🧼 Setor I: Limpeza", "Álcool com Eucalipto", "--", "-", 1.0, "Lt"),
    (53, "#15", "🧼 Setor I: Limpeza", "Detergente - Transparente", "Ypê", "-", 3.0, "Un"),
    (54, "#11", "🧼 Setor I: Limpeza", "Sabão em pó AZUL", "Ypê", "-", 2.0, "Kg"),
    (55, "#12", "🧼 Setor I: Limpeza", "Amaciante Confort Concent.", "Bebê Hipoalergênico", "frasco 0,5 Lt", 1.0, "Frasco (0,5Lt)"),
    (56, "#19", "🧼 Setor I: Limpeza", "Bombril", "--", "-", 1.0, "Sq"),
    (57, "#20", "🧼 Setor I: Limpeza", "Pano de Pia - Amarelo", "3M", "-", 1.0, "Sq"),
    (58, "#21", "🧼 Setor I: Limpeza", "Esponja 3 ou 4 unidades", "Ypê", "3M", 1.0, "Sq"),
    (59, "#22", "🧼 Setor I: Limpeza", "Saco de Lixo", "50 Lts.", "100 Lts.", 1.0, "Pct"),

    # 🥫 SETOR J: MERCEARIA (LATAS E CONDIMENTOS)
    (60, "#66", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Colorau", "--", "-", 1.0, "Sq"),
    (61, "#45", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Maionese (com bico)", "Hellmann's", "Heinz (2 Pq / 1 Gr / Pote)", 1.0, "Un"),
    (62, "#46", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Atum – Água (Light) - Sólido", "Gomes da Costa", "-", 2.0, "Lt"),
    (63, "#47", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Óleo de soja", "--", "-", 1.0, "Lt"),
    (64, "#48", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Vinagre de Maçã", "--", "-", 1.0, "Lt"),
    (65, "#49", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Azeite de Oliva 0,2% ou 0,5%", "Andorinha", "Gallo", 1.0, "Vd"),
    (66, "#50", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Milho em lata", "Pramesa", "Predilecta", 2.0, "Lt"),
    (67, "#51", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Molho Shoyo Premium", "Sakura", "Ajinoshoyo", 1.0, "Pote"),
    (68, "#52", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Ketchup - Sem pimenta", "Pramesa", "Hellmann's", 1.0, "Un"),
    (69, "#53", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Mostarda", "Pramesa", "Hellmann's", 1.0, "Un"),
    (70, "#54", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Champignon", "Pramesa", "1 Pq", 1.0, "Vd"),
    (71, "#55", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Batata Palha – não fina", "Elma Chips", "Sacos GR", 3.0, "Sq"),
    (72, "#56", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Macarrão de Arroz", "Urbano", "-", 1.0, "Kg"),
    (73, "#57", "🥫 Setor J: Mercearia (Latas e Condimentos)", "Queijo ralado", "Vigor", "Président (100g)", 1.0, "Un (100g)"),

    # 🌾 SETOR K: MERCEARIA (GRÃOS)
    (74, "#1", "🌾 Setor K: Mercearia (Grãos)", "Arroz Branco", "Tio João", "Tio Mingote", 5.0, "Kg"),
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
        mes_atual = agora_br().strftime("%m %Y")
        executar_com_retry(
            sheet.append_rows,
            [
                ["Chave", "Valor"],
                ["mes_ano_ativo", mes_atual],
                ["data_compra_ativa", hoje_br().strftime("%d/%m/%Y")]
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
                str(ordem), cod, setor, prod, m1, m2,
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
            return sheet
    except gspread.WorksheetNotFound:
        sheet = criar_aba_no_inicio(sp, titulo_aba, linhas="160", colunas="18")

    # Se a aba do mês acabou de ser criada (ou estava vazia), popula com o Catálogo Oficial
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
            str(r["Marca1"]),
            str(r["Marca2"]),
            str(r["Unidade"]),
            "FALSE",  # Planejado (azul)
            formatar_num_planilha(qtd_p, 3),
            formatar_num_planilha(preco_ref, 2),
            "0,00",   # Subtotal Planejado
            "FALSE",  # Comprado (verde)
            formatar_num_planilha(qtd_p, 3),
            formatar_num_planilha(preco_ref, 2),
            "0,00",   # Subtotal Real
            ""        # ObsMes
        ])
    executar_com_retry(sheet.clear)
    executar_com_retry(sheet.append_rows, linhas_mes, value_input_option="USER_ENTERED")
    return sheet

@st.cache_data(ttl=180, show_spinner=False)
def ler_dados_aba_mes_cached(mes_ano_str, ano_str=None):
    sheet = obter_aba_mes(mes_ano_str, ano_str)
    vals = executar_com_retry(sheet.get_values)
    if len(vals) > 1:
        df = pd.DataFrame(vals[1:], columns=vals[0])
    else:
        df = pd.DataFrame(columns=COLUNAS_MES)
    for c in COLUNAS_MES:
        if c not in df.columns:
            df[c] = ""

    # Sincroniza novos produtos do Catálogo que ainda não estejam na aba do mês
    df_cat = carregar_df_catalogo(ano_str)
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
    return df

def carregar_df_mes(mes_ano_str, ano_str=None):
    df = ler_dados_aba_mes_cached(mes_ano_str, ano_str).copy()
    sp = get_spreadsheet_por_ano(ano_str)
    sheet = executar_com_retry(sp.worksheet, f"{mes_ano_str} Compras")
    return df, sheet

def salvar_df_mes(sheet, df_mes, ano_str=None, atualizar_preco_catalogo=True):
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

        linhas_salvar.append([
            str(int(safe_float(r["Ordem_num"]))),
            cod_str,
            str(r["Setor"]),
            str(r["Produto"]),
            str(r["Marca1"]),
            str(r["Marca2"]),
            str(r["Unidade"]),
            "TRUE" if plan_b else "FALSE",
            formatar_num_planilha(qtd_pl, 3),
            formatar_num_planilha(pr_pl, 2),
            formatar_num_planilha(sub_pl, 2),
            "TRUE" if comp_b else "FALSE",
            formatar_num_planilha(qtd_co, 3),
            formatar_num_planilha(pr_co, 2),
            formatar_num_planilha(sub_co, 2),
            str(r.get("ObsMes", "") or "")
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
    cabecalho = vals[0] if len(vals) > 0 else COLUNAS_RESUMO
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
        str(dados_resumo_dict.get("PagamentoFarmacia", "")),
        str(dados_resumo_dict.get("ObsFechamento", ""))
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
                        "PagamentoFarmacia": r[13] if len(r) > 13 else "",
                        "ObsFechamento": r[14] if len(r) > 14 else ""
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

# === CARREGAMENTO INICIAL DE CONFIGURAÇÃO DO MÊS ATIVO ===
ano_corrente = agora_br().strftime("%Y")
mes_corrente = agora_br().strftime("%m %Y")

try:
    config_dict = carregar_config_dict(ano_corrente)
except Exception as e:
    st.error(f"⚠️ Não foi possível conectar à planilha 'Compras {ano_corrente}'. Verifique se o e-mail do robô foi compartilhado na pasta 'mercado' e se o Secrets está configurado. Detalhe: {e}")
    st.stop()

mes_ano_ativo = config_dict.get("mes_ano_ativo", mes_corrente)
if not mes_ano_ativo or " " not in mes_ano_ativo:
    mes_ano_ativo = mes_corrente
ano_ativo = mes_ano_ativo.split(" ")[-1]

# === MENU LATERAL COM RECOLHIMENTO AUTOMÁTICO (PADRÃO LUZ & ÁGUA) ===
if "recolher_menu" not in st.session_state:
    st.session_state["recolher_menu"] = 0
if "fechar_menu_agora" not in st.session_state:
    st.session_state["fechar_menu_agora"] = False

def acionar_fechamento_menu():
    st.session_state["recolher_menu"] += 1
    st.session_state["fechar_menu_agora"] = True

st.sidebar.markdown("### 🛒Compras")

# Seletor rápido de Mês/Ano no topo da barra lateral
opcoes_meses = []
for a in range(2026, 2031):
    for m in range(1, 13):
        opcoes_meses.append(f"{m:02d} {a}")
if mes_ano_ativo not in opcoes_meses:
    opcoes_meses.insert(0, mes_ano_ativo)

novo_mes_sel = st.sidebar.selectbox(
    "📅 Mês/Ano Ativo:",
    opcoes_meses,
    index=opcoes_meses.index(mes_ano_ativo)
)
if novo_mes_sel != mes_ano_ativo:
    salvar_configs({"mes_ano_ativo": novo_mes_sel}, novo_mes_sel.split(" ")[-1])
    st.rerun()

menu = st.sidebar.radio(
    "Navegação",
    [
        "1. Planejamento (Casa)",
        "2. Conferência (Mercado)",
        "3. O que Faltou Comprar",
        "4. Tabela de Preços do Mês",
        "5. Relatório / Histórico",
        "6. Cadastro de Produtos"
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

# Carrega os dados do mês ativo
df_mes, sheet_mes = carregar_df_mes(mes_ano_ativo, ano_ativo)
totais_atuais = calcular_totais_df(df_mes)
resumo_salvo = obter_resumo_mes(mes_ano_ativo, ano_ativo)

# ==============================================================================
# GUIA 1: PLANEJAMENTO (CASA - PRÉ-COMPRA COM SELETOR AZUL)
# ==============================================================================
if menu == "1. Planejamento (Casa)":
    st.markdown('<h2 style="margin-bottom: 0px;">📝 1. Planejamento (Pré-Compra)</h2>', unsafe_allow_html=True)
    st.caption(f"📂 Planilha: **Compras {ano_ativo}** | Guia: **{mes_ano_ativo} Compras** | {VERSAO_APP}")

    if "msg_sucesso_plan" in st.session_state:
        st.success(st.session_state.pop("msg_sucesso_plan"))

    # Painel de Resumo Rápido no Topo
    c_top1, c_top2 = st.columns(2)
    with c_top1:
        st.markdown(f"""
        <div class="card-farmacia">
            <b>💊 1º Parada: Farmácia (Separado)</b><br>
            Itens marcados: <b>{totais_atuais['itens_plan_farm']}</b><br>
            Previsto Farmácia: <b>{formatar_moeda_br(totais_atuais['farm_plan'])}</b>
        </div>
        """, unsafe_allow_html=True)
    with c_top2:
        st.markdown(f"""
        <div class="card-azul">
            <b>🛒 2º Parada: Mercado (+ Extras)</b><br>
            Itens marcados (🔵): <b>{totais_atuais['itens_plan_merc']}</b><br>
            Previsto Mercado: <b>{formatar_moeda_br(totais_atuais['merc_plan'])}</b>
        </div>
        """, unsafe_allow_html=True)

    # Filtro opcional de setor para facilitar a revisão com a esposa
    opcoes_filtro_setor = ["📋 Todos os Setores (Circuito Completo)"] + SETORES_OFICIAIS
    filtro_setor = st.selectbox("Filtrar por Departamento / Setor:", opcoes_filtro_setor, index=0)

    with st.expander("➕ Adicionar Item Avulso Rápido para este Mês"):
        with st.form("form_item_avulso_mes", clear_on_submit=True):
            ca1, ca2 = st.columns(2)
            with ca1:
                av_prod = st.text_input("Nome do Produto Avulso")
                av_setor = st.selectbox("Setor no Circuito", SETORES_OFICIAIS, index=len(SETORES_OFICIAIS)-1)
                av_m1 = st.text_input("Marca 1 (ou deixe em branco p/ Sem marca)", value="--")
            with ca2:
                av_qtd = st.number_input("Quantidade", min_value=0.1, value=1.0, step=0.5, format="%.2f")
                av_unid = st.text_input("Unidade (Un, Kg, Pct, Cx, Lt...)", value="Un")
                av_preco = st.number_input("Preço Unit. Estimado (R$)", min_value=0.0, value=0.0, step=0.5, format="%.2f")
            if st.form_submit_button("Inserir Item Avulso já Marcado (🔵)", use_container_width=True):
                if av_prod.strip():
                    nova_ordem = int(df_mes["Ordem_num"].max() + 1) if not df_mes.empty else 84
                    novo_cod = f"#AV{nova_ordem}"
                    sub_av = arredondar_moeda(av_qtd * av_preco, 2)
                    executar_com_retry(
                        sheet_mes.append_row,
                        [
                            str(nova_ordem), novo_cod, av_setor, av_prod.strip(),
                            av_m1.strip() or "--", "Avulso do Mês", av_unid.strip() or "Un",
                            "TRUE", formatar_num_planilha(av_qtd, 3), formatar_num_planilha(av_preco, 2),
                            formatar_num_planilha(sub_av, 2),
                            "FALSE", formatar_num_planilha(av_qtd, 3), formatar_num_planilha(av_preco, 2),
                            "0,00", "Item avulso"
                        ],
                        value_input_option="USER_ENTERED"
                    )
                    limpar_cache_dados()
                    st.session_state["msg_sucesso_plan"] = f"✅ Item avulso '{av_prod}' adicionado e marcado para compra!"
                    st.rerun()

    st.info("💡 **Como usar em casa:** Marque o seletor **🔵 Comprar** nos itens que faltam na despensa e ajuste a **Qtd** ao lado se já tiver alguma unidade em casa. Ao final, clique em **Salvar Planejamento**.")

    setores_exibir = SETORES_OFICIAIS if filtro_setor.startswith("📋") else [filtro_setor]

    with st.form("form_planejamento_casa", clear_on_submit=False):
        valores_plan = {}
        for setor_nome in setores_exibir:
            df_setor = df_mes[df_mes["Setor"] == setor_nome]
            if df_setor.empty:
                continue
            st.markdown(f'<div class="setor-header">{setor_nome}</div>', unsafe_allow_html=True)

            for idx_row, row in df_setor.iterrows():
                cod = str(row["Codigo"])
                prod = str(row["Produto"])
                m1 = exibir_marca_limpa(row["Marca1"])
                m2 = str(row["Marca2"] or "").strip()
                m2_txt = f" | 2ª Opção/Obs: <b>{m2}</b>" if m2 not in ["", "-", "--", "nan"] else ""
                unid = str(row["Unidade"])
                plan_atual = bool(row["Planejado_bool"])
                qtd_atual = float(row["QtdPlanejada_num"]) if row["QtdPlanejada_num"] > 0 else 1.0
                pr_atual = float(row["PrecoUnit_num"])

                st.markdown(
                    f"**{prod}** <span class='item-sub'>({cod}) — Marca: <b>{m1}</b>{m2_txt} | Unid: <b>{unid}</b></span>",
                    unsafe_allow_html=True
                )
                c1, c2, c3 = st.columns([1.4, 1.1, 1.2])
                with c1:
                    escolha_az = st.radio(
                        f"Marcar {cod}",
                        options=["— Não", "🔵 Comprar"],
                        index=1 if plan_atual else 0,
                        horizontal=True,
                        label_visibility="collapsed",
                        key=f"pl_rad_{mes_ano_ativo}_{idx_row}"
                    )
                with c2:
                    nova_qtd = st.number_input(
                        f"Qtd ({unid})",
                        min_value=0.0,
                        value=qtd_atual,
                        step=0.5 if unid == "Kg" else 1.0,
                        format="%.2f",
                        key=f"pl_qtd_{mes_ano_ativo}_{idx_row}"
                    )
                with c3:
                    novo_pr = st.number_input(
                        "Preço Unit. (R$)",
                        min_value=0.0,
                        value=pr_atual,
                        step=0.50,
                        format="%.2f",
                        key=f"pl_pr_{mes_ano_ativo}_{idx_row}"
                    )
                valores_plan[idx_row] = (escolha_az == "🔵 Comprar", nova_qtd, novo_pr)
                st.markdown('<hr style="margin: 6px 0px; opacity: 0.2;">', unsafe_allow_html=True)

        st.markdown("### 💳 Planejamento de Pagamento para o Caixa (Mercado)")
        st.caption("Lembrete: pagar **1º em Dinheiro** no caixa e dividir o restante entre Débito ou Crédito (Bradesco, Mercado Pago ou Nubank):")

        din_prev = st.number_input(
            "💵 1º Dinheiro em Espécie a entregar no Caixa (R$)",
            min_value=0.0,
            value=safe_float(resumo_salvo.get("Dinheiro", 0.0)),
            step=10.0,
            format="%.2f"
        )
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            brad_deb = st.number_input("💳 Bradesco — DÉBITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("BradescoDebito", 0.0)), step=10.0, format="%.2f")
            mp_deb = st.number_input("💳 Mercado Pago — DÉBITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("MercadoPagoDebito", 0.0)), step=10.0, format="%.2f")
            nu_deb = st.number_input("💳 Nubank — DÉBITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("NubankDebito", 0.0)), step=10.0, format="%.2f")
        with col_b2:
            brad_cred = st.number_input("💳 Bradesco — CRÉDITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("BradescoCredito", 0.0)), step=10.0, format="%.2f")
            mp_cred = st.number_input("💳 Mercado Pago — CRÉDITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("MercadoPagoCredito", 0.0)), step=10.0, format="%.2f")
            nu_cred = st.number_input("💳 Nubank — CRÉDITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("NubankCredito", 0.0)), step=10.0, format="%.2f")

        pag_farm_str = st.selectbox(
            "💊 Forma de Pagamento na Farmácia (Antes do Mercado):",
            ["Dinheiro", "Bradesco - Débito", "Bradesco - Crédito", "Mercado Pago - Débito", "Mercado Pago - Crédito", "Nubank - Débito", "Nubank - Crédito"],
            index=0
        )

        btn_salvar_plan = st.form_submit_button("💾 Salvar Planejamento do Mês (🔵)", use_container_width=True)

    if btn_salvar_plan:
        for idx_r, (b_plan, q_pl, p_pl) in valores_plan.items():
            df_mes.at[idx_r, "Planejado_bool"] = b_plan
            df_mes.at[idx_r, "QtdPlanejada_num"] = q_pl
            df_mes.at[idx_r, "PrecoUnit_num"] = p_pl
            # Se ainda não foi comprado, já deixa a quantidade e preço real pré-alinhados com o planejado
            if not df_mes.at[idx_r, "Comprado_bool"]:
                df_mes.at[idx_r, "QtdComprada_num"] = q_pl
                df_mes.at[idx_r, "PrecoRealUnit_num"] = p_pl

        salvar_df_mes(sheet_mes, df_mes, ano_ativo, atualizar_preco_catalogo=True)
        novos_tot = calcular_totais_df(df_mes)
        salvar_resumo_pagamento(mes_ano_ativo, {
            "DataCompra": resumo_salvo.get("DataCompra") or hoje_br().strftime("%d/%m/%Y"),
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
            "ObsFechamento": resumo_salvo.get("ObsFechamento", "")
        }, ano_ativo)
        st.session_state["msg_sucesso_plan"] = f"✅ Planejamento de {mes_ano_ativo} salvo com sucesso! Previsto Mercado: {formatar_moeda_br(novos_tot['merc_plan'])} | Farmácia: {formatar_moeda_br(novos_tot['farm_plan'])}"
        st.rerun()

    # Simulador visual imediato do saldo após o Dinheiro
    saldo_apos_dinheiro = max(0.0, totais_atuais["merc_plan"] - safe_float(resumo_salvo.get("Dinheiro", 0.0)))
    st.markdown(f"""
    <div class="card-alerta-caixa">
        <b>📢 LEMBRETE P/ HORA DE PASSAR NO CAIXA (MERCADO):</b><br>
        1º Entregar em <b>💵 Dinheiro</b>: <b>{formatar_moeda_br(resumo_salvo.get('Dinheiro', 0.0))}</b><br>
        2º Saldo Restante p/ passar nos Cartões (Débito/Crédito): <b>{formatar_moeda_br(saldo_apos_dinheiro)}</b>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# GUIA 2: CONFERÊNCIA (NO MERCADO / RETORNO - COM TICK VERDE)
# ==============================================================================
elif menu == "2. Conferência (Mercado)":
    st.markdown('<h2 style="margin-bottom: 0px;">✅ 2. Conferência (Mercado / Retorno)</h2>', unsafe_allow_html=True)
    st.caption(f"Guia ativa: **{mes_ano_ativo} Compras** — Marque o Tick Verde (✅) e ajuste pesos/valores reais.")

    if "msg_sucesso_conf" in st.session_state:
        st.success(st.session_state.pop("msg_sucesso_conf"))

    c_res1, c_res2 = st.columns(2)
    with c_res1:
        st.markdown(f"""
        <div class="card-farmacia">
            <b>💊 Farmácia (1º Parada)</b><br>
            Comprados: <b>{totais_atuais['itens_comp_farm']} / {totais_atuais['itens_plan_farm']}</b><br>
            Gasto Real: <b>{formatar_moeda_br(totais_atuais['farm_real'])}</b> <span class="item-sub">(Prev: {formatar_moeda_br(totais_atuais['farm_plan'])})</span>
        </div>
        """, unsafe_allow_html=True)
    with c_res2:
        st.markdown(f"""
        <div class="card-verde">
            <b>🛒 Mercado no Carrinho (✅)</b><br>
            Comprados: <b>{totais_atuais['itens_comp_merc']} / {totais_atuais['itens_plan_merc']}</b><br>
            Gasto Real: <b>{formatar_moeda_br(totais_atuais['merc_real'])}</b> <span class="item-sub">(Prev: {formatar_moeda_br(totais_atuais['merc_plan'])})</span>
        </div>
        """, unsafe_allow_html=True)

    col_f1, col_f2 = st.columns([1.3, 1.7])
    with col_f1:
        apenas_planejados = st.checkbox("Mostrar só itens planejados (🔵)", value=True)
    with col_f2:
        setor_conf_sel = st.selectbox("Ir direto ao Setor:", ["📋 Circuito Completo (A → L)"] + SETORES_OFICIAIS, index=0)

    setores_conf = SETORES_OFICIAIS if setor_conf_sel.startswith("📋") else [setor_conf_sel]

    with st.form("form_conferencia_mercado", clear_on_submit=False):
        valores_conf = {}
        algum_item_exibido = False

        for setor_nome in setores_conf:
            df_setor = df_mes[df_mes["Setor"] == setor_nome]
            if apenas_planejados:
                df_setor = df_setor[df_setor["Planejado_bool"] | df_setor["Comprado_bool"]]
            if df_setor.empty:
                continue

            algum_item_exibido = True
            st.markdown(f'<div class="setor-header">{setor_nome}</div>', unsafe_allow_html=True)

            for idx_row, row in df_setor.iterrows():
                cod = str(row["Codigo"])
                prod = str(row["Produto"])
                m1 = exibir_marca_limpa(row["Marca1"])
                m2 = str(row["Marca2"] or "").strip()
                m2_txt = f" | {m2}" if m2 not in ["", "-", "--", "nan"] else ""
                unid = str(row["Unidade"])
                comp_atual = bool(row["Comprado_bool"])
                qtd_c_atual = float(row["QtdComprada_num"]) if row["QtdComprada_num"] > 0 else float(row["QtdPlanejada_num"])
                pr_c_atual = float(row["PrecoRealUnit_num"]) if row["PrecoRealUnit_num"] > 0 else float(row["PrecoUnit_num"])
                obs_atual = str(row.get("ObsMes", "") or "")

                badge_plan = "🔵 Planejado" if row["Planejado_bool"] else "⚪ Extra não planejado"
                st.markdown(
                    f"**{prod}** <span class='item-sub'>({cod} • {badge_plan}) — Marca: <b>{m1}{m2_txt}</b> | Planejado: <b>{formatar_qtd_br(row['QtdPlanejada_num'])} {unid}</b></span>",
                    unsafe_allow_html=True
                )

                cc1, cc2, cc3, cc4 = st.columns([1.1, 1.0, 1.1, 1.3])
                with cc1:
                    chk_verde = st.checkbox(
                        "✅ Comprado",
                        value=comp_atual,
                        key=f"cf_chk_{mes_ano_ativo}_{idx_row}"
                    )
                with cc2:
                    qtd_real = st.number_input(
                        f"Qtd/Peso ({unid})",
                        min_value=0.0,
                        value=qtd_c_atual,
                        step=0.1 if unid == "Kg" else 1.0,
                        format="%.2f",
                        key=f"cf_qtd_{mes_ano_ativo}_{idx_row}"
                    )
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

                valores_conf[idx_row] = (chk_verde, qtd_real, pr_real, obs_in)
                st.markdown('<hr style="margin: 6px 0px; opacity: 0.2;">', unsafe_allow_html=True)

        if not algum_item_exibido:
            st.warning("Nenhum item planejado para este filtro. Desmarque a opção 'Mostrar só itens planejados' acima ou vá na guia 1. Planejamento.")

        st.markdown("### 🧾 Fechamento do Caixa (Como foi pago)")
        data_c_padrao = hoje_br()
        if resumo_salvo.get("DataCompra"):
            try:
                data_c_padrao = datetime.strptime(resumo_salvo["DataCompra"], "%d/%m/%Y").date()
            except Exception:
                pass

        dt_compra_in = st.date_input("Data Real da Compra", value=data_c_padrao, format="DD/MM/YYYY")
        din_real = st.number_input("💵 1º Pago em DINHEIRO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("Dinheiro", 0.0)), step=10.0, format="%.2f")

        cp1, cp2 = st.columns(2)
        with cp1:
            b_deb_r = st.number_input("💳 Bradesco — DÉBITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("BradescoDebito", 0.0)), step=10.0, format="%.2f")
            m_deb_r = st.number_input("💳 Mercado Pago — DÉBITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("MercadoPagoDebito", 0.0)), step=10.0, format="%.2f")
            n_deb_r = st.number_input("💳 Nubank — DÉBITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("NubankDebito", 0.0)), step=10.0, format="%.2f")
        with cp2:
            b_cred_r = st.number_input("💳 Bradesco — CRÉDITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("BradescoCredito", 0.0)), step=10.0, format="%.2f")
            m_cred_r = st.number_input("💳 Mercado Pago — CRÉDITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("MercadoPagoCredito", 0.0)), step=10.0, format="%.2f")
            n_cred_r = st.number_input("💳 Nubank — CRÉDITO (R$)", min_value=0.0, value=safe_float(resumo_salvo.get("NubankCredito", 0.0)), step=10.0, format="%.2f")

        opcoes_pag_farm = ["Dinheiro", "Bradesco - Débito", "Bradesco - Crédito", "Mercado Pago - Débito", "Mercado Pago - Crédito", "Nubank - Débito", "Nubank - Crédito"]
        idx_pf = opcoes_pag_farm.index(resumo_salvo.get("PagamentoFarmacia")) if resumo_salvo.get("PagamentoFarmacia") in opcoes_pag_farm else 0
        pag_farm_r = st.selectbox("💊 Pago na Farmácia com:", opcoes_pag_farm, index=idx_pf)
        obs_fech_r = st.text_input("Observação geral da compra do mês:", value=str(resumo_salvo.get("ObsFechamento", "")))

        btn_salvar_conf = st.form_submit_button("✅ Salvar Conferência e Fechamento", use_container_width=True)

    if btn_salvar_conf:
        for idx_r, (chk_v, q_r, p_r, ob_r) in valores_conf.items():
            df_mes.at[idx_r, "Comprado_bool"] = chk_v
            df_mes.at[idx_r, "QtdComprada_num"] = q_r
            df_mes.at[idx_r, "PrecoRealUnit_num"] = p_r
            if p_r > 0:
                df_mes.at[idx_r, "PrecoUnit_num"] = p_r
            df_mes.at[idx_r, "ObsMes"] = ob_r

        salvar_df_mes(sheet_mes, df_mes, ano_ativo, atualizar_preco_catalogo=True)
        novos_tot = calcular_totais_df(df_mes)
        salvar_resumo_pagamento(mes_ano_ativo, {
            "DataCompra": dt_compra_in.strftime("%d/%m/%Y"),
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
            "ObsFechamento": obs_fech_r
        }, ano_ativo)
        st.session_state["msg_sucesso_conf"] = f"✅ Conferência salva! Total Real Mercado: {formatar_moeda_br(novos_tot['merc_real'])} | Farmácia: {formatar_moeda_br(novos_tot['farm_real'])}"
        st.rerun()

    # Conferência matemática entre Soma dos Pagamentos e Total do Carrinho do Mercado
    soma_pagamentos_merc = (
        safe_float(resumo_salvo.get("Dinheiro", 0.0)) +
        safe_float(resumo_salvo.get("BradescoDebito", 0.0)) +
        safe_float(resumo_salvo.get("BradescoCredito", 0.0)) +
        safe_float(resumo_salvo.get("MercadoPagoDebito", 0.0)) +
        safe_float(resumo_salvo.get("MercadoPagoCredito", 0.0)) +
        safe_float(resumo_salvo.get("NubankDebito", 0.0)) +
        safe_float(resumo_salvo.get("NubankCredito", 0.0))
    )
    alvo_caixa = totais_atuais["merc_real"] if totais_atuais["merc_real"] > 0 else totais_atuais["merc_plan"]
    falta_alocar = arredondar_moeda(alvo_caixa - soma_pagamentos_merc, 2)
    saldo_pos_din = max(0.0, alvo_caixa - safe_float(resumo_salvo.get("Dinheiro", 0.0)))

    st.markdown(f"""
    <div class="card-alerta-caixa">
        <b>📢 RESUMO DE CAIXA (MERCADO):</b><br>
        • Valor do Mercado: <b>{formatar_moeda_br(alvo_caixa)}</b><br>
        • 1º Pagamento em <b>💵 Dinheiro</b>: <b>{formatar_moeda_br(resumo_salvo.get('Dinheiro', 0.0))}</b> → <b>Resta p/ Cartões: {formatar_moeda_br(saldo_pos_din)}</b><br>
        • Soma total lançada (Dinheiro + Cartões): <b>{formatar_moeda_br(soma_pagamentos_merc)}</b>
        {"✅ <i>(Pagamento 100% fechado!)</i>" if abs(falta_alocar) < 0.05 else f"⚠️ <i>(Diferença p/ alocar nos cartões: {formatar_moeda_br(falta_alocar)})</i>"}
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# GUIA 3: O QUE FALTOU COMPRAR (PENDÊNCIAS DO MÊS)
# ==============================================================================
elif menu == "3. O que Faltou Comprar":
    st.markdown('<h2 style="margin-bottom: 0px;">⚠️ 3. O que Faltou Comprar</h2>', unsafe_allow_html=True)
    st.caption(f"Itens marcados no planejamento (🔵) de **{mes_ano_ativo}** que não foram comprados ou vieram em quantidade menor.")

    if "msg_faltou" in st.session_state:
        st.success(st.session_state.pop("msg_faltou"))

    # Filtra itens planejados que não foram marcados como comprados OU cuja quantidade comprada foi menor que a planejada
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
                    m1 = exibir_marca_limpa(rf["Marca1"])
                    pr_base = rf["PrecoRealUnit_num"] if rf["PrecoRealUnit_num"] > 0 else rf["PrecoUnit_num"]
                    chk_f = st.checkbox(
                        f"✅ Dar baixa: **{rf['Produto']}** ({m1}) — Faltam **{formatar_qtd_br(qtd_falta)} {rf['Unidade']}** | Estimado: **{formatar_moeda_br(custo_falta)}** (Unit: {formatar_moeda_br(pr_base)})",
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
# GUIA 4: TABELA DE PREÇOS DO MÊS (ATUALIZAÇÃO RÁPIDA DE VALORES)
# ==============================================================================
elif menu == "4. Tabela de Preços do Mês":
    st.markdown('<h2 style="margin-bottom: 0px;">💲 4. Tabela de Preços do Mês</h2>', unsafe_allow_html=True)
    st.caption(f"Insira ou atualize rapidamente os preços unitários de **{mes_ano_ativo}** para calcular a previsão exata da compra.")

    if "msg_precos" in st.session_state:
        st.success(st.session_state.pop("msg_precos"))

    # Botão para puxar preços da guia Catalogo (últimos preços praticados)
    if st.button("📥 Puxar Últimos Preços Registrados no Catálogo Geral", use_container_width=True):
        df_cat_ref = carregar_df_catalogo(ano_ativo)
        mapa_cat = {str(r["Codigo"]).strip(): safe_float(r["PrecoRef_num"]) for _, r in df_cat_ref.iterrows()}
        for idx_r, r in df_mes.iterrows():
            cod_r = str(r["Codigo"]).strip()
            if cod_r in mapa_cat and mapa_cat[cod_r] > 0:
                df_mes.at[idx_r, "PrecoUnit_num"] = mapa_cat[cod_r]
                if df_mes.at[idx_r, "PrecoRealUnit_num"] <= 0:
                    df_mes.at[idx_r, "PrecoRealUnit_num"] = mapa_cat[cod_r]
        salvar_df_mes(sheet_mes, df_mes, ano_ativo, atualizar_preco_catalogo=False)
        st.session_state["msg_precos"] = "✅ Preços sincronizados com a base de referência!"
        st.rerun()

    setor_pr_sel = st.selectbox("Filtrar Setor para digitar preços:", ["📋 Todos os Setores"] + SETORES_OFICIAIS, index=0)
    df_pr_view = df_mes if setor_pr_sel.startswith("📋") else df_mes[df_mes["Setor"] == setor_pr_sel]

    st.caption("💡 Você pode digitar o preço inteiro (ex: `5`), com vírgula (ex: `35,00`) ou com ponto (ex: `35.00`).")

    df_editor_pr = pd.DataFrame({
        "idx_orig": df_pr_view.index,
        "Código": df_pr_view["Codigo"],
        "Setor": df_pr_view["Setor"],
        "Produto": df_pr_view["Produto"],
        "Marca 1": df_pr_view["Marca1"].apply(exibir_marca_limpa),
        "Unid.": df_pr_view["Unidade"],
        "Qtd Padrão": df_pr_view["QtdPlanejada_num"].apply(formatar_qtd_br),
        "Preço Unit. (R$)": df_pr_view["PrecoUnit_num"].apply(lambda v: f"{safe_float(v):.2f}".replace(".", ","))
    })

    editado_pr = st.data_editor(
        df_editor_pr,
        hide_index=True,
        use_container_width=True,
        disabled=["idx_orig", "Código", "Setor", "Produto", "Marca 1", "Unid.", "Qtd Padrão"],
        column_config={
            "idx_orig": None,
            "Preço Unit. (R$)": st.column_config.TextColumn("Preço Unit. (R$)", help="Digite ex: 5 ou 35,00 ou 35.50")
        }
    )

    if st.button("💾 Salvar Tabela de Preços do Mês", type="primary", use_container_width=True):
        for _, r_ed in editado_pr.iterrows():
            idx_o = int(r_ed["idx_orig"])
            novo_p = safe_float(r_ed["Preço Unit. (R$)"])
            df_mes.at[idx_o, "PrecoUnit_num"] = novo_p
            if not df_mes.at[idx_o, "Comprado_bool"] or df_mes.at[idx_o, "PrecoRealUnit_num"] <= 0:
                df_mes.at[idx_o, "PrecoRealUnit_num"] = novo_p
        salvar_df_mes(sheet_mes, df_mes, ano_ativo, atualizar_preco_catalogo=True)
        st.session_state["msg_precos"] = f"✅ Preços de {mes_ano_ativo} atualizados com sucesso!"
        st.rerun()

# ==============================================================================
# GUIA 5: RELATÓRIO / COFRE HISTÓRICO (COMPARATIVO ENTRE MESES E CARTÕES)
# ==============================================================================
elif menu == "5. Relatório / Histórico":
    st.markdown('<h2 style="margin-bottom: 0px;">📊 5. Relatório / Cofre Histórico</h2>', unsafe_allow_html=True)
    st.caption("Comparativo mensal de gastos (Mercado vs. Farmácia) e divisão por forma de pagamento (Dinheiro e Cartões Débito/Crédito).")

    ano_hist_sel = st.selectbox("Consultar Planilha Anual:", [str(a) for a in range(2026, 2031)], index=0)
    try:
        sh_res_h = obter_aba_resumo_mensal(ano_hist_sel)
        vals_rh = executar_com_retry(sh_res_h.get_values)
    except Exception:
        vals_rh = []

    if len(vals_rh) <= 1:
        st.info(f"Ainda não há resumos mensais salvos em Compras {ano_hist_sel}. Salve o Planejamento ou a Conferência para alimentar o histórico!")
    else:
        df_rh = pd.DataFrame(vals_rh[1:], columns=vals_rh[0])
        st.markdown(f"### 📅 Resumo Mensal — Compras {ano_hist_sel}")

        linhas_md = [
            "| Mês/Ano | Data | 🛒 Mercado (Prev.) | 🛒 Mercado (Real) | 💊 Farmácia (Real) | 💵 Dinheiro | 💳 Total Cartões |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]
        for _, r in df_rh.iterrows():
            m_ano = str(r.get("MesAno", ""))
            dt_c = str(r.get("DataCompra", "-"))
            mp = safe_float(r.get("TotalMercadoPlanejado", 0.0))
            mr = safe_float(r.get("TotalMercadoReal", 0.0))
            fr = safe_float(r.get("TotalFarmaciaReal", 0.0))
            din = safe_float(r.get("Dinheiro", 0.0))
            cartoes = (
                safe_float(r.get("BradescoDebito", 0.0)) +
                safe_float(r.get("BradescoCredito", 0.0)) +
                safe_float(r.get("MercadoPagoDebito", 0.0)) +
                safe_float(r.get("MercadoPagoCredito", 0.0)) +
                safe_float(r.get("NubankDebito", 0.0)) +
                safe_float(r.get("NubankCredito", 0.0))
            )
            linhas_md.append(
                f"| **{m_ano}** | {dt_c} | {formatar_moeda_br(mp)} | **{formatar_moeda_br(mr)}** | {formatar_moeda_br(fr)} | {formatar_moeda_br(din)} | {formatar_moeda_br(cartoes)} |"
            )
        st.markdown("\n".join(linhas_md))

        st.markdown("### 💳 Detalhamento por Cartão (Débito vs. Crédito)")
        meses_disp = df_rh["MesAno"].astype(str).tolist()
        mes_det_sel = st.selectbox("Ver abertura de pagamentos do mês:", meses_disp, index=len(meses_disp)-1)
        row_det = df_rh[df_rh["MesAno"] == mes_det_sel].iloc[-1]

        st.markdown(f"""
        | Forma de Pagamento (Mercado) | Débito | Crédito | Subtotal |
        | :--- | :--- | :--- | :--- |
        | **💵 Dinheiro (1º no Caixa)** | - | - | **{formatar_moeda_br(row_det.get('Dinheiro', 0.0))}** |
        | **🏦 Bradesco** | {formatar_moeda_br(row_det.get('BradescoDebito', 0.0))} | {formatar_moeda_br(row_det.get('BradescoCredito', 0.0))} | **{formatar_moeda_br(safe_float(row_det.get('BradescoDebito', 0.0)) + safe_float(row_det.get('BradescoCredito', 0.0)))}** |
        | **🤝 Mercado Pago** | {formatar_moeda_br(row_det.get('MercadoPagoDebito', 0.0))} | {formatar_moeda_br(row_det.get('MercadoPagoCredito', 0.0))} | **{formatar_moeda_br(safe_float(row_det.get('MercadoPagoDebito', 0.0)) + safe_float(row_det.get('MercadoPagoCredito', 0.0)))}** |
        | **🟣 Nubank** | {formatar_moeda_br(row_det.get('NubankDebito', 0.0))} | {formatar_moeda_br(row_det.get('NubankCredito', 0.0))} | **{formatar_moeda_br(safe_float(row_det.get('NubankDebito', 0.0)) + safe_float(row_det.get('NubankCredito', 0.0)))}** |
        """)
        st.caption(f"💊 **Farmácia ({mes_det_sel}):** {formatar_moeda_br(row_det.get('TotalFarmaciaReal', 0.0))} (Pago via: {row_det.get('PagamentoFarmacia', '-')}) | 📝 **Obs:** {row_det.get('ObsFechamento', '-')}")

# ==============================================================================
# GUIA 6: CADASTRO DE PRODUTOS E DEPARTAMENTOS (CATÁLOGO FIXO)
# ==============================================================================
elif menu == "6. Cadastro de Produtos":
    st.markdown('<h2 style="margin-bottom: 0px;">🗂️ 6. Cadastro de Produtos e Circuito</h2>', unsafe_allow_html=True)
    st.caption("Adicione novos produtos fixos escolhendo em qual Departamento/Setor do seu circuito eles entram, ou edite marcas, quantidades e unidades.")

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
                prox_num = int(df_cat_atual["Ordem_num"].max() + 1) if not df_cat_atual.empty else 84
                np_cod = st.text_input("Código do Item:", value=f"#{prox_num}")
                np_qtd = st.number_input("Quantidade Padrão Mensal:", min_value=0.1, value=1.0, step=0.5, format="%.2f")
                np_unid = st.selectbox(
                    "Unidade / Métrica:",
                    ["Un", "Kg", "Lt", "Pct", "Pct (0,5Kg)", "Cx", "Cx Pq", "Sc", "Sc/Un", "Vd", "Refil", "Rolo", "Rol", "Sq", "Tb", "Pote", "Bifes", "Cx (30 Comp)", "Frasco (0,5Lt)", "Un (100g)", "Un/Kit"]
                )
                np_preco = st.number_input("Preço Unitário de Referência (R$):", min_value=0.0, value=0.0, step=0.50, format="%.2f")

            if st.form_submit_button("➕ Salvar Novo Produto no Catálogo e no Mês Ativo", use_container_width=True):
                if not np_prod.strip():
                    st.warning("⚠️ Informe o nome do produto.")
                else:
                    sh_cat = obter_aba_catalogo(ano_ativo)
                    executar_com_retry(
                        sh_cat.append_row,
                        [
                            str(prox_num),
                            np_cod.strip(),
                            np_setor,
                            np_prod.strip(),
                            np_m1.strip() or "--",
                            np_m2.strip() or "-",
                            formatar_num_planilha(np_qtd, 3),
                            np_unid,
                            formatar_num_planilha(np_preco, 2),
                            "TRUE"
                        ],
                        value_input_option="USER_ENTERED"
                    )
                    limpar_cache_dados()
                    st.session_state["msg_cat"] = f"✅ Produto '{np_prod}' cadastrado no {np_setor}!"
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
            "Ordem": st.column_config.NumberColumn("Ordem", min_value=1, step=1),
            "Setor": st.column_config.SelectboxColumn("Setor", options=SETORES_OFICIAIS, required=True),
            "QtdPadrao": st.column_config.NumberColumn("Qtd Padrão", min_value=0.1, step=0.5, format="%.2f"),
            "PrecoRef": st.column_config.NumberColumn("Preço Ref (R$)", min_value=0.0, step=0.10, format="R$ %.2f"),
            "Ativo": st.column_config.CheckboxColumn("Ativo?")
        }
    )

    if st.button("💾 Salvar Alterações do Catálogo", type="primary", use_container_width=True):
        sh_cat = obter_aba_catalogo(ano_ativo)
        linhas_c = [COLUNAS_CATALOGO]
        cat_ord = cat_editado.sort_values("Ordem").reset_index(drop=True)
        for idx_c, rc in cat_ord.iterrows():
            if not str(rc.get("Produto", "")).strip():
                continue
            linhas_c.append([
                str(int(safe_float(rc.get("Ordem", idx_c + 1)))),
                str(rc.get("Codigo", f"#{idx_c+1}")),
                str(rc.get("Setor", SETORES_OFICIAIS[-1])),
                str(rc.get("Produto", "")).strip(),
                str(rc.get("Marca1", "--")).strip() or "--",
                str(rc.get("Marca2", "-")).strip() or "-",
                formatar_num_planilha(safe_float(rc.get("QtdPadrao", 1.0)), 3),
                str(rc.get("Unidade", "Un")).strip() or "Un",
                formatar_num_planilha(safe_float(rc.get("PrecoRef", 0.0)), 2),
                "TRUE" if safe_bool(rc.get("Ativo", True)) else "FALSE"
            ])
        executar_com_retry(sh_cat.clear)
        executar_com_retry(sh_cat.append_rows, linhas_c, value_input_option="USER_ENTERED")
        limpar_cache_dados()
        st.session_state["msg_cat"] = "✅ Catálogo de produtos atualizado com sucesso!"
        st.rerun()
# === FIM DO CÓDIGO - VERSÃO v.1.1 ===

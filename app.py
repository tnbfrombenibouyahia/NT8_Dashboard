import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta, date
import calendar
import datetime as dt
import yfinance as yf
import plotly.graph_objects as go
import numpy as np

import streamlit_authenticator as stauth

# Vos modules perso
from data_cleaner import load_and_clean_csv, update_historical_data
from gdrive_backup import get_drive_service_from_secrets, restore_user_data, backup_user_data
from utils_visuals import (
    plot_equity_curve,
    plot_drawdown_curve,
    plot_gain_loss_pie,
    plot_asset_distribution,
    plot_avg_duration_per_day,
    plot_return_vs_duration,
    compute_stats_dict,
    plot_pnl_by_hour,
    plot_pnl_by_day_of_week,
    plot_daily_pnl,
    plot_daily_drawdown,
    plot_histogram_mae_mfe_etd,
    plot_scatter_mfe_vs_profit,
    plot_pct_mfe_captured,
    plot_pct_mae_vs_etd,
    plot_scatter_mfe_captured,
    plot_heatmap_mfe_mae,
    plot_mfe_vs_time,
)


# ─────────────────────────────────────────────────────────────────────────
# Configuration de la page Streamlit
# ─────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🥷 Trading Dashboard",
    layout="wide",
    page_icon="🥷",
    initial_sidebar_state="expanded"
)


# ─────────────────────────────────────────────────────────────────────────
# Liste d'utilisateurs de test : noms, emails (usernames) et mots de passe hashés
# ─────────────────────────────────────────────────────────────────────────
names = ["Théo Naïm BENHELLAL", "Alexis DURIN"]
usernames = ["theonaimben@gmail.com", "alexisdurin@gmail.com"]

hashed_passwords = [
    '$2b$12$diwoxjm5v8dciC0/UUJXLuTPPFx5UrfiwhhgQwNVZYi4lZTwQJI0O',
    '$2b$12$/DFXDjyc2sEGqPXCweJqduJcxE6tSlvk1MnAYVIJErU1/ELgM7b9C'
]

credentials = {
    "usernames": {
        "theonaimben@gmail.com": {
            "name": "Théo Naïm BENHELLAL",
            "password": "$2b$12$diwoxjm5v8dciC0/UUJXLuTPPFx5UrfiwhhgQwNVZYi4lZTwQJI0O"
        },
        "durinalexis@gmail.com": {
            "name": "Alexis DURIN",
            "password": "$2b$12$83LWaR64YJwamdbNj/rE8u1V9EES1tnuIulQEKfneQl95ILZStMy6"
        }
    }
}


# ─────────────────────────────────────────────────────────────────────────
# Authentification avec streamlit-authenticator
# ─────────────────────────────────────────────────────────────────────────
authenticator = stauth.Authenticate(
    credentials,
    "dashboard_cookie",     # nom du cookie
    "abcdef",               # clé de hachage
    cookie_expiry_days=7    # durée de validité (jours)
)

login_result = authenticator.login("Login", "main")

try:
    name, authentication_status, username = login_result
except TypeError:
    name = authentication_status = username = None

# ─────────────────────────────────────────────────────────────────────────
# Gestion de l’état de connexion
# ─────────────────────────────────────────────────────────────────────────
if authentication_status is False:
    st.error("Nom d’utilisateur ou mot de passe invalide ❌")
    st.stop()

elif authentication_status is None:
    st.warning("Veuillez entrer vos identifiants 🔐")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────
# Si on arrive ici, l’utilisateur est authentifié
# ─────────────────────────────────────────────────────────────────────────
authenticator.logout("🚪 Se déconnecter", "sidebar")
st.sidebar.success(f"Connecté en tant que {name}")
st.success(f"Bienvenue {name} 👋")

# ─────────────────────────────────────────────────────────────────────────
# 🔁 Restauration automatique Google Drive si données manquantes
# ─────────────────────────────────────────────────────────────────────────
user_data_dir = os.path.join("data", username)  
data_file = os.path.join(user_data_dir, "trades_historique.csv")
journal_file = os.path.join(user_data_dir, "journal_notes.json")

try:
    drive_service = get_drive_service_from_secrets()
    restore_user_data(
        drive_service=drive_service,
        local_data_dir=user_data_dir,
        backup_folder_name="Streamlit_Backup",
        username=username
    )
    
    print("✅ Restauration automatique terminée.")
except Exception as e:
    print(f"❌ Erreur de restauration automatique : {e}")

# ─────────────────────────────────────────────────────────────────────────
# Définition des chemins de fichiers pour CET utilisateur
# ─────────────────────────────────────────────────────────────────────────
user_data_dir = os.path.join("data", username)  
os.makedirs(user_data_dir, exist_ok=True)

data_file = os.path.join(user_data_dir, "trades_historique.csv")
journal_file = os.path.join(user_data_dir, "journal_notes.json")

# Initialisation si inexistant
if not os.path.exists(data_file):
    pd.DataFrame(columns=[
        "Entry time", "Exit time", "Instrument", "Market pos.",
        "Entry price", "Exit price", "Qty", "Profit",
        "MAE", "MFE", "ETD"
    ]).to_csv(data_file, index=False)

if not os.path.exists(journal_file):
    with open(journal_file, "w") as f:
        json.dump({}, f)

# ─────────────────────────────────────────────────────────────────────────
# Lecture de l'historique
# ─────────────────────────────────────────────────────────────────────────
try:
    if os.path.exists(data_file):
        df_histo = pd.read_csv(data_file, parse_dates=["Entry time", "Exit time"])
        df_histo = df_histo[pd.notnull(df_histo["Entry time"])]
        df_histo["Instrument"] = df_histo["Instrument"].str.extract(r"^([A-Z]+)")
    else:
        st.warning("Aucun fichier d'historique trouvé pour cet utilisateur.")
        st.stop()
except Exception as e:
    st.error(f"Erreur lors du chargement du fichier historique : {e}")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────
# UI Style global
# ─────────────────────────────────────────────────────────────────────────
st.markdown("""
    <style>
        html, body, [class*="css"]  {
            font-family: 'Inter', sans-serif;
        }
        .block-container {
            padding-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🥷 Dashboard NinjaTrader")

# ─────────────────────────────────────────────────────────────────────────
# Section Filtres
# ─────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.header("👀 Filtres")
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    instruments = df_histo["Instrument"].unique().tolist()
    instrument = st.selectbox("🇺🇸 Instrument", ["Tous"] + instruments)

with col_f2:
    directions = df_histo["Market pos."].unique().tolist()
    direction = st.selectbox("📌 Positions", ["Tous"] + directions)

with col_f3:
    if not df_histo["Entry time"].dropna().empty:
        default_start = pd.to_datetime(df_histo["Entry time"]).min().date()
        default_end = pd.to_datetime(df_histo["Entry time"]).max().date()
    else:
        default_start = date.today() - timedelta(days=30)
        default_end = date.today()

    date_range = st.date_input("📅 Période", (default_start, default_end))

# Application des filtres
df_filtered = df_histo.copy()

if instrument != "Tous":
    df_filtered = df_filtered[df_filtered["Instrument"] == instrument]
if direction != "Tous":
    df_filtered = df_filtered[df_filtered["Market pos."] == direction]

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
elif isinstance(date_range, date):
    start_date = end_date = date_range
else:
    start_date = df_histo["Entry time"].min().date()
    end_date = df_histo["Entry time"].max().date()

if not df_filtered.empty and pd.api.types.is_datetime64_any_dtype(df_filtered["Entry time"]):
    df_filtered = df_filtered[
        (df_filtered["Entry time"].dt.date >= start_date) &
        (df_filtered["Entry time"].dt.date <= end_date)
    ]

# ─────────────────────────────────────────────────────────────────────────
# Sidebar : Upload CSV
# ─────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 📂 Import Zone")
uploaded_file = st.sidebar.file_uploader("", type=["csv"])

if uploaded_file:
    # Chargement et nettoyage
    df_new = load_and_clean_csv(uploaded_file)

    # Fusion avec l'historique propre à l'utilisateur
    user_csv_path = os.path.join(user_data_dir, "trades_historique.csv")
    df_combined, new_count = update_historical_data(df_new, user_csv_path)

    # Logs console (utile sur Streamlit Cloud)
    print(f"[UPLOAD] ✅ Fichier importé par : {username}")
    print(f"[UPLOAD] ➕ {new_count} nouveaux trades ajoutés.")
    print(f"[UPLOAD] 📁 Chemin : {user_csv_path}")

    # Message utilisateur
    st.sidebar.success(f"{new_count} nouveaux trades ajoutés à l'historique. Recharge la page pour voir les changements.")
    st.sidebar.info(f"📁 Données sauvegardées dans : `{user_csv_path}`")

# ─────────────────────────────────────────────────────────────────────────
# Sidebar : Journal de séance
# ─────────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("## 📓 Journal de séance")

image_dir = os.path.join(user_data_dir, "journal_images")
os.makedirs(image_dir, exist_ok=True)

with open(journal_file, "r") as f:
    journal = json.load(f)

# Convertir si ancien format (v = string)
for k, v in journal.items():
    if isinstance(v, str):
        journal[k] = {"text": v, "images": []}

aujourd_hui = pd.to_datetime("today").normalize()
cle_du_jour = str(aujourd_hui)

if cle_du_jour not in journal:
    st.sidebar.warning("📝 Tu n’as pas encore rempli ta note de trading aujourd’hui !")

note = st.sidebar.text_area(
    "✍️ Ta note du jour",
    value=journal.get(cle_du_jour, {}).get("text", ""),
    height=150
)
images = st.sidebar.file_uploader("📸 Ajouter des captures", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if st.sidebar.button("💾 Sauvegarder ma note", use_container_width=True):
    saved_images = []
    for img in images:
        img_path = os.path.join(image_dir, f"{cle_du_jour}_{img.name}")
        with open(img_path, "wb") as f:
            f.write(img.getbuffer())
        saved_images.append(img_path)

    journal[cle_du_jour] = {"text": note, "images": saved_images}
    with open(journal_file, "w") as f:
        json.dump(journal, f)
    st.sidebar.success("Note enregistrée avec succès 🎉")

        # Sauvegarde automatique sur Google Drive
    try:
        from gdrive_backup import get_drive_service, backup_user_data
        json_key_path = "dashboarding-tn8-7a67de160a56.json"
        drive_service = get_drive_service(json_key_path)
        backup_user_data(
            drive_service=drive_service,
            local_data_dir=user_data_dir,
            backup_folder_name="Streamlit_Backup",
            json_key_path=json_key_path,
            username=username
        )
        st.sidebar.success("🪣 Sauvegarde Drive terminée ✅")
    except Exception as e:
        st.sidebar.error(f"❌ Erreur de sauvegarde Drive : {e}")


# ─────────────────────────────────────────────────────────────────────────
# Calcul de colonnes supplémentaires
# ─────────────────────────────────────────────────────────────────────────
if not df_filtered.empty:
    df_filtered["Durée (min)"] = (
        df_filtered["Exit time"] - df_filtered["Entry time"]
    ).dt.total_seconds() / 60
    df_filtered["Rendement (%)"] = (
        df_filtered["Profit"] / (df_filtered["Entry price"] * df_filtered["Qty"])
    ) * 100

# ─────────────────────────────────────────────────────────────────────────
# Profit / Risk Zone
# ─────────────────────────────────────────────────────────────────────────
st.markdown("## 🎰 Profit / Risk Zone")
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(plot_equity_curve(df_filtered), use_container_width=True, key="equity")

with col2:
    st.plotly_chart(plot_drawdown_curve(df_filtered), use_container_width=True, key='drawdown')

col_daily1, col_daily2 = st.columns(2)
with col_daily1:
    st.plotly_chart(plot_daily_pnl(df_filtered), use_container_width=True, key="daily_pnl")
with col_daily2:
    st.plotly_chart(plot_daily_drawdown(df_filtered), use_container_width=True, key="daily_drawdown")

# Statistiques clés
stats = compute_stats_dict(df_filtered)

def render_stat_card(title, value, emoji):
    return f"""
    <div style="background-color:#0e1117;padding:18px;border-radius:12px;margin:10px;
    text-align:center;box-shadow:0 0 10px rgba(0,0,0,0.3);min-width:160px;">
        <div style="font-size:32px;">{emoji}</div>
        <div style="font-weight:500;font-size:14px;color:#ccc;margin-top:4px;">{title}</div>
        <div style="font-size:26px;font-weight:bold;margin-top:2px;color:#fff;">{value}</div>
    </div>
    """

st.markdown("")
cols1 = st.columns(4)
cols1[0].markdown(render_stat_card("Meilleur Trade", f"${stats['best_trade']}", "🍫"), unsafe_allow_html=True)
cols1[1].markdown(render_stat_card("Pire Trade", f"${stats['worst_trade']}", "🌶️"), unsafe_allow_html=True)
cols1[2].markdown(render_stat_card("Gain Moyen", f"${stats['avg_gain']}", "📈"), unsafe_allow_html=True)
cols1[3].markdown(render_stat_card("Perte Moyenne", f"${stats['avg_loss']}", "📉"), unsafe_allow_html=True)

cols2 = st.columns(4)
cols2[0].markdown(render_stat_card("Total Trades", stats["total_trades"], "💽"), unsafe_allow_html=True)
cols2[1].markdown(render_stat_card("Winrate", f"{stats['winrate']}%", "🎲"), unsafe_allow_html=True)
cols2[2].markdown(render_stat_card("Sharpe Ratio", stats["sharpe_ratio"], "🌊"), unsafe_allow_html=True)
cols2[3].markdown(render_stat_card("Profit Factor", stats["profit_factor"], "🧘‍♂️"), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────
# Timing Zone
# ─────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🏄‍♂️ Timing Zone")

col1b, col2b = st.columns(2)
with col1b:
    st.plotly_chart(plot_avg_duration_per_day(df_filtered), use_container_width=True, key="avg_duration")
with col2b:
    st.plotly_chart(plot_return_vs_duration(df_filtered), use_container_width=True, key="return_duration")

col3, col4 = st.columns(2)
with col3:
    st.plotly_chart(plot_pnl_by_day_of_week(df_filtered), use_container_width=True, key="pnl_day")
with col4:
    st.plotly_chart(plot_pnl_by_hour(df_filtered), use_container_width=True, key="pnl_hour")

# Statistiques Timing
st.markdown("---")
st.subheader("📊 Statistiques Timing")

if all(col in df_filtered.columns for col in ["Durée (min)", "Entry time", "Profit"]):
    avg_duration = round(df_filtered["Durée (min)"].mean(), 2)
    active_days = df_filtered["Entry time"].dt.date.nunique()

    try:
        best_day = df_filtered.groupby(df_filtered["Entry time"].dt.day_name())["Profit"].sum().idxmax()
    except ValueError:
        best_day = "N/A"

    try:
        worst_day = df_filtered.groupby(df_filtered["Entry time"].dt.day_name())["Profit"].sum().idxmin()
    except ValueError:
        worst_day = "N/A"

    try:
        best_hour = df_filtered.groupby(df_filtered["Entry time"].dt.hour)["Profit"].sum().idxmax()
    except ValueError:
        best_hour = "N/A"

    try:
        worst_hour = df_filtered.groupby(df_filtered["Entry time"].dt.hour)["Profit"].sum().idxmin()
    except ValueError:
        worst_hour = "N/A"
else:
    avg_duration = 0
    active_days = 0
    best_day = worst_day = best_hour = worst_hour = "N/A"

cols_timing = st.columns(3)
cols_timing[0].markdown(render_stat_card("Durée Moyenne", f"{avg_duration} min", "⏱️"), unsafe_allow_html=True)
cols_timing[1].markdown(render_stat_card("Jours Actifs", active_days, "📆"), unsafe_allow_html=True)
cols_timing[2].markdown(render_stat_card("Heure la + rentable", f"{best_hour}h" if best_hour != "N/A" else "N/A", "🎬"), unsafe_allow_html=True)

cols_timing2 = st.columns(3)
cols_timing2[0].markdown(render_stat_card("Jour le + rentable", best_day, "📈"), unsafe_allow_html=True)
cols_timing2[1].markdown(render_stat_card("Jour le - performant", worst_day, "📉"), unsafe_allow_html=True)
cols_timing2[2].markdown(render_stat_card("Heure la - rentable", f"{worst_hour}h" if worst_hour != "N/A" else "N/A", "🚹"), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────
# Distribution
# ─────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🧀 Distribution")

col5, col6 = st.columns(2)
with col5:
    st.plotly_chart(plot_asset_distribution(df_filtered), use_container_width=True, key="asset_distr")
with col6:
    st.plotly_chart(plot_gain_loss_pie(df_filtered), use_container_width=True, key="gain_loss")

# ─────────────────────────────────────────────────────────────────────────
# Optimisation des targets
# ─────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 👨‍🔬 Optimisation des targets")

st.plotly_chart(plot_histogram_mae_mfe_etd(df_filtered), use_container_width=True, key="hist_mfe")
st.plotly_chart(plot_scatter_mfe_vs_profit(df_filtered), use_container_width=True, key="mfe_profit")

mae_mean = round(df_filtered["MAE"].mean(), 2) if "MAE" in df_filtered else 0
mfe_mean = round(df_filtered["MFE"].mean(), 2) if "MFE" in df_filtered else 0
etd_mean = round(df_filtered["ETD"].mean(), 2) if "ETD" in df_filtered else 0
mfe_mae_ratio = round(mfe_mean / mae_mean, 2) if mae_mean != 0 else 0

cols_targets = st.columns(4)
cols_targets[0].markdown(render_stat_card("MAE moyen", f"${mae_mean}", "🧨"), unsafe_allow_html=True)
cols_targets[1].markdown(render_stat_card("MFE moyen", f"${mfe_mean}", "🍾"), unsafe_allow_html=True)
cols_targets[2].markdown(render_stat_card("ETD moyen", f"${etd_mean}", "🤺"), unsafe_allow_html=True)
cols_targets[3].markdown(render_stat_card("Ratio MFE/MAE", mfe_mae_ratio, "🧑‍⚖️"), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────
# 🎯 Analyse des sorties
# ─────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.header("🎯 Analyse des sorties")

with st.expander("🧠 % du MFE capté par trade", expanded=True):
    st.plotly_chart(plot_pct_mfe_captured(df_filtered), use_container_width=True)
    st.caption("""
    Ce graphique indique le pourcentage du mouvement favorable (MFE) capté par chaque trade.

    Exemples :
    - 100% = tu as sorti au plus haut du mouvement favorable.
    - 50% = tu as capté la moitié du potentiel avant de sortir.
    - 0% = tu es sorti au break-even alors que le trade avait du potentiel.

    👉 Objectif : te rapprocher de la droite, en captant une part croissante du mouvement,
    sans augmenter ton risque. Un bon trader capture efficacement sans rester trop longtemps.
    """)

    # Calculs pour le commentaire interactif
    mfe_series = (df_filtered["Profit"] / df_filtered["MFE"] * 100).replace([np.inf, -np.inf], np.nan).dropna()
    mfe_series = mfe_series[(mfe_series >= 0) & (mfe_series <= 300)]

    q1 = mfe_series.quantile(0.25)
    mean = mfe_series.mean()
    median = mfe_series.median()
    q3 = mfe_series.quantile(0.75)

    st.markdown(f"""
    💬 **Analyse des sorties :**

    - **Q1 : {q1:.1f}%** → 25% des trades ont capté **moins de {q1:.1f}%** du mouvement favorable. Cela peut indiquer des sorties trop précoces ou un manque de confiance.
    - **Moyenne : {mean:.1f}%** → En moyenne, tu captures **{mean:.1f}%** du potentiel. C'est ton niveau global d'efficacité de sortie.
    - **Médiane : {median:.1f}%** → 50% des trades capturent plus de **{median:.1f}%**, l'autre moitié moins. Une médiane supérieure à 70% est déjà **très solide**.
    - **Q3 : {q3:.1f}%** → 25% des trades les plus efficaces captent plus de **{q3:.1f}%**, ce sont tes meilleures sorties.

    👉 **Objectif** : faire monter la médiane et la moyenne vers Q3, tout en gardant un bon ratio gain/risque. Une courbe étalée avec un Q1 très bas peut indiquer des trades gâchés malgré du potentiel.
    """)
    

with st.expander("🧠 % du MAE encaissé sur profit réalisé", expanded=True):
    st.plotly_chart(plot_pct_mae_vs_etd(df_filtered), use_container_width=True)
    st.caption("""
    Ce graphique mesure combien de drawdown (MAE) tu as encaissé **avant de finir en profit**.

    Exemples :
    - 20% = tu es resté assez proche de ton prix d’entrée avant de sortir gagnant.
    - 100% = tu as encaissé un drawdown aussi grand que ton profit final.
    - >100% = tu étais bien dans le rouge avant de finir dans le vert (stress élevé).

    👉 Objectif : réduire ces valeurs. Plus tu es capable de sortir gagnant sans gros stress,
    plus ton trading est propre et maîtrisé.
    """)

    # Calculs pour analyse interactive du MAE
    mae_series = (df_filtered["MAE"] / df_filtered["ETD"] * 100).replace([np.inf, -np.inf], np.nan).dropna()
    mae_series = mae_series[(mae_series >= 0) & (mae_series <= 300)]

    q1_mae = mae_series.quantile(0.25)
    mean_mae = mae_series.mean()
    median_mae = mae_series.median()
    q3_mae = mae_series.quantile(0.75)

    st.markdown(f"""
    💬 **Analyse du stress (MAE) encaissé avant profit :**

    - **Q1 : {q1_mae:.1f}%** → 25% des trades gagnants ont encaissé **moins de {q1_mae:.1f}%** de drawdown avant de finir en profit. Cela traduit une bonne précision ou un timing propre.
    - **Moyenne : {mean_mae:.1f}%** → En moyenne, tu encaisses **{mean_mae:.1f}%** de drawdown par rapport à ton gain. Moins c’est élevé, plus ton trade est stable.
    - **Médiane : {median_mae:.1f}%** → 50% des trades ont encaissé moins de **{median_mae:.1f}%**, c’est ton niveau médian de stress avant gain.
    - **Q3 : {q3_mae:.1f}%** → 25% des trades gagnants ont encaissé plus de **{q3_mae:.1f}%** de drawdown : c’est ton quart le plus stressant.

    👉 **Objectif** : faire baisser la moyenne et la médiane pour un trading plus propre et maîtrisé. Une médiane < 50% indique que tu restes souvent proche de ton point d’entrée avant de sortir gagnant, ce qui est excellent.
    """)

# ─────────────────────────────────────────────────────────────────────────
# Liste des trades filtrés
# ─────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 Liste des trades")

st.dataframe(df_filtered.sort_values("Entry time", ascending=False), use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────
# Dernière Session (navigation sur les notes)
# ─────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🎞️ Dernière Session")

dates_dispo = sorted(journal.keys())
if len(dates_dispo) >= 1:
    if "note_index" not in st.session_state:
        st.session_state.note_index = len(dates_dispo) - 1

    colA, colB, colC = st.columns([1,6,1])
    with colA:
        if st.button("⬅️", use_container_width=True) and st.session_state.note_index > 0:
            st.session_state.note_index -= 1

    selected_date = dates_dispo[st.session_state.note_index]
    selected_note = journal[selected_date]

    with colB:
        st.markdown(
            f"<div style='text-align: center; font-size: 26px; padding-top: 6px;'>📅 {selected_date.split(' ')[0]}</div>",
            unsafe_allow_html=True
        )

    with colC:
        if st.button("➡️", use_container_width=True) and st.session_state.note_index < len(dates_dispo) - 1:
            st.session_state.note_index += 1

    st.markdown(f"> {selected_note['text']}")

    for path in selected_note.get("images", []):
        st.image(path, use_container_width=True)

else:
    st.info("👉 Ajoute au moins une note pour naviguer.")

# ─────────────────────────────────────────────────────────────────────────
# Listing complet de toutes les sessions enregistrées
# ─────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🧾 Listing de toutes les sessions enregistrées")

records = []
for d in sorted(journal.keys(), reverse=True):
    note = journal[d]
    preview_text = note["text"][:120] + ("..." if len(note["text"]) > 120 else "")
    records.append({
        "Date": d.split(" ")[0],
        "Résumé": preview_text,
        "Nb images": len(note.get("images", [])),
        "Clé": d
    })

df_notes = pd.DataFrame(records)

if not df_notes.empty:
    for idx, row in df_notes.iterrows():
        with st.expander(f"📅 {row['Date']} — {row['Résumé']}"):
            st.markdown(f"### 🗒️ Note du {row['Date']}")
            st.markdown(journal[row["Clé"]]["text"])
            for path in journal[row["Clé"]].get("images", []):
                st.image(path, use_container_width=True)
else:
    st.info("Aucune note à afficher.")

from gdrive_backup import get_drive_service_from_secrets, backup_user_data

st.markdown("---")
st.subheader("☁️ Sauvegarde Google Drive")

if st.button("🔁 Sauvegarder mes données sur Drive", use_container_width=True):
    try:
        drive_service = get_drive_service_from_secrets()
        backup_user_data(
            drive_service=drive_service,
            local_data_dir=user_data_dir,
            backup_folder_name="Streamlit_Backup",
            username=username
        )
        st.success("📦 Données sauvegardées sur Google Drive avec succès !")
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde : {e}")

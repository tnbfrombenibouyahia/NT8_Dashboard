import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import calplot  # Nouveau module
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from datetime import datetime, timedelta
import calendar
import datetime as dt
import yfinance as yf
import plotly.graph_objects as go
import numpy as np



# === Couleurs harmonisées ===
COLOR_PROFIT = "#3b82f6"     # bleu foncé moderne
COLOR_DRAWDOWN = "#ef4444"   # rouge vif foncé
COLOR_PRESENCE = "#10b981"   # vert présent
COLOR_ABSENCE = "#9ca3af"    # gris clair

def plot_equity_curve(df):
    if df.empty:
        return px.area(title="Aucune donnée")

    df = df.sort_values("Entry time").copy()
    df["Cumulative P&L"] = df["Profit"].cumsum()
    df["Trade #"] = range(1, len(df) + 1)

    fig = px.area(
        df,
        x="Trade #",
        y="Cumulative P&L",
        title="📈 Courbe de Capital (par trade)",
        labels={"Trade #": "Trade #", "Cumulative P&L": "Profit Cumulé"},
    )
    fig.update_traces(line_color=COLOR_PROFIT, fillcolor="rgba(59, 130, 246, 0.3)", fill="tozeroy")
    return fig


def plot_drawdown_curve(df):
    if df.empty:
        return px.area(title="Aucune donnée")

    df = df.sort_values("Entry time").copy()
    df["Cumulative P&L"] = df["Profit"].cumsum()
    df["Drawdown"] = df["Cumulative P&L"] - df["Cumulative P&L"].cummax()
    df["Trade #"] = range(1, len(df) + 1)

    fig = px.area(
        df,
        x="Trade #",
        y="Drawdown",
        title="📉 Courbe de Drawdown (par trade)",
        labels={"Trade #": "Trade #", "Drawdown": "Drawdown"},
    )
    fig.update_traces(line_color=COLOR_DRAWDOWN, fillcolor="rgba(239, 68, 68, 0.3)", fill="tozeroy")
    return fig


def plot_daily_drawdown(df):
    if df.empty:
        return px.bar(title="Aucune donnée")

    df = df.sort_values("Entry time")
    df["Cumulative"] = df["Profit"].cumsum()
    df["Drawdown"] = df["Cumulative"] - df["Cumulative"].cummax()
    df["Date"] = df["Entry time"].dt.date

    daily_min_dd = df.groupby("Date")["Drawdown"].min().reset_index()

    fig = px.bar(
        daily_min_dd,
        x="Date",
        y="Drawdown",
        title="📉 Drawdown quotidien",
        labels={"Drawdown": "Drawdown min", "Date": "Date"},
    )
    fig.update_traces(marker_color=COLOR_DRAWDOWN)
    fig.update_yaxes(autorange="reversed")
    return fig

def plot_daily_pnl(df):
    if df.empty:
        return px.bar(title="Aucune donnée")

    df["Date"] = df["Entry time"].dt.date
    daily_pnl = df.groupby("Date")["Profit"].sum().reset_index()

    fig = px.bar(
        daily_pnl,
        x="Date",
        y="Profit",
        title="💵 Profit quotidien",
        labels={"Profit": "Profit", "Date": "Date"},
    )
    fig.update_traces(marker_color=COLOR_PROFIT)
    return fig

def plot_gain_loss_pie(df):
    if df.empty:
        return px.pie(title="Aucune donnée")

    df["Profit Label"] = df["Profit"].apply(lambda x: "Gain" if x > 0 else "Perte")
    pie_data = df["Profit Label"].value_counts().reset_index()
    pie_data.columns = ["Résultat", "Nombre"]

    fig = px.pie(
        pie_data,
        values="Nombre",
        names="Résultat",
        title="🥧 Répartition Gains / Pertes",
        hole=0.4
    )
    fig.update_traces(textinfo="percent+label")
    return fig

def plot_asset_distribution(df):
    if df.empty:
        return px.pie(title="Aucune donnée")

    asset_counts = df["Instrument"].value_counts().reset_index()
    asset_counts.columns = ["Instrument", "Nombre de trades"]

    fig = px.pie(
        asset_counts,
        values="Nombre de trades",
        names="Instrument",
        title="📊 Répartition des actifs tradés",
        hole=0.4
    )
    fig.update_traces(textinfo="percent+label")
    return fig

def plot_avg_duration_per_day(df):
    if df.empty:
        return px.bar(title="Aucune donnée")

    df["Date"] = df["Entry time"].dt.date
    daily_avg = df.groupby("Date")["Durée (min)"].mean().reset_index()

    fig = px.bar(
        daily_avg,
        x="Date",
        y="Durée (min)",
        title="⏱️ Durée moyenne des trades par jour",
        labels={"Durée (min)": "Durée moyenne (min)", "Date": "Jour"},
    )
    fig.update_layout(xaxis_title="Jour", yaxis_title="Durée (min)")
    fig.update_traces(marker_color=COLOR_PROFIT)
    return fig

def plot_return_vs_duration(df):
    if df.empty:
        return px.scatter(title="Aucune donnée")

    fig = px.scatter(
        df,
        x="Durée (min)",
        y="Rendement (%)",
        title="📈 Scatter Plot : Rendement (%) vs Durée",
        labels={"Durée (min)": "Durée (min)", "Rendement (%)": "Rendement (%)"},
        hover_data=["Entry time", "Instrument", "Profit"]
    )
    fig.update_traces(marker=dict(size=10, opacity=0.7, line=dict(width=1, color=COLOR_PROFIT)))
    return fig

def compute_stats_dict(df):
    if df.empty:
        return {
            "total_trades": 0,
            "winrate": 0,
            "total_profit": 0,
            "avg_gain": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
            "avg_duration": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "sharpe_ratio": 0,
        }

    total_trades = len(df)
    wins = df[df["Profit"] > 0]
    losses = df[df["Profit"] < 0]
    winrate = round(len(wins) / total_trades * 100, 2)
    total_profit = df["Profit"].sum()
    avg_gain = round(wins["Profit"].mean(), 2) if not wins.empty else 0
    avg_loss = round(losses["Profit"].mean(), 2) if not losses.empty else 0
    profit_factor = round(wins["Profit"].sum() / abs(losses["Profit"].sum()), 2) if not losses.empty else 0
    best_trade = df["Profit"].max()
    worst_trade = df["Profit"].min()
    avg_duration = round(df["Durée (min)"].mean(), 2)
    sharpe_ratio = round(df["Profit"].mean() / df["Profit"].std(), 2) if df["Profit"].std() != 0 else 0

    df = df.sort_values("Entry time")
    df["Cumulative"] = df["Profit"].cumsum()
    drawdown = df["Cumulative"] - df["Cumulative"].cummax()
    max_drawdown = round(drawdown.min(), 2)

    return {
        "total_trades": total_trades,
        "winrate": winrate,
        "total_profit": total_profit,
        "avg_gain": avg_gain,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "avg_duration": avg_duration,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "sharpe_ratio": sharpe_ratio,
    }

def plot_pnl_by_hour(df):
    if df.empty:
        return px.bar(title="Aucune donnée")

    df["Hour"] = df["Entry time"].dt.hour
    hourly_pnl = df.groupby("Hour")["Profit"].sum().reset_index()

    fig = px.bar(
        hourly_pnl,
        x="Hour",
        y="Profit",
        title="⏰ PnL par Heure d’entrée",
        labels={"Hour": "Heure (0-23)", "Profit": "PnL"},
    )
    fig.update_layout(xaxis=dict(dtick=1))
    fig.update_traces(marker_color=COLOR_PROFIT)
    return fig

def plot_pnl_by_day_of_week(df):
    if df.empty:
        return px.bar(title="Aucune donnée")

    df["Day"] = df["Entry time"].dt.dayofweek
    day_map = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi", 5: "Samedi", 6: "Dimanche"}
    df["Day"] = df["Day"].map(day_map)

    daily_pnl = df.groupby("Day")["Profit"].sum().reindex(["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]).reset_index()

    fig = px.bar(
        daily_pnl,
        x="Day",
        y="Profit",
        title="📅 PnL par Jour de la semaine",
        labels={"Day": "Jour", "Profit": "PnL"},
    )
    fig.update_traces(marker_color=COLOR_PROFIT)
    return fig

def plot_market_position_distribution(df):
    if df.empty:
        return px.pie(title="Aucune donnée")

    pos_counts = df["Market pos."].value_counts().reset_index()
    pos_counts.columns = ["Position", "Nombre"]

    fig = px.pie(
        pos_counts,
        values="Nombre",
        names="Position",
        title="📌 Répartition Long / Short",
        hole=0.4
    )
    fig.update_traces(textinfo="percent+label")
    return fig


def plot_histogram_mae_mfe_etd(df):
    if df.empty or not all(x in df.columns for x in ["MAE", "MFE", "ETD"]):
        fig = go.Figure()
        fig.update_layout(title="Aucune donnée", template="plotly_dark")
        return fig

    fig = go.Figure()
    fig.add_histogram(x=df["MAE"], name="MAE")
    fig.add_histogram(x=df["MFE"], name="MFE")
    fig.add_histogram(x=df["ETD"], name="ETD")

    fig.update_layout(
        barmode='overlay',
        title="Distribution MAE / MFE / ETD",
        template="plotly_dark",
        xaxis_title="Valeur",
        yaxis_title="Fréquence"
    )
    fig.update_traces(opacity=0.65)
    return fig

def plot_scatter_mfe_vs_profit(df):
    if df.empty:
        return px.scatter(title="Aucune donnée")

    df = df.copy()
    df = df.dropna(subset=["MFE", "Profit"])

    # Quartiles
    q1 = df["MFE"].quantile(0.25)
    median = df["MFE"].median()
    q3 = df["MFE"].quantile(0.75)

    # Régression linéaire
    x = df["MFE"]
    y = df["Profit"]
    slope, intercept = np.polyfit(x, y, 1)

    # Droite de tendance
    x_range = np.linspace(x.min(), x.max(), 100)
    y_pred = slope * x_range + intercept

    # Création du graphique
    fig = px.scatter(
        df,
        x="MFE",
        y="Profit",
        title=f"📈 MFE vs Profit réalisé (pente = {slope:.2f})",
        labels={"MFE": "Max Favorable Excursion", "Profit": "Profit réalisé"},
        hover_data=["Entry time", "Exit time", "Instrument"]
    )

    # Ajout de la droite de tendance
    fig.add_trace(go.Scatter(
        x=x_range,
        y=y_pred,
        mode='lines',
        name="Tendance",
        line=dict(dash="dot", color="orange")
    ))

    # Ajout des lignes de quartiles
    fig.add_vline(x=q1, line_dash="dot", line_color="green", annotation_text=f"Q1 : {q1:.1f}$", annotation_position="top left")
    fig.add_vline(x=median, line_dash="dash", line_color="white", annotation_text=f"Médiane : {median:.1f}$", annotation_position="top left")
    fig.add_vline(x=q3, line_dash="dot", line_color="green", annotation_text=f"Q3 : {q3:.1f}$", annotation_position="top right")

    fig.update_layout(
        xaxis_title="Max Favorable Excursion",
        yaxis_title="Profit réalisé",
        template="plotly_dark"
    )

    return fig


def plot_heatmap_mae_vs_mfe(df):
    if df.empty:
        return px.density_heatmap(title="Aucune donnée")

    fig = px.density_heatmap(
        df,
        x="MAE",
        y="MFE",
        nbinsx=30,
        nbinsy=30,
        title="📉 Heatmap MAE vs MFE",
        labels={"MAE": "Max Adverse Excursion", "MFE": "Max Favorable Excursion"},
        color_continuous_scale="Blues"
    )
    return fig


def plot_presence_timeline(df, selected_month):
    if df.empty:
        return px.scatter(title="Aucune donnée")

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Entry time"].dt.date)

    # Début et fin du mois sélectionné
    start = datetime(selected_month.year, selected_month.month, 1)
    end = (start + pd.DateOffset(months=1)) - timedelta(days=1)

    # Générer tous les jours ouvrés du mois
    date_range = pd.date_range(start=start, end=end, freq='B')
    presence_map = pd.Series(0, index=date_range)
    presence_map[df["Date"].value_counts().index] = 1

    presence_df = presence_map.reset_index()
    presence_df.columns = ["Date", "Présence"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=presence_df["Date"],
        y=[1]*len(presence_df),
        mode='markers',
        marker=dict(
            size=14,
            color=[COLOR_PRESENCE if val == 1 else COLOR_ABSENCE for val in presence_df["Présence"]],
            line=dict(width=0)
        ),
        hoverinfo='x+text',
        text=["✅ Présent" if v == 1 else "❌ Absent" for v in presence_df["Présence"]],
        showlegend=False
    ))

    fig.update_layout(
        title=f"📆 Présence - {selected_month.strftime('%B %Y')} (timeline)",
        xaxis_title="Date",
        yaxis_visible=False,
        yaxis_showticklabels=False,
        height=140,
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


def plot_presence_histogram(df, selected_month):
    if df.empty:
        return px.bar(title="Aucune donnée")

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Entry time"].dt.date)

    # Début et fin du mois sélectionné
    start = datetime(selected_month.year, selected_month.month, 1)
    end = (start + pd.DateOffset(months=1)) - timedelta(days=1)

    # Tous les jours ouvrés
    date_range = pd.date_range(start=start, end=end, freq='B')
    presence_map = pd.Series(0, index=date_range)
    presence_map[df["Date"].value_counts().index] = 1
    presence_df = presence_map.reset_index()
    presence_df.columns = ["Date", "Présence"]

    fig = px.bar(
        presence_df,
        x="Date",
        y="Présence",
        labels={"Présence": "Présence", "Date": "Jour"},
    )
    fig.update_traces(marker_color=COLOR_PRESENCE)
    fig.update_layout(
    xaxis=dict(
        range=[presence_df["Date"].min(), presence_df["Date"].max()],
        showgrid=False,
        ticks="",
        showticklabels=False,
    ),
    yaxis=dict(
        showgrid=False,
        ticks="",
        showticklabels=False
    ),
    showlegend=False,
    height=50,
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="#0e1117",
    paper_bgcolor="#0e1117",
)

    return fig

def clean_outliers(df, column, lower=0, upper=300):
    if column in df:
        return df[(df[column] >= lower) & (df[column] <= upper)]
    return df

def plot_pct_mfe_captured(df):
    df = df.copy()
    df["% MFE Captured"] = (df["Profit"] / df["MFE"] * 100).replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["% MFE Captured"])
    df = df[(df["% MFE Captured"] >= 0) & (df["% MFE Captured"] <= 300)]

    # Calcul de l’histogramme manuellement
    counts, bins = np.histogram(df["% MFE Captured"], bins=40)
    bin_centers = 0.5 * (bins[:-1] + bins[1:])

    # Création du histogramme avec dégradé rouge → bleu
    fig = go.Figure(data=[
        go.Bar(
            x=bin_centers,
            y=counts,
            marker=dict(
                color=counts,
                colorscale=[[0, "#ef4444"], [0.5, "#8b5cf6"], [1, "#3b82f6"]],
                colorbar=dict(title="Nombre de trades")
            )
        )
    ])

    # Statistiques
    median = df["% MFE Captured"].median()
    mean = df["% MFE Captured"].mean()
    q1 = df["% MFE Captured"].quantile(0.25)
    q3 = df["% MFE Captured"].quantile(0.75)

    # Lignes statistiques
    fig.add_vline(x=median, line_dash="dash", line_color="white", annotation_text=f"Médiane : {median:.1f}%", annotation_position="top left")
    fig.add_vline(x=mean, line_dash="dot", line_color="white", annotation_text=f"Moyenne : {mean:.1f}%", annotation_position="top left")
    fig.add_vline(x=q1, line_dash="dot", line_color="white", annotation_text=f"Q1 : {q1:.1f}%", annotation_position="top left")
    fig.add_vline(x=q3, line_dash="dot", line_color="white", annotation_text=f"Q3 : {q3:.1f}%", annotation_position="top right")

    # Mise en forme
    fig.update_layout(
        title="🎯 % du MFE capté par trade",
        xaxis_title="% du MFE capté",
        yaxis_title="Nombre de trades",
        template="plotly_dark",
        bargap=0.1
    )
    return fig

def plot_pct_mae_vs_etd(df):
    df = df.copy()
    df["% MAE / ETD"] = (df["MAE"] / df["ETD"] * 100).replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["% MAE / ETD"])
    df = df[(df["% MAE / ETD"] >= 0) & (df["% MAE / ETD"] <= 300)]

    # Créer les bins manuellement pour accéder aux fréquences
    counts, bins = np.histogram(df["% MAE / ETD"], bins=40)
    bin_centers = 0.5 * (bins[1:] + bins[:-1])

    # Créer le graphique manuellement avec go.Bar pour pouvoir appliquer un dégradé
    fig = go.Figure(data=[
        go.Bar(
            x=bin_centers,
            y=counts,
            marker=dict(
                color=counts,
                colorscale=[
                    [0.0, "#ef4444"],  # Rouge
                    [0.5, "#8b5cf6"],  # Violet
                    [1.0, "#3b82f6"]   # Bleu
                ],
                colorbar=dict(title="Nombre de trades")
            )
        )
    ])

    # Statistiques
    median = df["% MAE / ETD"].median()
    mean = df["% MAE / ETD"].mean()
    q1 = df["% MAE / ETD"].quantile(0.25)
    q3 = df["% MAE / ETD"].quantile(0.75)

    # Ajouter lignes de stats
    fig.add_vline(x=median, line_dash="dash", line_color="white", annotation_text=f"Médiane : {median:.1f}%", annotation_position="top left")
    fig.add_vline(x=mean, line_dash="dot", line_color="white", annotation_text=f"Moyenne : {mean:.1f}%", annotation_position="bottom left")
    fig.add_vline(x=q1, line_dash="dot", line_color="white", annotation_text=f"Q1 : {q1:.1f}%", annotation_position="top right")
    fig.add_vline(x=q3, line_dash="dot", line_color="white", annotation_text=f"Q3 : {q3:.1f}%", annotation_position="bottom right")

    fig.update_layout(
        title="🧨 % du MAE encaissé sur profit réalisé",
        xaxis_title="% du MAE encaissé",
        yaxis_title="Nombre de trades",
        bargap=0.1,
        template="plotly_dark"
    )
    return fig

def plot_scatter_mfe_captured(df):
    df = df.copy()
    df["% MFE Captured"] = (df["Profit"] / df["MFE"] * 100).replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["% MFE Captured"])
    df = df[(df["% MFE Captured"] >= 0) & (df["% MFE Captured"] <= 300)]

    fig = px.scatter(
        df,
        x="% MFE Captured",
        y="Profit",
        title="🔁 Scatter : % MFE capté vs Profit réalisé",
        hover_data=["Entry time", "Instrument"],
        labels={"Profit": "Profit réalisé", "% MFE Captured": "% MFE capté"}
    )
    fig.update_layout(template="plotly_dark")
    return fig

def plot_heatmap_mfe_mae(df):
    df = df.copy()
    df["% MFE Captured"] = (df["Profit"] / df["MFE"] * 100).replace([np.inf, -np.inf], np.nan)
    df["% MAE Captured"] = (df["MAE"] / df["Profit"] * 100).replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["% MFE Captured", "% MAE Captured"])
    df = df[(df["% MFE Captured"] >= 0) & (df["% MFE Captured"] <= 300)]
    df = df[(df["% MAE Captured"] >= 0) & (df["% MAE Captured"] <= 300)]

    fig = px.density_heatmap(
        df,
        x="% MFE Captured",
        y="% MAE Captured",
        nbinsx=40,
        nbinsy=40,
        color_continuous_scale="Blues",
        title="🌡️ Heatmap : % MFE capté vs % MAE encaissé"
    )
    fig.update_layout(template="plotly_dark")
    return fig

def plot_mfe_vs_time(df):
    df = df.copy()
    df = df.dropna(subset=["Entry time", "MFE"])
    fig = px.scatter(df, x="Entry time", y="MFE")
    fig.update_layout(title="MFE en fonction du temps")
    return fig






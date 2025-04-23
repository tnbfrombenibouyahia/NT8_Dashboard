import pandas as pd
import numpy as np
import os
import locale
from dateutil import parser

def parse_money(val, fr_format=False):
    if pd.isna(val):
        return np.nan
    val = str(val).strip()

    # Format FR
    if fr_format:
        val = val.replace("\xa0", "")  # espace insécable
        val = val.replace(" €", "").replace("€", "").replace(" $", "").replace("$", "")
        val = val.replace(",", ".")  # virgule décimale
        # Supprimer + interpréter le signe si "-" est explicitement là
        val = val.replace("−", "-")  # en cas de tiret spécial
    else:
        val = val.replace('(', '-').replace(')', '')
        val = val.replace('$', '').replace(',', '')

    try:
        return float(val)
    except ValueError:
        return np.nan

def parse_datetime(value, fmt):
    try:
        if fmt == 'fr':
            return pd.to_datetime(value, format="%d/%m/%Y %H:%M:%S", errors="coerce")
        return pd.to_datetime(value, errors="coerce")
    except:
        try:
            return parser.parse(value)
        except:
            return pd.NaT

def load_and_clean_csv(file):
    try:
        df = pd.read_csv(file, sep=None, engine='python')
    except Exception as e:
        import streamlit as st
        st.error(f"❌ Erreur lors de la lecture du fichier CSV : {e}")
        return pd.DataFrame()

    # Détection du format (us ou fr)
    data_format = detect_format(df)
    fr_format = (data_format == 'fr')

    # Nettoyage colonnes inutiles
    df = df.drop(columns=["Unnamed: 19"], errors="ignore")

    # Conversion des montants
    monetary_columns = ["Profit", "Cum. net profit", "MAE", "MFE", "ETD", "Commission"]
    for col in monetary_columns:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: parse_money(x, fr_format=fr_format))

    # ✅ Conversion des prix en float (Entry/Exit price)
    price_columns = ["Entry price", "Exit price"]
    for col in price_columns:
        if col in df.columns:
            if fr_format:
                df[col] = df[col].astype(str).str.replace(',', '.').str.replace('\xa0', '').astype(float)
            else:
                df[col] = df[col].astype(float)

    # Conversion des dates
    if "Entry time" in df.columns:
        df["Entry time"] = df["Entry time"].apply(lambda x: parse_datetime(x, fmt=data_format))
    if "Exit time" in df.columns:
        df["Exit time"] = df["Exit time"].apply(lambda x: parse_datetime(x, fmt=data_format))

    # ID unique
    if "Trade number" in df.columns:
        df["trade_id"] = df["Trade number"].astype(str) + "_" + df["Entry time"].astype(str)
    else:
        df["trade_id"] = df.index.astype(str) + "_" + df["Entry time"].astype(str)

    return df

def update_historical_data(df_new, historical_path):
    if os.path.exists(historical_path):
        df_hist = pd.read_csv(historical_path, parse_dates=["Entry time", "Exit time"])
        if "Trade number" in df_hist.columns:
            df_hist["trade_id"] = df_hist["Trade number"].astype(str) + "_" + df_hist["Entry time"].astype(str)
        else:
            df_hist["trade_id"] = df_hist.index.astype(str) + "_" + df_hist["Entry time"].astype(str)

        df_to_add = df_new[~df_new["trade_id"].isin(df_hist["trade_id"])]
        df_updated = pd.concat([df_hist, df_to_add], ignore_index=True).drop(columns=["trade_id"], errors="ignore")
        df_updated.to_csv(historical_path, index=False)
        return df_updated, len(df_to_add)
    else:
        df_new.drop(columns=["trade_id"], errors="ignore").to_csv(historical_path, index=False)
        return df_new.drop(columns=["trade_id"], errors="ignore"), len(df_new)

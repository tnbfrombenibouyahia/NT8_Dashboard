# 🥷 NinjaTrader Dashboard — Multi-User Trading Analytics App

A clean, fast, and secure web dashboard for **futures traders**, especially those using **NinjaTrader 8**.  
It helps you **visualize**, **analyze**, and **journal** your trading performance with ease.  
Built with **Streamlit** and `streamlit-authenticator`, it supports both **individual and multi-user** usage.

---

## 🎬 Live Demo

> Watch a 90-second walkthrough of the app 👇  
[![Demo Video](https://img.youtube.com/vi/YOUR_VIDEO_ID/0.jpg)](https://www.youtube.com/watch?v=YOUR_VIDEO_ID)

---

## 🚀 Features

✅ Import your trade history in seconds (CSV from NinjaTrader 8)  
✅ Clean & aggregate data by user  
✅ **User data is automatically backed up and secured on Google Drive**  
✅ Visualize key metrics: PnL, drawdown, Sharpe, trade durations…  
✅ Analyze **MFE, MAE, ETD** — crucial metrics for scalping strategies  
✅ Explore behavioral insights:  
 • % of favorable movement captured (MFE)  
 • % of drawdown endured before profit (MAE/ETD)  
✅ Track daily presence and journal each session  
✅ Multi-user authentication with secure credentials (hashed with `bcrypt`)  

---

## 🔒 Login System

The app supports **multi-user login** with email & password.

🔐 Each user’s credentials are stored securely in a YAML config (hashed).  
📁 Their data is isolated in a personal folder structure like this:

data/
└── user_email/
├── trades_historique.csv
├── journal_notes.json
└── session_images/

Optional: all user data is **automatically backed up to Google Drive** via API.

---

## 🗂️ Tech Stack

- `streamlit` 🧩  
- `streamlit-authenticator` 🔐  
- `pandas`, `numpy`, `plotly`, `matplotlib` 📊  
- Google Drive API (`google-api-python-client`) ☁️  
- Clean modular architecture with auto user folder creation

---

🧠 About the Project

Built by Théo Naïm, as a real-world tool to analyze personal trades on NinjaTrader 8.
The goal: build a clear, intuitive and secure dashboard to track trading performance over time.

🔗 Connect with me on LinkedIn : https://www.linkedin.com/in/th%C3%A9o-na%C3%AFm-benhellal-56bb6218a/
📬 Interested in improving your trading analytics or need a custom dashboard?
Feel free to contact me — I’m open to collaboration!

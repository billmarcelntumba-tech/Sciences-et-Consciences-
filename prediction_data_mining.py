# ==========================================================
# MODULE ML : PRÉVISION D'OCCUPATION DES LITS (CORRIGÉ)
# ==========================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet
import warnings

warnings.filterwarnings("ignore")

# ==========================================================
# CONFIGURATION
# ==========================================================
SQLSERVER = {
    "SERVER": ".\\SQLEXPRESS",
    "DATABASE": "dw_hgrkatuba",
    "DRIVER": "ODBC Driver 17 for SQL Server"
}

SEUIL_OCCUPATION_CRITIQUE = 0.85  # 85% - Alerte critique
SEUIL_OCCUPATION_AVERTISSEMENT = 0.75  # 75% - Alerte avertissement
HORIZON_PREVISION = 30  # 30 jours de prévision


# ==========================================================
# CONNEXION SQL SERVER
# ==========================================================
def get_engine():
    import urllib
    params = urllib.parse.quote_plus(
        f"DRIVER={SQLSERVER['DRIVER']};"
        f"SERVER={SQLSERVER['SERVER']};"
        f"DATABASE={SQLSERVER['DATABASE']};"
        f"Trusted_Connection=yes;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")


# ==========================================================
# EXTRACTION DES DONNÉES HISTORIQUES
# ==========================================================
def extraire_historique_occupation(engine):
    """
    Extrait l'historique d'occupation des lits par service
    """
    query = """
    SELECT 
        t.date_complete,
        s.nom_service,
        s.service_sk,
        fh.nb_lits_occupes,
        s.capacite_lits,
        CAST(fh.nb_lits_occupes AS FLOAT) / NULLIF(s.capacite_lits, 0) AS taux_occupation
    FROM faits_hospitalisation fh
    JOIN dim_temps t ON fh.temps_sk = t.temps_sk
    JOIN dim_service s ON fh.service_sk = s.service_sk
    WHERE s.capacite_lits > 0
    ORDER BY t.date_complete, s.nom_service
    """
    df = pd.read_sql(query, engine)
    df['date_complete'] = pd.to_datetime(df['date_complete'])
    return df


# ==========================================================
# MODÈLE ARIMA
# ==========================================================
def predire_arima(serie, horizon=30):
    """
    Prédiction avec ARIMA (AutoRegressive Integrated Moving Average)
    """
    try:
        model = ARIMA(serie, order=(5, 1, 0))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=horizon)
        return forecast.values
    except Exception as e:
        print(f"⚠️ ARIMA a échoué : {e}")
        return np.full(horizon, np.nan)


# ==========================================================
# MODÈLE PROPHET
# ==========================================================
def predire_prophet(df, horizon=30):
    """
    Prédiction avec Prophet (saisonnalités)
    """
    try:
        df_prophet = df.rename(columns={'date_complete': 'ds', 'taux_occupation': 'y'})
        model = Prophet(yearly_seasonality=True, weekly_seasonality=True)
        model.fit(df_prophet)
        future = model.make_future_dataframe(periods=horizon)
        forecast = model.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(horizon)
    except Exception as e:
        print(f"⚠️ Prophet a échoué : {e}")
        return pd.DataFrame()


# ==========================================================
# MODÈLE RÉGRESSION LINÉAIRE
# ==========================================================
def predire_regression(serie, horizon=30):
    """
    Prédiction avec Régression Linéaire (tendance)
    """
    try:
        X = np.arange(len(serie)).reshape(-1, 1)
        y = serie.values
        model = LinearRegression()
        model.fit(X, y)
        X_pred = np.arange(len(serie), len(serie) + horizon).reshape(-1, 1)
        y_pred = model.predict(X_pred)
        return y_pred
    except Exception as e:
        print(f"⚠️ Régression a échoué : {e}")
        return np.full(horizon, np.nan)


# ==========================================================
# PRÉVISION GLOBALE PAR SERVICE (CORRIGÉE)
# ==========================================================
def generer_previsions(engine):
    """
    Génère les prévisions d'occupation pour chaque service
    et les alertes associées.
    """
    print("📊 Extraction des données historiques...")
    df_hist = extraire_historique_occupation(engine)
    services = df_hist['nom_service'].unique()

    predictions = []
    alertes = []

    for service in services:
        print(f"\n📊 Traitement du service : {service}")

        df_service = df_hist[df_hist['nom_service'] == service].copy()

        # Ne garder que les colonnes numériques pour le resample
        df_service_num = df_service[
            ['date_complete', 'taux_occupation', 'capacite_lits', 'service_sk', 'nb_lits_occupes']]

        # Resample quotidien avec ffill (CORRIGÉ)
        df_service_num = df_service_num.set_index('date_complete').resample('D').mean().ffill().reset_index()

        # Ajouter le nom du service (non numérique)
        df_service_num['nom_service'] = service

        # Réorganiser les colonnes
        df_service = df_service_num[
            ['date_complete', 'nom_service', 'service_sk', 'nb_lits_occupes', 'capacite_lits', 'taux_occupation']]

        if len(df_service) < 30:
            print(f"⏩ Service {service} : données insuffisantes ({len(df_service)} jours)")
            continue

        # --- ARIMA ---
        pred_arima = predire_arima(df_service['taux_occupation'], HORIZON_PREVISION)

        # --- Prophet ---
        df_prophet = predire_prophet(df_service[['date_complete', 'taux_occupation']], HORIZON_PREVISION)

        # --- Régression ---
        pred_reg = predire_regression(df_service['taux_occupation'], HORIZON_PREVISION)

        # Agrégation des prédictions (moyenne des 3 modèles)
        last_date = df_service['date_complete'].max()
        service_sk = df_service['service_sk'].iloc[0]
        capacite = df_service['capacite_lits'].iloc[0]

        for i in range(HORIZON_PREVISION):
            pred_date = last_date + timedelta(days=i + 1)
            val_arima = pred_arima[i] if i < len(pred_arima) else np.nan
            val_prophet = df_prophet.iloc[i]['yhat'] if not df_prophet.empty and i < len(df_prophet) else np.nan
            val_reg = pred_reg[i] if i < len(pred_reg) else np.nan

            # Moyenne des modèles valides
            vals = [v for v in [val_arima, val_prophet, val_reg] if not np.isnan(v)]
            pred_final = np.mean(vals) if vals else 0.5

            # Clipping entre 0 et 1
            pred_final = max(0, min(1, pred_final))

            # Lits occupés
            lits_occupes = int(pred_final * capacite)

            # Intervalle de confiance
            conf_inf = df_prophet.iloc[i]['yhat_lower'] if not df_prophet.empty and i < len(
                df_prophet) else pred_final * 0.85
            conf_sup = df_prophet.iloc[i]['yhat_upper'] if not df_prophet.empty and i < len(
                df_prophet) else pred_final * 1.15

            predictions.append({
                'date_prevision': pred_date.date(),
                'service_sk': service_sk,
                'occupation_predite': pred_final * 100,  # en pourcentage
                'nb_lits_occupes_predits': lits_occupes,
                'intervalle_inf': conf_inf * 100,
                'intervalle_sup': conf_sup * 100,
                'modele': 'Ensemble',
                'horizon_jours': i + 1
            })

            # Détection d'alerte
            if pred_final >= SEUIL_OCCUPATION_CRITIQUE:
                alertes.append({
                    'service_sk': service_sk,
                    'date_alerte': pred_date.date(),
                    'seuil_atteint': pred_final * 100,
                    'type_alerte': 'Critique',
                    'resolu': 0
                })
            elif pred_final >= SEUIL_OCCUPATION_AVERTISSEMENT:
                alertes.append({
                    'service_sk': service_sk,
                    'date_alerte': pred_date.date(),
                    'seuil_atteint': pred_final * 100,
                    'type_alerte': 'Avertissement',
                    'resolu': 0
                })

    # Insertion dans SQL Server
    df_pred = pd.DataFrame(predictions)
    df_alerts = pd.DataFrame(alertes)

    print(f"\n📦 Insertion des prévisions dans SQL Server...")

    with engine.begin() as conn:
        # Nettoyer les anciennes prévisions
        conn.execute(text("DELETE FROM previsions_occupation"))
        conn.execute(text("DELETE FROM alertes_occupation"))

        # Insérer nouvelles prévisions
        if not df_pred.empty:
            df_pred.to_sql('previsions_occupation', conn, if_exists='append', index=False)

        # Insérer alertes
        if not df_alerts.empty:
            df_alerts.to_sql('alertes_occupation', conn, if_exists='append', index=False)

    print(f"\n✅ Prévisions générées : {len(df_pred)} lignes")
    print(f"⚠️ Alertes générées : {len(df_alerts)} lignes")

    # Résumé par service
    if not df_pred.empty:
        print("\n📈 Résumé par service (moyenne des prévisions sur 30 jours) :")
        resume = df_pred.groupby('service_sk').agg({
            'occupation_predite': 'mean',
            'intervalle_inf': 'mean',
            'intervalle_sup': 'mean'
        }).round(2)
        print(resume)


# ==========================================================
# EXÉCUTION PRINCIPALE
# ==========================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  PRÉVISION D'OCCUPATION DES LITS (ARIMA + Prophet + Régression)")
    print("=" * 60)

    engine = get_engine()
    generer_previsions(engine)

    print("\n" + "=" * 60)
    print("  ✅ EXÉCUTION TERMINÉE AVEC SUCCÈS")
    print("=" * 60)
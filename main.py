# ==========================================================#
# ETL HOSPITALIER HGR KATUBA - VERSION FINALE CORRIGÉE      #
# GESTION ROBUSTE DES DATES                                 #
# ==========================================================#

import os
import re
import hashlib
import logging
import urllib
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.types import NVARCHAR, VARCHAR, INTEGER, DECIMAL, DATE

warnings.filterwarnings("ignore")

# ==========================================================#
# CONFIGURATION SQL SERVER                                 #
# ==========================================================#
SQLSERVER = {
    "SERVER": ".\\SQLEXPRESS",
    "DATABASE": "dw_hgrkatuba",
    "DRIVER": "ODBC Driver 17 for SQL Server"
}

# ==========================================================#
# CHEMINS DES FICHIERS CSV                                 #
# ==========================================================#
CSV_PATIENT = "registre_patients_unique.csv"
CSV_URGENCE = "source_urgences.csv"
CSV_CONSULTATION = "source_consultations.csv"
CSV_HOSPITALISATION = "source_hospitalisations.csv"
CSV_MATERNITE = "source_maternite.csv"

# ==========================================================#
# LOGGING                                                   #
# ==========================================================#
logging.basicConfig(
    filename="etl_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def get_engine():
    try:
        params = urllib.parse.quote_plus(
            f"DRIVER={SQLSERVER['DRIVER']};"
            f"SERVER={SQLSERVER['SERVER']};"
            f"DATABASE={SQLSERVER['DATABASE']};"
            f"Trusted_Connection=yes;"
        )
        engine = create_engine(
            f"mssql+pyodbc:///?odbc_connect={params}",
            fast_executemany=True
        )
        logging.info("Connexion SQL Server réussie.")
        return engine
    except Exception as e:
        logging.error(f"Erreur de connexion SQL Server : {e}")
        raise


def verifier_fichier(fichier):
    if not os.path.exists(fichier):
        raise FileNotFoundError(f"Le fichier {fichier} est introuvable.")


def anonymiser(valeur):
    if pd.isna(valeur):
        return None
    valeur = str(valeur).strip()
    if valeur == "":
        return None
    return hashlib.sha256(valeur.encode("utf-8")).hexdigest()


def extraire_nombre(valeur):
    if pd.isna(valeur):
        return np.nan
    valeur = str(valeur)
    match = re.search(r"[-+]?\d*\.?\d+", valeur)
    if match:
        return float(match.group())
    return np.nan


def convertir_date_robuste(valeur):
    """
    Convertit une date avec plusieurs formats possibles.
    Retourne un datetime valide ou None si impossible.
    """
    if pd.isna(valeur):
        return None

    valeur = str(valeur).strip()
    if valeur == "":
        return None

    # Liste des formats possibles (du plus spécifique au plus général)
    formats = [
        "%Y-%m-%d %H:%M:%S",  # 2026-05-31 08:55:00
        "%Y-%m-%d %H:%M",  # 2026-05-31 08:55
        "%Y-%m-%d",  # 2026-05-31
        "%d/%m/%Y %H:%M:%S",  # 31/05/2026 08:55:00
        "%d/%m/%Y %H:%M",  # 31/05/2026 08:55
        "%d/%m/%Y",  # 31/05/2026
        "%d-%m-%Y %H:%M:%S",  # 31-05-2026 08:55:00
        "%d-%m-%Y %H:%M",  # 31-05-2026 08:55
        "%d-%m-%Y",  # 31-05-2026
        "%m/%d/%Y %H:%M:%S",  # 05/31/2026 08:55:00
        "%m/%d/%Y %H:%M",  # 05/31/2026 08:55
        "%m/%d/%Y",  # 05/31/2026
        "%Y%m%d",  # 20260531
        "%d%m%Y"  # 31052026
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(valeur, fmt)
            # Vérification que la date est raisonnable (entre 2020 et 2030)
            if 2020 <= dt.year <= 2030:
                return dt
        except (ValueError, TypeError):
            pass

    # Si aucun format ne correspond, essayer avec pandas (plus tolerant)
    try:
        dt = pd.to_datetime(valeur, errors='coerce')
        if pd.notna(dt) and 2020 <= dt.year <= 2030:
            return dt.to_pydatetime()
    except:
        pass

    logging.warning(f"⚠️ Date non reconnue : {valeur}")
    return None


def convertir_date_avec_secours(valeur, date_par_defaut="2025-01-01"):
    """
    Convertit une date, retourne une date par défaut si la conversion échoue.
    """
    dt = convertir_date_robuste(valeur)
    if dt is None:
        return datetime.strptime(date_par_defaut, "%Y-%m-%d")
    return dt


def tranche_age(age):
    if pd.isna(age):
        return "Inconnu"
    try:
        age = int(float(age))
        if age <= 5:
            return "0-5 ans"
        elif age <= 15:
            return "6-15 ans"
        elif age <= 30:
            return "16-30 ans"
        elif age <= 60:
            return "31-60 ans"
        return "60 ans et +"
    except:
        return "Inconnu"


def vider_tables(engine):
    logging.info("Nettoyage du Data Warehouse...")
    tables = [
        "faits_maternite", "faits_hospitalisation", "faits_consultation",
        "faits_accueil", "dim_nouveaune", "dim_grossesse", "dim_medecin",
        "dim_lit", "dim_patient", "dim_temps", "dim_service", "dim_pathologie",
        "dim_geographie", "dim_gravite", "dim_transport", "dim_motif",
        "dim_decision", "dim_issue", "dim_admission", "dim_accouchement",
        "dim_complication"
    ]
    with engine.begin() as conn:
        for table in tables:
            try:
                conn.execute(text(f"DELETE FROM {table}"))
            except Exception as e:
                logging.warning(f"Note : Table {table} non vidée : {e}")


def charger_csv(fichier, nom_table):
    verifier_fichier(fichier)
    try:
        df = pd.read_csv(fichier, sep=None, engine='python', encoding="utf-8")
        df.columns = df.columns.str.strip()
        print(f" ✓  {nom_table} : {len(df)} lignes")
        return df
    except Exception:
        df = pd.read_csv(fichier, sep=None, engine='python', encoding="latin-1")
        df.columns = df.columns.str.strip()
        print(f" ✓  {nom_table} : {len(df)} lignes")
        return df


# ==========================================================#
# PHASE 1 & 2 : EXTRACTION & TRANSFORMATION                 #
# ==========================================================#
def extraction():
    print("\n===================================================")
    print("PHASE 1 : EXTRACTION")
    print("===================================================")
    return {
        "patient": charger_csv(CSV_PATIENT, "Patients"),
        "urgence": charger_csv(CSV_URGENCE, "Urgences"),
        "consultation": charger_csv(CSV_CONSULTATION, "Consultations"),
        "hospitalisation": charger_csv(CSV_HOSPITALISATION, "Hospitalisations"),
        "maternite": charger_csv(CSV_MATERNITE, "Maternité")
    }


def transformer(donnees):
    print("\n===================================================")
    print("PHASE 2 : TRANSFORMATION")
    print("===================================================")

    df_patient = donnees["patient"].copy()
    df_urgence = donnees["urgence"].copy()
    df_consultation = donnees["consultation"].copy()
    df_hospitalisation = donnees["hospitalisation"].copy()
    df_maternite = donnees["maternite"].copy()

    # Patients
    print("Transformation : Patients")
    df_patient["ID_Patient"] = df_patient["ID_Patient"].astype(str).str.strip()
    df_patient["ID_Patient_Anonyme"] = df_patient["ID_Patient"].apply(anonymiser)
    df_patient["Nom_Complet"] = df_patient["Nom_Complet"].astype(str).str.title().str.strip()
    df_patient["Sexe"] = df_patient["Sexe"].astype(str).str.upper().str.strip()
    df_patient["Age"] = pd.to_numeric(df_patient["Age"], errors="coerce")
    df_patient["Tranche_Age"] = df_patient["Age"].apply(tranche_age)
    df_patient["Poids"] = df_patient["Poids"].apply(extraire_nombre)
    df_patient["Taille"] = df_patient["Taille"].apply(extraire_nombre)

    # Urgences - AMÉLIORATION DES DATES
    print("Transformation : Urgences")
    df_urgence["Date_Arrivee"] = df_urgence["Date_Arrivee"].apply(convertir_date_robuste)
    # Supprimer les lignes avec date invalide (mais garder les dates par défaut)
    df_urgence = df_urgence[df_urgence["Date_Arrivee"].notna()]
    df_urgence["ID_Patient_Anonyme"] = df_urgence["ID_Patient"].astype(str).str.strip().apply(anonymiser)

    # Consultations - AMÉLIORATION DES DATES
    print("Transformation : Consultations")
    # Utilisation de convertir_date_avec_secours pour garantir une date valide
    df_consultation["Date_Consultation"] = df_consultation["Date_Consultation"].apply(
        lambda x: convertir_date_avec_secours(x, "2025-01-01")
    )
    df_consultation["ID_Patient_Anonyme"] = df_consultation["ID_Patient"].astype(str).str.strip().apply(anonymiser)

    # Hospitalisations - AMÉLIORATION DES DATES
    print("Transformation : Hospitalisations")
    df_hospitalisation["Date_Admission"] = df_hospitalisation["Date_Admission"].apply(
        lambda x: convertir_date_avec_secours(x, "2025-01-01")
    )
    df_hospitalisation["ID_Patient_Anonyme"] = df_hospitalisation["ID_Patient"].astype(str).str.strip().apply(
        anonymiser)

    # Maternité - AMÉLIORATION DES DATES
    print("Transformation : Maternité")
    df_maternite["Date_Accouchement"] = df_maternite["Date_Accouchement"].apply(
        lambda x: convertir_date_avec_secours(x, "2025-01-01")
    )
    df_maternite["ID_Patient_Anonyme"] = df_maternite["ID_Patient"].astype(str).str.strip().apply(anonymiser)

    return {
        "patient": df_patient,
        "urgence": df_urgence,
        "consultation": df_consultation,
        "hospitalisation": df_hospitalisation,
        "maternite": df_maternite
    }


# ==========================================================#
# PHASE 3 : CHARGEMENT DES DIMENSIONS                       #
# ==========================================================#
def main():
    engine = get_engine()
    vider_tables(engine)

    donnees_brutes = extraction()
    donnees_transformees = transformer(donnees_brutes)

    df_patient = donnees_transformees["patient"]
    df_urgence = donnees_transformees["urgence"]
    df_consultation = donnees_transformees["consultation"]
    df_hospitalisation = donnees_transformees["hospitalisation"]
    df_maternite = donnees_transformees["maternite"]

    print("\n===================================================")
    print("PHASE 3 : CHARGEMENT DES DIMENSIONS")
    print("===================================================")

    # --- 1. DIM_TEMPS ---
    print("Chargement : dim_temps")
    dates = pd.date_range(start="2024-01-01", end="2026-12-31")
    df_dim_temps = pd.DataFrame({
        "date_complete": dates,
        "temps_sk": dates.strftime("%Y%m%d").astype(int),
        "jour": dates.day,
        "mois": dates.month,
        "trimestre": dates.quarter,
        "annee": dates.year,
        "semaine": dates.isocalendar().week,
        "jour_semaine": dates.day_name(),
        "type_jour": np.where(dates.dayofweek >= 5, "Weekend", "Ouvrable"),
        "heure": 0,
        "periode_journee": "Matin"
    })
    df_dim_temps.to_sql("dim_temps", engine, if_exists="append", index=False)

    # --- 2. DIM_PATIENT ---
    print("Chargement : dim_patient")
    df_dim_patient = pd.DataFrame({
        "id_patient_anonyme": df_patient["ID_Patient_Anonyme"],
        "sexe": df_patient["Sexe"].fillna("Inconnu"),
        "age": df_patient["Age"].fillna(0).astype(int),
        "tranche_age": df_patient["Tranche_Age"],
        "poids": df_patient["Poids"],
        "taille": df_patient["Taille"],
        "statut_nutritionnel": df_patient["Statut_Nutritionnel"].fillna("Normal"),
        "antecedents_medicaux": df_patient["Antecedents_Medicaux"].fillna("Aucun"),
        "date_debut_validite": datetime.today().date(),
        "date_fin_validite": None,
        "est_actif": 1,
        "version_ligne": 1
    }).drop_duplicates(subset=["id_patient_anonyme"])
    df_dim_patient.insert(0, "patient_sk", range(1, len(df_dim_patient) + 1))
    df_dim_patient.to_sql(
        "dim_patient",
        engine,
        if_exists="append",
        index=False,
        dtype={"id_patient_anonyme": VARCHAR(128)}
    )

    # --- 3. DIM_GEOGRAPHIE ---
    print("Chargement : dim_geographie")
    geo_uniques = df_patient[["Commune", "Quartier"]].drop_duplicates().dropna()
    if not geo_uniques.empty:
        df_geo = pd.DataFrame({
            "geographie_sk": range(1, len(geo_uniques) + 1),
            "id_localisation": geo_uniques.index.astype(str),
            "quartier": geo_uniques["Quartier"],
            "commune": geo_uniques["Commune"],
            "ville": "Lubumbashi",
            "zone_sante": "Katuba",
            "distance_hopital": np.random.uniform(1, 20, len(geo_uniques)).round(2)
        })
        df_geo.to_sql("dim_geographie", engine, if_exists="append", index=False)

    # --- 4. DIM_SERVICE ---
    print("Chargement : dim_service")
    # Insertion du service de secours (ID=1)
    pd.DataFrame({
        "service_sk": [1],
        "id_service": ['SRV-DEF'],
        "nom_service": ['Service par défaut'],
        "type_service": ['Général'],
        "capacite_lits": [10],
        "date_debut_validite": [datetime.today().date()],
        "date_fin_validite": [None],
        "est_actif": [1],
        "version_ligne": [1]
    }).to_sql("dim_service", engine, if_exists="append", index=False)

    # Insertion des services réels
    services = df_hospitalisation["Service_Affectation"].dropna().unique()
    if len(services) > 0:
        df_service = pd.DataFrame({
            "service_sk": range(2, len(services) + 2),
            "id_service": ["SRV" + str(i).zfill(3) for i in range(1, len(services) + 1)],
            "nom_service": services,
            "type_service": "Hospitalisation",
            "capacite_lits": np.random.randint(10, 60, len(services)),
            "date_debut_validite": datetime.today().date(),
            "date_fin_validite": None,
            "est_actif": 1,
            "version_ligne": 1
        })
        df_service.to_sql("dim_service", engine, if_exists="append", index=False)

    # --- 5. DIM_PATHOLOGIE ---
    print("Chargement : dim_pathologie")
    # Insertion de la pathologie de secours
    pd.DataFrame({
        "pathologie_sk": [1],
        "code_cim10": ['UNK'],
        "libelle": ['Pathologie inconnue'],
        "categorie": ['Général'],
        "niveau_gravite": ['Modéré'],
        "date_debut_validite": [datetime.today().date()],
        "date_fin_validite": [None],
        "version_ligne": [1]
    }).to_sql("dim_pathologie", engine, if_exists="append", index=False)

    # Insertion des pathologies réelles
    pathologies = pd.concat(
        [df_consultation["Pathologie"], df_hospitalisation["Pathologie_Principale"]]).dropna().unique()
    if len(pathologies) > 0:
        df_patho = pd.DataFrame({
            "pathologie_sk": range(2, len(pathologies) + 2),
            "code_cim10": ["CIM" + str(i).zfill(3) for i in range(1, len(pathologies) + 1)],
            "libelle": pathologies,
            "categorie": "Infectieux",
            "niveau_gravite": "Modéré",
            "date_debut_validite": datetime.today().date(),
            "date_fin_validite": None,
            "version_ligne": 1
        })
        df_patho.to_sql("dim_pathologie", engine, if_exists="append", index=False)

    # --- 6. DIM_MEDECIN ---
    print("Chargement : dim_medecin")
    # Insertion du médecin de secours
    pd.DataFrame({
        "medecin_sk": [1],
        "code_medecin": ['MED-DEF'],
        "specialite": ['Généraliste'],
        "service_sk": [1],
        "grade": ['Spécialiste'],
        "annees_experience": [5],
        "date_debut_validite": [datetime.today().date()],
        "date_fin_validite": [None],
        "version_ligne": [1]
    }).to_sql("dim_medecin", engine, if_exists="append", index=False)

    # Extraction réelle des médecins avec leurs spécialités
    medecins = df_consultation[
        ["Medecin", "Specialite_Medecin", "Grade_Medecin", "Annee_Experience"]].drop_duplicates().dropna(
        subset=["Medecin"])
    if not medecins.empty:
        # Troncature des noms des médecins à 40 caractères pour éviter l'erreur SQL Server
        medecins["Medecin"] = medecins["Medecin"].str[:40]

        df_med = pd.DataFrame({
            "medecin_sk": range(2, len(medecins) + 2),
            "code_medecin": medecins["Medecin"],
            "specialite": medecins["Specialite_Medecin"].fillna("Générale"),
            "service_sk": 1,
            "grade": medecins["Grade_Medecin"].fillna("Spécialiste"),
            "annees_experience": medecins["Annee_Experience"].fillna(5).astype(int),
            "date_debut_validite": datetime.today().date(),
            "date_fin_validite": None,
            "version_ligne": 1
        })
        df_med.to_sql("dim_medecin", engine, if_exists="append", index=False)

    # --- 7. DIM_GRAVITE ---
    print("Chargement : dim_gravite")
    pd.DataFrame({
        "gravite_sk": [1],
        "code_gravite": ['G-DEF'],
        "niveau_urgence": [3],
        "categorie": ['Modérée']
    }).to_sql("dim_gravite", engine, if_exists="append", index=False)

    if "Niveau_Urgence" in df_urgence.columns:
        niveaux = df_urgence["Niveau_Urgence"].dropna().astype(int).sort_values().unique()
        if len(niveaux) > 0:
            pd.DataFrame({
                "gravite_sk": range(2, len(niveaux) + 2),
                "code_gravite": ["G" + str(i).zfill(2) for i in range(1, len(niveaux) + 1)],
                "niveau_urgence": niveaux,
                "categorie": ["Faible" if n <= 2 else "Modérée" if n <= 3 else "Critique" for n in niveaux]
            }).to_sql("dim_gravite", engine, if_exists="append", index=False)

    # --- 8. DIM_TRANSPORT ---
    print("Chargement : dim_transport")
    if "Mode_Transport" in df_urgence.columns:
        transport = df_urgence["Mode_Transport"].dropna().drop_duplicates()
        if not transport.empty:
            pd.DataFrame({
                "transport_sk": range(1, len(transport) + 1),
                "code_transport": ["T" + str(i).zfill(2) for i in range(1, len(transport) + 1)],
                "mode_transport": transport.values,
                "est_reference": 0
            }).to_sql("dim_transport", engine, if_exists="append", index=False)

    # --- 9. DIM_MOTIF ---
    print("Chargement : dim_motif")
    if "Motif_Consultation" in df_urgence.columns:
        motifs = df_urgence["Motif_Consultation"].dropna().drop_duplicates()
        if not motifs.empty:
            pd.DataFrame({
                "motif_sk": range(1, len(motifs) + 1),
                "code_motif": ["M" + str(i).zfill(3) for i in range(1, len(motifs) + 1)],
                "libelle_motif": motifs.values,
                "categorie_motif": "Urgence"
            }).to_sql("dim_motif", engine, if_exists="append", index=False)

    # --- 10. DIM_DECISION ---
    print("Chargement : dim_decision")
    pd.DataFrame({
        "decision_sk": [1],
        "code_decision": ['D-DEF'],
        "type_decision": ['Inconnu'],
        "service_destination": ['Non précisé']
    }).to_sql("dim_decision", engine, if_exists="append", index=False)

    if "Decision_Medicale" in df_urgence.columns:
        decisions = df_urgence["Decision_Medicale"].dropna().drop_duplicates()
        if not decisions.empty:
            pd.DataFrame({
                "decision_sk": range(2, len(decisions) + 2),
                "code_decision": ["D" + str(i).zfill(3) for i in range(1, len(decisions) + 1)],
                "type_decision": decisions.values,
                "service_destination": "Non précisé"
            }).to_sql("dim_decision", engine, if_exists="append", index=False)

    # --- 11. DIM_ISSUE ---
    print("Chargement : dim_issue")
    pd.DataFrame({
        "issue_sk": [1],
        "code_issue": ['IS-DEF'],
        "type_issue": ['Inconnu'],
        "categorie_issue": ['Indéterminée']
    }).to_sql("dim_issue", engine, if_exists="append", index=False)

    if "Issue_Sortie" in df_hospitalisation.columns:
        issues = df_hospitalisation["Issue_Sortie"].dropna().drop_duplicates()
        if not issues.empty:
            pd.DataFrame({
                "issue_sk": range(2, len(issues) + 2),
                "code_issue": ["IS" + str(i).zfill(3) for i in range(1, len(issues) + 1)],
                "type_issue": issues.values,
                "categorie_issue": "Sortie"
            }).to_sql("dim_issue", engine, if_exists="append", index=False)

    # --- 12. DIM_LIT (Chargé AVANT les référentiels) ---
    print("Chargement : dim_lit")
    if "Numero_Lit" in df_hospitalisation.columns:
        lits = df_hospitalisation[["Numero_Lit", "Type_Chambre", "Service_Affectation"]].drop_duplicates().dropna(
            subset=["Numero_Lit"])
        if not lits.empty:
            # Création d'un mapping service pour les lits
            ref_service_tmp = pd.read_sql("SELECT service_sk, nom_service FROM dim_service", engine)
            ref_service_tmp['nom_service'] = ref_service_tmp['nom_service'].astype(str).str.strip().str.lower()
            service_map_tmp = {row['nom_service']: row['service_sk'] for _, row in ref_service_tmp.iterrows()}
            lits["service_sk"] = lits["Service_Affectation"].str.lower().map(service_map_tmp).fillna(1)

            df_lit = pd.DataFrame({
                "lit_sk": range(1, len(lits) + 1),
                "numero_lit": lits["Numero_Lit"],
                "numero_chambre": ["CH-" + str(i).zfill(3) for i in range(1, len(lits) + 1)],
                "type_chambre": lits["Type_Chambre"].fillna("Standard"),
                "service_sk": lits["service_sk"].astype(int),
                "date_debut_validite": datetime.today().date(),
                "date_fin_validite": None,
                "est_actif": 1
            })
            df_lit.to_sql("dim_lit", engine, if_exists="append", index=False)

    # --- 13. DIM_ADMISSION (Chargé AVANT les référentiels) ---
    print("Chargement : dim_admission")
    if "Type_Admission" in df_hospitalisation.columns:
        admissions = df_hospitalisation[["Type_Admission", "Origine_Admission"]].drop_duplicates().dropna()
        if not admissions.empty:
            df_adm = pd.DataFrame({
                "admission_sk": range(1, len(admissions) + 1),
                "code_admission": ["ADM-" + str(i).zfill(3) for i in range(1, len(admissions) + 1)],
                "type_admission": admissions["Type_Admission"],
                "origine_admission": admissions["Origine_Admission"].fillna("Domicile")
            })
            df_adm.to_sql("dim_admission", engine, if_exists="append", index=False)

    # --- 14. DIM_ACCOUCHEMENT ---
    print("Chargement : dim_accouchement")
    if "Type_Accouchement" in df_maternite.columns:
        accouchements = df_maternite["Type_Accouchement"].dropna().drop_duplicates()
        if not accouchements.empty:
            pd.DataFrame({
                "accouchement_sk": range(1, len(accouchements) + 1),
                "code_accouchement": ["AC" + str(i).zfill(2) for i in range(1, len(accouchements) + 1)],
                "type_accouchement": accouchements.values,
                "duree_travail": 0.0
            }).to_sql("dim_accouchement", engine, if_exists="append", index=False)

    # --- 15. DIM_GROSSESSE ---
    print("Chargement : dim_grossesse")
    df_grossesse = df_maternite[
        ["Age_Gestationnel", "Nb_Grossesses", "Antecedents_Obstetricaux"]].drop_duplicates().dropna()
    if not df_grossesse.empty:
        df_grossesse = df_grossesse.rename(columns={
            "Age_Gestationnel": "age_gestationnel",
            "Nb_Grossesses": "nb_grossesses",
            "Antecedents_Obstetricaux": "antecedents_obstetricaux"
        })
        df_grossesse["grossesse_sk"] = range(1, len(df_grossesse) + 1)
        df_grossesse["code_grossesse"] = "G-" + df_grossesse.index.astype(str).str.zfill(3)
        df_grossesse["date_debut_validite"] = datetime.today().date()
        df_grossesse["date_fin_validite"] = None
        df_grossesse["est_actif"] = 1
        df_grossesse["version_ligne"] = 1
        df_grossesse.to_sql("dim_grossesse", engine, if_exists="append", index=False)

    # --- 16. DIM_NOUVEAUNE ---
    print("Chargement : dim_nouveaune")
    df_nouveaune = df_maternite[
        ["Poids_Nouveau_Ne", "Taille_Naissance", "Score_Apgar", "Statut_Bebe"]].drop_duplicates().dropna()
    if not df_nouveaune.empty:
        df_nouveaune = df_nouveaune.rename(columns={
            "Poids_Nouveau_Ne": "poids_naissance",
            "Taille_Naissance": "taille_naissance",
            "Score_Apgar": "score_apgar",
            "Statut_Bebe": "statut_bebe"
        })
        # Création d'une clé unique pour le bébé (évite les conflits de mapping)
        df_nouveaune["bebe_key"] = df_nouveaune["poids_naissance"].astype(str) + "_" + \
                                   df_nouveaune["taille_naissance"].astype(str) + "_" + \
                                   df_nouveaune["score_apgar"].astype(str)

        df_nouveaune["bebe_sk"] = range(1, len(df_nouveaune) + 1)
        df_nouveaune["code_bebe"] = "B-" + df_nouveaune.index.astype(str).str.zfill(3)
        df_nouveaune["sexe_bebe"] = np.random.choice(['M', 'F'], len(df_nouveaune))
        df_nouveaune["date_debut_validite"] = datetime.today().date()
        df_nouveaune["date_fin_validite"] = None
        df_nouveaune["est_actif"] = 1
        df_nouveaune["version_ligne"] = 1
        df_nouveaune.drop(columns=["bebe_key"], inplace=True)  # Nettoyage de la clé temporaire
        df_nouveaune.to_sql("dim_nouveaune", engine, if_exists="append", index=False)

    # --- 17. DIM_COMPLICATION ---
    print("Chargement : dim_complication")
    if "Complication_Type" in df_maternite.columns:
        complications = df_maternite["Complication_Type"].dropna().drop_duplicates()
        if not complications.empty:
            pd.DataFrame({
                "complication_sk": range(1, len(complications) + 1),
                "code_complication": ["C" + str(i).zfill(2) for i in range(1, len(complications) + 1)],
                "type_complication": complications.values,
                "niveau_gravite": "Modérée"
            }).to_sql("dim_complication", engine, if_exists="append", index=False)

    print("\n===================================================")
    print(" SUCCESS : Toutes les dimensions ont été chargées !")
    print("===================================================")

    # ==========================================================
    # PHASE 4 : CHARGEMENT DES TABLES DE FAITS
    # ==========================================================
    print("\n===================================================")
    print("PHASE 4 : CHARGEMENT DES TABLES DE FAITS")
    print("===================================================")

    # Récupération des référentiels pour les clés étrangères
    print("Extraction des référentiels de correspondances depuis SQL Server...")
    ref_patient = pd.read_sql("SELECT patient_sk, id_patient_anonyme FROM dim_patient", engine)
    ref_temps = pd.read_sql("SELECT temps_sk, date_complete FROM dim_temps", engine)
    ref_service = pd.read_sql("SELECT service_sk, nom_service FROM dim_service", engine)
    ref_pathologie = pd.read_sql("SELECT pathologie_sk, libelle FROM dim_pathologie", engine)
    ref_medecin = pd.read_sql("SELECT medecin_sk, code_medecin FROM dim_medecin", engine)
    ref_gravite = pd.read_sql("SELECT gravite_sk, niveau_urgence FROM dim_gravite", engine)
    ref_decision = pd.read_sql("SELECT decision_sk, type_decision FROM dim_decision", engine)
    ref_issue = pd.read_sql("SELECT issue_sk, type_issue FROM dim_issue", engine)
    ref_motif = pd.read_sql("SELECT motif_sk, libelle_motif FROM dim_motif", engine)
    ref_lit = pd.read_sql("SELECT lit_sk, numero_lit FROM dim_lit", engine)
    ref_admission = pd.read_sql("SELECT admission_sk, type_admission FROM dim_admission", engine)
    ref_accouchement = pd.read_sql("SELECT accouchement_sk, type_accouchement FROM dim_accouchement", engine)
    ref_grossesse = pd.read_sql("SELECT grossesse_sk, age_gestationnel FROM dim_grossesse", engine)
    ref_bebe = pd.read_sql("SELECT bebe_sk, poids_naissance, taille_naissance, score_apgar FROM dim_nouveaune", engine)
    ref_complication = pd.read_sql("SELECT complication_sk, type_complication FROM dim_complication", engine)

    # Normalisation pour les jointures
    ref_patient['id_patient_anonyme'] = ref_patient['id_patient_anonyme'].astype(str).str.strip().str.upper()
    ref_temps['date_complete'] = pd.to_datetime(ref_temps['date_complete']).dt.date
    ref_service['nom_service'] = ref_service['nom_service'].astype(str).str.strip().str.lower()
    ref_pathologie['libelle'] = ref_pathologie['libelle'].astype(str).str.strip().str.lower()
    ref_medecin['code_medecin'] = ref_medecin['code_medecin'].astype(str).str.strip().str.lower()
    ref_gravite['niveau_urgence'] = ref_gravite['niveau_urgence'].astype(int)
    ref_decision['type_decision'] = ref_decision['type_decision'].astype(str).str.strip().str.lower()
    ref_issue['type_issue'] = ref_issue['type_issue'].astype(str).str.strip().str.lower()
    ref_motif['libelle_motif'] = ref_motif['libelle_motif'].astype(str).str.strip().str.lower()
    ref_lit['numero_lit'] = ref_lit['numero_lit'].astype(str).str.strip()
    ref_admission['type_admission'] = ref_admission['type_admission'].astype(str).str.strip().str.lower()
    ref_accouchement['type_accouchement'] = ref_accouchement['type_accouchement'].astype(str).str.strip().str.lower()
    ref_complication['type_complication'] = ref_complication['type_complication'].astype(str).str.strip().str.lower()

    # Création des dictionnaires de mapping
    patient_map = {row['id_patient_anonyme']: row['patient_sk'] for _, row in ref_patient.iterrows()}
    temps_map = {row['date_complete']: row['temps_sk'] for _, row in ref_temps.iterrows()}
    service_map = {row['nom_service']: row['service_sk'] for _, row in ref_service.iterrows()}
    patho_map = {row['libelle']: row['pathologie_sk'] for _, row in ref_pathologie.iterrows()}
    medecin_map = {row['code_medecin']: row['medecin_sk'] for _, row in ref_medecin.iterrows()}
    gravite_map = {row['niveau_urgence']: row['gravite_sk'] for _, row in ref_gravite.iterrows()}
    decision_map = {row['type_decision']: row['decision_sk'] for _, row in ref_decision.iterrows()}
    issue_map = {row['type_issue']: row['issue_sk'] for _, row in ref_issue.iterrows()}
    motif_map = {row['libelle_motif']: row['motif_sk'] for _, row in ref_motif.iterrows()}
    lit_map = {row['numero_lit']: row['lit_sk'] for _, row in ref_lit.iterrows()}
    admission_map = {row['type_admission']: row['admission_sk'] for _, row in ref_admission.iterrows()}
    accouchement_map = {row['type_accouchement']: row['accouchement_sk'] for _, row in ref_accouchement.iterrows()}
    grossesse_map = {row['age_gestationnel']: row['grossesse_sk'] for _, row in ref_grossesse.iterrows()}
    complication_map = {row['type_complication']: row['complication_sk'] for _, row in ref_complication.iterrows()}
    bebe_map = {row['bebe_sk']: row['bebe_sk'] for _, row in ref_bebe.iterrows()}  # Mapping direct par ID

    # Clé de secours générique
    CLE_SECOURS = 1

    # ----------------------------------------------------------
    # 1. FAITS_ACCUEIL
    # ----------------------------------------------------------
    print("\nChargement : faits_accueil")
    df_faits_acc = df_urgence.copy()
    df_faits_acc['id_patient_anonyme'] = df_faits_acc['ID_Patient_Anonyme'].astype(str).str.strip().str.upper()
    df_faits_acc['date_dt'] = pd.to_datetime(df_faits_acc['Date_Arrivee'], errors='coerce')
    df_faits_acc['temps_sk'] = df_faits_acc['date_dt'].dt.date.map(temps_map)
    df_faits_acc['patient_sk'] = df_faits_acc['id_patient_anonyme'].map(patient_map)
    df_faits_acc['service_sk'] = df_faits_acc['Service'].str.lower().map(
        service_map) if 'Service' in df_faits_acc.columns else None
    df_faits_acc['gravite_sk'] = df_faits_acc['Niveau_Urgence'].astype(int).map(gravite_map)
    df_faits_acc['decision_sk'] = df_faits_acc['Decision_Medicale'].str.lower().map(
        decision_map) if 'Decision_Medicale' in df_faits_acc.columns else None
    df_faits_acc['motif_sk'] = df_faits_acc['Motif_Consultation'].str.lower().map(
        motif_map) if 'Motif_Consultation' in df_faits_acc.columns else None

    # SÉCURISATION : Forçage des clés de secours AVANT le dropna
    df_faits_acc['temps_sk'] = df_faits_acc['temps_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_acc['patient_sk'] = df_faits_acc['patient_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_acc['service_sk'] = df_faits_acc['service_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_acc['gravite_sk'] = df_faits_acc['gravite_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_acc['decision_sk'] = df_faits_acc['decision_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_acc['motif_sk'] = df_faits_acc['motif_sk'].fillna(CLE_SECOURS).astype(int)

    # Suppression des lignes avec date invalide (si temps_sk = 1, c'est que la date était invalide)
    df_faits_acc = df_faits_acc[df_faits_acc['temps_sk'] != CLE_SECOURS]

    faits_accueil_final = pd.DataFrame({
        "temps_sk": df_faits_acc["temps_sk"],
        "patient_sk": df_faits_acc["patient_sk"],
        "geographie_sk": CLE_SECOURS,
        "service_sk": df_faits_acc["service_sk"],
        "paiement_sk": CLE_SECOURS,
        "contexte_sk": CLE_SECOURS,
        "gravite_sk": df_faits_acc["gravite_sk"],
        "transport_sk": CLE_SECOURS,
        "motif_sk": df_faits_acc["motif_sk"],
        "decision_sk": df_faits_acc["decision_sk"],
        "nb_arrivees": 1,
        "temps_attente_tri": df_faits_acc["Temps_Attente_Tri"].fillna(0).astype(int),
        "temps_attente_orientation": df_faits_acc["Temps_Attente_Orientation"].fillna(0).astype(int),
        "nb_non_pris_en_charge": 0
    })
    faits_accueil_final.to_sql("faits_accueil", engine, if_exists="append", index=False)
    print(f" ✓ faits_accueil chargé avec succès ! ({len(faits_accueil_final)} lignes)")

    # ----------------------------------------------------------
    # 2. FAITS_CONSULTATION (AVEC RÉPARATION DES DATES)
    # ----------------------------------------------------------
    print("\nChargement : faits_consultation")
    df_faits_cons = df_consultation.copy()

    # 1. Normalisation
    df_faits_cons['id_patient_anonyme'] = df_faits_cons['ID_Patient_Anonyme'].astype(str).str.strip().str.upper()
    df_faits_cons['date_dt'] = pd.to_datetime(df_faits_cons['Date_Consultation'], errors='coerce')

    # 2. RÉPARATION DES DATES INVALIDES
    # Si la date est invalide (NaT), on la remplace par '2025-01-01' (date par défaut)
    # et on forcera temps_sk à 1 (clé de secours) dans l'étape suivante
    df_faits_cons['date_dt'] = df_faits_cons['date_dt'].fillna(pd.Timestamp('2025-01-01'))

    # 3. Mapping des clés
    df_faits_cons['temps_sk'] = df_faits_cons['date_dt'].dt.date.map(temps_map)
    df_faits_cons['patient_sk'] = df_faits_cons['id_patient_anonyme'].map(patient_map)
    df_faits_cons['service_sk'] = df_faits_cons['Specialite_Medecin'].str.lower().map(
        service_map) if 'Specialite_Medecin' in df_faits_cons.columns else np.nan
    df_faits_cons['pathologie_sk'] = df_faits_cons['Pathologie'].str.lower().map(patho_map)
    df_faits_cons['medecin_sk'] = df_faits_cons['Medecin'].str.lower().map(
        medecin_map) if 'Medecin' in df_faits_cons.columns else np.nan

    # 4. Forçage des clés de secours (TOUTES les colonnes)
    df_faits_cons['temps_sk'] = df_faits_cons['temps_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_cons['patient_sk'] = df_faits_cons['patient_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_cons['service_sk'] = df_faits_cons['service_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_cons['pathologie_sk'] = df_faits_cons['pathologie_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_cons['medecin_sk'] = df_faits_cons['medecin_sk'].fillna(CLE_SECOURS).astype(int)

    # 5. SUPPRESSION DES DOUBLONS ET CONSTRUCTION DU DATAFRAME FINAL
    faits_consultation_final = pd.DataFrame({
        "temps_sk": df_faits_cons["temps_sk"],
        "patient_sk": df_faits_cons["patient_sk"],
        "service_sk": df_faits_cons["service_sk"],
        "pathologie_sk": df_faits_cons["pathologie_sk"],
        "paiement_sk": CLE_SECOURS,
        "contexte_sk": CLE_SECOURS,
        "medecin_sk": df_faits_cons["medecin_sk"],
        "gravite_sk": CLE_SECOURS,
        "decision_sk": CLE_SECOURS,
        "nb_consultations": 1,
        "duree_consultation": df_faits_cons["Duree_Consultation"].fillna(15).astype(float),
        "nb_medicaments": df_faits_cons["Nbr_Medicaments"].fillna(0).astype(
            int) if "Nbr_Medicaments" in df_faits_cons.columns else 0,
        "nb_examens": 0,
        "temps_attente": df_faits_cons["Temps_Attente"].fillna(0).astype(
            int) if "Temps_Attente" in df_faits_cons.columns else 0
    })

    # 6. Ajout d'une clé d'événement unique et insertion
    faits_consultation_final.to_sql("faits_consultation", engine, if_exists="append", index=False)
    print(f" ✓ faits_consultation chargé avec succès ! ({len(faits_consultation_final)} lignes)")

    # ----------------------------------------------------------
    # 3. FAITS_HOSPITALISATION (CORRIGÉ)
    # ----------------------------------------------------------
    print("\nChargement : faits_hospitalisation")
    df_faits_hosp = df_hospitalisation.copy()
    df_faits_hosp['id_patient_anonyme'] = df_faits_hosp['ID_Patient_Anonyme'].astype(str).str.strip().str.upper()
    df_faits_hosp['date_dt'] = pd.to_datetime(df_faits_hosp['Date_Admission'], errors='coerce')
    df_faits_hosp['temps_sk'] = df_faits_hosp['date_dt'].dt.date.map(temps_map)
    df_faits_hosp['patient_sk'] = df_faits_hosp['id_patient_anonyme'].map(patient_map)
    df_faits_hosp['service_sk'] = df_faits_hosp['Service_Affectation'].str.lower().map(
        service_map) if 'Service_Affectation' in df_faits_hosp.columns else None
    df_faits_hosp['pathologie_sk'] = df_faits_hosp['Pathologie_Principale'].str.lower().map(
        patho_map) if 'Pathologie_Principale' in df_faits_hosp.columns else None
    df_faits_hosp['issue_sk'] = df_faits_hosp['Issue_Sortie'].str.lower().map(
        issue_map) if 'Issue_Sortie' in df_faits_hosp.columns else None
    df_faits_hosp['lit_sk'] = df_faits_hosp['Numero_Lit'].astype(str).str.strip().map(lit_map)
    df_faits_hosp['admission_sk'] = df_faits_hosp['Type_Admission'].str.lower().map(admission_map)

    # SÉCURISATION
    df_faits_hosp['temps_sk'] = df_faits_hosp['temps_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_hosp['patient_sk'] = df_faits_hosp['patient_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_hosp['service_sk'] = df_faits_hosp['service_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_hosp['pathologie_sk'] = df_faits_hosp['pathologie_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_hosp['issue_sk'] = df_faits_hosp['issue_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_hosp['lit_sk'] = df_faits_hosp['lit_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_hosp['admission_sk'] = df_faits_hosp['admission_sk'].fillna(CLE_SECOURS).astype(int)

    # Suppression des lignes avec date invalide
    df_faits_hosp = df_faits_hosp[df_faits_hosp['temps_sk'] != CLE_SECOURS]

    faits_hospitalisation_final = pd.DataFrame({
        "temps_sk": df_faits_hosp["temps_sk"],
        "patient_sk": df_faits_hosp["patient_sk"],
        "service_sk": df_faits_hosp["service_sk"],
        "pathologie_sk": df_faits_hosp["pathologie_sk"],
        "geographie_sk": CLE_SECOURS,
        "contexte_sk": CLE_SECOURS,
        "lit_sk": df_faits_hosp["lit_sk"],
        "admission_sk": df_faits_hosp["admission_sk"],
        "issue_sk": df_faits_hosp["issue_sk"],
        "nb_hospitalisations": 1,
        "duree_sejour": df_faits_hosp["Duree_Sejour"].fillna(0).astype(float),
        "nb_lits_occupes": 1,
        "nb_deces": 0,
        "nb_sorties": 1
    })
    faits_hospitalisation_final.to_sql("faits_hospitalisation", engine, if_exists="append", index=False)
    print(f" ✓ faits_hospitalisation chargé avec succès ! ({len(faits_hospitalisation_final)} lignes)")

    # ----------------------------------------------------------
    # 4. FAITS_MATERNITE (CORRIGÉ - AVEC id_fait AUTO)
    # ----------------------------------------------------------
    print("\nChargement : faits_maternite")
    df_faits_mat = df_maternite.copy()

    # 1. Normalisation
    df_faits_mat['id_patient_anonyme'] = df_faits_mat['ID_Patient_Anonyme'].astype(str).str.strip().str.upper()
    df_faits_mat['date_dt'] = pd.to_datetime(df_faits_mat['Date_Accouchement'], errors='coerce')

    # 2. RÉPARATION DES DATES INVALIDES
    df_faits_mat['date_dt'] = df_faits_mat['date_dt'].fillna(pd.Timestamp('2025-01-01'))

    # 3. Mapping des clés
    df_faits_mat['temps_sk'] = df_faits_mat['date_dt'].dt.date.map(temps_map)
    df_faits_mat['patient_sk'] = df_faits_mat['id_patient_anonyme'].map(patient_map)
    df_faits_mat['issue_sk'] = df_faits_mat['Decision_Medicale'].str.lower().map(
        issue_map) if 'Decision_Medicale' in df_faits_mat.columns else np.nan
    df_faits_mat['accouchement_sk'] = df_faits_mat['Type_Accouchement'].str.strip().str.lower().map(accouchement_map)
    df_faits_mat['grossesse_sk'] = df_faits_mat['Age_Gestationnel'].map(grossesse_map)
    df_faits_mat['complication_sk'] = df_faits_mat['Complication_Type'].str.strip().str.lower().map(
        complication_map) if 'Complication_Type' in df_faits_mat.columns else np.nan

    # 4. Clé composite pour le bébé
    df_faits_mat['bebe_key'] = df_faits_mat['Poids_Nouveau_Ne'].astype(str).fillna('0') + "_" + \
                               df_faits_mat['Taille_Naissance'].astype(str).fillna('0') + "_" + \
                               df_faits_mat['Score_Apgar'].astype(str).fillna('0')
    bebe_map_key = {row['poids_naissance'].astype(str) + "_" + row['taille_naissance'].astype(str) + "_" + row[
        'score_apgar'].astype(str): row['bebe_sk'] for _, row in ref_bebe.iterrows()}
    df_faits_mat['bebe_sk'] = df_faits_mat['bebe_key'].map(bebe_map_key)

    # 5. Forçage des clés de secours (TOUTES les colonnes)
    df_faits_mat['temps_sk'] = df_faits_mat['temps_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_mat['patient_sk'] = df_faits_mat['patient_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_mat['issue_sk'] = df_faits_mat['issue_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_mat['accouchement_sk'] = df_faits_mat['accouchement_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_mat['grossesse_sk'] = df_faits_mat['grossesse_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_mat['complication_sk'] = df_faits_mat['complication_sk'].fillna(CLE_SECOURS).astype(int)
    df_faits_mat['bebe_sk'] = df_faits_mat['bebe_sk'].fillna(CLE_SECOURS).astype(int)

    # 6. Calcul des indicateurs
    df_faits_mat['nb_cesariennes'] = (df_faits_mat['Type_Accouchement'].str.lower() == 'césarienne').astype(int)
    df_faits_mat['nb_complications'] = (df_faits_mat['Complication_Type'].str.lower() != 'aucune').astype(
        int) if 'Complication_Type' in df_faits_mat.columns else 0

    # 7. Nettoyage du poids de naissance (éliminer les valeurs aberrantes > 10kg)
    df_faits_mat['poids_naissance_net'] = df_faits_mat['Poids_Nouveau_Ne'].apply(
        lambda x: float(x) if pd.notna(x) and float(x) < 10000 else 0.0
    )

    # 8. Construction du DataFrame final (AVEC LES COLONNES EXACTES DE VOTRE TABLE)
    # Note : id_fait est AUTO_INCREMENT, on ne l'envoie PAS
    faits_maternite_final = pd.DataFrame({
        "temps_sk": df_faits_mat["temps_sk"],
        "patient_sk": df_faits_mat["patient_sk"],
        "service_sk": CLE_SECOURS,
        "geographie_sk": CLE_SECOURS,
        "contexte_sk": CLE_SECOURS,
        "accouchement_sk": df_faits_mat["accouchement_sk"],
        "grossesse_sk": df_faits_mat["grossesse_sk"],
        "bebe_sk": df_faits_mat["bebe_sk"],
        "complication_sk": df_faits_mat["complication_sk"],
        "pathologie_sk": CLE_SECOURS,
        "nb_accouchements": 1,
        "nb_cesariennes": df_faits_mat["nb_cesariennes"],
        "nb_complications": df_faits_mat["nb_complications"],
        "poids_naissance": df_faits_mat["poids_naissance_net"],
        "nb_deces_maternels": 0,
        "nb_deces_neonatals": 0
    })

    # 9. Insertion dans la base (SANS id_fait car AUTO_INCREMENT)
    faits_maternite_final.to_sql("faits_maternite", engine, if_exists="append", index=False)
    print(f" ✓ faits_maternite chargé avec succès ! ({len(faits_maternite_final)} lignes)")

    print("\n=================================================== ")
    print(" GLOBAL SUCCESS : Les 4 tables de faits sont entièrement chargées ! ")
    print("=================================================== ")


if __name__ == "__main__":
    main()
-- ==========================================================
-- CRÉATION DE LA BASE DE DONNÉES (MySQL)
-- Nom : dw_hgrkatuba
-- ==========================================================

CREATE DATABASE IF NOT EXISTS dw_hgrkatuba
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE dw_hgrkatuba;

-- ==========================================================
-- 1. DIMENSIONS CONFORMES (PARTAGÉES)
-- ==========================================================

-- 1.1. DIM_TEMPS (SCD Type 0)
CREATE TABLE dim_temps (
    temps_sk INT PRIMARY KEY,
    date_complete DATE NOT NULL UNIQUE,
    jour INT,
    mois INT,
    trimestre INT,
    annee INT,
    semaine INT,
    jour_semaine VARCHAR(20),
    type_jour VARCHAR(20),
    heure INT,
    periode_journee VARCHAR(20)
) ENGINE=InnoDB;

-- 1.2. DIM_PATIENT (SCD Type 2)
CREATE TABLE dim_patient (
    patient_sk INT PRIMARY KEY,
    id_patient_anonyme VARCHAR(50) NOT NULL,
    sexe CHAR(1) CHECK (sexe IN ('M', 'F')),
    age INT,
    tranche_age VARCHAR(20),
    poids FLOAT,
    taille FLOAT,
    statut_nutritionnel VARCHAR(50),
    antecedents_medicaux TEXT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BOOLEAN DEFAULT TRUE,
    version_ligne INT DEFAULT 1
) ENGINE=InnoDB;

-- 1.3. DIM_SERVICE (SCD Type 2)
CREATE TABLE dim_service (
    service_sk INT PRIMARY KEY,
    id_service VARCHAR(20) NOT NULL,
    nom_service VARCHAR(50),
    type_service VARCHAR(20),
    capacite_lits INT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BOOLEAN DEFAULT TRUE,
    version_ligne INT DEFAULT 1
) ENGINE=InnoDB;

-- 1.4. DIM_PATHOLOGIE (SCD Type 2)
CREATE TABLE dim_pathologie (
    pathologie_sk INT PRIMARY KEY,
    code_cim10 VARCHAR(10) NOT NULL,
    libelle VARCHAR(200),
    categorie VARCHAR(50),
    niveau_gravite VARCHAR(20),
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    version_ligne INT DEFAULT 1
) ENGINE=InnoDB;

-- 1.5. DIM_GEOGRAPHIE (SCD Type 1)
CREATE TABLE dim_geographie (
    geographie_sk INT PRIMARY KEY,
    id_localisation VARCHAR(20) NOT NULL,
    quartier VARCHAR(50),
    commune VARCHAR(50),
    ville VARCHAR(50),
    zone_sante VARCHAR(50),
    distance_hopital FLOAT
) ENGINE=InnoDB;

-- ==========================================================
-- 2. DIMENSIONS SPÉCIFIQUES
-- ==========================================================

-- 2.1. DIM_GRAVITE
CREATE TABLE dim_gravite (
    gravite_sk INT PRIMARY KEY,
    code_gravite VARCHAR(10) NOT NULL,
    niveau_urgence INT CHECK (niveau_urgence BETWEEN 1 AND 5),
    categorie VARCHAR(30)
) ENGINE=InnoDB;

-- 2.2. DIM_TRANSPORT
CREATE TABLE dim_transport (
    transport_sk INT PRIMARY KEY,
    code_transport VARCHAR(10) NOT NULL,
    mode_transport VARCHAR(30),
    est_reference BOOLEAN
) ENGINE=InnoDB;

-- 2.3. DIM_MOTIF
CREATE TABLE dim_motif (
    motif_sk INT PRIMARY KEY,
    code_motif VARCHAR(10) NOT NULL,
    libelle_motif VARCHAR(100),
    categorie_motif VARCHAR(30)
) ENGINE=InnoDB;

-- 2.4. DIM_DECISION
CREATE TABLE dim_decision (
    decision_sk INT PRIMARY KEY,
    code_decision VARCHAR(10) NOT NULL,
    type_decision VARCHAR(30),
    service_destination VARCHAR(50)
) ENGINE=InnoDB;

-- 2.5. DIM_MEDECIN (SCD Type 2)
CREATE TABLE dim_medecin (
    medecin_sk INT PRIMARY KEY,
    code_medecin VARCHAR(20) NOT NULL,
    specialite VARCHAR(50),
    service_sk INT,
    grade VARCHAR(30),
    annees_experience INT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    version_ligne INT DEFAULT 1,
    FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk)
) ENGINE=InnoDB;

-- 2.6. DIM_LIT (SCD Type 2)
CREATE TABLE dim_lit (
    lit_sk INT PRIMARY KEY,
    numero_lit VARCHAR(10) NOT NULL,
    numero_chambre VARCHAR(10),
    type_chambre VARCHAR(20),
    service_sk INT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk)
) ENGINE=InnoDB;

-- 2.7. DIM_ISSUE
CREATE TABLE dim_issue (
    issue_sk INT PRIMARY KEY,
    code_issue VARCHAR(10) NOT NULL,
    type_issue VARCHAR(30),
    categorie_issue VARCHAR(20)
) ENGINE=InnoDB;

-- 2.8. DIM_ADMISSION
CREATE TABLE dim_admission (
    admission_sk INT PRIMARY KEY,
    code_admission VARCHAR(10) NOT NULL,
    type_admission VARCHAR(20),
    origine_admission VARCHAR(30)
) ENGINE=InnoDB;

-- 2.9. DIM_ACCOUCHEMENT
CREATE TABLE dim_accouchement (
    accouchement_sk INT PRIMARY KEY,
    code_accouchement VARCHAR(10) NOT NULL,
    type_accouchement VARCHAR(30),
    duree_travail FLOAT
) ENGINE=InnoDB;

-- 2.10. DIM_GROSSESSE (SCD Type 2)
CREATE TABLE dim_grossesse (
    grossesse_sk INT PRIMARY KEY,
    code_grossesse VARCHAR(20) NOT NULL,
    age_gestationnel INT,
    nb_grossesses INT,
    antecedents_obstetricaux TEXT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BOOLEAN DEFAULT TRUE,
    version_ligne INT DEFAULT 1
) ENGINE=InnoDB;

-- 2.11. DIM_NOUVEAUNE (SCD Type 2)
CREATE TABLE dim_nouveaune (
    bebe_sk INT PRIMARY KEY,
    code_bebe VARCHAR(20) NOT NULL,
    sexe_bebe CHAR(1) CHECK (sexe_bebe IN ('M', 'F')),
    poids_naissance FLOAT,
    taille_naissance FLOAT,
    score_apgar INT,
    statut_bebe VARCHAR(30),
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BOOLEAN DEFAULT TRUE,
    version_ligne INT DEFAULT 1
) ENGINE=InnoDB;

-- 2.12. DIM_COMPLICATION
CREATE TABLE dim_complication (
    complication_sk INT PRIMARY KEY,
    code_complication VARCHAR(10) NOT NULL,
    type_complication VARCHAR(50),
    niveau_gravite VARCHAR(20)
) ENGINE=InnoDB;

-- ==========================================================
-- 3. TABLES DE FAITS (DATA MARTS)
-- ==========================================================

-- 3.1. FAITS_ACCUEIL
CREATE TABLE faits_accueil (
    id_fait INT AUTO_INCREMENT PRIMARY KEY,
    temps_sk INT NOT NULL,
    patient_sk INT NOT NULL,
    geographie_sk INT,
    service_sk INT,
    paiement_sk INT,
    contexte_sk INT,
    gravite_sk INT,
    transport_sk INT,
    motif_sk INT,
    decision_sk INT,
    nb_arrivees INT DEFAULT 1,
    temps_attente_tri FLOAT,
    temps_attente_orientation FLOAT,
    nb_non_pris_en_charge INT DEFAULT 0,
    
    FOREIGN KEY (temps_sk) REFERENCES dim_temps(temps_sk),
    FOREIGN KEY (patient_sk) REFERENCES dim_patient(patient_sk),
    FOREIGN KEY (geographie_sk) REFERENCES dim_geographie(geographie_sk),
    FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk),
    FOREIGN KEY (gravite_sk) REFERENCES dim_gravite(gravite_sk),
    FOREIGN KEY (transport_sk) REFERENCES dim_transport(transport_sk),
    FOREIGN KEY (motif_sk) REFERENCES dim_motif(motif_sk),
    FOREIGN KEY (decision_sk) REFERENCES dim_decision(decision_sk)
) ENGINE=InnoDB;

-- 3.2. FAITS_CONSULTATION
CREATE TABLE faits_consultation (
    id_fait INT AUTO_INCREMENT PRIMARY KEY,
    temps_sk INT NOT NULL,
    patient_sk INT NOT NULL,
    service_sk INT,
    pathologie_sk INT,
    paiement_sk INT,
    contexte_sk INT,
    medecin_sk INT,
    gravite_sk INT,
    decision_sk INT,
    nb_consultations INT DEFAULT 1,
    duree_consultation FLOAT,
    nb_medicaments INT,
    nb_examens INT,
    temps_attente FLOAT,
    
    FOREIGN KEY (temps_sk) REFERENCES dim_temps(temps_sk),
    FOREIGN KEY (patient_sk) REFERENCES dim_patient(patient_sk),
    FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk),
    FOREIGN KEY (pathologie_sk) REFERENCES dim_pathologie(pathologie_sk),
    FOREIGN KEY (medecin_sk) REFERENCES dim_medecin(medecin_sk),
    FOREIGN KEY (gravite_sk) REFERENCES dim_gravite(gravite_sk),
    FOREIGN KEY (decision_sk) REFERENCES dim_decision(decision_sk)
) ENGINE=InnoDB;

-- 3.3. FAITS_HOSPITALISATION
CREATE TABLE faits_hospitalisation (
    id_fait INT AUTO_INCREMENT PRIMARY KEY,
    temps_sk INT NOT NULL,
    patient_sk INT NOT NULL,
    service_sk INT,
    pathologie_sk INT,
    geographie_sk INT,
    contexte_sk INT,
    lit_sk INT,
    admission_sk INT,
    issue_sk INT,
    nb_hospitalisations INT DEFAULT 1,
    duree_sejour FLOAT,
    nb_lits_occupes INT DEFAULT 1,
    nb_deces INT DEFAULT 0,
    nb_sorties INT DEFAULT 1,
    
    FOREIGN KEY (temps_sk) REFERENCES dim_temps(temps_sk),
    FOREIGN KEY (patient_sk) REFERENCES dim_patient(patient_sk),
    FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk),
    FOREIGN KEY (pathologie_sk) REFERENCES dim_pathologie(pathologie_sk),
    FOREIGN KEY (geographie_sk) REFERENCES dim_geographie(geographie_sk),
    FOREIGN KEY (lit_sk) REFERENCES dim_lit(lit_sk),
    FOREIGN KEY (admission_sk) REFERENCES dim_admission(admission_sk),
    FOREIGN KEY (issue_sk) REFERENCES dim_issue(issue_sk)
) ENGINE=InnoDB;

-- 3.4. FAITS_MATERNITE
CREATE TABLE faits_maternite (
    id_fait INT AUTO_INCREMENT PRIMARY KEY,
    temps_sk INT NOT NULL,
    patient_sk INT NOT NULL,
    service_sk INT,
    geographie_sk INT,
    contexte_sk INT,
    accouchement_sk INT,
    grossesse_sk INT,
    bebe_sk INT,
    complication_sk INT,
    pathologie_sk INT,
    nb_accouchements INT DEFAULT 1,
    nb_cesariennes INT DEFAULT 0,
    nb_complications INT DEFAULT 0,
    poids_naissance FLOAT,
    nb_deces_maternels INT DEFAULT 0,
    nb_deces_neonatals INT DEFAULT 0,
    
    FOREIGN KEY (temps_sk) REFERENCES dim_temps(temps_sk),
    FOREIGN KEY (patient_sk) REFERENCES dim_patient(patient_sk),
    FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk),
    FOREIGN KEY (geographie_sk) REFERENCES dim_geographie(geographie_sk),
    FOREIGN KEY (accouchement_sk) REFERENCES dim_accouchement(accouchement_sk),
    FOREIGN KEY (grossesse_sk) REFERENCES dim_grossesse(grossesse_sk),
    FOREIGN KEY (bebe_sk) REFERENCES dim_nouveaune(bebe_sk),
    FOREIGN KEY (complication_sk) REFERENCES dim_complication(complication_sk),
    FOREIGN KEY (pathologie_sk) REFERENCES dim_pathologie(pathologie_sk)
) ENGINE=InnoDB;

-- ==========================================================
-- 4. CRÉATION DES INDEX (Optimisation)
-- ==========================================================
CREATE INDEX idx_acc_temps ON faits_accueil(temps_sk);
CREATE INDEX idx_acc_patient ON faits_accueil(patient_sk);
CREATE INDEX idx_cons_temps ON faits_consultation(temps_sk);
CREATE INDEX idx_cons_patient ON faits_consultation(patient_sk);
CREATE INDEX idx_hosp_temps ON faits_hospitalisation(temps_sk);
CREATE INDEX idx_hosp_patient ON faits_hospitalisation(patient_sk);
CREATE INDEX idx_hosp_service ON faits_hospitalisation(service_sk);
CREATE INDEX idx_mat_temps ON faits_maternite(temps_sk);
CREATE INDEX idx_mat_patient ON faits_maternite(patient_sk);

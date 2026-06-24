-- ==========================================================
-- CRÉATION DE LA BASE DE DONNÉES (SQL Server)
-- Nom : dw_hgrkatuba
-- ==========================================================

-- Connexion au serveur
CREATE DATABASE dw_hgrkatuba;
GO

USE dw_hgrkatuba;
GO

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
    jour_semaine NVARCHAR(20),
    type_jour NVARCHAR(20),
    heure INT,
    periode_journee NVARCHAR(20)
);
GO

-- 1.2. DIM_PATIENT (SCD Type 2)
CREATE TABLE dim_patient (
    patient_sk INT PRIMARY KEY,
    id_patient_anonyme NVARCHAR(50) NOT NULL,
    sexe CHAR(1) CHECK (sexe IN ('M', 'F')),
    age INT,
    tranche_age NVARCHAR(20),
    poids DECIMAL(10,2),
    taille DECIMAL(10,2),
    statut_nutritionnel NVARCHAR(50),
    antecedents_medicaux NVARCHAR(MAX),
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BIT DEFAULT 1,
    version_ligne INT DEFAULT 1
);
GO

-- 1.3. DIM_SERVICE (SCD Type 2)
CREATE TABLE dim_service (
    service_sk INT PRIMARY KEY,
    id_service NVARCHAR(20) NOT NULL,
    nom_service NVARCHAR(50),
    type_service NVARCHAR(20),
    capacite_lits INT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BIT DEFAULT 1,
    version_ligne INT DEFAULT 1
);
GO

-- 1.4. DIM_PATHOLOGIE (SCD Type 2)
CREATE TABLE dim_pathologie (
    pathologie_sk INT PRIMARY KEY,
    code_cim10 NVARCHAR(10) NOT NULL,
    libelle NVARCHAR(200),
    categorie NVARCHAR(50),
    niveau_gravite NVARCHAR(20),
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    version_ligne INT DEFAULT 1
);
GO

-- 1.5. DIM_GEOGRAPHIE (SCD Type 1)
CREATE TABLE dim_geographie (
    geographie_sk INT PRIMARY KEY,
    id_localisation NVARCHAR(20) NOT NULL,
    quartier NVARCHAR(50),
    commune NVARCHAR(50),
    ville NVARCHAR(50),
    zone_sante NVARCHAR(50),
    distance_hopital DECIMAL(10,2)
);
GO

-- ==========================================================
-- 2. DIMENSIONS SPÉCIFIQUES
-- ==========================================================

-- 2.1. DIM_GRAVITE
CREATE TABLE dim_gravite (
    gravite_sk INT PRIMARY KEY,
    code_gravite NVARCHAR(10) NOT NULL,
    niveau_urgence INT CHECK (niveau_urgence BETWEEN 1 AND 5),
    categorie NVARCHAR(30)
);
GO

-- 2.2. DIM_TRANSPORT
CREATE TABLE dim_transport (
    transport_sk INT PRIMARY KEY,
    code_transport NVARCHAR(10) NOT NULL,
    mode_transport NVARCHAR(30),
    est_reference BIT
);
GO

-- 2.3. DIM_MOTIF
CREATE TABLE dim_motif (
    motif_sk INT PRIMARY KEY,
    code_motif NVARCHAR(10) NOT NULL,
    libelle_motif NVARCHAR(100),
    categorie_motif NVARCHAR(30)
);
GO

-- 2.4. DIM_DECISION
CREATE TABLE dim_decision (
    decision_sk INT PRIMARY KEY,
    code_decision NVARCHAR(10) NOT NULL,
    type_decision NVARCHAR(30),
    service_destination NVARCHAR(50)
);
GO

-- 2.5. DIM_MEDECIN (SCD Type 2)
CREATE TABLE dim_medecin (
    medecin_sk INT PRIMARY KEY,
    code_medecin NVARCHAR(20) NOT NULL,
    specialite NVARCHAR(50),
    service_sk INT,
    grade NVARCHAR(30),
    annees_experience INT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    version_ligne INT DEFAULT 1,
    CONSTRAINT fk_medecin_service FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk)
);
GO

-- 2.6. DIM_LIT (SCD Type 2)
CREATE TABLE dim_lit (
    lit_sk INT PRIMARY KEY,
    numero_lit NVARCHAR(10) NOT NULL,
    numero_chambre NVARCHAR(10),
    type_chambre NVARCHAR(20),
    service_sk INT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BIT DEFAULT 1,
    CONSTRAINT fk_lit_service FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk)
);
GO

-- 2.7. DIM_ISSUE
CREATE TABLE dim_issue (
    issue_sk INT PRIMARY KEY,
    code_issue NVARCHAR(10) NOT NULL,
    type_issue NVARCHAR(30),
    categorie_issue NVARCHAR(20)
);
GO

-- 2.8. DIM_ADMISSION
CREATE TABLE dim_admission (
    admission_sk INT PRIMARY KEY,
    code_admission NVARCHAR(10) NOT NULL,
    type_admission NVARCHAR(20),
    origine_admission NVARCHAR(30)
);
GO

-- 2.9. DIM_ACCOUCHEMENT
CREATE TABLE dim_accouchement (
    accouchement_sk INT PRIMARY KEY,
    code_accouchement NVARCHAR(10) NOT NULL,
    type_accouchement NVARCHAR(30),
    duree_travail DECIMAL(10,2)
);
GO

-- 2.10. DIM_GROSSESSE (SCD Type 2)
CREATE TABLE dim_grossesse (
    grossesse_sk INT PRIMARY KEY,
    code_grossesse NVARCHAR(20) NOT NULL,
    age_gestationnel INT,
    nb_grossesses INT,
    antecedents_obstetricaux NVARCHAR(MAX),
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BIT DEFAULT 1,
    version_ligne INT DEFAULT 1
);
GO

-- 2.11. DIM_NOUVEAUNE (SCD Type 2)
CREATE TABLE dim_nouveaune (
    bebe_sk INT PRIMARY KEY,
    code_bebe NVARCHAR(20) NOT NULL,
    sexe_bebe CHAR(1) CHECK (sexe_bebe IN ('M', 'F')),
    poids_naissance DECIMAL(10,2),
    taille_naissance DECIMAL(10,2),
    score_apgar INT,
    statut_bebe NVARCHAR(30),
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BIT DEFAULT 1,
    version_ligne INT DEFAULT 1
);
GO

-- 2.12. DIM_COMPLICATION
CREATE TABLE dim_complication (
    complication_sk INT PRIMARY KEY,
    code_complication NVARCHAR(10) NOT NULL,
    type_complication NVARCHAR(50),
    niveau_gravite NVARCHAR(20)
);
GO

-- ==========================================================
-- 3. TABLES DE FAITS (DATA MARTS)
-- ==========================================================

-- 3.1. FAITS_ACCUEIL
CREATE TABLE faits_accueil (
    id_fait INT IDENTITY(1,1) PRIMARY KEY,
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
    temps_attente_tri DECIMAL(10,2),
    temps_attente_orientation DECIMAL(10,2),
    nb_non_pris_en_charge INT DEFAULT 0,
    
    CONSTRAINT fk_acc_temps FOREIGN KEY (temps_sk) REFERENCES dim_temps(temps_sk),
    CONSTRAINT fk_acc_patient FOREIGN KEY (patient_sk) REFERENCES dim_patient(patient_sk),
    CONSTRAINT fk_acc_geo FOREIGN KEY (geographie_sk) REFERENCES dim_geographie(geographie_sk),
    CONSTRAINT fk_acc_service FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk),
    CONSTRAINT fk_acc_gravite FOREIGN KEY (gravite_sk) REFERENCES dim_gravite(gravite_sk),
    CONSTRAINT fk_acc_transport FOREIGN KEY (transport_sk) REFERENCES dim_transport(transport_sk),
    CONSTRAINT fk_acc_motif FOREIGN KEY (motif_sk) REFERENCES dim_motif(motif_sk),
    CONSTRAINT fk_acc_decision FOREIGN KEY (decision_sk) REFERENCES dim_decision(decision_sk)
);
GO

-- 3.2. FAITS_CONSULTATION
CREATE TABLE faits_consultation (
    id_fait INT IDENTITY(1,1) PRIMARY KEY,
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
    duree_consultation DECIMAL(10,2),
    nb_medicaments INT,
    nb_examens INT,
    temps_attente DECIMAL(10,2),
    
    CONSTRAINT fk_cons_temps FOREIGN KEY (temps_sk) REFERENCES dim_temps(temps_sk),
    CONSTRAINT fk_cons_patient FOREIGN KEY (patient_sk) REFERENCES dim_patient(patient_sk),
    CONSTRAINT fk_cons_service FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk),
    CONSTRAINT fk_cons_patho FOREIGN KEY (pathologie_sk) REFERENCES dim_pathologie(pathologie_sk),
    CONSTRAINT fk_cons_medecin FOREIGN KEY (medecin_sk) REFERENCES dim_medecin(medecin_sk),
    CONSTRAINT fk_cons_gravite FOREIGN KEY (gravite_sk) REFERENCES dim_gravite(gravite_sk),
    CONSTRAINT fk_cons_decision FOREIGN KEY (decision_sk) REFERENCES dim_decision(decision_sk)
);
GO

-- 3.3. FAITS_HOSPITALISATION
CREATE TABLE faits_hospitalisation (
    id_fait INT IDENTITY(1,1) PRIMARY KEY,
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
    duree_sejour DECIMAL(10,2),
    nb_lits_occupes INT DEFAULT 1,
    nb_deces INT DEFAULT 0,
    nb_sorties INT DEFAULT 1,
    
    CONSTRAINT fk_hosp_temps FOREIGN KEY (temps_sk) REFERENCES dim_temps(temps_sk),
    CONSTRAINT fk_hosp_patient FOREIGN KEY (patient_sk) REFERENCES dim_patient(patient_sk),
    CONSTRAINT fk_hosp_service FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk),
    CONSTRAINT fk_hosp_patho FOREIGN KEY (pathologie_sk) REFERENCES dim_pathologie(pathologie_sk),
    CONSTRAINT fk_hosp_geo FOREIGN KEY (geographie_sk) REFERENCES dim_geographie(geographie_sk),
    CONSTRAINT fk_hosp_lit FOREIGN KEY (lit_sk) REFERENCES dim_lit(lit_sk),
    CONSTRAINT fk_hosp_admission FOREIGN KEY (admission_sk) REFERENCES dim_admission(admission_sk),
    CONSTRAINT fk_hosp_issue FOREIGN KEY (issue_sk) REFERENCES dim_issue(issue_sk)
);
GO

-- 3.4. FAITS_MATERNITE
CREATE TABLE faits_maternite (
    id_fait INT IDENTITY(1,1) PRIMARY KEY,
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
    poids_naissance DECIMAL(10,2),
    nb_deces_maternels INT DEFAULT 0,
    nb_deces_neonatals INT DEFAULT 0,
    
    CONSTRAINT fk_mat_temps FOREIGN KEY (temps_sk) REFERENCES dim_temps(temps_sk),
    CONSTRAINT fk_mat_patient FOREIGN KEY (patient_sk) REFERENCES dim_patient(patient_sk),
    CONSTRAINT fk_mat_service FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk),
    CONSTRAINT fk_mat_geo FOREIGN KEY (geographie_sk) REFERENCES dim_geographie(geographie_sk),
    CONSTRAINT fk_mat_accouchement FOREIGN KEY (accouchement_sk) REFERENCES dim_accouchement(accouchement_sk),
    CONSTRAINT fk_mat_grossesse FOREIGN KEY (grossesse_sk) REFERENCES dim_grossesse(grossesse_sk),
    CONSTRAINT fk_mat_bebe FOREIGN KEY (bebe_sk) REFERENCES dim_nouveaune(bebe_sk),
    CONSTRAINT fk_mat_complication FOREIGN KEY (complication_sk) REFERENCES dim_complication(complication_sk),
    CONSTRAINT fk_mat_patho FOREIGN KEY (pathologie_sk) REFERENCES dim_pathologie(pathologie_sk)
);
GO

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
GO

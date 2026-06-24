-- ==========================================================
-- CRÉATION DE LA BASE DE DONNÉES DATA WAREHOUSE
-- Nom : dw_hgrkatuba
-- Type : PostgreSQL 
-- Auteur : Projet MSI - HGR Katuba
-- ==========================================================

-- Création de la nouvelle base
CREATE DATABASE dw_hgrkatuba
    ENCODING 'UTF8'
    LC_COLLATE 'French_France.1252'
    LC_CTYPE 'French_France.1252'
    TEMPLATE template0;

-- Connexion à la base
\c dw_hgrkatuba;

-- ==========================================================
-- 1. CRÉATION DES DIMENSIONS CONFORMES (PARTAGÉES)
-- Ces dimensions sont utilisées par tous les Data Marts.
-- ==========================================================

-- 1.1. DIM_TEMPS (SCD Type 0 - Statique)
-- Rôle : Permet l'analyse temporelle (heure, jour, semaine, mois, saison)
CREATE TABLE dim_temps (
    temps_sk INT PRIMARY KEY,
    date_complete DATE NOT NULL UNIQUE,
    jour INT,
    mois INT,
    trimestre INT,
    annee INT,
    semaine INT,
    jour_semaine VARCHAR(20),
    type_jour VARCHAR(20), -- 'Ouvrable', 'Weekend', 'Férié'
    heure INT,
    periode_journee VARCHAR(20) -- 'Matin', 'Après-midi', 'Nuit'
);

-- 1.2. DIM_PATIENT (SCD Type 2 - Historisation)
-- Rôle : Profil démographique et clinique du patient
CREATE TABLE dim_patient (
    patient_sk INT PRIMARY KEY,
    id_patient_anonyme VARCHAR(50) NOT NULL,
    sexe CHAR(1) CHECK (sexe IN ('M', 'F')),
    age INT,
    tranche_age VARCHAR(20), -- '0-5 ans', '6-15 ans', 'Adulte', 'Senior'
    poids FLOAT,
    taille FLOAT,
    statut_nutritionnel VARCHAR(50),
    antecedents_medicaux TEXT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BOOLEAN DEFAULT TRUE,
    version_ligne INT DEFAULT 1
);

-- 1.3. DIM_SERVICE (SCD Type 2 - Historisation)
-- Rôle : Structure hospitalière (service, spécialité, capacité)
CREATE TABLE dim_service (
    service_sk INT PRIMARY KEY,
    id_service VARCHAR(20) NOT NULL,
    nom_service VARCHAR(50),
    type_service VARCHAR(20), -- 'Urgence', 'Consultation', 'Hospitalisation'
    capacite_lits INT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BOOLEAN DEFAULT TRUE,
    version_ligne INT DEFAULT 1
);

-- 1.4. DIM_PATHOLOGIE (SCD Type 2 - Historisation)
-- Rôle : Classification des maladies (CIM-10)
CREATE TABLE dim_pathologie (
    pathologie_sk INT PRIMARY KEY,
    code_cim10 VARCHAR(10) NOT NULL,
    libelle VARCHAR(200),
    categorie VARCHAR(50), -- 'Infectieux', 'Cardio', 'Maternel', 'Nutrition'
    niveau_gravite VARCHAR(20),
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    version_ligne INT DEFAULT 1
);

-- 1.5. DIM_GEOGRAPHIE (SCD Type 1 - Mise à jour directe)
-- Rôle : Localisation spatiale du patient
CREATE TABLE dim_geographie (
    geographie_sk INT PRIMARY KEY,
    id_localisation VARCHAR(20) NOT NULL,
    quartier VARCHAR(50),
    commune VARCHAR(50),
    ville VARCHAR(50),
    zone_sante VARCHAR(50),
    distance_hopital FLOAT
);

-- ==========================================================
-- 2. CRÉATION DES DIMENSIONS SPÉCIFIQUES
-- Ces dimensions sont propres à un ou deux Data Marts.
-- ==========================================================

-- 2.1. DIM_GRAVITE (SCD Type 1)
-- Rôle : Niveau d'urgence pour les admissions
CREATE TABLE dim_gravite (
    gravite_sk INT PRIMARY KEY,
    code_gravite VARCHAR(10) NOT NULL,
    niveau_urgence INT CHECK (niveau_urgence BETWEEN 1 AND 5),
    categorie VARCHAR(30) -- 'Vitale', 'Sévère', 'Modérée', 'Légère'
);

-- 2.2. DIM_TRANSPORT (SCD Type 1)
-- Rôle : Mode d'arrivée du patient
CREATE TABLE dim_transport (
    transport_sk INT PRIMARY KEY,
    code_transport VARCHAR(10) NOT NULL,
    mode_transport VARCHAR(30), -- 'Ambulance', 'Véhicule privé', 'À pied'
    est_reference BOOLEAN -- 'Oui' si référé par un autre hôpital
);

-- 2.3. DIM_MOTIF (SCD Type 1)
-- Rôle : Raison de la consultation ou de l'admission
CREATE TABLE dim_motif (
    motif_sk INT PRIMARY KEY,
    code_motif VARCHAR(10) NOT NULL,
    libelle_motif VARCHAR(100),
    categorie_motif VARCHAR(30) -- 'Infectieux', 'Traumatique', 'Chronique'
);

-- 2.4. DIM_DECISION (SCD Type 1)
-- Rôle : Décision médicale prise après consultation
CREATE TABLE dim_decision (
    decision_sk INT PRIMARY KEY,
    code_decision VARCHAR(10) NOT NULL,
    type_decision VARCHAR(30), -- 'Retour domicile', 'Hospitalisation', 'Orientation'
    service_destination VARCHAR(50)
);

-- 2.5. DIM_MEDECIN (SCD Type 2 - Historisation)
-- Rôle : Informations sur le professionnel de santé
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
    -- Clé étrangère vers service (historique)
    CONSTRAINT fk_medecin_service FOREIGN KEY (service_sk) 
        REFERENCES dim_service(service_sk)
);

-- 2.6. DIM_LIT (SCD Type 2 - Historisation)
-- Rôle : Ressources d'hospitalisation
CREATE TABLE dim_lit (
    lit_sk INT PRIMARY KEY,
    numero_lit VARCHAR(10) NOT NULL,
    numero_chambre VARCHAR(10),
    type_chambre VARCHAR(20), -- 'Standard', 'Réanimation', 'Isolement'
    service_sk INT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BOOLEAN DEFAULT TRUE,
    -- Clé étrangère vers service
    CONSTRAINT fk_lit_service FOREIGN KEY (service_sk) 
        REFERENCES dim_service(service_sk)
);

-- 2.7. DIM_ISSUE (SCD Type 1)
-- Rôle : Issue finale d'une hospitalisation
CREATE TABLE dim_issue (
    issue_sk INT PRIMARY KEY,
    code_issue VARCHAR(10) NOT NULL,
    type_issue VARCHAR(30), -- 'Guérison', 'Transfert', 'Décès', 'Abandon'
    categorie_issue VARCHAR(20) -- 'Positive', 'Négative', 'Neutre'
);

-- 2.8. DIM_ADMISSION (SCD Type 1)
-- Rôle : Modalités d'entrée à l'hôpital
CREATE TABLE dim_admission (
    admission_sk INT PRIMARY KEY,
    code_admission VARCHAR(10) NOT NULL,
    type_admission VARCHAR(20), -- 'Urgence', 'Programmée'
    origine_admission VARCHAR(30) -- 'Domicile', 'Transfert', 'Autre structure'
);

-- 2.9. DIM_ACCOUCHEMENT (SCD Type 1)
-- Rôle : Modalités de l'accouchement
CREATE TABLE dim_accouchement (
    accouchement_sk INT PRIMARY KEY,
    code_accouchement VARCHAR(10) NOT NULL,
    type_accouchement VARCHAR(30), -- 'Normal', 'Césarienne', 'Assisté'
    duree_travail FLOAT
);

-- 2.10. DIM_GROSSESSE (SCD Type 2 - Historisation)
-- Rôle : Caractéristiques de la grossesse
CREATE TABLE dim_grossesse (
    grossesse_sk INT PRIMARY KEY,
    code_grossesse VARCHAR(20) NOT NULL,
    age_gestationnel INT, -- en semaines
    nb_grossesses INT,
    antecedents_obstetricaux TEXT,
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BOOLEAN DEFAULT TRUE,
    version_ligne INT DEFAULT 1
);

-- 2.11. DIM_NOUVEAUNE (SCD Type 2 - Historisation)
-- Rôle : État de santé du nouveau-né
CREATE TABLE dim_nouveaune (
    bebe_sk INT PRIMARY KEY,
    code_bebe VARCHAR(20) NOT NULL,
    sexe_bebe CHAR(1) CHECK (sexe_bebe IN ('M', 'F')),
    poids_naissance FLOAT, -- en kg
    taille_naissance FLOAT, -- en cm
    score_apgar INT,
    statut_bebe VARCHAR(30), -- 'Sain', 'Complication', 'Critique'
    date_debut_validite DATE NOT NULL,
    date_fin_validite DATE,
    est_actif BOOLEAN DEFAULT TRUE,
    version_ligne INT DEFAULT 1
);

-- 2.12. DIM_COMPLICATION (SCD Type 1)
-- Rôle : Complications liées à la grossesse/accouchement
CREATE TABLE dim_complication (
    complication_sk INT PRIMARY KEY,
    code_complication VARCHAR(10) NOT NULL,
    type_complication VARCHAR(50), -- 'Hémorragie', 'Infection', 'Détresse', etc.
    niveau_gravite VARCHAR(20) -- 'Faible', 'Modérée', 'Sévère'
);

-- ==========================================================
-- 3. CRÉATION DES TABLES DE FAITS (DATA MARTS)
-- Ces tables contiennent les mesures (indicateurs) et les clés étrangères
-- vers les dimensions.
-- ==========================================================

-- 3.1. FAITS_ACCUEIL (Data Mart Accueil & Urgences)
-- Rôle : Analyse des flux d'arrivée, temps d'attente, orientation
CREATE TABLE faits_accueil (
    id_fait SERIAL PRIMARY KEY,
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
    -- Mesures (Indicateurs)
    nb_arrivees INT DEFAULT 1,
    temps_attente_tri FLOAT,
    temps_attente_orientation FLOAT,
    nb_non_pris_en_charge INT DEFAULT 0,
    -- Clés étrangères
    CONSTRAINT fk_acc_temps FOREIGN KEY (temps_sk) REFERENCES dim_temps(temps_sk),
    CONSTRAINT fk_acc_patient FOREIGN KEY (patient_sk) REFERENCES dim_patient(patient_sk),
    CONSTRAINT fk_acc_geo FOREIGN KEY (geographie_sk) REFERENCES dim_geographie(geographie_sk),
    CONSTRAINT fk_acc_service FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk),
    CONSTRAINT fk_acc_gravite FOREIGN KEY (gravite_sk) REFERENCES dim_gravite(gravite_sk),
    CONSTRAINT fk_acc_transport FOREIGN KEY (transport_sk) REFERENCES dim_transport(transport_sk),
    CONSTRAINT fk_acc_motif FOREIGN KEY (motif_sk) REFERENCES dim_motif(motif_sk),
    CONSTRAINT fk_acc_decision FOREIGN KEY (decision_sk) REFERENCES dim_decision(decision_sk)
);

-- 3.2. FAITS_CONSULTATION (Data Mart Consultations)
-- Rôle : Analyse des consultations, des diagnostics et des décisions
CREATE TABLE faits_consultation (
    id_fait SERIAL PRIMARY KEY,
    temps_sk INT NOT NULL,
    patient_sk INT NOT NULL,
    service_sk INT,
    pathologie_sk INT,
    paiement_sk INT,
    contexte_sk INT,
    medecin_sk INT,
    gravite_sk INT,
    decision_sk INT,
    -- Mesures (Indicateurs)
    nb_consultations INT DEFAULT 1,
    duree_consultation FLOAT,
    nb_medicaments INT,
    nb_examens INT,
    temps_attente FLOAT,
    -- Clés étrangères
    CONSTRAINT fk_cons_temps FOREIGN KEY (temps_sk) REFERENCES dim_temps(temps_sk),
    CONSTRAINT fk_cons_patient FOREIGN KEY (patient_sk) REFERENCES dim_patient(patient_sk),
    CONSTRAINT fk_cons_service FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk),
    CONSTRAINT fk_cons_patho FOREIGN KEY (pathologie_sk) REFERENCES dim_pathologie(pathologie_sk),
    CONSTRAINT fk_cons_medecin FOREIGN KEY (medecin_sk) REFERENCES dim_medecin(medecin_sk),
    CONSTRAINT fk_cons_gravite FOREIGN KEY (gravite_sk) REFERENCES dim_gravite(gravite_sk),
    CONSTRAINT fk_cons_decision FOREIGN KEY (decision_sk) REFERENCES dim_decision(decision_sk)
);

-- 3.3. FAITS_HOSPITALISATION (Data Mart Hospitalisations)
-- Rôle : Gestion des lits, durée de séjour, mortalité
CREATE TABLE faits_hospitalisation (
    id_fait SERIAL PRIMARY KEY,
    temps_sk INT NOT NULL,
    patient_sk INT NOT NULL,
    service_sk INT,
    pathologie_sk INT,
    geographie_sk INT,
    contexte_sk INT,
    lit_sk INT,
    admission_sk INT,
    issue_sk INT,
    -- Mesures (Indicateurs)
    nb_hospitalisations INT DEFAULT 1,
    duree_sejour FLOAT,
    nb_lits_occupes INT DEFAULT 1,
    nb_deces INT DEFAULT 0,
    nb_sorties INT DEFAULT 1,
    -- Clés étrangères
    CONSTRAINT fk_hosp_temps FOREIGN KEY (temps_sk) REFERENCES dim_temps(temps_sk),
    CONSTRAINT fk_hosp_patient FOREIGN KEY (patient_sk) REFERENCES dim_patient(patient_sk),
    CONSTRAINT fk_hosp_service FOREIGN KEY (service_sk) REFERENCES dim_service(service_sk),
    CONSTRAINT fk_hosp_patho FOREIGN KEY (pathologie_sk) REFERENCES dim_pathologie(pathologie_sk),
    CONSTRAINT fk_hosp_geo FOREIGN KEY (geographie_sk) REFERENCES dim_geographie(geographie_sk),
    CONSTRAINT fk_hosp_lit FOREIGN KEY (lit_sk) REFERENCES dim_lit(lit_sk),
    CONSTRAINT fk_hosp_admission FOREIGN KEY (admission_sk) REFERENCES dim_admission(admission_sk),
    CONSTRAINT fk_hosp_issue FOREIGN KEY (issue_sk) REFERENCES dim_issue(issue_sk)
);

-- 3.4. FAITS_MATERNITE (Data Mart Maternité)
-- Rôle : Suivi des accouchements, complications, santé mère/enfant
CREATE TABLE faits_maternite (
    id_fait SERIAL PRIMARY KEY,
    temps_sk INT NOT NULL,
    patient_sk INT NOT NULL,
    service_sk INT,
    geographie_sk INT,
    contexte_sk INT,
    accouchement_sk INT,
    grossesse_sk INT,
    bebe_sk INT,
    complication_sk INT,
    pathologie_sk INT, -- Ajouté car visible sur votre image (liaison)
    -- Mesures (Indicateurs)
    nb_accouchements INT DEFAULT 1,
    nb_cesariennes INT DEFAULT 0,
    nb_complications INT DEFAULT 0,
    poids_naissance FLOAT,
    nb_deces_maternels INT DEFAULT 0,
    nb_deces_neonatals INT DEFAULT 0,
    -- Clés étrangères
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

-- ==========================================================
-- 4. CRÉATION DES INDEX (Pour optimiser les performances)
-- Les index sont essentiels pour les requêtes OLAP.
-- ==========================================================

-- Index sur les clés étrangères des tables de faits
CREATE INDEX idx_acc_temps ON faits_accueil(temps_sk);
CREATE INDEX idx_acc_patient ON faits_accueil(patient_sk);
CREATE INDEX idx_acc_service ON faits_accueil(service_sk);
CREATE INDEX idx_acc_gravite ON faits_accueil(gravite_sk);

CREATE INDEX idx_cons_temps ON faits_consultation(temps_sk);
CREATE INDEX idx_cons_patient ON faits_consultation(patient_sk);
CREATE INDEX idx_cons_medecin ON faits_consultation(medecin_sk);
CREATE INDEX idx_cons_patho ON faits_consultation(pathologie_sk);

CREATE INDEX idx_hosp_temps ON faits_hospitalisation(temps_sk);
CREATE INDEX idx_hosp_patient ON faits_hospitalisation(patient_sk);
CREATE INDEX idx_hosp_service ON faits_hospitalisation(service_sk);
CREATE INDEX idx_hosp_lit ON faits_hospitalisation(lit_sk);
CREATE INDEX idx_hosp_issue ON faits_hospitalisation(issue_sk);

CREATE INDEX idx_mat_temps ON faits_maternite(temps_sk);
CREATE INDEX idx_mat_patient ON faits_maternite(patient_sk);
CREATE INDEX idx_mat_accouchement ON faits_maternite(accouchement_sk);
CREATE INDEX idx_mat_bebe ON faits_maternite(bebe_sk);

-- Index sur les attributs de recherche dans les dimensions
CREATE INDEX idx_patient_anonyme ON dim_patient(id_patient_anonyme);
CREATE INDEX idx_service_nom ON dim_service(nom_service);
CREATE INDEX idx_cim10 ON dim_pathologie(code_cim10);
CREATE INDEX idx_medecin_code ON dim_medecin(code_medecin);

-- ==========================================================
-- 5. FIN DU SCRIPT
-- ==========================================================
COMMENT ON DATABASE dw_hgrkatuba IS 'Data Warehouse du système décisionnel de l''HGR Katuba';

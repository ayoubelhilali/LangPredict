import os

# Le contenu du fichier (Cahier des charges formel)
content = """================================================================================
FICHE DESCRIPTIVE DU MINI-PROJET
Sujet : Application Web de Correction Automatique d'Examens (OMR)
Étudiant : Ayoub EL HILALI
Formation : Génie Informatique - ENSA Alhoceima
================================================================================

1. PRÉSENTATION DU PROJET
--------------------------------------------------------------------------------
Ce projet vise à développer une application web permettant d'automatiser la 
correction des feuilles de réponses (QCM). Le système utilise des techniques 
de Vision par Ordinateur (Computer Vision) pour analyser une photo de la 
feuille, extraire les réponses de l'étudiant et calculer la note instantanément, 
sans nécessiter d'entraînement de modèle Machine Learning (Zéro-Training).

2. DESCRIPTION FONCTIONNELLE
--------------------------------------------------------------------------------
L'application se divise en deux volets principaux :

A. Interface Utilisateur (Rôle Enseignant)
   1. Importation d'image : 
      L'utilisateur téléverse une photo (.jpg, .png) de la feuille de réponse 
      ou utilise la webcam.
   2. Correction One-Click : 
      Lancement du processus d'analyse via un simple bouton.
   3. Visualisation des Résultats : 
      - Affichage de la note calculée (ex: 18/20).
      - Affichage de la "Copie Corrigée" : L'image originale est renvoyée 
        avec des superpositions graphiques (cadres verts pour les bonnes 
        réponses, rouges pour les erreurs).

B. Traitement Backend (Logique de Pré-traitement)
   Le cœur du projet repose sur une chaîne de traitement d'image stricte :
   
   1. Phase de Pré-traitement (Obligatoire) :
      - Conversion en niveaux de gris & Floutage (Denoising).
      - Détection de contours (Canny Edge Detection).
      - Transformation de Perspective : Identification des 4 coins de la 
        feuille et "mise à plat" mathématique de l'image pour corriger 
        l'angle de prise de vue.
   
   2. Phase d'Extraction :
      - Seuillage Adaptatif (Adaptive Thresholding) pour binariser l'image.
      - Découpage par grille (Grid Slicing) pour isoler chaque case à cocher.
      - Analyse de densité de pixels pour déterminer le choix de l'étudiant.

3. STACK TECHNIQUE
--------------------------------------------------------------------------------
Architecture : Client-Serveur

A. Frontend (Interface)
   - Technologie : React.js
   - Rôle : Gestion de l'UI, upload asynchrone et affichage dynamique.

B. Backend (API)
   - Technologie : Python (Flask)
   - Rôle : Serveur REST API exposant l'endpoint de correction.

C. Traitement d'Image
   - Librairie : OpenCV (cv2)
   - Rôle : Algorithmes de transformation géométrique et analyse morphologique.
   - Librairie : NumPy
   - Rôle : Opérations matricielles pour le calcul de pixels.

4. CONFORMITÉ AUX EXIGENCES
--------------------------------------------------------------------------------
- Pas de Machine Learning : Utilisation d'algorithmes déterministes (Computer 
  Vision classique).
- Pré-traitement intensif : Le projet met l'accent sur la normalisation des 
  données (nettoyage, redressement de perspective) avant l'analyse.
================================================================================
"""

filename = "Descriptif_Projet_Grader.txt"

# Création du fichier
with open(filename, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ Le fichier '{filename}' a été créé avec succès dans votre dossier actuel.")
print("Vous pouvez maintenant l'envoyer à votre professeur.")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'analyse d'image pour la stéganographie LSB
Ce script identifie les zones optimales d'une image pour l'insertion 
de données cachées en utilisant la méthode LSB.
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

class ImageAnalyzer:
    """Classe pour analyser une image et trouver les meilleures zones pour la stéganographie LSB."""
    
    def __init__(self, image_path):
        """
        Initialise l'analyseur avec le chemin de l'image.
        
        Args:
            image_path (str): Chemin vers l'image à analyser
        """
        self.image_path = Path(image_path)
        self.image = cv2.imread(str(image_path))
        if self.image is None:
            raise FileNotFoundError(f"Impossible de charger l'image: {image_path}")
        
        # Convertir l'image de BGR à RGB pour l'affichage
        self.image_rgb = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        
        # Convertir en niveaux de gris pour les analyses de texture
        self.gray_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        
        # Dimensions de l'image
        self.height, self.width = self.gray_image.shape[:2]
        
    def calculate_edge_density(self, block_size=8):
        """
        Calcule la densité des contours de l'image en utilisant le détecteur de Canny.
        Les zones avec beaucoup de contours sont généralement bonnes pour cacher des données.
        
        Args:
            block_size (int): Taille des blocs pour l'analyse
            
        Returns:
            np.ndarray: Carte de chaleur indiquant les densités de contours
        """
        # Détection des contours avec Canny
        edges = cv2.Canny(self.gray_image, 100, 200)
        
        # Initialiser la carte de densité
        h_blocks = self.height // block_size
        w_blocks = self.width // block_size
        edge_density_map = np.zeros((h_blocks, w_blocks))
        
        # Calculer la densité des contours par bloc
        for y in range(h_blocks):
            for x in range(w_blocks):
                y1, y2 = y * block_size, (y + 1) * block_size
                x1, x2 = x * block_size, (x + 1) * block_size
                block = edges[y1:y2, x1:x2]
                edge_density_map[y, x] = np.sum(block) / (block_size * block_size)
                
        return edge_density_map
    
    def calculate_texture_complexity(self, block_size=8):
        """
        Calcule la complexité de texture en utilisant les écarts types locaux.
        Les zones à haute complexité sont idéales pour la stéganographie.
        
        Args:
            block_size (int): Taille des blocs pour l'analyse
            
        Returns:
            np.ndarray: Carte de chaleur indiquant la complexité de texture
        """
        # Initialiser la carte de complexité
        h_blocks = self.height // block_size
        w_blocks = self.width // block_size
        texture_map = np.zeros((h_blocks, w_blocks))
        
        # Calculer l'écart type local pour chaque bloc
        for y in range(h_blocks):
            for x in range(w_blocks):
                y1, y2 = y * block_size, (y + 1) * block_size
                x1, x2 = x * block_size, (x + 1) * block_size
                block = self.gray_image[y1:y2, x1:x2]
                texture_map[y, x] = np.std(block)
                
        return texture_map
    
    def detect_optimal_regions(self, block_size=8, threshold_percentile=75):
        """
        Identifie les régions optimales pour l'insertion de données en combinant
        la densité des contours et la complexité de texture.
        
        Args:
            block_size (int): Taille des blocs pour l'analyse
            threshold_percentile (int): Percentile pour déterminer le seuil des zones optimales
            
        Returns:
            tuple: (image originale avec zones optimales marquées, masque binaire des zones optimales)
        """
        # Obtenir les cartes d'analyse
        edge_map = self.calculate_edge_density(block_size)
        texture_map = self.calculate_texture_complexity(block_size)
        
        # Combiner les deux métriques (pondération égale)
        combined_map = 0.5 * edge_map + 0.5 * texture_map
        
        # Normaliser entre 0 et 1
        combined_map = (combined_map - np.min(combined_map)) / (np.max(combined_map) - np.min(combined_map))
        
        # Trouver les régions au-dessus du seuil (zones les plus complexes)
        threshold = np.percentile(combined_map, threshold_percentile)
        optimal_regions = combined_map >= threshold
        
        # Créer un masque à la taille de l'image originale
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        for y in range(optimal_regions.shape[0]):
            for x in range(optimal_regions.shape[1]):
                if optimal_regions[y, x]:
                    y1, y2 = y * block_size, (y + 1) * block_size
                    x1, x2 = x * block_size, (x + 1) * block_size
                    mask[y1:y2, x1:x2] = 255
        
        # Créer une visualisation de l'image avec les zones optimales en surbrillance
        highlighted_image = self.image_rgb.copy()
        highlight_color = np.array([0, 255, 0], dtype=np.uint8)  # Vert
        
        for y in range(self.height):
            for x in range(self.width):
                if mask[y, x] == 255:
                    # Appliquer une légère teinte verte aux pixels des zones optimales
                    highlighted_image[y, x] = (highlighted_image[y, x] * 0.7 + highlight_color * 0.3).astype(np.uint8)
        
        return highlighted_image, mask
    
    def visualize_analysis(self, block_size=8, threshold_percentile=75):
        """
        Visualise les résultats de l'analyse avec différentes métriques.
        
        Args:
            block_size (int): Taille des blocs pour l'analyse
            threshold_percentile (int): Percentile pour déterminer le seuil des zones optimales
        """
        # Obtenir les résultats
        edge_map = self.calculate_edge_density(block_size)
        texture_map = self.calculate_texture_complexity(block_size)
        highlighted_image, mask = self.detect_optimal_regions(block_size, threshold_percentile)
        
        # Calculer la capacité d'insertion potentielle (en octets)
        optimal_pixels = np.sum(mask) // 255
        capacity_bytes = optimal_pixels // 8  # 8 pixels = 1 octet (1 bit par pixel)
        capacity_percentage = (optimal_pixels / (self.height * self.width)) * 100
        
        # Créer la visualisation
        plt.figure(figsize=(15, 10))
        
        plt.subplot(2, 2, 1)
        plt.imshow(self.image_rgb)
        plt.title("Image originale")
        plt.axis('off')
        
        plt.subplot(2, 2, 2)
        plt.imshow(highlighted_image)
        plt.title(f"Zones optimales pour insertion (vert)")
        plt.axis('off')
        
        plt.subplot(2, 2, 3)
        plt.imshow(edge_map, cmap='hot')
        plt.title("Densité des contours")
        plt.colorbar(fraction=0.046, pad=0.04)
        plt.axis('off')
        
        plt.subplot(2, 2, 4)
        plt.imshow(texture_map, cmap='viridis')
        plt.title("Complexité de texture")
        plt.colorbar(fraction=0.046, pad=0.04)
        plt.axis('off')
        
        plt.tight_layout()
        
        # Afficher les informations de capacité
        plt.figtext(0.5, 0.01, 
                   f"Capacité d'insertion potentielle: {capacity_bytes} octets ({capacity_percentage:.2f}% de l'image)",
                   ha='center', fontsize=12, bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
        
        # Sauvegarder l'analyse
        output_path = self.image_path.parent / f"{self.image_path.stem}_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Analyse enregistrée sous: {output_path}")
        print(f"Capacité d'insertion potentielle: {capacity_bytes} octets ({capacity_percentage:.2f}% de l'image)")
        
        return highlighted_image, mask, capacity_bytes


def main():
    """Fonction principale pour tester l'analyseur d'image."""
    # Charger et analyser l'image
    image_path = "99a28395d6c0e059ea4585a6e94df5c9.jpg"
    analyzer = ImageAnalyzer(image_path)
    
    # Visualiser les résultats
    highlighted_image, mask, capacity = analyzer.visualize_analysis(block_size=16, threshold_percentile=75)
    
    print(f"Analyse terminée. Capacité d'insertion LSB estimée: {capacity} octets.")


if __name__ == "__main__":
    main()
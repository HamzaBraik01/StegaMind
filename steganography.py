#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'insertion de données secrètes pour la stéganographie LSB
Ce script permet d'insérer des données dans les zones optimales d'une image
en utilisant la méthode LSB (Least Significant Bit).
"""

import cv2
import numpy as np
from pathlib import Path
import os
import struct
from image_analyzer import ImageAnalyzer


class SteganographyEncoder:
    """Classe pour encoder des données secrètes dans une image en utilisant la stéganographie LSB."""
    
    def __init__(self, image_path, block_size=16, threshold_percentile=75):
        """
        Initialise l'encodeur de stéganographie.
        
        Args:
            image_path (str): Chemin vers l'image à utiliser
            block_size (int): Taille des blocs pour l'analyse des zones optimales
            threshold_percentile (int): Percentile pour déterminer le seuil des zones optimales
        """
        self.image_path = Path(image_path)
        self.block_size = block_size
        self.threshold_percentile = threshold_percentile
        
        # Initialiser l'analyseur d'image pour trouver les zones optimales
        self.analyzer = ImageAnalyzer(image_path)
        
        # Obtenir l'image et le masque des zones optimales
        _, self.optimal_mask = self.analyzer.detect_optimal_regions(
            block_size=self.block_size, 
            threshold_percentile=self.threshold_percentile
        )
        
        # Calculer la capacité d'insertion (en octets)
        optimal_pixels = np.sum(self.optimal_mask) // 255
        self.capacity = optimal_pixels * 3 // 8  # 3 canaux, 1 bit par canal, 8 bits par octet
        
        # Charger l'image en mode BGR pour le traitement
        self.image = cv2.imread(str(image_path))
        
        # Dimensions de l'image
        self.height, self.width, self.channels = self.image.shape
        
        # Liste des coordonnées optimales pour l'insertion (dans l'ordre)
        self.optimal_pixels = self._get_optimal_pixels()
        
    def _get_optimal_pixels(self):
        """
        Obtient les coordonnées de tous les pixels optimaux selon le masque.
        
        Returns:
            list: Liste de tuples (y, x, c) représentant les coordonnées des pixels optimaux
                  et leur canal (0=B, 1=G, 2=R)
        """
        optimal_coords = []
        
        # Pour chaque pixel optimal, nous pouvons utiliser les 3 canaux (B, G, R)
        for y in range(self.height):
            for x in range(self.width):
                if self.optimal_mask[y, x] == 255:  # Si c'est un pixel optimal
                    for c in range(self.channels):
                        optimal_coords.append((y, x, c))
        
        return optimal_coords
        
    def _text_to_bits(self, text):
        """
        Convertit un texte en une chaîne de bits.
        
        Args:
            text (str): Texte à convertir
            
        Returns:
            str: Chaîne de bits (ex: '101010101...')
        """
        # Convertir le texte en bytes
        text_bytes = text.encode('utf-8')
        
        # Convertir chaque byte en bits
        bits = ''.join([format(byte, '08b') for byte in text_bytes])
        
        return bits
    
    def _file_to_bits(self, file_path):
        """
        Convertit un fichier binaire en une chaîne de bits.
        
        Args:
            file_path (str): Chemin vers le fichier à convertir
            
        Returns:
            str: Chaîne de bits (ex: '101010101...')
        """
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        # Obtenir le nom du fichier (pour le stockage)
        file_name = os.path.basename(file_path)
        file_name_bytes = file_name.encode('utf-8')
        
        # Structure: [taille du nom (4 bytes)][nom du fichier][taille des données (4 bytes)][données]
        name_length = len(file_name_bytes)
        data_length = len(file_bytes)
        
        # Convertir les longueurs en bytes (format little-endian)
        name_length_bytes = struct.pack('<I', name_length)
        data_length_bytes = struct.pack('<I', data_length)
        
        # Combiner toutes les informations
        all_bytes = name_length_bytes + file_name_bytes + data_length_bytes + file_bytes
        
        # Convertir en bits
        bits = ''.join([format(byte, '08b') for byte in all_bytes])
        
        return bits
    
    def _check_capacity(self, data_bits):
        """
        Vérifie si l'image a une capacité suffisante pour insérer les données.
        
        Args:
            data_bits (str): Chaîne de bits à insérer
            
        Returns:
            bool: True si la capacité est suffisante, False sinon
        """
        # Ajouter 32 bits pour stocker la longueur des données
        total_bits = len(data_bits) + 32
        
        # Vérifier la capacité (nombre de pixels optimaux)
        return total_bits <= len(self.optimal_pixels)
        
    def _embed_bits_lsb(self, bits):
        """
        Intègre les bits dans l'image en utilisant la technique LSB.
        
        Args:
            bits (str): Chaîne de bits à insérer
            
        Returns:
            np.ndarray: Image avec les données intégrées
        """
        # Créer une copie de l'image pour ne pas modifier l'original
        stego_image = self.image.copy()
        
        # Ajouter la longueur des données au début (32 bits)
        length_bits = format(len(bits), '032b')
        all_bits = length_bits + bits
        
        total_bits = len(all_bits)
        
        # Vérifier la capacité une dernière fois
        if total_bits > len(self.optimal_pixels):
            raise ValueError(f"Capacité insuffisante. Besoin de {total_bits} bits, mais seulement {len(self.optimal_pixels)} disponibles.")
        
        # Insérer chaque bit dans le LSB des pixels optimaux
        for i, bit in enumerate(all_bits):
            if i >= len(self.optimal_pixels):
                break
                
            y, x, c = self.optimal_pixels[i]
            
            # Modifier le bit le moins significatif du pixel
            pixel_value = stego_image[y, x, c]
            
            # Effacer le LSB et définir la nouvelle valeur
            new_value = (pixel_value & 0xFE) | int(bit)
            stego_image[y, x, c] = new_value
            
        return stego_image
    
    def encode_text(self, secret_text, output_path=None):
        """
        Encode un texte secret dans l'image en utilisant les zones optimales.
        
        Args:
            secret_text (str): Texte à cacher dans l'image
            output_path (str, optional): Chemin de sortie pour l'image stéganographiée
            
        Returns:
            str: Chemin de l'image stéganographiée
        """
        # Convertir le texte en bits
        text_bits = self._text_to_bits(secret_text)
        
        # Vérifier la capacité
        if not self._check_capacity(text_bits):
            text_len_bytes = len(text_bits) // 8
            raise ValueError(
                f"Le texte est trop long ({text_len_bytes} octets) pour la capacité de l'image ({self.capacity} octets)."
            )
        
        # Intégrer les bits dans l'image
        stego_image = self._embed_bits_lsb(text_bits)
        
        # Définir le chemin de sortie
        if output_path is None:
            output_path = str(self.image_path.parent / f"{self.image_path.stem}_stego.png")
        
        # Enregistrer l'image
        cv2.imwrite(output_path, stego_image)
        
        print(f"Message caché avec succès dans: {output_path}")
        print(f"Taille du message: {len(text_bits) // 8} octets")
        
        return output_path
    
    def encode_file(self, file_path, output_path=None):
        """
        Encode un fichier dans l'image en utilisant les zones optimales.
        
        Args:
            file_path (str): Chemin vers le fichier à cacher
            output_path (str, optional): Chemin de sortie pour l'image stéganographiée
            
        Returns:
            str: Chemin de l'image stéganographiée
        """
        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Le fichier {file_path} n'existe pas.")
        
        # Convertir le fichier en bits
        file_bits = self._file_to_bits(file_path)
        
        # Vérifier la capacité
        if not self._check_capacity(file_bits):
            file_len_bytes = len(file_bits) // 8
            raise ValueError(
                f"Le fichier est trop volumineux ({file_len_bytes} octets) pour la capacité de l'image ({self.capacity} octets)."
            )
        
        # Intégrer les bits dans l'image
        stego_image = self._embed_bits_lsb(file_bits)
        
        # Définir le chemin de sortie
        if output_path is None:
            output_path = str(self.image_path.parent / f"{self.image_path.stem}_stego.png")
        
        # Enregistrer l'image
        cv2.imwrite(output_path, stego_image)
        
        print(f"Fichier caché avec succès dans: {output_path}")
        print(f"Taille du fichier: {len(file_bits) // 8} octets")
        
        return output_path


def main():
    """Fonction principale pour tester l'encodeur de stéganographie."""
    # Chemin de l'image
    image_path = "99a28395d6c0e059ea4585a6e94df5c9.jpg"
    
    # Créer l'encodeur
    encoder = SteganographyEncoder(image_path, block_size=16, threshold_percentile=75)
    
    # Afficher la capacité
    print(f"Capacité d'insertion: {encoder.capacity} octets")
    
    # Option 1: Encoder un texte
    message_secret = "Ceci est un message secret caché dans l'image en utilisant les zones optimales identifiées par l'IA."
    encoder.encode_text(message_secret)
    
    # Option 2: Encoder un fichier (exemple avec un fichier texte)
    # with open("secret.txt", "w") as f:
    #     f.write("Contenu secret pour tester l'insertion de fichier.")
    # encoder.encode_file("secret.txt")


if __name__ == "__main__":
    main()
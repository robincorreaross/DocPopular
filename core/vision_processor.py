"""
vision_processor.py - Processamento de imagem para documentos usando OpenCV.
Funcionalidades: Auto-crop, Auto-rotate, Detecção de Frente/Verso.
"""

import numpy as np
import cv2
from PIL import Image
from core import logger

def pil_to_cv2(pil_img):
    """Converte imagem PIL para formato OpenCV (BGR)."""
    open_cv_image = np.array(pil_img.convert('RGB'))
    # Convert RGB to BGR
    return open_cv_image[:, :, ::-1].copy()

def cv2_to_pil(cv2_img):
    """Converte imagem OpenCV (BGR) para PIL (RGB)."""
    cv2_img_rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(cv2_img_rgb)

def process_smart_capture(pil_img):
    """
    Processa a imagem capturada para aplicar auto-crop e rotação.
    Retorna uma tupla (img_pil, is_half), onde is_half indica se a imagem
    parece ser apenas uma das faces (frente ou verso) do documento.
    """
    img_cv = pil_to_cv2(pil_img)
    img_h, img_w = img_cv.shape[:2]
    
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Detectar bordas e dilatar para conectar partes quebradas
    edged = cv2.Canny(blurred, 30, 150)
    kernel = np.ones((5,5), np.uint8)
    dilated = cv2.dilate(edged, kernel, iterations=2)
    
    # Encontrar contornos
    cnts, _ = cv2.findContours(dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not cnts:
        # Se não achou na canny, tenta threshold de Otsu invertido
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not cnts:
        logger.vision("Nenhum contorno detectado. Usando imagem original.")
        return pil_img, False
    
    # Filtrar contornos que representem pelo menos 3% da imagem (evitar sujeiras minúsculas)
    min_area = 0.03 * img_w * img_h
    large_cnts = [c for c in cnts if cv2.contourArea(c) > min_area]
    
    if not large_cnts:
        # Se todos os contornos forem microscópicos, não corta
        return pil_img, False
        
    # Combina todos os pontos dos contornos grandes em um array para englobar as duas faces (caso o RG seja aberto)
    all_points = np.vstack(large_cnts)
    x, y, w, h = cv2.boundingRect(all_points)
    
    area_box = w * h
    area_img = img_w * img_h
    
    # Se a área for muito pequena (ruído) ou quase do tamanho da imagem inteira (já cortado)
    if area_box < 0.1 * area_img or area_box > 0.95 * area_img:
        logger.vision(f"Crop ignorado (área {area_box/area_img:.1%}). Muito pequena ou quase tela cheia.")
        return pil_img, False
        
    logger.vision(f"Documento detectado! Crop aplicado: {w}x{h} (ratio {w/h:.2f})")
    cropped = img_cv[y:y+h, x:x+w]
    
    # Inteligência: Detectar se a box recortada É apenas uma face
    # (Só avaliamos se é 1 face SE realmente houve um crop limpo)
    ratio = max(w, h) / min(w, h)
    
    # RG fechado/CNH tem ratio ~1.5. RG aberto tem ratio > 2.0. 
    is_half = (1.3 < ratio < 1.8)
    
    return cv2_to_pil(cropped), is_half

def auto_rotate_document(pil_img):
    """
    Tenta rotacionar o documento para a orientação correta se ele estiver 'deitado'.
    Assume que documentos de identificação são geralmente verticais (Portrait).
    """
    w, h = pil_img.size
    if w > h:
        logger.vision("Documento deitado detectado. Rotacionando -90° para portrait.")
        return pil_img.rotate(-90, expand=True)
    return pil_img

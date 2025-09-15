INSTRUCCIONES PARA OBTENER EL DATASET YAHOO ANSWERS
=====================================================

ARCHIVO REQUERIDO: train.csv

Este archivo NO está incluido en el repositorio debido a su tamaño (319 MB).

CÓMO OBTENERLO:
1. Ve a: https://www.kaggle.com/datasets/soumikrakshit/yahoo-answers-dataset
2. Haz clic en "Download" (requiere cuenta de Kaggle gratuita)
3. Extrae el archivo "train.csv" del ZIP descargado
4. Colócalo en esta carpeta: dataset/train.csv

VERIFICACIÓN:
- Tamaño esperado: ~319 MB
- Formato: CSV con 4 columnas
- Columnas: class_index,question_title,question_content,best_answer
- Filas: Al menos 20,000 (el sistema usa las primeras 20k)

Una vez colocado correctamente, el sistema lo detectará automáticamente.

IMPORTANTE: SIN ESTE ARCHIVO EL SISTEMA NO FUNCIONARÁ

================================================================================

INFORMACIÓN ORIGINAL DEL DATASET:

The Yahoo! Answers topic classification dataset is constructed using 10 largest main categories. Each class contains 140,000 training samples and 6,000 testing samples. Therefore, the total number of training samples is 1,400,000 and testing samples 60,000 in this dataset.

There are 4 columns in them, corresponding to class index (1 to 10), question title, question content and best answer. The text fields are escaped using double quotes ("), and any internal double quote is escaped by 2 double quotes (""). New lines are escaped by a backslash followed with an "n" character, that is "\n".

# trainer/task.py
import argparse
import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

# Función para convertir los datos en secuencias que el modelo pueda aprender
def create_sequences(data, sequence_length, prediction_horizon):
    X, y = [], []
    for i in range(len(data) - sequence_length - prediction_horizon + 1):
        X.append(data[i:(i + sequence_length)])
        y.append(data[i + sequence_length + prediction_horizon - 1])
    return np.array(X), np.array(y)

def main():
    # Argumentos que recibiremos desde la configuración de Vertex AI
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-gcs-path', type=str, required=True)
    parser.add_argument('--model-output-path', type=str, required=True)
    args = parser.parse_args()

    # Parámetros del modelo (ajustables)
    SEQUENCE_LENGTH = 120  # Usar 120 mediciones pasadas
    PREDICTION_HORIZON = 15   # Para predecir el valor 15 mediciones en el futuro

    # Cargar los datos desde el archivo CSV en Google Cloud Storage
    print(f"Cargando datos desde: {args.data_gcs_path}")
    df = pd.read_csv(args.data_gcs_path)

    # Usar la columna "Valor" para el entrenamiento
    pressure_data = df['Valor'].values.reshape(-1, 1)

    # Normalizar los datos a una escala de 0 a 1 (mejora el entrenamiento)
    print("Normalizando datos...")
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(pressure_data)

    # Crear las secuencias de entrenamiento
    print("Creando secuencias de tiempo...")
    X, y = create_sequences(scaled_data, SEQUENCE_LENGTH, PREDICTION_HORIZON)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))

    # Dividir los datos en conjuntos de entrenamiento y validación
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    # Construir el modelo de red neuronal (LSTM)
    print("Construyendo el modelo LSTM...")
    model = tf.keras.models.Sequential([
        tf.keras.layers.LSTM(units=50, return_sequences=True, input_shape=(X_train.shape[1], 1)),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.LSTM(units=50),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(units=25),
        tf.keras.layers.Dense(units=1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    model.summary()

    # Entrenar el modelo
    print("Iniciando entrenamiento...")
    model.fit(X_train, y_train, epochs=20, batch_size=32, validation_data=(X_val, y_val))

    # Guardar el modelo entrenado en la ruta de GCS especificada
    print(f"Guardando el modelo en: {args.model_output_path}")
    model.save(args.model_output_path)
    print("¡Modelo guardado exitosamente!")

if __name__ == '__main__':
    main()
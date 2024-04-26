import numpy as np
import tensorflow as tf
from keras.api.preprocessing.sequence import pad_sequences

def build_model(input_shape):
    """ Building a simple LSTM model """
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(64, input_shape=input_shape, return_sequences=True),
        tf.keras.layers.LSTM(32),
        tf.keras.layers.Dense(16, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

def train_model(data, max_moves=40):
    """ Prepare the dataset and train the LSTM model """
    feature_columns = [col for col in data.columns if col not in ['Label']]
    
    padded_features = []

    for col in feature_columns:
        feature_list = data[col].apply(lambda x: np.array(x, dtype=np.float32)).tolist()
        padded_feature = pad_sequences(feature_list, maxlen=max_moves, dtype='float32', padding='post', truncating='post')
        padded_features.append(padded_feature)
    
    X = np.stack(padded_features, axis=-1) 
    y = data['Label'].values

    input_shape = (X.shape[1], X.shape[2])

    model = build_model(input_shape)
    model.summary()

    model.fit(X, y, epochs=10, batch_size=32, validation_split=0.2)

    return model

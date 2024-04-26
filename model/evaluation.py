import numpy as np
from keras.api.preprocessing.sequence import pad_sequences
from sklearn.metrics import classification_report


def evaluate_model(model, eval_data, max_moves=40):
    """Evaluate the trained model on evaluation data."""
    feature_columns = [col for col in eval_data.columns if col not in ['Label']]
    
    padded_features = []

    for col in feature_columns:
        feature_list = eval_data[col].apply(lambda x: np.array(x, dtype=np.float32)).tolist()
        padded_feature = pad_sequences(feature_list, maxlen=max_moves, dtype='float32', padding='post', truncating='post')
        padded_features.append(padded_feature)
    
    X_eval = np.stack(padded_features, axis=-1)
    y_eval = eval_data['Label'].values

    eval_loss, eval_accuracy = model.evaluate(X_eval, y_eval)
    print(f"Evaluation Loss: {eval_loss}")
    print(f"Evaluation Accuracy: {eval_accuracy}")

    y_pred = (model.predict(X_eval) > 0.5).astype("int32")
    
    print("Classification Report:")
    print(classification_report(y_eval, y_pred))

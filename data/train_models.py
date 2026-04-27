import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent

def train_diabetes_model():
    print("Training Diabetes Model...")
    x_path = DATA_DIR / 'Diabetes_XTrain.csv'
    y_path = DATA_DIR / 'Diabetes_YTrain.csv'
    
    if x_path.exists() and y_path.exists():
        x_values = pd.read_csv(x_path).values
        y_values = pd.read_csv(y_path).values.reshape((-1,))
        model = KNeighborsClassifier(n_neighbors=3)
        model.fit(x_values, y_values)
        joblib.dump(model, DATA_DIR / 'diabetes_model.pkl')
        print("-> Saved diabetes_model.pkl")
    else:
        print("-> Missing Diabetes CSV files!")

def train_breast_model():
    print("Training Breast Cancer Model...")
    csv_path = DATA_DIR / 'Breast_train.csv'
    
    if csv_path.exists():
        data = pd.read_csv(csv_path).values
        x_values = data[:, :-1]
        y_values = data[:, -1]
        model = RandomForestClassifier(n_estimators=16, criterion='entropy', max_depth=5)
        model.fit(np.nan_to_num(x_values), y_values)
        joblib.dump(model, DATA_DIR / 'breast_model.pkl')
        print("-> Saved breast_model.pkl")
    else:
        print("-> Missing Breast Cancer CSV file!")

def train_heart_model():
    print("Training Heart Disease Model...")
    csv_path = DATA_DIR / 'Heart_train.csv'
    
    if csv_path.exists():
        data = pd.read_csv(csv_path).values
        x_values = data[:, :-1]
        y_values = data[:, -1:]
        model = RandomForestClassifier(n_estimators=16, criterion='entropy', max_depth=9)
        model.fit(np.nan_to_num(x_values), y_values.ravel())
        joblib.dump(model, DATA_DIR / 'heart_disease_model.pkl')
        print("-> Saved heart_disease_model.pkl")
    else:
        print("-> Missing Heart Disease CSV file!")

if __name__ == "__main__":
    train_diabetes_model()
    train_breast_model()
    train_heart_model()
    print("All models trained and saved successfully.")

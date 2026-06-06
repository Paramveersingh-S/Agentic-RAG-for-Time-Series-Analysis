import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
import xgboost as xgb
from sklearn.ensemble import IsolationForest
import warnings

warnings.filterwarnings('ignore')

class TimeSeriesModelingHub:
    """
    A hub for time-series forecasting and anomaly detection algorithms.
    """

    @staticmethod
    def forecast_arima(series: pd.Series, steps: int = 24, order: tuple = (5, 1, 0)):
        """
        Baseline forecasting using ARIMA.
        
        Args:
            series (pd.Series): The historical time-series data.
            steps (int): Number of steps to forecast.
            order (tuple): ARIMA (p, d, q) order.
            
        Returns:
            pd.Series: Forecasted values.
        """
        model = ARIMA(series, order=order)
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=steps)
        return forecast

    @staticmethod
    def forecast_xgboost(train_df: pd.DataFrame, target_col: str, feature_cols: list, test_features: pd.DataFrame):
        """
        Multivariate forecasting using XGBoost utilizing dbt-generated lag features.
        
        Args:
            train_df (pd.DataFrame): Training data containing features and target.
            target_col (str): The column name of the target variable.
            feature_cols (list): List of feature column names (e.g., lags, rolling avgs).
            test_features (pd.DataFrame): Features for the future steps to predict.
            
        Returns:
            np.ndarray: Predicted values.
        """
        X_train = train_df[feature_cols]
        y_train = train_df[target_col]
        
        # Initialize and fit XGBoost Regressor
        model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1)
        model.fit(X_train, y_train)
        
        # Predict
        predictions = model.predict(test_features[feature_cols])
        return predictions

    @staticmethod
    def detect_anomalies_isolation_forest(df: pd.DataFrame, feature_cols: list, contamination: float = 0.05):
        """
        Anomaly detection using Isolation Forests.
        
        Args:
            df (pd.DataFrame): Dataframe containing the time-series and features.
            feature_cols (list): Features to use for anomaly detection (e.g., value, rolling_stddev).
            contamination (float): The proportion of outliers in the data set.
            
        Returns:
            pd.DataFrame: Original dataframe with an added 'is_anomaly' boolean column.
        """
        X = df[feature_cols].fillna(0)  # Handle any missing lag features simply
        
        model = IsolationForest(contamination=contamination, random_state=42)
        model.fit(X)
        
        # Predictions: -1 for anomaly, 1 for normal
        preds = model.predict(X)
        
        df_result = df.copy()
        df_result['is_anomaly'] = preds == -1
        return df_result

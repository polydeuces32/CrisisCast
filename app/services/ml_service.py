"""
ML service for forecasting and volatility analysis
"""

from __future__ import annotations

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import joblib
import os
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
import ta
import warnings
warnings.filterwarnings('ignore')

from app.core.database import get_db, get_db_session, MarketData, Forecast, ModelPerformance
from app.core.config import settings

logger = logging.getLogger(__name__)

class MLService:
    """Machine Learning service for forecasting and analysis"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.model_scores = {}  # stores best R² per market/symbol key
        self.running = False
        self.model_dir = "data/models"
        
        # Create model directory if it doesn't exist
        os.makedirs(self.model_dir, exist_ok=True)
    
    async def start_model_updates(self):
        """Start periodic model updates"""
        self.running = True
        logger.info("Starting ML model updates...")
        
        # Initial model training
        await self.train_all_models()
        
        # Start periodic updates
        while self.running:
            try:
                await asyncio.sleep(settings.model_update_interval)
                if self.running:
                    await self.update_models()
            except Exception as e:
                logger.error(f"Error in model updates: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def stop_model_updates(self):
        """Stop model updates"""
        self.running = False
        logger.info("Stopped ML model updates")
    
    async def train_all_models(self):
        """Train models for all markets"""
        for market in settings.supported_markets:
            try:
                await self.train_market_models(market)
            except Exception as e:
                logger.error(f"Error training models for {market}: {e}")
    
    async def train_market_models(self, market: str):
        """Train models for a specific market"""
        logger.info(f"Training models for {market}")
        
        # Get market data
        data = await self._get_market_data(market)
        
        if data.empty:
            logger.warning(f"No data available for {market}")
            return
        
        # Get unique symbols
        symbols = data['symbol'].unique()
        
        for symbol in symbols:
            try:
                await self._train_symbol_models(market, symbol, data)
            except Exception as e:
                logger.error(f"Error training models for {market}/{symbol}: {e}")
    
    async def _train_symbol_models(self, market: str, symbol: str, data: pd.DataFrame):
        """Train models for a specific symbol"""
        symbol_data = data[data['symbol'] == symbol].copy()
        
        if len(symbol_data) < 50:  # Need minimum data points
            logger.warning(f"Insufficient data for {market}/{symbol}")
            return
        
        # Prepare features and target
        features, target = self._prepare_features(symbol_data)
        
        if features is None or target is None:
            logger.warning(f"Could not prepare features for {market}/{symbol}")
            return
        
        # Chronological split — keeps temporal order to avoid data leakage
        split_idx = int(len(features) * 0.8)
        X_train, X_test = features[:split_idx], features[split_idx:]
        y_train, y_test = target[:split_idx], target[split_idx:]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train multiple models
        models = {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'gradient_boosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'linear_regression': LinearRegression(),
            'ridge': Ridge(alpha=1.0)
        }
        
        best_model = None
        best_score = -np.inf
        best_model_name = None
        
        for model_name, model in models.items():
            try:
                # Train model
                model.fit(X_train_scaled, y_train)
                
                # Evaluate model
                y_pred = model.predict(X_test_scaled)
                score = r2_score(y_test, y_pred)
                
                # Store model
                model_key = f"{market}_{symbol}_{model_name}"
                self.models[model_key] = model
                self.scalers[model_key] = scaler
                
                # Save model
                model_path = os.path.join(self.model_dir, f"{model_key}.joblib")
                scaler_path = os.path.join(self.model_dir, f"{model_key}_scaler.joblib")
                
                joblib.dump(model, model_path)
                joblib.dump(scaler, scaler_path)
                
                # Track performance
                await self._save_model_performance(
                    market, symbol, model_name, score, y_test, y_pred
                )
                
                # Update best model
                if score > best_score:
                    best_score = score
                    best_model = model
                    best_model_name = model_name
                
                logger.info(f"Trained {model_name} for {market}/{symbol}: R² = {score:.4f}")
                
            except Exception as e:
                logger.error(f"Error training {model_name} for {market}/{symbol}: {e}")
        
        # Store best model and its R² score for use as confidence signal
        if best_model is not None:
            best_key = f"{market}_{symbol}_best"
            self.models[best_key] = best_model
            self.scalers[best_key] = scaler
            self.model_scores[best_key] = max(0.0, best_score)  # clamp negative R²
    
    def _prepare_features(self, data: pd.DataFrame) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Prepare features for ML models"""
        try:
            # Sort by timestamp
            data = data.sort_values('timestamp')
            
            # Create time-based features
            data['hour'] = data['timestamp'].dt.hour
            data['day_of_week'] = data['timestamp'].dt.dayofweek
            data['day_of_month'] = data['timestamp'].dt.day
            data['month'] = data['timestamp'].dt.month
            
            # Create price-based features
            data['price_change'] = data['price'].pct_change()
            data['price_ma_7'] = data['price'].rolling(window=7).mean()
            data['price_ma_30'] = data['price'].rolling(window=30).mean()
            data['price_std_7'] = data['price'].rolling(window=7).std()
            data['price_std_30'] = data['price'].rolling(window=30).std()
            
            # Create volume features
            if 'volume' in data.columns and data['volume'].notna().any():
                data['volume_ma_7'] = data['volume'].rolling(window=7).mean()
                data['volume_ma_30'] = data['volume'].rolling(window=30).mean()
                data['volume_std_7'] = data['volume'].rolling(window=7).std()
                data['volume_std_30'] = data['volume'].rolling(window=30).std()
                data['volume_change'] = data['volume'].pct_change()
            else:
                data['volume_ma_7'] = 0
                data['volume_ma_30'] = 0
                data['volume_std_7'] = 0
                data['volume_std_30'] = 0
                data['volume_change'] = 0
            
            # Create technical indicators
            data['rsi'] = ta.momentum.RSIIndicator(data['price']).rsi()
            data['macd'] = ta.trend.MACD(data['price']).macd()
            data['bb_upper'] = ta.volatility.BollingerBands(data['price']).bollinger_hband()
            data['bb_lower'] = ta.volatility.BollingerBands(data['price']).bollinger_lband()
            data['bb_middle'] = ta.volatility.BollingerBands(data['price']).bollinger_mavg()
            
            # Create volatility features
            data['volatility_7'] = data['price_change'].rolling(window=7).std()
            data['volatility_30'] = data['price_change'].rolling(window=30).std()
            
            # Create lag features
            for lag in [1, 2, 3, 7, 14, 30]:
                data[f'price_lag_{lag}'] = data['price'].shift(lag)
                data[f'volume_lag_{lag}'] = data['volume'].shift(lag)
            
            # Select feature columns
            feature_columns = [
                'hour', 'day_of_week', 'day_of_month', 'month',
                'price_change', 'price_ma_7', 'price_ma_30', 'price_std_7', 'price_std_30',
                'volume_ma_7', 'volume_ma_30', 'volume_std_7', 'volume_std_30', 'volume_change',
                'rsi', 'macd', 'bb_upper', 'bb_lower', 'bb_middle',
                'volatility_7', 'volatility_30'
            ]
            
            # Add lag features
            for lag in [1, 2, 3, 7, 14, 30]:
                feature_columns.extend([f'price_lag_{lag}', f'volume_lag_{lag}'])
            
            # Prepare features and target
            features = data[feature_columns].fillna(0).values
            target = data['price'].values
            
            # Remove rows with NaN values
            valid_indices = ~(np.isnan(features).any(axis=1) | np.isnan(target))
            features = features[valid_indices]
            target = target[valid_indices]
            
            return features, target
            
        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            return None, None
    
    async def _save_model_performance(self, market: str, symbol: str, model_name: str, 
                                    score: float, y_test: np.ndarray, y_pred: np.ndarray):
        """Save model performance metrics"""
        try:
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)

            with get_db_session() as db:
                db.add(ModelPerformance(
                    model_name=model_name, market=market, symbol=symbol,
                    metric_name='r2_score', metric_value=score,
                    evaluation_date=datetime.utcnow(), model_version='1.0'
                ))
                db.add(ModelPerformance(
                    model_name=model_name, market=market, symbol=symbol,
                    metric_name='mse', metric_value=mse,
                    evaluation_date=datetime.utcnow(), model_version='1.0'
                ))
                db.add(ModelPerformance(
                    model_name=model_name, market=market, symbol=symbol,
                    metric_name='mae', metric_value=mae,
                    evaluation_date=datetime.utcnow(), model_version='1.0'
                ))
                db.commit()
        except Exception as e:
            logger.error(f"Error saving model performance: {e}")
    
    async def generate_forecast(self, market: str, symbol: str, horizon_days: int = 180, 
                              include_ai_explanation: bool = True) -> Dict[str, Any]:
        """Generate forecast for a symbol"""
        try:
            # Get latest data
            data = await self._get_market_data(market, symbol)
            
            if data.empty:
                return {
                    "error": "No data available",
                    "market": market,
                    "symbol": symbol
                }
            
            # Get best model
            model_key = f"{market}_{symbol}_best"
            if model_key not in self.models:
                # Try to load model
                await self._load_model(model_key)
            
            if model_key not in self.models:
                return {
                    "error": "No trained model available",
                    "market": market,
                    "symbol": symbol
                }
            
            # Prepare features for prediction
            features, _ = self._prepare_features(data)
            
            if features is None or len(features) == 0:
                return {
                    "error": "Could not prepare features",
                    "market": market,
                    "symbol": symbol
                }
            
            # Use latest features for prediction
            latest_features = features[-1:].reshape(1, -1)
            
            # Scale features
            scaler = self.scalers[model_key]
            latest_features_scaled = scaler.transform(latest_features)
            
            # Generate forecast
            model = self.models[model_key]
            predicted_price = model.predict(latest_features_scaled)[0]
            
            # Confidence derived from the model's R² on the held-out test set
            confidence_score = min(0.95, max(0.1, self.model_scores.get(model_key, 0.5)))
            
            # Determine trend direction
            current_price = data['price'].iloc[-1]
            trend_direction = "bullish" if predicted_price > current_price else "bearish"
            
            # Calculate volatility score
            volatility_score = await self.calculate_volatility_score(market, symbol)
            
            # Generate AI explanation if requested
            ai_explanation = None
            if include_ai_explanation:
                ai_explanation = await self._generate_ai_explanation(
                    market, symbol, predicted_price, current_price, trend_direction, volatility_score
                )
            
            # Create forecast record
            forecast_data = {
                "market": market,
                "symbol": symbol,
                "forecast_date": datetime.utcnow().isoformat(),
                "horizon_days": horizon_days,
                "current_price": current_price,
                "predicted_price": predicted_price,
                "confidence_score": confidence_score,
                "trend_direction": trend_direction,
                "volatility_score": volatility_score,
                "ai_explanation": ai_explanation,
                "model_version": "1.0",
                "additional_metrics": {
                    "price_change_percent": ((predicted_price - current_price) / current_price) * 100,
                    "risk_level": "high" if volatility_score > 0.7 else "medium" if volatility_score > 0.4 else "low"
                }
            }
            
            # Save forecast to database
            await self._save_forecast(forecast_data)
            
            return forecast_data
            
        except Exception as e:
            logger.error(f"Error generating forecast for {market}/{symbol}: {e}")
            return {
                "error": str(e),
                "market": market,
                "symbol": symbol
            }
    
    async def calculate_volatility_score(self, market: str, symbol: str, timeframe: str = "30d") -> float:
        """Calculate volatility score for a symbol"""
        try:
            # Get market data
            data = await self._get_market_data(market, symbol)
            
            if data.empty or len(data) < 10:
                return 0.5  # Default moderate volatility
            
            # Calculate price changes
            price_changes = data['price'].pct_change().dropna()
            
            # Calculate volatility based on timeframe
            if timeframe == "7d":
                window = min(7, len(price_changes))
            elif timeframe == "30d":
                window = min(30, len(price_changes))
            elif timeframe == "90d":
                window = min(90, len(price_changes))
            else:
                window = min(30, len(price_changes))
            
            # Calculate rolling volatility
            volatility = price_changes.rolling(window=window).std().iloc[-1]
            
            # Normalize to 0-1 scale
            volatility_score = min(1.0, max(0.0, volatility * 10))  # Scale factor may need adjustment
            
            return volatility_score
            
        except Exception as e:
            logger.error(f"Error calculating volatility score: {e}")
            return 0.5
    
    async def _generate_ai_explanation(self, market: str, symbol: str, predicted_price: float, 
                                     current_price: float, trend_direction: str, 
                                     volatility_score: float) -> str:
        """Generate AI explanation for forecast"""
        try:
            # This is a simplified explanation generator
            # In practice, you'd integrate with OpenAI or Ollama
            
            price_change_percent = ((predicted_price - current_price) / current_price) * 100
            
            explanation = f"""
            Based on the current market data for {symbol} in the {market} market, our analysis suggests:
            
            • **Price Forecast**: The predicted price of ${predicted_price:.2f} represents a {price_change_percent:+.1f}% change from the current price of ${current_price:.2f}
            
            • **Trend Analysis**: The {trend_direction} trend indicates {'upward momentum' if trend_direction == 'bullish' else 'downward pressure'} in the market
            
            • **Volatility Assessment**: With a volatility score of {volatility_score:.2f}, the market shows {'high' if volatility_score > 0.7 else 'moderate' if volatility_score > 0.4 else 'low'} volatility levels
            
            • **Risk Factors**: {'High volatility suggests increased risk and potential for significant price swings' if volatility_score > 0.7 else 'Moderate volatility indicates stable market conditions' if volatility_score > 0.4 else 'Low volatility suggests stable but potentially limited growth opportunities'}
            
            • **Recommendation**: {'Consider the high volatility when making investment decisions' if volatility_score > 0.7 else 'Monitor market conditions for any significant changes' if volatility_score > 0.4 else 'Stable conditions may present good entry points for long-term positions'}
            
            *This analysis is based on historical data and machine learning models. Past performance does not guarantee future results.*
            """
            
            return explanation.strip()
            
        except Exception as e:
            logger.error(f"Error generating AI explanation: {e}")
            return "AI explanation not available at this time."
    
    async def _save_forecast(self, forecast_data: Dict[str, Any]):
        """Save forecast to database"""
        try:
            with get_db_session() as db:
                db.add(Forecast(
                    market=forecast_data["market"],
                    symbol=forecast_data["symbol"],
                    forecast_date=datetime.fromisoformat(forecast_data["forecast_date"]),
                    horizon_days=forecast_data["horizon_days"],
                    predicted_price=forecast_data["predicted_price"],
                    confidence_score=forecast_data["confidence_score"],
                    trend_direction=forecast_data["trend_direction"],
                    volatility_score=forecast_data["volatility_score"],
                    model_version=forecast_data["model_version"],
                    additional_metrics=forecast_data["additional_metrics"]
                ))
                db.commit()
        except Exception as e:
            logger.error(f"Error saving forecast: {e}")
    
    async def _get_market_data(self, market: str, symbol: Optional[str] = None) -> pd.DataFrame:
        """Get market data from database"""
        try:
            with get_db_session() as db:
                query = db.query(MarketData).filter(MarketData.market == market)
                if symbol:
                    query = query.filter(MarketData.symbol == symbol)
                cutoff_date = datetime.utcnow() - timedelta(days=365)
                query = query.filter(MarketData.timestamp >= cutoff_date)
                data = query.order_by(MarketData.timestamp.asc()).all()

            if not data:
                return pd.DataFrame()

            return pd.DataFrame([{
                'timestamp': r.timestamp,
                'price': r.price,
                'volume': r.volume,
                'market_cap': r.market_cap,
                'symbol': r.symbol,
                'source': r.source,
            } for r in data])

        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return pd.DataFrame()
    
    async def _load_model(self, model_key: str):
        """Load model from disk"""
        try:
            model_path = os.path.join(self.model_dir, f"{model_key}.joblib")
            scaler_path = os.path.join(self.model_dir, f"{model_key}_scaler.joblib")
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                model = joblib.load(model_path)
                scaler = joblib.load(scaler_path)
                
                self.models[model_key] = model
                self.scalers[model_key] = scaler
                
                logger.info(f"Loaded model: {model_key}")
            
        except Exception as e:
            logger.error(f"Error loading model {model_key}: {e}")
    
    async def update_models(self):
        """Update models with new data"""
        logger.info("Updating models with new data...")
        await self.train_all_models()
    
    async def retrain_models(self, market: str, model_type: Optional[str] = None):
        """Retrain models for a specific market"""
        logger.info(f"Retraining models for {market}")
        await self.train_market_models(market)
    
    async def retrain_all_models(self):
        """Retrain all models"""
        logger.info("Retraining all models")
        await self.train_all_models()
    
    async def get_market_trends(self, market: str, timeframe: str = "6m") -> Dict[str, Any]:
        """Get overall market trends and sentiment"""
        try:
            # Get market data
            data = await self._get_market_data(market)
            
            if data.empty:
                return {
                    "market": market,
                    "timeframe": timeframe,
                    "trend": "neutral",
                    "sentiment": "unknown",
                    "volatility": 0.5,
                    "message": "No data available"
                }
            
            # Calculate overall trend
            symbols = data['symbol'].unique()
            trends = []
            
            for symbol in symbols:
                symbol_data = data[data['symbol'] == symbol]
                if len(symbol_data) > 1:
                    price_change = (symbol_data['price'].iloc[-1] - symbol_data['price'].iloc[0]) / symbol_data['price'].iloc[0]
                    trends.append(price_change)
            
            if trends:
                avg_trend = sum(trends) / len(trends)
                overall_trend = "bullish" if avg_trend > 0.05 else "bearish" if avg_trend < -0.05 else "neutral"
                sentiment = "positive" if avg_trend > 0 else "negative" if avg_trend < 0 else "neutral"
            else:
                overall_trend = "neutral"
                sentiment = "unknown"
                avg_trend = 0
            
            # Calculate overall volatility
            all_volatility = []
            for symbol in symbols:
                symbol_data = data[data['symbol'] == symbol]
                if len(symbol_data) > 1:
                    volatility = symbol_data['price'].pct_change().std()
                    if not pd.isna(volatility):
                        all_volatility.append(volatility)
            
            overall_volatility = sum(all_volatility) / len(all_volatility) if all_volatility else 0.5
            
            return {
                "market": market,
                "timeframe": timeframe,
                "trend": overall_trend,
                "sentiment": sentiment,
                "average_change_percent": avg_trend * 100,
                "volatility": min(1.0, max(0.0, overall_volatility * 10)),
                "symbols_analyzed": len(symbols),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market trends: {e}")
            return {
                "market": market,
                "timeframe": timeframe,
                "trend": "unknown",
                "sentiment": "unknown",
                "volatility": 0.5,
                "error": str(e)
            }
    
    async def calculate_detailed_volatility(self, market: str, symbol: str, timeframe: str = "30d", 
                                          include_breakdown: bool = True) -> Dict[str, Any]:
        """Calculate detailed volatility analysis for a symbol"""
        try:
            # Get basic volatility score
            volatility_score = await self.calculate_volatility_score(market, symbol, timeframe)
            
            result = {
                "market": market,
                "symbol": symbol,
                "volatility_score": volatility_score,
                "timeframe": timeframe,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            if include_breakdown:
                # Get market data for detailed analysis
                data = await self._get_market_data(market, symbol)
                
                if not data.empty and len(data) > 1:
                    price_changes = data['price'].pct_change().dropna()
                    
                    # Calculate breakdown metrics
                    breakdown = {
                        "price_volatility": price_changes.std(),
                        "max_daily_change": price_changes.max(),
                        "min_daily_change": price_changes.min(),
                        "volatility_percentile": 0.5,  # Placeholder
                        "trend_consistency": 0.5,  # Placeholder
                        "outlier_frequency": 0.1  # Placeholder
                    }
                    
                    result["breakdown"] = breakdown
                else:
                    result["breakdown"] = None
                    result["message"] = "Insufficient data for detailed analysis"
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating detailed volatility: {e}")
            return {
                "market": market,
                "symbol": symbol,
                "volatility_score": 0.5,
                "timeframe": timeframe,
                "error": str(e)
            }
    
    async def compare_volatility_scores(self, market: str, symbols: List[str], timeframe: str = "30d") -> Dict[str, Any]:
        """Compare volatility scores across multiple symbols"""
        try:
            comparison_data = {}
            
            for symbol in symbols:
                volatility_score = await self.calculate_volatility_score(market, symbol, timeframe)
                comparison_data[symbol] = {
                    "volatility_score": volatility_score,
                    "risk_level": "high" if volatility_score > 0.7 else "medium" if volatility_score > 0.4 else "low"
                }
            
            # Calculate rankings
            sorted_symbols = sorted(comparison_data.items(), key=lambda x: x[1]["volatility_score"], reverse=True)
            
            return {
                "market": market,
                "timeframe": timeframe,
                "comparison": comparison_data,
                "rankings": [{"symbol": symbol, "volatility_score": data["volatility_score"]} 
                           for symbol, data in sorted_symbols],
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error comparing volatility scores: {e}")
            return {
                "market": market,
                "timeframe": timeframe,
                "error": str(e)
            }
    
    async def generate_volatility_heatmap(self, market: str, timeframe: str = "30d") -> Dict[str, Any]:
        """Generate volatility heatmap data for market visualization"""
        try:
            # Get all symbols for the market
            data = await self._get_market_data(market)
            
            if data.empty:
                return {
                    "market": market,
                    "timeframe": timeframe,
                    "heatmap_data": [],
                    "message": "No data available"
                }
            
            symbols = data['symbol'].unique()
            heatmap_data = []
            
            for symbol in symbols:
                volatility_score = await self.calculate_volatility_score(market, symbol, timeframe)
                heatmap_data.append({
                    "symbol": symbol,
                    "volatility_score": volatility_score,
                    "risk_level": "high" if volatility_score > 0.7 else "medium" if volatility_score > 0.4 else "low"
                })
            
            return {
                "market": market,
                "timeframe": timeframe,
                "heatmap_data": heatmap_data,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating volatility heatmap: {e}")
            return {
                "market": market,
                "timeframe": timeframe,
                "error": str(e)
            }
    
    async def get_volatility_history(self, market: str, symbol: str, days_back: int = 30) -> Dict[str, Any]:
        """Get historical volatility data"""
        try:
            # Get historical data
            data = await self._get_market_data(market, symbol)
            
            if data.empty:
                return {
                    "market": market,
                    "symbol": symbol,
                    "days_back": days_back,
                    "history": [],
                    "message": "No data available"
                }
            
            # Calculate daily volatility scores
            history = []
            for i in range(7, len(data)):  # Start from day 7 to have enough data
                window_data = data.iloc[i-7:i]
                if len(window_data) > 1:
                    volatility = window_data['price'].pct_change().std()
                    if not pd.isna(volatility):
                        history.append({
                            "date": window_data['timestamp'].iloc[-1].isoformat(),
                            "volatility_score": min(1.0, max(0.0, volatility * 10)),
                            "price": window_data['price'].iloc[-1]
                        })
            
            return {
                "market": market,
                "symbol": symbol,
                "days_back": days_back,
                "history": history[-days_back:],  # Limit to requested days
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting volatility history: {e}")
            return {
                "market": market,
                "symbol": symbol,
                "days_back": days_back,
                "error": str(e)
            }
    
    async def generate_custom_forecast(self, market: str, symbol: str, custom_parameters: Dict[str, Any], 
                                     horizon_days: int = 180) -> Dict[str, Any]:
        """Generate custom forecast with specific parameters"""
        try:
            # For now, use the standard forecast but with custom parameters
            # In a real implementation, you'd use the custom parameters to modify the model behavior
            
            forecast_data = await self.generate_forecast(market, symbol, horizon_days)
            
            # Add custom parameters info
            forecast_data["custom_parameters"] = custom_parameters
            forecast_data["custom_forecast"] = True
            
            return forecast_data
            
        except Exception as e:
            logger.error(f"Error generating custom forecast: {e}")
            return {
                "error": str(e),
                "market": market,
                "symbol": symbol,
                "custom_parameters": custom_parameters
            }
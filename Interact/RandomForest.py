import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import datetime
from typing import Dict, Optional, List

class WorkoutPlanAPI:
    """运动计划函数接口，供其他脚本调用获取次日运动次数计划""" 
    def __init__(self, model_path: str = "workout_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.features = [
            "day_of_week", "is_weekend", "workout_duration", 
            "calories_burned", "workout_score", "previous_days_count",
            "average_duration_last_3", "average_score_last_3",
            "max_consecutive_days", "recovery_days"
        ]
        self.workout_types = ["squat", "sit_up", "push_up"]
        self._load_model()
    
    def _load_model(self) -> None:
        """加载预训练的模型和标准化器"""
        try:
            model_data = joblib.load(self.model_path)
            self.model = model_data["model"]
            self.scaler = model_data["scaler"]
        except FileNotFoundError:
            # 若模型不存在，初始化一个新模型
            self.model = RandomForestRegressor(
                n_estimators=100, 
                random_state=42,
                min_samples_split=5,
                min_samples_leaf=2,
                max_depth=10,
                n_jobs=-1
            )
    
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df['day_of_week'] = df['date'].dt.dayofweek
            df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # 排序确保时间顺序正确
        df = df.sort_values('date')
        df['average_duration_last_3'] = df['workout_duration'].rolling(window=3, min_periods=1).mean()
        df['average_score_last_3'] = df['workout_score'].rolling(window=3, min_periods=1).mean()
        
        # 计算特征
        df['is_workout_day'] = df['workout_count'] > 0
        df['consecutive'] = df.groupby(
            (df['is_workout_day'] != df['is_workout_day'].shift()).cumsum()
        ).cumcount() + 1
        df['max_consecutive_days'] = df['consecutive'] * df['is_workout_day']

        df['days_since_last_workout'] = df['date'].diff().dt.days.fillna(0)
        df.loc[~df['is_workout_day'], 'days_since_last_workout'] = 0
        df['recovery_days'] = df.groupby(
            (df['is_workout_day'] == 0).cumsum()
        )['days_since_last_workout'].cumsum()
        
        # 确保所有特征存在
        for feature in self.features:
            if feature not in df.columns:
                df[feature] = 0
                
        return df
    
    def train_model(self, historical_data: pd.DataFrame) -> None:
        """
        训练模型（若需要更新模型时调用）
        
        参数:
            historical_data: 包含历史运动数据的DataFrame，需包含以下列：
            date, workout_type, workout_count, workout_duration,
            calories_burned, workout_score
        """
        processed_data = self._preprocess_data(historical_data)
        X = processed_data[self.features]
        y = processed_data["next_day_workout_count"]
        
        # 标准化特征
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        
        # 训练模型
        self.model.fit(X_scaled, y)
        
        # 保存更新后的模型
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler
        }, self.model_path)
    
    def get_tomorrow_plan(self, user_data: pd.DataFrame) -> Dict[str, int]:
        """
        获取明天三种运动的次数计划
        
        参数:
            user_data: 用户历史运动数据，需包含以下列：
                date (日期), workout_type (运动类型), workout_count (次数),
                workout_duration (时长), calories_burned (热量消耗), workout_score (得分)
        
        返回:
            包含三种运动次日计划次数的字典，格式如：
            {"squat": 15, "sit_up": 20, "push_up": 12}
        """
        plan_result = {}
        
        for workout_type in self.workout_types:
            type_data = user_data[user_data['workout_type'] == workout_type].copy()
            
            # 数据不足时使用默认值
            if len(type_data) < 10:
                defaults = {"squat": 15, "sit_up": 20, "push_up": 12}
                plan_result[workout_type] = defaults[workout_type]
                continue

            processed_data = self._preprocess_data(type_data)
            latest_data = processed_data.iloc[-1].to_dict()
            latest_data['date'] = pd.to_datetime(latest_data['date']) + datetime.timedelta(days=1)
            latest_data['previous_days_count'] = latest_data.get('workout_count', 0)
            
            input_df = pd.DataFrame([latest_data])
            input_processed = self._preprocess_data(input_df)
            X = input_processed[self.features]
            
            # 标准化并预测
            X_scaled = self.scaler.transform(X)
            prediction = self.model.predict(X_scaled)[0]
            plan_count = max(0, round(prediction))
            plan_result[workout_type] = plan_count
        
        return plan_result
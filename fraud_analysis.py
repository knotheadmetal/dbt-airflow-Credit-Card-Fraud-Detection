#!/usr/bin/env python3
"""
Script de análise avançada de fraude de cartão de crédito
"""

import pandas as pd
import numpy as np
import psycopg2
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json

class FraudAnalyzer:
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None
        self.df = None
        
    def connect_db(self):
        """Conecta ao banco de dados PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            print("Conexão com banco de dados estabelecida")
        except Exception as e:
            print(f"Erro ao conectar ao banco: {e}")
            
    def load_data(self):
        """Carrega dados da camada Silver"""
        query = """
        SELECT * FROM silver_transactions
        ORDER BY transaction_timestamp
        """
        self.df = pd.read_sql(query, self.conn)
        print(f"Dados carregados: {len(self.df)} transações")
        
    def temporal_analysis(self):
        """Análise temporal de fraudes"""
        print("\n=== ANÁLISE TEMPORAL ===")
        
        # Análise por hora do dia
        hourly_fraud = self.df.groupby('hour_of_day').agg({
            'is_fraud': ['count', 'sum', 'mean']
        }).round(4)
        hourly_fraud.columns = ['total_transactions', 'fraud_count', 'fraud_rate']
        
        print("\nFraude por hora do dia:")
        print(hourly_fraud)
        
        # Análise por dia da semana
        daily_fraud = self.df.groupby('day_of_week').agg({
            'is_fraud': ['count', 'sum', 'mean']
        }).round(4)
        daily_fraud.columns = ['total_transactions', 'fraud_count', 'fraud_rate']
        
        print("\nFraude por dia da semana:")
        print(daily_fraud)
        
        return {
            'hourly_analysis': hourly_fraud.to_dict(),
            'daily_analysis': daily_fraud.to_dict()
        }
        
    def amount_analysis(self):
        """Análise de valores de transação"""
        print("\n=== ANÁLISE DE VALORES ===")
        
        # Estatísticas por categoria de valor
        amount_stats = self.df.groupby(['amount_category', 'is_fraud']).agg({
            'amount': ['count', 'mean', 'median', 'std']
        }).round(2)
        
        print("\nEstatísticas por categoria de valor:")
        print(amount_stats)
        
        # Comparação fraude vs legítima
        fraud_amounts = self.df[self.df['is_fraud'] == True]['amount']
        legit_amounts = self.df[self.df['is_fraud'] == False]['amount']
        
        comparison = {
            'fraud_avg': fraud_amounts.mean(),
            'legitimate_avg': legit_amounts.mean(),
            'fraud_median': fraud_amounts.median(),
            'legitimate_median': legit_amounts.median(),
            'fraud_std': fraud_amounts.std(),
            'legitimate_std': legit_amounts.std()
        }
        
        print(f"\nComparação de valores:")
        for key, value in comparison.items():
            print(f"{key}: {value:.2f}")
            
        return comparison
        
    def feature_analysis(self):
        """Análise das features V1-V28"""
        print("\n=== ANÁLISE DE FEATURES ===")
        
        # Features mais discriminativas (V4, V11, V14)
        key_features = ['v4', 'v11', 'v14']
        
        feature_stats = {}
        for feature in key_features:
            fraud_values = self.df[self.df['is_fraud'] == True][feature]
            legit_values = self.df[self.df['is_fraud'] == False][feature]
            
            stats = {
                'fraud_mean': fraud_values.mean(),
                'legitimate_mean': legit_values.mean(),
                'fraud_std': fraud_values.std(),
                'legitimate_std': legit_values.std(),
                'separation': abs(fraud_values.mean() - legit_values.mean())
            }
            
            feature_stats[feature] = stats
            
            print(f"\n{feature.upper()}:")
            print(f"  Fraude - Média: {stats['fraud_mean']:.3f}, Desvio: {stats['fraud_std']:.3f}")
            print(f"  Legítima - Média: {stats['legitimate_mean']:.3f}, Desvio: {stats['legitimate_std']:.3f}")
            print(f"  Separação: {stats['separation']:.3f}")
            
        return feature_stats
        
    def anomaly_detection(self):
        """Detecção de anomalias usando Isolation Forest"""
        print("\n=== DETECÇÃO DE ANOMALIAS ===")
        
        # Selecionar features para análise
        feature_cols = [f'v{i}' for i in range(1, 29)] + ['amount']
        X = self.df[feature_cols]
        
        # Normalizar dados
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Aplicar Isolation Forest
        iso_forest = IsolationForest(
            contamination=0.002,  # Aproximadamente a taxa de fraude
            random_state=42,
            n_estimators=100
        )
        
        anomaly_scores = iso_forest.fit_predict(X_scaled)
        anomaly_scores_prob = iso_forest.decision_function(X_scaled)
        
        # Adicionar scores ao DataFrame
        self.df['anomaly_score'] = anomaly_scores
        self.df['anomaly_prob'] = anomaly_scores_prob
        
        # Avaliar performance
        y_true = self.df['is_fraud'].astype(int)
        y_pred = (anomaly_scores == -1).astype(int)
        
        print("Relatório de classificação (Isolation Forest):")
        print(classification_report(y_true, y_pred))
        
        print("\nMatriz de confusão:")
        print(confusion_matrix(y_true, y_pred))
        
        # Estatísticas de anomalias
        anomalies_detected = sum(anomaly_scores == -1)
        actual_frauds = sum(y_true)
        
        results = {
            'anomalies_detected': anomalies_detected,
            'actual_frauds': actual_frauds,
            'detection_rate': sum((anomaly_scores == -1) & (y_true == 1)) / actual_frauds,
            'false_positive_rate': sum((anomaly_scores == -1) & (y_true == 0)) / sum(y_true == 0)
        }
        
        print(f"\nResultados da detecção:")
        print(f"Anomalias detectadas: {results['anomalies_detected']}")
        print(f"Fraudes reais: {results['actual_frauds']}")
        print(f"Taxa de detecção: {results['detection_rate']:.3f}")
        print(f"Taxa de falsos positivos: {results['false_positive_rate']:.3f}")
        
        return results
        
    def risk_analysis(self):
        """Análise de níveis de risco"""
        print("\n=== ANÁLISE DE RISCO ===")
        
        risk_stats = self.df.groupby('risk_level').agg({
            'is_fraud': ['count', 'sum', 'mean'],
            'amount': 'mean'
        }).round(4)
        
        risk_stats.columns = ['total_transactions', 'fraud_count', 'fraud_rate', 'avg_amount']
        
        print("Estatísticas por nível de risco:")
        print(risk_stats)
        
        return risk_stats.to_dict()
        
    def generate_insights(self):
        """Gera insights de negócio"""
        print("\n=== INSIGHTS DE NEGÓCIO ===")
        
        total_transactions = len(self.df)
        total_frauds = self.df['is_fraud'].sum()
        fraud_rate = total_frauds / total_transactions
        
        total_amount = self.df['amount'].sum()
        fraud_amount = self.df[self.df['is_fraud'] == True]['amount'].sum()
        
        insights = {
            'total_transactions': total_transactions,
            'total_frauds': total_frauds,
            'fraud_rate': fraud_rate,
            'total_amount': total_amount,
            'fraud_amount': fraud_amount,
            'fraud_amount_percentage': fraud_amount / total_amount,
            'avg_transaction_amount': self.df['amount'].mean(),
            'avg_fraud_amount': self.df[self.df['is_fraud'] == True]['amount'].mean(),
            'avg_legitimate_amount': self.df[self.df['is_fraud'] == False]['amount'].mean()
        }
        
        print(f"Total de transações: {insights['total_transactions']:,}")
        print(f"Total de fraudes: {insights['total_frauds']:,}")
        print(f"Taxa de fraude: {insights['fraud_rate']:.4f} ({insights['fraud_rate']*100:.2f}%)")
        print(f"Valor total transacionado: ${insights['total_amount']:,.2f}")
        print(f"Valor total em fraudes: ${insights['fraud_amount']:,.2f}")
        print(f"% do valor em fraudes: {insights['fraud_amount_percentage']*100:.2f}%")
        print(f"Valor médio por transação: ${insights['avg_transaction_amount']:.2f}")
        print(f"Valor médio de fraude: ${insights['avg_fraud_amount']:.2f}")
        print(f"Valor médio legítimo: ${insights['avg_legitimate_amount']:.2f}")
        
        return insights
        
    def save_results(self, results, filename):
        """Salva resultados em arquivo JSON"""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResultados salvos em {filename}")
        
    def run_complete_analysis(self):
        """Executa análise completa"""
        print("=== INICIANDO ANÁLISE COMPLETA DE FRAUDE ===")
        print(f"Timestamp: {datetime.now()}")
        
        self.connect_db()
        self.load_data()
        
        results = {
            'timestamp': datetime.now(),
            'temporal_analysis': self.temporal_analysis(),
            'amount_analysis': self.amount_analysis(),
            'feature_analysis': self.feature_analysis(),
            'anomaly_detection': self.anomaly_detection(),
            'risk_analysis': self.risk_analysis(),
            'business_insights': self.generate_insights()
        }
        
        self.save_results(results, '/home/ubuntu/etl-pipeline/fraud_analysis_results.json')
        
        if self.conn:
            self.conn.close()
            
        print("\n=== ANÁLISE COMPLETA FINALIZADA ===")
        return results

if __name__ == "__main__":
    # Configuração do banco de dados
    db_config = {
        'host': 'localhost',
        'database': 'fraud_detection',
        'user': 'user',
        'password': 'password',
        'port': 5432
    }
    
    # Executar análise
    analyzer = FraudAnalyzer(db_config)
    results = analyzer.run_complete_analysis()


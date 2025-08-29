#!/usr/bin/env python3
"""
Script para gerar dados simulados de fraude de cartão de crédito
baseado nas características do dataset original do Kaggle
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_fraud_data(num_transactions=10000):
    """
    Gera dados simulados de transações de cartão de crédito com fraudes
    """
    np.random.seed(42)
    random.seed(42)
    
    # Gerar timestamps para 2 dias
    start_time = datetime(2023, 9, 1, 0, 0, 0)
    timestamps = []
    for i in range(num_transactions):
        # Adicionar variação temporal realística
        hours_offset = np.random.exponential(scale=12) % 48  # 2 dias
        timestamp = start_time + timedelta(hours=hours_offset)
        timestamps.append(timestamp)
    
    timestamps.sort()
    
    # Gerar features V1-V28 (simulando PCA components)
    features = {}
    for i in range(1, 29):
        if i in [4, 11, 14]:  # Features mais discriminativas para fraude
            # Distribuição bimodal para features importantes
            normal_values = np.random.normal(0, 1, int(num_transactions * 0.998))
            fraud_values = np.random.normal(3, 1.5, int(num_transactions * 0.002))
            values = np.concatenate([normal_values, fraud_values])
            np.random.shuffle(values)
            features[f'V{i}'] = values[:num_transactions]
        else:
            # Distribuição normal padrão para outras features
            features[f'V{i}'] = np.random.normal(0, 1, num_transactions)
    
    # Gerar valores de transação
    # Transações legítimas: distribuição log-normal
    legitimate_amounts = np.random.lognormal(mean=3.5, sigma=1.2, size=int(num_transactions * 0.998))
    # Transações fraudulentas: valores menores em média
    fraud_amounts = np.random.lognormal(mean=2.8, sigma=1.5, size=int(num_transactions * 0.002))
    
    amounts = np.concatenate([legitimate_amounts, fraud_amounts])
    np.random.shuffle(amounts)
    amounts = amounts[:num_transactions]
    
    # Gerar labels de classe (0 = legítima, 1 = fraude)
    # Aproximadamente 0.172% de fraudes (492 de 284,807)
    fraud_rate = 0.00172
    num_frauds = int(num_transactions * fraud_rate)
    
    classes = [0] * (num_transactions - num_frauds) + [1] * num_frauds
    random.shuffle(classes)
    
    # Criar DataFrame
    data = {
        'Time': [(t - timestamps[0]).total_seconds() for t in timestamps],
        **features,
        'Amount': amounts,
        'Class': classes
    }
    
    df = pd.DataFrame(data)
    
    # Ajustar features para fraudes serem mais detectáveis
    fraud_mask = df['Class'] == 1
    if fraud_mask.sum() > 0:
        # Tornar V4, V11, V14 mais extremos para fraudes
        df.loc[fraud_mask, 'V4'] = np.random.normal(4, 2, fraud_mask.sum())
        df.loc[fraud_mask, 'V11'] = np.random.normal(-3, 1.5, fraud_mask.sum())
        df.loc[fraud_mask, 'V14'] = np.random.normal(-5, 2, fraud_mask.sum())
        
        # Ajustar valores para fraudes (geralmente menores)
        df.loc[fraud_mask, 'Amount'] = np.random.lognormal(mean=2.2, sigma=1.8, size=fraud_mask.sum())
    
    return df

def save_to_csv(df, filename):
    """Salva o DataFrame em CSV"""
    df.to_csv(filename, index=False)
    print(f"Dataset salvo em {filename}")
    print(f"Total de transações: {len(df)}")
    print(f"Transações fraudulentas: {df['Class'].sum()}")
    print(f"Taxa de fraude: {df['Class'].mean():.4f}")

if __name__ == "__main__":
    # Gerar dataset
    print("Gerando dados simulados de fraude de cartão de crédito...")
    df = generate_fraud_data(num_transactions=50000)
    
    # Salvar em CSV
    save_to_csv(df, "/home/ubuntu/etl-pipeline/creditcard.csv")
    
    # Mostrar estatísticas básicas
    print("\nEstatísticas do dataset:")
    print(df.describe())
    
    print("\nDistribuição de classes:")
    print(df['Class'].value_counts())
    
    print("\nPrimeiras 5 linhas:")
    print(df.head())


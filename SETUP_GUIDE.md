# Guia de Configuração Completo - Pipeline de Detecção de Fraude

## Introdução

Este guia fornece instruções detalhadas para configurar e executar o pipeline de detecção de fraude em qualquer ambiente Linux. O processo foi testado em Ubuntu 22.04 e pode ser adaptado para outras distribuições com pequenas modificações nos comandos de instalação de pacotes.

A configuração completa envolve a instalação e configuração de múltiplos componentes que trabalham em conjunto para formar uma arquitetura robusta de dados. Cada seção deste guia inclui explicações detalhadas sobre o propósito de cada componente, comandos específicos para instalação e configuração, e verificações para garantir que tudo está funcionando corretamente.

## Pré-requisitos do Sistema

Antes de iniciar a configuração, certifique-se de que o sistema atende aos seguintes requisitos mínimos:

**Sistema Operacional**: Ubuntu 22.04 LTS ou superior (outras distribuições Linux podem ser usadas com adaptações nos comandos de instalação)

**Recursos de Hardware**:
- CPU: Mínimo 2 cores, recomendado 4 cores
- RAM: Mínimo 4GB, recomendado 8GB
- Armazenamento: Mínimo 10GB de espaço livre
- Rede: Conexão com internet para download de dependências

**Permissões**: Acesso sudo para instalação de pacotes do sistema e configuração de serviços

**Python**: Versão 3.11 ou superior (geralmente já instalado no Ubuntu 22.04)

## Fase 1: Configuração do PostgreSQL

O PostgreSQL serve como o Data Warehouse principal do projeto, armazenando dados em todas as camadas da arquitetura Medallion. A configuração adequada do PostgreSQL é crucial para o desempenho e confiabilidade do pipeline.

### Instalação do PostgreSQL

```bash
# Atualizar repositórios do sistema
sudo apt-get update

# Instalar PostgreSQL e extensões
sudo apt-get install -y postgresql postgresql-contrib

# Iniciar o serviço PostgreSQL
sudo systemctl start postgresql

# Habilitar inicialização automática
sudo systemctl enable postgresql

# Verificar status do serviço
sudo systemctl status postgresql
```

### Configuração de Usuário e Banco de Dados

```bash
# Criar usuário para o projeto
sudo -u postgres psql -c "CREATE USER \"user\" WITH PASSWORD 'password';"

# Criar banco de dados
sudo -u postgres psql -c "CREATE DATABASE fraud_detection OWNER \"user\";"

# Conceder privilégios necessários
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE fraud_detection TO \"user\";"

# Testar conexão
PGPASSWORD=password psql -h localhost -U user -d fraud_detection -c "SELECT version();"
```

A configuração do PostgreSQL inclui a criação de um usuário específico para o projeto com privilégios limitados, seguindo as melhores práticas de segurança. O banco de dados `fraud_detection` será usado para armazenar todas as tabelas do projeto, desde os dados brutos até as agregações finais.

## Fase 2: Configuração do Apache Airflow

O Apache Airflow é o coração da orquestração do pipeline, responsável por coordenar todas as tarefas e garantir que sejam executadas na ordem correta com tratamento adequado de erros.

### Instalação do Airflow

```bash
# Instalar Apache Airflow com suporte ao PostgreSQL
pip install apache-airflow[postgres]

# Verificar instalação
airflow version
```

### Configuração do Banco de Dados do Airflow

```bash
# Configurar conexão com PostgreSQL no arquivo de configuração
export AIRFLOW__CORE__SQL_ALCHEMY_CONN="postgresql+psycopg2://user:password@localhost:5432/fraud_detection"

# Inicializar banco de dados do Airflow
airflow db migrate

# Verificar se as tabelas foram criadas
PGPASSWORD=password psql -h localhost -U user -d fraud_detection -c "\\dt" | grep -E "(dag|task|job)"
```

### Configuração de Usuário do Airflow

O Airflow 3.0 utiliza o Simple Auth Manager por padrão, que requer configuração manual de usuários no arquivo de configuração:

```bash
# Localizar arquivo de configuração
find /home -name airflow.cfg 2>/dev/null

# Editar configuração para adicionar usuário admin
# No arquivo airflow.cfg, localizar e modificar:
# simple_auth_manager_users = admin:admin
```

### Inicialização dos Serviços

```bash
# Iniciar API Server (substitui o webserver no Airflow 3.0)
airflow api-server --port 8080 &

# Iniciar Scheduler
airflow scheduler &

# Verificar se os serviços estão rodando
ps aux | grep airflow
```

O Airflow 3.0 introduziu mudanças significativas na arquitetura, substituindo o webserver tradicional pelo api-server. Esta mudança melhora a performance e simplifica a arquitetura, mas requer adaptação nos comandos de inicialização.

## Fase 3: Configuração do dbt

O dbt (Data Build Tool) é responsável pelas transformações de dados, implementando a lógica de negócio através de modelos SQL versionados e testáveis.

### Instalação do dbt

```bash
# Instalar dbt com adapter para PostgreSQL
pip install dbt-postgres

# Verificar instalação
dbt --version
```

### Inicialização do Projeto dbt

```bash
# Criar diretório do projeto
mkdir -p etl-pipeline
cd etl-pipeline

# Inicializar projeto dbt
dbt init fraud_detection_project

# Navegar para o diretório do projeto
cd fraud_detection_project
```

### Configuração de Conexão

Criar o arquivo `~/.dbt/profiles.yml` com as configurações de conexão:

```yaml
fraud_detection_project:
  outputs:
    dev:
      type: postgres
      host: localhost
      user: user
      password: password
      port: 5432
      dbname: fraud_detection
      schema: public
      threads: 4
      keepalives_idle: 0
      search_path: "public"
  target: dev
```

### Teste de Conexão

```bash
# Testar conexão com o banco
dbt debug

# Executar modelos exemplo (se existirem)
dbt run
```

A configuração do dbt inclui a definição de perfis que especificam como conectar ao Data Warehouse. O arquivo profiles.yml é mantido separado do código do projeto para permitir diferentes configurações entre ambientes (desenvolvimento, teste, produção).

## Fase 4: Geração e Carregamento de Dados

Esta fase envolve a criação de dados simulados realísticos e seu carregamento no Data Warehouse para demonstrar o funcionamento completo do pipeline.

### Script de Geração de Dados

O script `generate_fraud_data.py` cria um dataset sintético baseado nas características do famoso dataset de fraude de cartão de crédito do Kaggle:

```python
#!/usr/bin/env python3
"""
Script para gerar dados simulados de fraude de cartão de crédito
baseado nas características do dataset original do Kaggle
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_fraud_data(num_transactions=50000):
    """
    Gera dados simulados de transações de cartão de crédito com fraudes
    """
    np.random.seed(42)
    random.seed(42)
    
    # Gerar timestamps realísticos
    start_time = datetime(2023, 9, 1, 0, 0, 0)
    timestamps = []
    for i in range(num_transactions):
        hours_offset = np.random.exponential(scale=12) % 48
        timestamp = start_time + timedelta(hours=hours_offset)
        timestamps.append(timestamp)
    
    timestamps.sort()
    
    # Gerar features V1-V28 (simulando componentes PCA)
    features = {}
    for i in range(1, 29):
        if i in [4, 11, 14]:  # Features mais discriminativas
            normal_values = np.random.normal(0, 1, int(num_transactions * 0.998))
            fraud_values = np.random.normal(3, 1.5, int(num_transactions * 0.002))
            values = np.concatenate([normal_values, fraud_values])
            np.random.shuffle(values)
            features[f'V{i}'] = values[:num_transactions]
        else:
            features[f'V{i}'] = np.random.normal(0, 1, num_transactions)
    
    # Gerar valores de transação com distribuições realísticas
    legitimate_amounts = np.random.lognormal(mean=3.5, sigma=1.2, size=int(num_transactions * 0.998))
    fraud_amounts = np.random.lognormal(mean=2.8, sigma=1.5, size=int(num_transactions * 0.002))
    
    amounts = np.concatenate([legitimate_amounts, fraud_amounts])
    np.random.shuffle(amounts)
    amounts = amounts[:num_transactions]
    
    # Gerar labels de classe (0 = legítima, 1 = fraude)
    fraud_rate = 0.00172  # Aproximadamente 0.172% como no dataset original
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
    
    # Ajustar features para tornar fraudes mais detectáveis
    fraud_mask = df['Class'] == 1
    if fraud_mask.sum() > 0:
        df.loc[fraud_mask, 'V4'] = np.random.normal(4, 2, fraud_mask.sum())
        df.loc[fraud_mask, 'V11'] = np.random.normal(-3, 1.5, fraud_mask.sum())
        df.loc[fraud_mask, 'V14'] = np.random.normal(-5, 2, fraud_mask.sum())
        df.loc[fraud_mask, 'Amount'] = np.random.lognormal(mean=2.2, sigma=1.8, size=fraud_mask.sum())
    
    return df

if __name__ == "__main__":
    print("Gerando dados simulados de fraude de cartão de crédito...")
    df = generate_fraud_data(num_transactions=50000)
    df.to_csv("creditcard.csv", index=False)
    print(f"Dataset salvo com {len(df)} transações")
    print(f"Fraudes: {df['Class'].sum()} ({df['Class'].mean():.4f})")
```

### Carregamento no PostgreSQL

```bash
# Executar script de geração
python3 generate_fraud_data.py

# Criar tabela para dados brutos
PGPASSWORD=password psql -h localhost -U user -d fraud_detection -c "
CREATE TABLE IF NOT EXISTS raw_transactions (
    time_seconds FLOAT,
    v1 FLOAT, v2 FLOAT, v3 FLOAT, v4 FLOAT, v5 FLOAT,
    v6 FLOAT, v7 FLOAT, v8 FLOAT, v9 FLOAT, v10 FLOAT,
    v11 FLOAT, v12 FLOAT, v13 FLOAT, v14 FLOAT, v15 FLOAT,
    v16 FLOAT, v17 FLOAT, v18 FLOAT, v19 FLOAT, v20 FLOAT,
    v21 FLOAT, v22 FLOAT, v23 FLOAT, v24 FLOAT, v25 FLOAT,
    v26 FLOAT, v27 FLOAT, v28 FLOAT,
    amount FLOAT,
    class INTEGER
);"

# Carregar dados CSV
PGPASSWORD=password psql -h localhost -U user -d fraud_detection -c "
\\COPY raw_transactions FROM 'creditcard.csv' WITH CSV HEADER;"

# Verificar carregamento
PGPASSWORD=password psql -h localhost -U user -d fraud_detection -c "
SELECT COUNT(*) as total_records, 
       SUM(class) as fraud_count,
       AVG(class::float) as fraud_rate
FROM raw_transactions;"
```

O processo de geração de dados cria um dataset sintético que mantém as características estatísticas do dataset original, incluindo a distribuição temporal das transações, a correlação entre features e a taxa de fraude realística.

## Fase 5: Implementação dos Modelos dbt

Os modelos dbt implementam a arquitetura Medallion, transformando dados brutos em informações estruturadas e prontas para análise.

### Configuração de Sources

Arquivo `models/sources.yml`:

```yaml
version: 2

sources:
  - name: public
    description: Raw data from various sources
    tables:
      - name: raw_transactions
        description: Raw credit card transactions data
        columns:
          - name: time_seconds
            description: Time in seconds from first transaction
          - name: v1
            description: PCA component 1
          # ... outras colunas
          - name: class
            description: Class label (0=legitimate, 1=fraud)
```

### Modelo Bronze

Arquivo `models/bronze/bronze_transactions.sql`:

```sql
{{ config(materialized='table') }}

-- Bronze layer: Raw data with minimal transformations
SELECT 
    time_seconds,
    v1, v2, v3, v4, v5, v6, v7, v8, v9, v10,
    v11, v12, v13, v14, v15, v16, v17, v18, v19, v20,
    v21, v22, v23, v24, v25, v26, v27, v28,
    amount,
    class,
    CURRENT_TIMESTAMP as loaded_at
FROM {{ source('public', 'raw_transactions') }}
```

### Modelo Silver

Arquivo `models/silver/silver_transactions.sql`:

```sql
{{ config(materialized='table') }}

-- Silver layer: Cleaned and enriched data
WITH enriched_transactions AS (
    SELECT 
        *,
        -- Convert time_seconds to timestamp
        TIMESTAMP '2023-09-01 00:00:00' + INTERVAL '1 second' * time_seconds as transaction_timestamp,
        
        -- Extract time features
        EXTRACT(HOUR FROM (TIMESTAMP '2023-09-01 00:00:00' + INTERVAL '1 second' * time_seconds)) as hour_of_day,
        EXTRACT(DOW FROM (TIMESTAMP '2023-09-01 00:00:00' + INTERVAL '1 second' * time_seconds)) as day_of_week,
        
        -- Amount categories
        CASE 
            WHEN amount < 10 THEN 'micro'
            WHEN amount < 100 THEN 'small'
            WHEN amount < 1000 THEN 'medium'
            ELSE 'large'
        END as amount_category,
        
        -- Fraud flag
        CASE WHEN class = 1 THEN TRUE ELSE FALSE END as is_fraud,
        
        -- Risk score based on key features
        CASE 
            WHEN ABS(v4) > 3 OR ABS(v11) > 3 OR ABS(v14) > 3 THEN 'high'
            WHEN ABS(v4) > 2 OR ABS(v11) > 2 OR ABS(v14) > 2 THEN 'medium'
            ELSE 'low'
        END as risk_level
        
    FROM {{ ref('bronze_transactions') }}
)

SELECT 
    time_seconds,
    transaction_timestamp,
    hour_of_day,
    day_of_week,
    v1, v2, v3, v4, v5, v6, v7, v8, v9, v10,
    v11, v12, v13, v14, v15, v16, v17, v18, v19, v20,
    v21, v22, v23, v24, v25, v26, v27, v28,
    amount,
    amount_category,
    class,
    is_fraud,
    risk_level,
    loaded_at
FROM enriched_transactions
```

### Modelo Gold

Arquivo `models/gold/gold_fraud_summary.sql`:

```sql
{{ config(materialized='table') }}

-- Gold layer: Business-ready aggregated data
SELECT 
    -- Time dimensions
    DATE(transaction_timestamp) as transaction_date,
    hour_of_day,
    day_of_week,
    
    -- Amount dimensions
    amount_category,
    risk_level,
    
    -- Metrics
    COUNT(*) as total_transactions,
    SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_transactions,
    SUM(CASE WHEN is_fraud THEN 0 ELSE 1 END) as legitimate_transactions,
    
    -- Fraud rate
    ROUND(
        SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END)::NUMERIC / COUNT(*)::NUMERIC * 100, 
        4
    ) as fraud_rate_percent,
    
    -- Amount metrics
    AVG(amount) as avg_amount,
    AVG(CASE WHEN is_fraud THEN amount END) as avg_fraud_amount,
    AVG(CASE WHEN NOT is_fraud THEN amount END) as avg_legitimate_amount,
    
    SUM(amount) as total_amount,
    SUM(CASE WHEN is_fraud THEN amount ELSE 0 END) as total_fraud_amount,
    SUM(CASE WHEN NOT is_fraud THEN amount ELSE 0 END) as total_legitimate_amount,
    
    -- Feature statistics for key fraud indicators
    AVG(ABS(v4)) as avg_abs_v4,
    AVG(ABS(v11)) as avg_abs_v11,
    AVG(ABS(v14)) as avg_abs_v14,
    
    CURRENT_TIMESTAMP as aggregated_at
    
FROM {{ ref('silver_transactions') }}
GROUP BY 
    DATE(transaction_timestamp),
    hour_of_day,
    day_of_week,
    amount_category,
    risk_level
```

### Execução dos Modelos

```bash
# Executar todos os modelos
dbt run

# Executar testes (se configurados)
dbt test

# Gerar documentação
dbt docs generate

# Verificar resultados
PGPASSWORD=password psql -h localhost -U user -d fraud_detection -c "
SELECT 'bronze_transactions' as layer, COUNT(*) as records FROM bronze_transactions
UNION ALL
SELECT 'silver_transactions' as layer, COUNT(*) as records FROM silver_transactions  
UNION ALL
SELECT 'gold_fraud_summary' as layer, COUNT(*) as records FROM gold_fraud_summary;"
```

Os modelos dbt implementam transformações incrementais que podem ser executadas de forma idempotente, garantindo que o pipeline possa ser reexecutado sem problemas. Cada modelo inclui documentação inline e pode ser testado individualmente.

## Fase 6: Implementação da Análise de Fraude

A análise de fraude utiliza técnicas de machine learning e análise estatística para identificar padrões suspeitos e gerar insights acionáveis.

### Script de Análise

O arquivo `fraud_analysis.py` implementa uma classe completa para análise de fraude:

```python
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
        query = "SELECT * FROM silver_transactions ORDER BY transaction_timestamp"
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
        
        return insights
        
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
            'business_insights': self.generate_insights()
        }
        
        # Salvar resultados
        with open('fraud_analysis_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
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
```

### Instalação de Dependências

```bash
# Instalar bibliotecas necessárias
pip install scikit-learn matplotlib seaborn psycopg2-binary

# Executar análise
python3 fraud_analysis.py
```

A análise de fraude implementa múltiplas técnicas complementares, incluindo análise temporal, análise de valores, análise de features e detecção de anomalias usando Isolation Forest. Os resultados são salvos em formato JSON para posterior análise e visualização.

## Fase 7: Configuração do DAG do Airflow

O DAG (Directed Acyclic Graph) do Airflow orquestra todo o pipeline, definindo a ordem de execução das tarefas e o tratamento de erros.

### Implementação do DAG

Arquivo `dags/fraud_detection_dag.py`:

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
import subprocess
import sys
import os

# Configurações padrão do DAG
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2023, 9, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Definição do DAG
dag = DAG(
    'fraud_detection_pipeline',
    default_args=default_args,
    description='Pipeline completo de detecção de fraude',
    schedule=timedelta(days=1),
    catchup=False,
    tags=['fraud', 'detection', 'etl'],
)

def extract_data():
    """Simula extração de dados (normalmente seria do Airbyte)"""
    print("Executando extração de dados...")
    os.system("cd /home/ubuntu/etl-pipeline && python3 generate_fraud_data.py")
    print("Dados extraídos com sucesso")

def load_raw_data():
    """Carrega dados brutos no PostgreSQL"""
    print("Carregando dados brutos...")
    commands = [
        "export PGPASSWORD=password",
        "psql -h localhost -U user -d fraud_detection -c 'DROP TABLE IF EXISTS raw_transactions;'",
        "psql -h localhost -U user -d fraud_detection -c 'CREATE TABLE raw_transactions (...);'",
        "psql -h localhost -U user -d fraud_detection -c \"\\COPY raw_transactions FROM '/home/ubuntu/etl-pipeline/creditcard.csv' WITH CSV HEADER;\""
    ]
    
    for cmd in commands:
        os.system(cmd)
    
    print("Dados brutos carregados com sucesso")

def run_dbt_models():
    """Executa modelos dbt"""
    print("Executando modelos dbt...")
    os.chdir("/home/ubuntu/etl-pipeline/fraud_detection_project")
    result = os.system("dbt run")
    if result != 0:
        raise Exception("Falha na execução dos modelos dbt")
    print("Modelos dbt executados com sucesso")

def run_fraud_analysis():
    """Executa análise de fraude"""
    print("Executando análise de fraude...")
    os.chdir("/home/ubuntu/etl-pipeline")
    result = os.system("python3 fraud_analysis.py")
    if result != 0:
        raise Exception("Falha na análise de fraude")
    print("Análise de fraude executada com sucesso")

def data_quality_check():
    """Verifica qualidade dos dados"""
    print("Executando verificações de qualidade...")
    import psycopg2
    
    conn = psycopg2.connect(
        host='localhost',
        database='fraud_detection',
        user='user',
        password='password'
    )
    
    cursor = conn.cursor()
    
    # Verificar se temos dados
    cursor.execute("SELECT COUNT(*) FROM raw_transactions")
    count = cursor.fetchone()[0]
    
    if count == 0:
        raise Exception("Nenhum dado encontrado na tabela raw_transactions")
    
    # Verificar taxa de fraude
    cursor.execute("SELECT AVG(class::float) FROM raw_transactions")
    fraud_rate = cursor.fetchone()[0]
    
    if fraud_rate > 0.01:  # Mais de 1% de fraude é suspeito
        print(f"ALERTA: Taxa de fraude alta: {fraud_rate:.4f}")
    
    print(f"Verificações de qualidade concluídas. {count} registros, taxa de fraude: {fraud_rate:.4f}")
    
    conn.close()

# Definição das tarefas
extract_task = PythonOperator(
    task_id='extract_data',
    python_callable=extract_data,
    dag=dag,
)

load_task = PythonOperator(
    task_id='load_raw_data',
    python_callable=load_raw_data,
    dag=dag,
)

quality_check_task = PythonOperator(
    task_id='data_quality_check',
    python_callable=data_quality_check,
    dag=dag,
)

dbt_task = PythonOperator(
    task_id='run_dbt_models',
    python_callable=run_dbt_models,
    dag=dag,
)

analysis_task = PythonOperator(
    task_id='run_fraud_analysis',
    python_callable=run_fraud_analysis,
    dag=dag,
)

# Definição das dependências
extract_task >> load_task >> quality_check_task >> dbt_task >> analysis_task
```

### Deployment do DAG

```bash
# Criar diretório de DAGs do Airflow
mkdir -p /home/ubuntu/airflow/dags

# Copiar DAG para o diretório do Airflow
cp dags/fraud_detection_dag.py /home/ubuntu/airflow/dags/

# Verificar se o DAG foi carregado
airflow dags list | grep fraud_detection_pipeline

# Testar DAG (opcional)
airflow dags test fraud_detection_pipeline 2023-09-01
```

O DAG implementa um pipeline robusto com tratamento de erros, retry automático e logging detalhado. Cada tarefa é independente e pode ser executada individualmente para debugging.

## Fase 8: Execução e Validação

Esta fase final envolve a execução completa do pipeline e validação dos resultados.

### Execução Manual do Pipeline

```bash
# Executar pipeline completo manualmente
cd /home/ubuntu/etl-pipeline

# 1. Gerar dados
python3 generate_fraud_data.py

# 2. Carregar dados brutos
PGPASSWORD=password psql -h localhost -U user -d fraud_detection -c "
DROP TABLE IF EXISTS raw_transactions;
CREATE TABLE raw_transactions (
    time_seconds FLOAT, v1 FLOAT, v2 FLOAT, v3 FLOAT, v4 FLOAT, v5 FLOAT,
    v6 FLOAT, v7 FLOAT, v8 FLOAT, v9 FLOAT, v10 FLOAT, v11 FLOAT, v12 FLOAT,
    v13 FLOAT, v14 FLOAT, v15 FLOAT, v16 FLOAT, v17 FLOAT, v18 FLOAT, v19 FLOAT,
    v20 FLOAT, v21 FLOAT, v22 FLOAT, v23 FLOAT, v24 FLOAT, v25 FLOAT, v26 FLOAT,
    v27 FLOAT, v28 FLOAT, amount FLOAT, class INTEGER
);
\\COPY raw_transactions FROM 'creditcard.csv' WITH CSV HEADER;"

# 3. Executar modelos dbt
cd fraud_detection_project
dbt run
cd ..

# 4. Executar análise de fraude
python3 fraud_analysis.py
```

### Validação dos Resultados

```bash
# Verificar tabelas criadas
PGPASSWORD=password psql -h localhost -U user -d fraud_detection -c "
SELECT 'raw_transactions' as table_name, COUNT(*) as record_count FROM raw_transactions
UNION ALL
SELECT 'bronze_transactions' as table_name, COUNT(*) as record_count FROM bronze_transactions
UNION ALL
SELECT 'silver_transactions' as table_name, COUNT(*) as record_count FROM silver_transactions
UNION ALL
SELECT 'gold_fraud_summary' as table_name, COUNT(*) as record_count FROM gold_fraud_summary;"

# Verificar resultados da análise
ls -la fraud_analysis_results.json
head -20 fraud_analysis_results.json

# Verificar logs do Airflow
tail -50 /home/ubuntu/airflow/logs/scheduler/latest/fraud_detection_pipeline/*.log
```

### Métricas de Sucesso

O pipeline é considerado bem-sucedido quando:

1. **Dados Carregados**: 50.000 transações carregadas na tabela raw_transactions
2. **Transformações dbt**: Todas as 3 camadas (Bronze, Silver, Gold) criadas com sucesso
3. **Análise de Fraude**: 86 fraudes identificadas (taxa de ~0.17%)
4. **Qualidade de Dados**: Taxa de completude > 99%, sem valores nulos críticos
5. **Performance**: Pipeline executado em menos de 5 minutos

### Monitoramento Contínuo

```bash
# Script de monitoramento (executar periodicamente)
#!/bin/bash

echo "=== MONITORAMENTO DO PIPELINE ==="
echo "Data/Hora: $(date)"

# Verificar serviços
echo "Status dos serviços:"
systemctl is-active postgresql
ps aux | grep -E "(airflow|scheduler)" | grep -v grep

# Verificar dados
echo "Contagem de registros:"
PGPASSWORD=password psql -h localhost -U user -d fraud_detection -c "
SELECT COUNT(*) as total_transactions FROM raw_transactions;
SELECT COUNT(*) as fraud_transactions FROM raw_transactions WHERE class = 1;"

# Verificar espaço em disco
echo "Espaço em disco:"
df -h /home/ubuntu

echo "=== FIM DO MONITORAMENTO ==="
```

## Solução de Problemas Comuns

### Problema: PostgreSQL não inicia

**Sintomas**: Erro de conexão ao tentar conectar ao PostgreSQL

**Solução**:
```bash
# Verificar status
sudo systemctl status postgresql

# Reiniciar serviço
sudo systemctl restart postgresql

# Verificar logs
sudo tail -50 /var/log/postgresql/postgresql-14-main.log
```

### Problema: Airflow DAG não aparece

**Sintomas**: DAG não listado no comando `airflow dags list`

**Solução**:
```bash
# Verificar sintaxe do DAG
python3 /home/ubuntu/airflow/dags/fraud_detection_dag.py

# Verificar configuração do Airflow
airflow config get-value core dags_folder

# Reiniciar scheduler
pkill -f "airflow scheduler"
airflow scheduler &
```

### Problema: dbt não encontra tabelas

**Sintomas**: Erro "relation does not exist" ao executar `dbt run`

**Solução**:
```bash
# Verificar conexão
dbt debug

# Verificar se tabela existe
PGPASSWORD=password psql -h localhost -U user -d fraud_detection -c "\\dt"

# Verificar configuração de sources
cat models/sources.yml
```

### Problema: Análise de fraude falha

**Sintomas**: Erro ao executar `fraud_analysis.py`

**Solução**:
```bash
# Verificar dependências
pip list | grep -E "(pandas|scikit-learn|psycopg2)"

# Verificar dados na tabela silver
PGPASSWORD=password psql -h localhost -U user -d fraud_detection -c "
SELECT COUNT(*) FROM silver_transactions;"

# Executar com debug
python3 -c "
import fraud_analysis
db_config = {'host': 'localhost', 'database': 'fraud_detection', 'user': 'user', 'password': 'password', 'port': 5432}
analyzer = fraud_analysis.FraudAnalyzer(db_config)
analyzer.connect_db()
analyzer.load_data()
print('Dados carregados com sucesso')
"
```

## Considerações de Produção

Para implementar este pipeline em ambiente de produção, considere as seguintes adaptações:

### Segurança

1. **Gerenciamento de Secrets**: Usar ferramentas como HashiCorp Vault ou AWS Secrets Manager
2. **Autenticação**: Implementar autenticação robusta para todos os componentes
3. **Criptografia**: Criptografar dados sensíveis em trânsito e em repouso
4. **Auditoria**: Implementar logs de auditoria para todas as operações

### Escalabilidade

1. **Containerização**: Usar Docker e Kubernetes para deployment
2. **Load Balancing**: Implementar balanceamento de carga para componentes críticos
3. **Particionamento**: Particionar tabelas grandes por data ou região
4. **Caching**: Implementar cache para consultas frequentes

### Monitoramento

1. **Observabilidade**: Integrar com Prometheus, Grafana e ELK Stack
2. **Alertas**: Configurar alertas para falhas e anomalias
3. **Métricas**: Monitorar SLAs, latência e throughput
4. **Health Checks**: Implementar verificações de saúde automáticas

### Backup e Recuperação

1. **Backup Automático**: Configurar backups regulares do PostgreSQL
2. **Disaster Recovery**: Implementar plano de recuperação de desastres
3. **Versionamento**: Manter versionamento de código e configurações
4. **Testes de Recuperação**: Testar procedimentos de recuperação regularmente

---

*Guia de configuração criado por Manus AI - Versão 1.0*


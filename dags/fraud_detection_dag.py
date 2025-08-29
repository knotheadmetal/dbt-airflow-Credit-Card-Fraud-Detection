from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
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
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=['fraud', 'detection', 'etl'],
)

def extract_data():
    """Simula extração de dados (normalmente seria do Airbyte)"""
    print("Executando extração de dados...")
    # Em um cenário real, isso seria feito pelo Airbyte
    # Aqui simulamos regenerando os dados
    os.system("cd /home/ubuntu/etl-pipeline && python3 generate_fraud_data.py")
    print("Dados extraídos com sucesso")

def load_raw_data():
    """Carrega dados brutos no PostgreSQL"""
    print("Carregando dados brutos...")
    # Recriar tabela e carregar dados
    commands = [
        "export PGPASSWORD=password",
        "psql -h localhost -U user -d fraud_detection -c 'DROP TABLE IF EXISTS raw_transactions;'",
        "psql -h localhost -U user -d fraud_detection -c 'CREATE TABLE raw_transactions (time_seconds FLOAT, v1 FLOAT, v2 FLOAT, v3 FLOAT, v4 FLOAT, v5 FLOAT, v6 FLOAT, v7 FLOAT, v8 FLOAT, v9 FLOAT, v10 FLOAT, v11 FLOAT, v12 FLOAT, v13 FLOAT, v14 FLOAT, v15 FLOAT, v16 FLOAT, v17 FLOAT, v18 FLOAT, v19 FLOAT, v20 FLOAT, v21 FLOAT, v22 FLOAT, v23 FLOAT, v24 FLOAT, v25 FLOAT, v26 FLOAT, v27 FLOAT, v28 FLOAT, amount FLOAT, class INTEGER);'",
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
    # Simulação de verificações de qualidade (normalmente seria Soda Core)
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


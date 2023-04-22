import boto3
import botocore
import json
import logging
import pymssql

from model import QueueModel
from os import environ
from botocore.exceptions import ClientError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

############Configurations###############
#Env variables loading
secret_name = environ['DB_CONNECTION_SECRET_NAME']
region_name = environ['REGION_NAME']
connect_instance_id = environ['CONNECT_INSTANCE_ID']
table_name = environ['TABLE_NAME']
pagination_size = environ['PAGINATION_SIZE']

#Exponential backoff configuration
config = botocore.config.Config(
    retries=dict(
        max_attempts=10,
        mode='adaptive'
    )
)

# Amazon connect client definition
connect_client = boto3.client('connect', config=config, region_name=region_name)
##########################################

def handler(event, context):
    LOGGER.info('Starting lambda execution')
    try:
        write_queues_to_db()
        return json.dumps({'status':200, 'message': 'Amazon connect queues saved to the database'})
    except Exception as e:
        LOGGER.error(f'Error writing the queues to the database {e.with_traceback(e.__traceback__)}')
        return json.dumps({'status':503, 'message': f'Error writing the queues to the database {e.with_traceback(e.__traceback__)}'})


    return json.dumps({'status':200})
    

def write_queues_to_db():
    #Obtain the db credentials
    conn_cred = get_db_secret(secret_name, region_name)
    
    LOGGER.info('Reading Amazon Connect queues')
    response = connect_client.list_queues(InstanceId=connect_instance_id, MaxResults=pagination_size)
    batch_write_to_db(conn_cred, response['QueueSummaryList'])
    
    while "NextToken" in response:
        response = connect_client.list_queues(
            InstanceId=connect_instance_id,
            NextToken=response['NextToken'],
            MaxResults=pagination_size
        )
        batch_write_to_db(conn_cred, response['QueueSummaryList'])
    

def get_db_secret(secret_name, region_name):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        LOGGER.error(f'Erro reading the secret connection string {e.with_traceback(e.__traceback__)}')
        raise e

    return json.loads(get_secret_value_response['SecretString'])


def batch_write_to_db(connection_credentials, queues):
    #Insert query definition
    insert_query = f'INSERT INTO {table_name} (id ,arn ,queue_name ,description ,outbound_caller_config_caller_id_name ,outbound_caller_config_caller_id_number_id ,outbound_caller_config_caller_id_flow_id ,hours_of_operation_id ,max_contacts ,status) VALUES (%s ,%s  ,%s  ,%s  ,%s  ,%s  ,%s  ,%s  ,%s  ,%s )'

    #Obtain queue details
    detailed_queues = get_queue_details(queues)

    #Map to model
    model_queues = list(map(lambda queue: QueueModel(**queue), detailed_queues))

    #Map to attribute tuples
    queues_attributes = list(map(lambda model: tuple(vars(model).values()), model_queues))
    print(queues_attributes)

    try:
        LOGGER.info('Starting database connection')
        #Create DB connection
        conn = pymssql.connect(
            server=connection_credentials['host'],
            user=connection_credentials['username'],
            password=connection_credentials['password'],
            database=connection_credentials['dbname']
        )

        #Write to db
        cursor = conn.cursor()
        cursor.executemany(insert_query, queues_attributes)
        conn.commit() 
        cursor.close()
        conn.close()
        LOGGER.info(f'Records saved: {detailed_queues}')
    except Exception as e:
        LOGGER.error(f'Error writng to the database, cause: {e.with_traceback(e.__traceback__)}')



def get_queue_details(queues):
    #Result detailed queues
    detailed_queues = []

    #Filter agents to get only queues
    filtered_queues = list(filter(lambda queue: queue['QueueType'] != "AGENT", queues))

    for queue in filtered_queues:
        LOGGER.info(f"Getting details for the queue: {queue['Id']}")
        response = connect_client.describe_queue(
            InstanceId=connect_instance_id,
            QueueId=queue['Id']
        )
        detailed_queues.append(response['Queue'])
    
    return detailed_queues
    

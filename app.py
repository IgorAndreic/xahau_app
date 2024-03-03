import asyncio
import json
import websockets
from motor.motor_asyncio import AsyncIOMotorClient
from flask import Flask
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Асинхронное подключение к MongoDB
mongo_uri = "mongodb://localhost:27017"
client = AsyncIOMotorClient(mongo_uri)
db = client.xahau_db  # Имя вашей базы данных
transactions_collection = db.transactions_evr  # Имя вашей коллекции

# Асинхронная функция для сохранения транзакции
async def save_transaction(transaction_data):
    transaction_data['processed'] = False
    await transactions_collection.insert_one(transaction_data)
    logging.info("Транзакция сохранена в MongoDB")  # Изменено с print на logging.info

async def load_addresses_from_file(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
        addresses_only = [item["address"] for group in data["groups"] for item in group["addresses"]]
        wss_url = data['xahauServer'][0] 
        return addresses_only, wss_url

# Загрузка адресов для отслеживания
addresses_to_track, wss_url = asyncio.run(load_addresses_from_file('/home/xahau/src/config.json'))
logging.info(f"Адреса для отслеживания: {addresses_to_track}")  # Изменено с print на logging.info

async def track_transactions(addresses):
    uri = wss_url
    async with websockets.connect(uri) as websocket:
        subscription_request = {"command": "subscribe", "accounts": addresses}
        await websocket.send(json.dumps(subscription_request))

        while True:
            response = await websocket.recv()
            response_data = json.loads(response)

            if 'transaction' in response_data:
                transaction = response_data['transaction']
                
                if transaction['TransactionType'] == 'Payment':
                    amount = transaction.get('Amount')
                    
                    if isinstance(amount, dict) and amount.get('currency') == 'EVR':
                        await save_transaction(response_data)
                        logging.info(f"Обнаружена транзакция EVR: {response_data}")  # Изменено с print на logging.info

# Запуск асинхронной функции в современном стиле
asyncio.run(track_transactions(addresses_to_track))

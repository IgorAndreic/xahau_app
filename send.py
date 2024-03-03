import asyncio
import json

from motor.motor_asyncio import AsyncIOMotorClient
from xrpl.models.requests import AccountInfo, AccountLines
from xrpl.asyncio.clients import AsyncJsonRpcClient
from make_payment import send_payment


# Параметры подключения к MongoDB
mongo_uri = "mongodb://localhost:27017"
db_name = "xahau_db"
collection_name = "transactions_evr"

def find_secret_by_address(address):
    filename = '/home/xahau/src/config.json'
    with open(filename, 'r') as file:
        data = json.load(file)
    # Проходим по всем группам
    for group in data["groups"]:
        # Теперь правильно проходим по списку адресов внутри каждой группы
        for addr in group["addresses"]:
            # Сравниваем адреса, не учитывая регистр букв
            if addr['address'].lower() == address.lower():
                return addr['secret']
    return None

def find_group_by_address(target_address):
    filename = '/home/xahau/src/config.json'
    with open(filename, 'r') as file:
        data = json.load(file)
    """Ищет группу по заданному адресу."""
    for group in data['groups']:
        # Проверяем, есть ли адрес в текущей группе
        if any(addr['address'].lower() == target_address.lower() for addr in group['addresses']):
            return group
    return None

def trustIssuers():
    filename = '/home/xahau/src/config.json'
    with open(filename, 'r') as file:
        data = json.load(file)
    # Извлечение значения trustIssuers
        trust_issuers = data['trustIssuers']
        https_url = data['xahauServer'][1]
    return trust_issuers, https_url

async def process_transaction(transaction):
    destination_address = transaction['transaction']['Destination']
    amount_info = transaction['transaction']['Amount']
    currency_code = amount_info['currency']
    issuer_address = amount_info['issuer']
    total_amount = amount_info['value']

    # Получение секретного ключа по адресу
    seed = find_secret_by_address(destination_address)
    
    # Получение данных о группе по адресу
    group_data = find_group_by_address(destination_address)

    # Вызов функции для распределения платежей
    await distribute_payments(seed, group_data, total_amount, currency_code, issuer_address)

async def check_account_and_balance(address, currency_code, required_amount):
    client = AsyncJsonRpcClient("https://rpc.node101.space")  # Адрес XRPL JSON RPC клиента

    # Получение информации о счете
    acct_info = AccountInfo(account=address, ledger_index="validated", strict=True)
    response = await client.request(acct_info)
    if not response.is_successful():
        return False, "Ошибка при получении информации об аккаунте"

    account_data = response.result["account_data"]
    # В XRPL нет прямого указания на "активность" счёта как таковую, но можно проверить баланс и другие параметры.
    # Здесь мы предполагаем, что счёт считается активным, если он существует и запрос успешен.

    # Проверка баланса XRP перед проверкой линий доверия, если это необходимо
    xrp_balance = int(account_data["Balance"]) / 1000000  # Перевод из дропс в XRP
    xrp_balance_float = float(xrp_balance)
    Fee = 1.2
    if xrp_balance_float < Fee:
        return False, "Недостаточно средств в XRP"

    # Проверка баланса в указанной валюте, если это не XRP
    required_amount_float = float(required_amount)

    acct_lines = AccountLines(account=address, ledger_index="validated", limit=400)
    response = await client.request(acct_lines)
    if response.is_successful():
        found_currency = False
        for line in response.result["lines"]:
            if line["currency"] == currency_code:
                found_currency = True
                # Убедимся, что баланс также преобразован в float перед сравнением
                line_balance_float = float(line["balance"])
                if line_balance_float < required_amount_float:
                    return False, f"Недостаточно средств на {address} в {currency_code}"
                break
        if not found_currency:
            return False, f"Валюта {currency_code} не найдена на счете"
    else:
        return False, "Ошибка при получении информации о линиях доверия"
    
    return True, "Все проверки пройдены"



async def distribute_payments(seed, group_data, total_amount, currency_code, issuer_address):
    #Распределяет платежи по указанным процентам в group_data.
    for recipient in group_data["destinations"]:
        # Расчёт суммы для отправки каждому получателю, округляем до двух знаков после запятой
        recipient_amount = "{:.2f}".format(float(total_amount) * (recipient["percent"] / 100))

        # Проверка счета и баланса перед отправкой платежа
        check_result, message = await check_account_and_balance(recipient["address"], currency_code, recipient_amount)
        if not check_result:
            print(f"Платеж на {recipient['address']} не выполнен: {message}")
            continue

        # Создание и отправка транзакции для каждого получателя
        response = await send_payment(
            seed, 
            recipient["address"], 
            recipient_amount, 
            currency_code, 
            issuer_address
        )
        # Используйте полученные данные из response для вывода информации о платеже
        transaction_hash = response["hash"]  # Получаем хэш транзакции из ответа
        recipient_address = response["Destination"]  # Адрес получателя
        amount_value = response["Amount"]["value"]  # Сумма платежа
        currency_code = response["Amount"]["currency"]  # Код валюты

        print(f"Платёж отправлен на {recipient_address} на сумму {amount_value} {currency_code}, хэш транзакции: {transaction_hash}")


async def main():
    
    clientdb = AsyncIOMotorClient(mongo_uri)
    db = clientdb[db_name]
    collection = db[collection_name]

    # Извлечение необработанной транзакции
    transaction = await collection.find_one({"processed": False})

    if transaction:
        await process_transaction(transaction)

        await collection.update_one({"_id": transaction['_id']}, {"$set": {"processed": True}})

    else:
        print("Необработанные транзакции не найдены")
    
# Запуск асинхронной функции
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
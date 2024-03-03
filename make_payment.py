import json
from xrpl.asyncio.transaction import submit_and_wait
from xrpl.models.transactions import Payment
from xrpl.core.keypairs import derive_classic_address, derive_keypair
from xrpl.wallet import Wallet
from xrpl.asyncio.account import get_next_valid_seq_number
from xrpl.asyncio.clients import AsyncJsonRpcClient

async def send_payment_evr(client, wallet_from: Wallet, wallet_to_address: str, amount: str, currency_code: str, issuer_address: str, sequence):
    # Ensure amount is a string and formatted to comply with XRPL precision rules
    # Assuming 'amount' is passed in as a string that already complies with the precision rules
    formatted_amount = "{:.15f}".format(float(amount)).rstrip('0').rstrip('.')
    send_max_value = "{:.15f}".format(float(amount) * 1.05).rstrip('0').rstrip('.')
    
    payment_tx = Payment(
        account=wallet_from.classic_address,
        destination=wallet_to_address,
        amount={
            "currency": currency_code,  # Currency code, e.g., "USD"
            "issuer": issuer_address,   # Issuer address of the token
            "value": formatted_amount   # Amount as a string
        },
        send_max={
            "currency": currency_code,  # Same currency as in 'amount'
            "issuer": issuer_address,   # Same issuer address as in 'amount'
            "value": send_max_value     # SendMax value as a string, slightly higher than 'amount'
        },
        sequence=sequence
    )

    # Sign and submit the transaction, wait for validation result
    response = await submit_and_wait(
        transaction=payment_tx,
        wallet=wallet_from,
        client=client,
    )
    print("Транзакция обработана и новая создана")         

    # Check for tecPATH_PARTIAL error in the response
    if "engine_result" in response.result and response.result["engine_result"] == "tecPATH_PARTIAL":
        # Log a custom message or handle the error as needed
        print("Transaction failed due to tecPATH_PARTIAL: Partial payment path could not be found. Please adjust the transaction parameters and try again.")
    else:
        # Log success or process the response further
        print(json.dumps(response.result, indent=4, sort_keys=True))
    
    return response
   
async def send_payment(seed, wallet_to_address, amount, currency_code, issuer_address):
    client = AsyncJsonRpcClient("https://rpc.node101.space")  # Адрес XRPL JSON RPC клиента
    
    seed = seed
    wallet_to_address = wallet_to_address  # Замените на адрес получателя
    amount = amount
    currency_code = currency_code
    issuer_address = issuer_address  # Адрес эмитента токена

    # Получите ключевую пару из сида
    keypair = derive_keypair(seed)
    public_key, private_key = keypair

    # Производный классический адрес (адрес кошелька)
    classic_address = derive_classic_address(public_key)

    sequence = await get_next_valid_seq_number(address=classic_address, client=client, ledger_index="current")
    print(f"Current Sequence for {classic_address}: {sequence}")
    
    # Создайте экземпляр кошелька с использованием полученных данных
    wallet_from = Wallet(seed=seed, public_key=public_key, private_key=private_key)
    
    print(wallet_from)
   
    response = await send_payment_evr(client, wallet_from, wallet_to_address, amount, currency_code, issuer_address, sequence)
    
    # Проверка ответа и возврат результатов
    if response and hasattr(response, 'result'):
        # Если в ответе есть результат, возвращаем его
        return response.result
    else:
        # Если ответ некорректен, возвращаем ошибку
        return {"error": "Не удалось отправить платеж или получить ответ от сервера."}

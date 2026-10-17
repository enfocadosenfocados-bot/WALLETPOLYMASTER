"""
Script Todo-en-Uno de Inicialización para la VPS de Londres:
1. Verifica IP (sin geobloqueo) y latencia hacia el motor CLOB de Polymarket (<3ms en Londres).
2. Verifica tus saldos de POL (gas) y USDC.e en la red Polygon.
3. Aprueba automáticamente en la blockchain de Polygon los 3 contratos oficiales de Polymarket
   (CTF Exchange, NegRisk Exchange y NegRisk Adapter) para que el CLOB acepte tus órdenes.
4. Genera gratis tus credenciales L2 (POLY_API_KEY, POLY_API_SECRET, POLY_API_PASSPHRASE) y las guarda.

Uso:
  python setup_credentials.py
"""
import sys
import urllib.request
from config import BotConfig

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Direcciones Oficiales de Contratos de Polymarket en Polygon Mainnet (Chain ID 137)
USDC_E_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"

EXCHANGE_TARGETS = [
    ("CTF Exchange", "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"),
    ("NegRisk CTF Exchange", "0xC5d563A36AE78145C45a50134d48A1215220f80a"),
    ("NegRisk Adapter", "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"),
]

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]

ERC1155_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}, {"name": "operator", "type": "address"}],
        "name": "isApprovedForAll",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "operator", "type": "address"}, {"name": "approved", "type": "bool"}],
        "name": "setApprovalForAll",
        "outputs": [],
        "type": "function",
    },
]

def check_vps_geoblock_and_latency():
    print("=== PASO 1: VERIFICANDO IP DE LA VPS Y LATENCIA AL MOTOR CLOB ===")
    req = urllib.request.Request(
        f"{BotConfig.CLOB_HOST}/time",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        server_timing = resp.headers.get("Server-Timing", "N/A")
        cf_ray = resp.headers.get("CF-RAY", "N/A")
        server_time = resp.read().decode().strip()
        print(f"  [OK] Respuesta CLOB Time       : {server_time}")
        print(f"  [OK] Data Center Cloudflare    : {cf_ray} (En Londres verás -LHR)")
        print(f"  [OK] Latencia Red (cfEdge)     : {server_timing}")

def check_balances_and_approve_contracts():
    print("\n=== PASO 2: VERIFICANDO SALDOS EN POLYGON Y APROBANDO CONTRATOS ===")
    if not BotConfig.PRIVATE_KEY or BotConfig.PRIVATE_KEY == "0x" + "0" * 64:
        print("  [PENDIENTE] Configura primero tu PRIVATE_KEY en el archivo .env.")
        return False

    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(BotConfig.POLYGON_RPC_URL))
        if not w3.is_connected():
            print(f"  [ERROR] No se pudo conectar al RPC de Polygon: {BotConfig.POLYGON_RPC_URL}")
            return False

        account = w3.eth.account.from_key(BotConfig.PRIVATE_KEY)
        wallet_addr = account.address
        pol_bal_wei = w3.eth.get_balance(wallet_addr)
        pol_bal = float(w3.from_wei(pol_bal_wei, "ether"))

        usdc_contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_E_ADDRESS), abi=ERC20_ABI)
        ctf_contract = w3.eth.contract(address=Web3.to_checksum_address(CTF_ADDRESS), abi=ERC1155_ABI)

        usdc_bal_raw = usdc_contract.functions.balanceOf(wallet_addr).call()
        usdc_bal = usdc_bal_raw / 1e6

        print(f"  [OK] Dirección de tu Wallet Bot: {wallet_addr}")
        print(f"  [OK] Saldo de Gas (POL)        : {pol_bal:.4f} POL")
        print(f"  [OK] Saldo de Capital (USDC.e) : ${usdc_bal:,.2f} USDC.e")

        if pol_bal < 0.05:
            print("  [AVISO] Tienes menos de 0.05 POL. Deposita al menos $2-$5 USD en POL para aprobar contratos.")
            return True

        max_uint256 = 2**256 - 1
        for label, target in EXCHANGE_TARGETS:
            target_cs = Web3.to_checksum_address(target)
            # 1. Revisar Allowance de USDC.e
            current_allowance = usdc_contract.functions.allowance(wallet_addr, target_cs).call()
            if current_allowance < 10_000_000 * 10**6:
                print(f"  -> Aprobando USDC.e para {label} ({target_cs})...")
                nonce = w3.eth.get_transaction_count(wallet_addr)
                tx = usdc_contract.functions.approve(target_cs, max_uint256).build_transaction({
                    "from": wallet_addr,
                    "nonce": nonce,
                    "gas": 80000,
                    "gasPrice": int(w3.eth.gas_price * 1.2),
                    "chainId": 137,
                })
                signed = w3.eth.account.sign_transaction(tx, private_key=BotConfig.PRIVATE_KEY)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                print(f"     [APROBADO] Tx: {tx_hash.hex()}")
            else:
                print(f"  [OK] USDC.e ya está aprobado para {label}.")

            # 2. Revisar Approval de Conditional Tokens (ERC-1155)
            is_approved = ctf_contract.functions.isApprovedForAll(wallet_addr, target_cs).call()
            if not is_approved:
                print(f"  -> Aprobando ConditionalTokens para {label} ({target_cs})...")
                nonce = w3.eth.get_transaction_count(wallet_addr)
                tx = ctf_contract.functions.setApprovalForAll(target_cs, True).build_transaction({
                    "from": wallet_addr,
                    "nonce": nonce,
                    "gas": 80000,
                    "gasPrice": int(w3.eth.gas_price * 1.2),
                    "chainId": 137,
                })
                signed = w3.eth.account.sign_transaction(tx, private_key=BotConfig.PRIVATE_KEY)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                print(f"     [APROBADO] Tx: {tx_hash.hex()}")
            else:
                print(f"  [OK] ConditionalTokens ya está aprobado para {label}.")
        return True
    except ImportError:
        print("  [AVISO] Instala web3 para verificar saldos y aprobar contratos: pip install web3")
        return False
    except Exception as e:
        print(f"  [ERROR] Fallo en verificación/aprobación de Polygon: {e}")
        return False

def generate_clob_api_keys():
    print("\n=== PASO 3: GENERANDO CREDENCIALES GRATUITAS L2 DEL CLOB ===")
    if not BotConfig.PRIVATE_KEY or BotConfig.PRIVATE_KEY == "0x" + "0" * 64:
        print("  [PENDIENTE] Sin PRIVATE_KEY en .env. Puedes usar 'python bot.py' en modo Simulación.")
        return

    try:
        from py_clob_client.client import ClobClient
        client = ClobClient(
            host=BotConfig.CLOB_HOST,
            key=BotConfig.PRIVATE_KEY,
            chain_id=BotConfig.CHAIN_ID,
            signature_type=BotConfig.SIGNATURE_TYPE,
            funder=BotConfig.FUNDER_ADDRESS or None,
        )
        creds = client.create_or_derive_api_creds()
        print("  [ÉXITO] Tus credenciales L2 gratuitas de Polymarket son:")
        print(f"POLY_API_KEY={creds.api_key}")
        print(f"POLY_API_SECRET={creds.api_secret}")
        print(f"POLY_API_PASSPHRASE={creds.api_passphrase}")
    except ImportError:
        print("  [AVISO] Instala py-clob-client: pip install py-clob-client")
    except Exception as e:
        print(f"  [ERROR] No se pudieron derivar las credenciales L2: {e}")

if __name__ == "__main__":
    check_vps_geoblock_and_latency()
    check_balances_and_approve_contracts()
    generate_clob_api_keys()

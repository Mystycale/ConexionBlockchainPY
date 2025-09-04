#!/usr/bin/env python3
# insertar.py

import os
import argparse
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

def parse_prescription_id(value: str, w3: Web3) -> bytes:
    """
    Convierte prescription_id a bytes32:
    - Si es 0x + 64 hex, lo toma tal cual.
    - Si no, aplica keccak256(text=value).
    """
    if value.startswith("0x") and len(value) == 66:
        return w3.to_bytes(hexstr=value)
    return w3.keccak(text=value)

def parse_content_hash(hex_str: str, w3: Web3) -> bytes:
    """
    Convierte content_hash a bytes32 EXCLUSIVAMENTE desde hex:
    - Debe empezar con '0x' y tener exactamente 66 caracteres.
    - Si no, lanza un error.
    """
    if not (hex_str.startswith("0x") and len(hex_str) == 66):
        raise ValueError(
            "content_hash debe ser un hex de 32 bytes (0x + 64 hex)."
        )
    return w3.to_bytes(hexstr=hex_str)

def main():
    # 1) Carga .env
    load_dotenv()  # Asegúrate que tu .env esté junto a este script
    rpc_url       = os.getenv("HOSPITAL_RPC")
    private_key   = os.getenv("PRIVATE_KEY")
    contract_addr = os.getenv("CONTRACT_ADDRESS")

    if not (rpc_url and private_key and contract_addr):
        print("❌ Define HOSPITAL_RPC, PRIVATE_KEY y CONTRACT_ADDRESS en tu .env")
        return

    # 2) Conecta al nodo Hospital
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"❌ No hay conexión con el nodo Hospital: {rpc_url}")
        return

    # 3) Carga la cuenta que firma
    account = Account.from_key(private_key)
    doctor  = account.address

    # 4) ABI mínimo
    abi = [{
        "inputs": [
            {"internalType":"bytes32","name":"prescriptionId","type":"bytes32"},
            {"internalType":"bytes32","name":"contentHash","type":"bytes32"},
            {"internalType":"bytes","name":"signature","type":"bytes"}
        ],
        "name":"registerPrescription",
        "outputs": [],
        "stateMutability":"nonpayable",
        "type":"function"
    }]
    contract = w3.eth.contract(
        address=w3.to_checksum_address(contract_addr),
        abi=abi
    )

    # 5) Argumentos CLI
    parser = argparse.ArgumentParser(
        description="Registra una receta on-chain (registerPrescription)."
    )
    parser.add_argument(
        "prescription_id",
        help="ID de receta (hex bytes32 o texto)."
    )
    parser.add_argument(
        "content_hash",
        help="Hash del contenido (hex bytes32)."
    )
    parser.add_argument(
        "signature",
        nargs="?",
        default="0x",
        help="Firma en hex (0x…) o vacío."
    )
    args = parser.parse_args()

    # 6) Parsear prescription_id y content_hash
    try:
        presc = parse_prescription_id(args.prescription_id, w3)
        chash = parse_content_hash(args.content_hash, w3)
    except ValueError as e:
        print(f"❌ Error de formato: {e}")
        return

    # 7) Preparar signature
    sig = args.signature
    if not sig.startswith("0x"):
        sig = "0x" + sig
    sig_bytes = bytes.fromhex(sig[2:])

    # 8) Construir transacción (gasPrice = 0 para Kaleido)
    nonce = w3.eth.get_transaction_count(doctor)
    tx = contract.functions.registerPrescription(presc, chash, sig_bytes) \
        .build_transaction({
            "from":        doctor,
            "nonce":       nonce,
            "gas":         300_000,
            "gasPrice":    0
        })

    # 9) Firmar y enviar
    signed_tx = account.sign_transaction(tx)
    tx_hash   = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt   = w3.eth.wait_for_transaction_receipt(tx_hash)

    # 10) Feedback
    print("\n✅ registerPrescription enviada con éxito")
    print(f"  prescriptionId: {args.prescription_id}")
    print(f"  contentHash   : {args.content_hash}")
    print(f"  signature     : {sig}")
    print(f"  txHash        : {tx_hash.hex()}")
    print(f"  blockNumber   : {receipt.blockNumber}")

if __name__ == "__main__":
    main()

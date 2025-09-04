#!/usr/bin/env python3
# get_prescription.py

import os
import argparse
from web3 import Web3
from web3.exceptions import ContractLogicError
from dotenv import load_dotenv

def parse_prescription_id(id_str: str, w3: Web3) -> bytes:
    """
    Si id_str es un bytes32 válido (0x + 64 hex), lo devuelve como tal.
    En caso contrario, calcula keccak256(text=id_str).
    """
    if id_str.startswith("0x") and len(id_str) == 66:
        return w3.to_bytes(hexstr=id_str)
    return w3.keccak(text=id_str)

def main():
    # 1. Carga .env
    load_dotenv()
    rpc_url         = os.getenv("FARMACIA_RPC")
    contract_addr   = os.getenv("CONTRACT_ADDRESS")
    if not rpc_url or not contract_addr:
        print("Error: define FARMACIA_RPC y CONTRACT_ADDRESS en tu .env")
        return

    # 2. Conecta con Farmacia
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"Error de conexión con {rpc_url}")
        return

    # 3. Prepara el contrato
    abi = [
        {
            "inputs":[{"internalType":"bytes32","name":"prescriptionId","type":"bytes32"}],
            "name":"getPrescription",
            "outputs":[
                {"internalType":"bytes32","name":"contentHash","type":"bytes32"},
                {"internalType":"bytes","name":"signature","type":"bytes"},
                {"internalType":"uint256","name":"issuedAt","type":"uint256"},
                {"internalType":"address","name":"doctor","type":"address"}
            ],
            "stateMutability":"view",
            "type":"function"
        }
    ]
    contract = w3.eth.contract(
        address=w3.to_checksum_address(contract_addr),
        abi=abi
    )

    # 4. Parsea argumentos
    parser = argparse.ArgumentParser(
        description="Recupera datos de una receta on-chain por prescriptionId"
    )
    parser.add_argument(
        "id",
        help="Prescription ID (0x… de 32 bytes) o texto legible que se keccakizará"
    )
    args = parser.parse_args()

    presc_id = parse_prescription_id(args.id, w3)

    # 5. Llama a getPrescription
    try:
        content_hash, signature, issued_at, doctor = (
            contract.functions.getPrescription(presc_id).call()
        )
    except ContractLogicError as e:
        print(f"Error: {e}")
        return

    # 6. Muestra resultados
    print("\n📋 Receta encontrada:")
    print(" prescriptionId:", args.id)
    print(" contentHash   :", content_hash.hex())
    print(" signature     :", signature.hex() or "0x")
    print(" issuedAt      :", issued_at)
    print(" doctor        :", doctor)

if __name__ == "__main__":
    main()

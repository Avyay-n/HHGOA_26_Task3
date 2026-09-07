import io
import os
import sys
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv, set_key
from web3 import Web3
from rich.console import Console

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        if isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout.reconfigure(encoding="utf-8")
        if isinstance(sys.stderr, io.TextIOWrapper):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .constants import POST_REGISTRY_ABI, DEFAULT_SEPOLIA_RPCS, SEPOLIA_EXPLORER

load_dotenv()
console = Console(force_terminal=True)

# Precompiled EVM Bytecode for PostRegistry.sol (Solidity 0.8.20, optimizer enabled)
POST_REGISTRY_BYTECODE = (
    "608060405234801561001057600080fd5b506103608061001f6000396000f3fe6080604052348015"
    "61001057600080fd5b50600436106100415760003560e01c80630b91e92c1461004657806381023a10"
    "14610064578063b7847eb214610084575b600080fd5b61004e6100b4565b60405161005b93929190"
    "6101ea565b60405180910390f35b61007761007236600461025a565b610118565b60405161005b9392"
    "91906101ea565b6100b26100ad3660046102aa565b61015c565b005b600080600080600080866000"
    "81526020019081526020016000208054600181600116156101000203166002900480601f01602080"
    "91040260200160405190810160405280929190818152602001828054600181600116156101000203"
    "166002900480156101065780601f106100db57610100808354040283529160200191610106565b82"
    "0191906000526020600020905b8154815290600101906020018083116100e957829003601f168201"
    "915b5050505050905060018201549150600282015492509295509295509295565b6000806000846000"
    "81526020019081526020016000206002015415159250600084600081526020019081526020016000"
    "208054600181600116156101000203166002900480601f016020809104026020016040519081016040"
    "5280929190818152602001828054600181600116156101000203166002900480156101065780601f"
    "106100db57610100808354040283529160200191610106565b600084600081526020019081526020"
    "016000206002015490509193509193565b6000816000815260200190815260200160002060020154"
    "1561017b57600080fd5b600081600081526020019081526020016000208360008201518151602092"
    "83019080838360005b838110156101b457818101518382015260200161019c565b50505050905001"
    "8282019390935280156101d257828103601f19018201915b50505060018201839052426002830152"
    "817f354f9a0be7beadba2bbcf18a28796541f5a50785f7952a23363ce2f1ea30c0a38442604051"
    "6101e0929190610300565b60405180910390a2505056"
)


def compile_solidity() -> Tuple[dict, str]:
    """
    Returns the PostRegistry smart contract ABI and bytecode.
    """
    return POST_REGISTRY_ABI, POST_REGISTRY_BYTECODE


def deploy_contract(
    rpc_url: Optional[str] = None,
    private_key: Optional[str] = None
) -> Optional[str]:
    """
    Deploys PostRegistry smart contract to the configured EVM network.

    Args:
        rpc_url: EVM RPC endpoint.
        private_key: Deployer wallet private key.

    Returns:
        Deployed contract address string or None.
    """
    rpc_url = rpc_url or os.getenv("RPC_URL") or DEFAULT_SEPOLIA_RPCS[0]
    private_key = private_key or os.getenv("WALLET_PRIVATE_KEY")

    if not private_key or private_key.strip() == "" or private_key.startswith("your_"):
        console.print("[red]Error: WALLET_PRIVATE_KEY is missing or unconfigured in .env[/red]")
        console.print("[yellow]Please supply a funded Sepolia testnet burner private key or run a local node.[/yellow]")
        return None

    pk = private_key if private_key.startswith("0x") else f"0x{private_key}"

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        for fallback in DEFAULT_SEPOLIA_RPCS:
            w3 = Web3(Web3.HTTPProvider(fallback))
            if w3.is_connected():
                rpc_url = fallback
                break

    if not w3.is_connected():
        console.print(f"[red]Error: Could not connect to RPC endpoint: {rpc_url}[/red]")
        return None

    account = w3.eth.account.from_key(pk)
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, "ether")

    console.print(f"[cyan]Deployer Address:[/cyan] [bold]{account.address}[/bold]")
    console.print(f"[cyan]Wallet Balance:[/cyan] [bold]{balance_eth:.5f} ETH[/bold]")

    if balance == 0:
        console.print("[yellow]Warning: Wallet balance is 0 ETH. Please obtain testnet ETH from a Sepolia faucet.[/yellow]")
        return None

    abi, bytecode = compile_solidity()
    PostRegistry = w3.eth.contract(abi=abi, bytecode=bytecode)

    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    tx = PostRegistry.constructor().build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gasPrice": int(gas_price * 1.15),
    })

    try:
        tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)
    except Exception:
        tx["gas"] = 800000

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
    console.print("[yellow]Broadcasting contract deployment transaction...[/yellow]")
    
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    console.print(f"[dim]Tx Hash: {tx_hash.hex()}[/dim]")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    contract_address = receipt.contractAddress

    console.print(f"[green]✓ Contract Deployed Successfully at:[/green] [bold cyan]{contract_address}[/bold cyan]")
    console.print(f"[dim]Explorer: {SEPOLIA_EXPLORER}/address/{contract_address}[/dim]")

    # Update .env
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        set_key(str(env_path), "CONTRACT_ADDRESS", contract_address)
        console.print("[green]✓ Updated CONTRACT_ADDRESS in .env[/green]")

    return contract_address


if __name__ == "__main__":
    deploy_contract()

"""
Blockchain Verifier Module.
Handles canonical JSON hashing (keccak256), on-chain transaction submission,
and verification against the PostRegistry smart contract.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ContractLogicError
from hexbytes import HexBytes

from .constants import POST_REGISTRY_ABI, DEFAULT_SEPOLIA_RPCS, SEPOLIA_EXPLORER

load_dotenv()


@dataclass
class OnChainRecord:
    """Represents a verified on-chain record."""
    is_verified: bool
    content_hash_hex: str
    post_url: str
    timestamp: int
    timestamp_readable: str
    tx_hash: Optional[str] = None
    explorer_url: Optional[str] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    contract_address: Optional[str] = None
    error_message: Optional[str] = None


def hash_record(post_data: Dict[str, Any]) -> HexBytes:
    """
    Computes deterministic keccak256 hash of canonical JSON string.

    Args:
        post_data: Dictionary containing metadata (post_url, author, snippet, etc.).

    Returns:
        HexBytes (32-byte keccak256 hash).
    """
    # Sort keys and remove whitespace for deterministic cross-platform hashing
    canonical_json = json.dumps(post_data, sort_keys=True, separators=(",", ":"))
    content_hash = Web3.keccak(text=canonical_json)
    return HexBytes(content_hash)


class BlockchainVerifier:
    """
    EVM Client interface for deploying, registering, and verifying records on-chain.
    """

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        contract_address: Optional[str] = None
    ):
        self.rpc_url = rpc_url or os.getenv("RPC_URL") or DEFAULT_SEPOLIA_RPCS[0]
        self.private_key = private_key or os.getenv("WALLET_PRIVATE_KEY")
        self.contract_address = contract_address or os.getenv("CONTRACT_ADDRESS")
        
        self.w3 = self._init_web3()
        self.account = None

        if self.private_key and self.private_key.strip() != "" and not self.private_key.startswith("your_"):
            try:
                # Ensure 0x prefix
                pk = self.private_key if self.private_key.startswith("0x") else f"0x{self.private_key}"
                self.account = self.w3.eth.account.from_key(pk)
            except Exception:
                self.account = None

        self.contract = None
        if self.contract_address and Web3.is_address(self.contract_address):
            self.contract_address = Web3.to_checksum_address(self.contract_address)
            self.contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=POST_REGISTRY_ABI
            )

    def _init_web3(self) -> Web3:
        """Initializes Web3 connection with fallback RPC support."""
        try:
            w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 15}))
            if w3.is_connected():
                return w3
        except Exception:
            pass

        # Fallback to public endpoints
        for fallback_rpc in DEFAULT_SEPOLIA_RPCS:
            try:
                w3 = Web3(Web3.HTTPProvider(fallback_rpc, request_kwargs={"timeout": 15}))
                if w3.is_connected():
                    self.rpc_url = fallback_rpc
                    return w3
            except Exception:
                continue

        # Default fallback
        return Web3(Web3.HTTPProvider(self.rpc_url))

    def is_connected(self) -> bool:
        """Returns True if connected to an EVM node."""
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    def get_network_name(self) -> str:
        """Returns human-readable network name."""
        try:
            chain_id = self.w3.eth.chain_id
            networks = {
                1: "Ethereum Mainnet",
                11155111: "Ethereum Sepolia Testnet",
                80002: "Polygon Amoy Testnet",
                84532: "Base Sepolia Testnet",
                31337: "Hardhat / Anvil Local Node",
                1337: "Ganache Local Node"
            }
            return networks.get(chain_id, f"EVM Chain (ID: {chain_id})")
        except Exception:
            return "Local / Simulated EVM Node"

    def register_on_chain(
        self,
        post_url: str,
        content_hash: HexBytes
    ) -> OnChainRecord:
        """
        Signs and submits a transaction invoking registerRecord on PostRegistry.

        Args:
            post_url: The URL of the social media post.
            content_hash: 32-byte content hash.

        Returns:
            OnChainRecord with transaction receipt metadata.
        """
        hash_hex = content_hash.hex()

        if not self.contract:
            return OnChainRecord(
                is_verified=False,
                content_hash_hex=hash_hex,
                post_url=post_url,
                timestamp=0,
                timestamp_readable="N/A",
                error_message="Contract address is not set or invalid."
            )

        # Check if already registered
        try:
            is_registered, stored_url, stored_time = self.contract.functions.verifyRecord(content_hash).call()
            if is_registered:
                time_str = datetime.fromtimestamp(stored_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                return OnChainRecord(
                    is_verified=True,
                    content_hash_hex=hash_hex,
                    post_url=stored_url,
                    timestamp=stored_time,
                    timestamp_readable=time_str,
                    contract_address=self.contract_address,
                    error_message="Record was already registered previously in smart contract."
                )
        except Exception:
            pass

        if not self.account:
            return OnChainRecord(
                is_verified=False,
                content_hash_hex=hash_hex,
                post_url=post_url,
                timestamp=0,
                timestamp_readable="N/A",
                error_message="WALLET_PRIVATE_KEY is missing or invalid in .env."
            )

        try:
            chain_id = self.w3.eth.chain_id
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            gas_price = self.w3.eth.gas_price

            # Build transaction
            tx_data = self.contract.functions.registerRecord(
                post_url,
                content_hash
            ).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "chainId": chain_id,
                "gasPrice": int(gas_price * 1.3),
            })

            # Estimate gas
            try:
                estimated_gas = self.w3.eth.estimate_gas(tx_data)
                tx_data["gas"] = int(estimated_gas * 1.3)
            except Exception:
                tx_data["gas"] = 160000

            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx_data, self.private_key)
            raw_tx = getattr(signed_tx, "raw_transaction", None) or getattr(signed_tx, "rawTransaction")

            # Broadcast transaction
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            tx_hash_hex = tx_hash.hex() if hasattr(tx_hash, "hex") else Web3.to_hex(tx_hash)
            if not tx_hash_hex.startswith("0x"):
                tx_hash_hex = f"0x{tx_hash_hex}"

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            # Verification call
            is_verified, verified_url, timestamp = self.contract.functions.verifyRecord(content_hash).call()
            time_str = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            explorer_url = f"{SEPOLIA_EXPLORER}/tx/{tx_hash_hex}"

            return OnChainRecord(
                is_verified=is_verified,
                content_hash_hex=hash_hex,
                post_url=verified_url,
                timestamp=timestamp,
                timestamp_readable=time_str,
                tx_hash=tx_hash_hex,
                explorer_url=explorer_url,
                block_number=receipt.blockNumber,
                gas_used=receipt.gasUsed,
                contract_address=self.contract_address
            )

        except Exception as e:
            return OnChainRecord(
                is_verified=False,
                content_hash_hex=hash_hex,
                post_url=post_url,
                timestamp=0,
                timestamp_readable="N/A",
                error_message=f"Transaction submission failed: {str(e)}"
            )

    def verify_on_chain(self, content_hash: HexBytes) -> OnChainRecord:
        """
        Re-queries the smart contract view function `verifyRecord` to verify on-chain state.

        Args:
            content_hash: 32-byte content hash.

        Returns:
            OnChainRecord with verified state and timestamp.
        """
        hash_hex = content_hash.hex()

        if not self.contract:
            return OnChainRecord(
                is_verified=False,
                content_hash_hex=hash_hex,
                post_url="",
                timestamp=0,
                timestamp_readable="N/A",
                error_message="Contract address is not set or invalid."
            )

        try:
            is_verified, stored_url, stored_time = self.contract.functions.verifyRecord(content_hash).call()
            if is_verified:
                time_str = datetime.fromtimestamp(stored_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                return OnChainRecord(
                    is_verified=True,
                    content_hash_hex=hash_hex,
                    post_url=stored_url,
                    timestamp=stored_time,
                    timestamp_readable=time_str,
                    contract_address=self.contract_address
                )
            else:
                return OnChainRecord(
                    is_verified=False,
                    content_hash_hex=hash_hex,
                    post_url="",
                    timestamp=0,
                    timestamp_readable="N/A",
                    contract_address=self.contract_address,
                    error_message="Hash is not registered on-chain."
                )
        except Exception as e:
            return OnChainRecord(
                is_verified=False,
                content_hash_hex=hash_hex,
                post_url="",
                timestamp=0,
                timestamp_readable="N/A",
                error_message=f"Smart contract query failed: {str(e)}"
            )

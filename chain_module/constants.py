"""
Blockchain and Smart Contract constants for PostRegistry.
"""

POST_REGISTRY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "bytes32",
                "name": "hash",
                "type": "bytes32"
            },
            {
                "indexed": False,
                "internalType": "string",
                "name": "postUrl",
                "type": "string"
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "timestamp",
                "type": "uint256"
            }
        ],
        "name": "RecordRegistered",
        "type": "event"
    },
    {
        "inputs": [
            {
                "internalType": "bytes32",
                "name": "",
                "type": "bytes32"
            }
        ],
        "name": "records",
        "outputs": [
            {
                "internalType": "string",
                "name": "postUrl",
                "type": "string"
            },
            {
                "internalType": "bytes32",
                "name": "contentHash",
                "type": "bytes32"
            },
            {
                "internalType": "uint256",
                "name": "timestamp",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "string",
                "name": "_postUrl",
                "type": "string"
            },
            {
                "internalType": "bytes32",
                "name": "_contentHash",
                "type": "bytes32"
            }
        ],
        "name": "registerRecord",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "bytes32",
                "name": "_contentHash",
                "type": "bytes32"
            }
        ],
        "name": "verifyRecord",
        "outputs": [
            {
                "internalType": "bool",
                "name": "isVerified",
                "type": "bool"
            },
            {
                "internalType": "string",
                "name": "postUrl",
                "type": "string"
            },
            {
                "internalType": "uint256",
                "name": "timestamp",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Standard public RPC endpoints for Ethereum Sepolia and testnets
DEFAULT_SEPOLIA_RPCS = [
    "https://ethereum-sepolia-rpc.publicnode.com",
    "https://sepolia.drpc.org",
    "https://rpc.sepolia.org",
    "https://1rpc.io/sepolia"
]

SEPOLIA_EXPLORER = "https://sepolia.etherscan.io"

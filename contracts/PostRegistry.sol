// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PostRegistry
 * @dev Immutable on-chain registry for verifying web and social media discoveries by cryptographic content hash.
 */
contract PostRegistry {
    struct Record {
        string postUrl;
        bytes32 contentHash;
        uint256 timestamp;
    }

    // Mapping from content hash to Record
    mapping(bytes32 => Record) public records;

    // Event emitted upon successful registration
    event RecordRegistered(bytes32 indexed hash, string postUrl, uint256 timestamp);

    /**
     * @notice Registers a newly discovered post hash and URL to the blockchain.
     * @param _postUrl The verified URL of the post or social media reference.
     * @param _contentHash The keccak256 cryptographic fingerprint of the post metadata.
     */
    function registerRecord(string memory _postUrl, bytes32 _contentHash) external {
        require(records[_contentHash].timestamp == 0, "Record already exists");
        records[_contentHash] = Record(_postUrl, _contentHash, block.timestamp);
        emit RecordRegistered(_contentHash, _postUrl, block.timestamp);
    }

    /**
     * @notice Verifies whether a content hash is registered on-chain.
     * @param _contentHash The keccak256 hash to look up.
     * @return isVerified Boolean indicating if the record exists.
     * @return postUrl The stored URL associated with the hash.
     * @return timestamp The block timestamp when the record was registered.
     */
    function verifyRecord(bytes32 _contentHash) external view returns (bool isVerified, string memory postUrl, uint256 timestamp) {
        Record memory rec = records[_contentHash];
        return (rec.timestamp != 0, rec.postUrl, rec.timestamp);
    }
}

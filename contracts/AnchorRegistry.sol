// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title AnchorRegistry — minimal timestamping registry for evidence merkle roots.
/// @notice Stores the block timestamp of the FIRST anchor() call for each root.
///         A stored value only proves "this root existed before this moment" —
///         honest positioning: testnet demo, not a notary.
contract AnchorRegistry {
    mapping(bytes32 => uint64) private timestamps;

    event Anchored(bytes32 indexed root, uint64 timestamp, address indexed sender);

    error AlreadyAnchored();

    /// @notice Anchor a 32-byte merkle root. Reverts if the root is already anchored.
    function anchor(bytes32 root) external {
        if (timestamps[root] != 0) revert AlreadyAnchored();
        uint64 ts = uint64(block.timestamp);
        timestamps[root] = ts;
        emit Anchored(root, ts, msg.sender);
    }

    /// @notice True once the root has been anchored by anyone.
    function exists(bytes32 root) external view returns (bool) {
        return timestamps[root] != 0;
    }

    /// @notice Anchor timestamp (unix seconds), 0 when never anchored.
    function getTimestamp(bytes32 root) external view returns (uint64) {
        return timestamps[root];
    }
}

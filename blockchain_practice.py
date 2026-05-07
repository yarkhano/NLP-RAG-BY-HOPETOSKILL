import hashlib   # For SHA-256 hashing
import datetime  # For timestamp generation


class Block:
    """
    Represents a single block in the blockchain.
    Each block stores: index, timestamp, data, previous hash, and its own hash.
    """

    def __init__(self, index, data, previous_hash):
        self.index         = index           # Block number (position in chain)
        self.timestamp     = str(datetime.datetime.now())  # Time block was created
        self.data          = data            # Payload / transaction data
        self.previous_hash = previous_hash   # Hash of the block before this one
        self.hash          = self.calculate_hash()  # This block's own hash

    def calculate_hash(self):
        """
        Combines all block fields into one string and hashes it with SHA-256.
        Any change in data will produce a completely different hash.
        """
        block_content = (
            str(self.index) +
            self.timestamp +
            str(self.data) +
            self.previous_hash
        )
        return hashlib.sha256(block_content.encode('utf-8')).hexdigest()


def create_genesis_block():
    """
    The Genesis Block is the very first block (index 0).
    It has no previous block, so previous_hash is set to '0'.
    """
    return Block(index=0, data="Genesis Block", previous_hash="0")


def create_next_block(previous_block, data):
    """
    Creates a new block linked to the previous block.
    Uses the previous block's hash to maintain the chain.
    """
    return Block(
        index         = previous_block.index + 1,   # Increment index
        data          = data,
        previous_hash = previous_block.hash         # Link to previous block
    )


def print_block(block):
    """Helper to display block details clearly."""
    print(f"\n{'='*55}")
    print(f"  Block #{block.index}")
    print(f"{'='*55}")
    print(f"  Timestamp     : {block.timestamp}")
    print(f"  Data          : {block.data}")
    print(f"  Previous Hash : {block.previous_hash[:20]}...")
    print(f"  Block Hash    : {block.hash[:20]}...")


# ----------- Main Program -----------
if __name__ == "__main__":
    # Step 1: Create the Genesis (first) block
    block0 = create_genesis_block()

    # Step 2: Create Block 1 linked to Genesis
    block1 = create_next_block(block0, "Alice sends 10 BTC to Bob")

    # Step 3: Create Block 2 linked to Block 1
    block2 = create_next_block(block1, "Bob sends 5 BTC to Charlie")

    # Display all blocks
    blockchain = [block0, block1, block2]
    print("\n*** Simple Blockchain Demo ***")
    for block in blockchain:
        print_block(block)

    print(f"\n{'='*55}")
    print("Chain integrity: Each block's Previous Hash matches")
    print(f"  Block 1 prev == Block 0 hash: {block1.previous_hash == block0.hash}")
    print(f"  Block 2 prev == Block 1 hash: {block2.previous_hash == block1.hash}")
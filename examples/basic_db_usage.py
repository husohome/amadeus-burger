"""
Basic example demonstrating the database client usage with settings overrides.
"""

from amadeus_burger import Settings
from amadeus_burger.db import SQLiteClient

def main():
    # Global settings
    Settings.sqlite.connection_string = "example.db"
    
    # Create client with default settings
    db = SQLiteClient()
    
    # Save some test data
    id1 = db.save({"type": "memory", "content": "Test memory 1"})
    id2 = db.save({"type": "memory", "content": "Test memory 2"})
    
    # Query with settings
    results = db.query("type = :type", {"type": "memory"})
    print(f"Found {results.count} memories")
    
    # Query with connection override
    results = db.query(
        "type = :type", 
        {"type": "memory"},
        connection_string="other.db"  # Override for this query only
    )

if __name__ == "__main__":
    main() 
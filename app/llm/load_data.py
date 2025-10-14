"""
Sample script to load initial data into the RAG knowledge base.

This script demonstrates how to initialize the RAG system with learning content.
"""

import asyncio
import logging
from pathlib import Path
from app.llm.main import get_llm_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_sample_learning_content():
    """Load sample learning content into the RAG system."""
    
    llm_service = get_llm_service()
    
    # Sample educational content
    sample_texts = [
        """
        Introduction to Python Programming
        
        Python is a high-level, interpreted programming language known for its simplicity and readability.
        It was created by Guido van Rossum and first released in 1991. Python supports multiple programming
        paradigms, including procedural, object-oriented, and functional programming.
        
        Key features:
        - Easy to learn and read syntax
        - Extensive standard library
        - Dynamic typing
        - Cross-platform compatibility
        - Large community and ecosystem
        """,
        
        """
        Data Structures in Python
        
        Python provides several built-in data structures:
        
        1. Lists: Ordered, mutable collections - [1, 2, 3]
        2. Tuples: Ordered, immutable collections - (1, 2, 3)
        3. Dictionaries: Key-value pairs - {'name': 'John', 'age': 30}
        4. Sets: Unordered collections of unique elements - {1, 2, 3}
        
        Understanding when to use each data structure is crucial for writing efficient code.
        """,
        
        """
        Object-Oriented Programming (OOP) Concepts
        
        OOP is a programming paradigm based on the concept of objects, which contain data and code.
        
        Four pillars of OOP:
        1. Encapsulation: Bundling data and methods that operate on that data
        2. Abstraction: Hiding complex implementation details
        3. Inheritance: Creating new classes from existing ones
        4. Polymorphism: Using a single interface to represent different types
        
        Python supports all OOP principles through classes and objects.
        """,
        
        """
        Python Functions and Best Practices
        
        Functions are reusable blocks of code that perform specific tasks.
        
        Best practices:
        - Use descriptive function names
        - Keep functions small and focused (Single Responsibility Principle)
        - Use type hints for better code documentation
        - Write docstrings to explain what the function does
        - Handle errors appropriately with try-except blocks
        - Use default parameters wisely
        
        Example:
        def calculate_average(numbers: list) -> float:
            \"\"\"Calculate the average of a list of numbers.\"\"\"
            return sum(numbers) / len(numbers)
        """,
        
        """
        Web Development with Python
        
        Python offers several frameworks for web development:
        
        1. Django: Full-featured framework with batteries included
        2. Flask: Lightweight and flexible micro-framework
        3. FastAPI: Modern framework for building APIs with automatic documentation
        
        FastAPI features:
        - Automatic API documentation (Swagger/OpenAPI)
        - Type checking with Pydantic
        - Async support for high performance
        - Easy to learn and use
        - Built-in validation
        """,
        
        """
        Database Concepts and SQL
        
        Databases store and organize data for efficient retrieval and manipulation.
        
        Types of databases:
        1. Relational (SQL): MySQL, PostgreSQL, SQLite
        2. NoSQL: MongoDB, Redis, Cassandra
        
        SQL basics:
        - SELECT: Retrieve data
        - INSERT: Add new records
        - UPDATE: Modify existing records
        - DELETE: Remove records
        - JOIN: Combine data from multiple tables
        
        Understanding database design and normalization is essential for building scalable applications.
        """,
        
        """
        Machine Learning Fundamentals
        
        Machine Learning (ML) is a subset of AI that enables systems to learn from data.
        
        Types of ML:
        1. Supervised Learning: Learning from labeled data (classification, regression)
        2. Unsupervised Learning: Finding patterns in unlabeled data (clustering, dimensionality reduction)
        3. Reinforcement Learning: Learning through trial and error with rewards
        
        Popular Python libraries:
        - scikit-learn: Traditional ML algorithms
        - TensorFlow: Deep learning framework
        - PyTorch: Deep learning with dynamic computation graphs
        - pandas: Data manipulation and analysis
        - NumPy: Numerical computing
        """
    ]
    
    # Metadata for each text
    metadatas = [
        {"source": "Python Basics", "category": "programming", "difficulty": "beginner"},
        {"source": "Data Structures Guide", "category": "programming", "difficulty": "beginner"},
        {"source": "OOP Tutorial", "category": "programming", "difficulty": "intermediate"},
        {"source": "Functions Guide", "category": "programming", "difficulty": "intermediate"},
        {"source": "Web Development", "category": "web", "difficulty": "intermediate"},
        {"source": "Database Tutorial", "category": "database", "difficulty": "intermediate"},
        {"source": "ML Introduction", "category": "machine-learning", "difficulty": "advanced"}
    ]
    
    logger.info("Loading sample learning content into RAG system...")
    
    try:
        result = llm_service.load_knowledge_base(
            texts=sample_texts,
            metadatas=metadatas
        )
        
        logger.info(f"Successfully loaded content: {result}")
        
        # Get stats
        stats = llm_service.get_knowledge_base_stats()
        logger.info(f"Knowledge base stats: {stats}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error loading sample content: {e}")
        raise


def load_from_directory(directory_path: str):
    """
    Load content from a directory of text files.
    
    Args:
        directory_path: Path to directory containing text files
    """
    llm_service = get_llm_service()
    
    logger.info(f"Loading content from directory: {directory_path}")
    
    try:
        result = llm_service.load_knowledge_base(directory_path=directory_path)
        logger.info(f"Successfully loaded content: {result}")
        
        # Get stats
        stats = llm_service.get_knowledge_base_stats()
        logger.info(f"Knowledge base stats: {stats}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error loading content from directory: {e}")
        raise


if __name__ == "__main__":
    # Load sample content
    load_sample_learning_content()
    
    # Optionally load from a directory
    # Uncomment and modify the path as needed
    # load_from_directory("./data/learning_content")
    
    logger.info("Data loading complete!")

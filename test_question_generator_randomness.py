#!/usr/bin/env python3
"""
Test script to demonstrate question generator randomness parameters.
"""

import asyncio
import logging
from app.llm.agents.question_generator import QuestionGeneratorAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_randomness_modes():
    """Test different creativity modes and randomness parameters."""
    
    topic = "Photosynthesis in plants"
    num_questions = 3
    
    print("🌱 Testing Question Generator Randomness Parameters\n")
    
    # Test 1: Conservative mode
    print("1. Testing CONSERVATIVE mode (low randomness, focused responses)")
    print("-" * 70)
    
    generator = QuestionGeneratorAgent(
        temperature=0.3,
        top_k=20, 
        top_p=0.8
    )
    
    questions = await generator.agenerate_questions(
        topic=topic,
        num_questions=num_questions,
        creativity_mode="conservative"
    )
    
    print(f"Generated {len(questions.questions)} questions in conservative mode:")
    for i, q in enumerate(questions.questions, 1):
        print(f"  {i}. {q.question_text[:100]}...")
    print()
    
    # Test 2: Creative mode
    print("2. Testing CREATIVE mode (high randomness, varied responses)")
    print("-" * 70)
    
    generator.set_creativity_mode("creative")
    questions = await generator.agenerate_questions(
        topic=topic,
        num_questions=num_questions
    )
    
    print(f"Generated {len(questions.questions)} questions in creative mode:")
    for i, q in enumerate(questions.questions, 1):
        print(f"  {i}. {q.question_text[:100]}...")
    print()
    
    # Test 3: Custom parameters
    print("3. Testing CUSTOM parameters (temperature=0.9, top_k=50, top_p=0.95)")
    print("-" * 70)
    
    questions = await generator.agenerate_questions(
        topic=topic,
        num_questions=num_questions,
        temperature=0.9,
        top_k=50,
        top_p=0.95
    )
    
    print(f"Generated {len(questions.questions)} questions with custom parameters:")
    for i, q in enumerate(questions.questions, 1):
        print(f"  {i}. {q.question_text[:100]}...")
    print()
    
    # Test 4: Show parameter differences
    print("4. Parameter comparison")
    print("-" * 70)
    
    modes = ["conservative", "balanced", "creative", "highly_creative"]
    for mode in modes:
        generator.set_creativity_mode(mode)
        params = generator.get_generation_params()
        print(f"{mode.upper():15} - temp: {params['temperature']:.1f}, "
              f"top_k: {params['top_k']:2d}, top_p: {params['top_p']:.2f}")
    
    print("\n✅ Randomness testing completed!")

def test_sync_generation():
    """Test synchronous generation with different parameters."""
    
    print("\n🔄 Testing Synchronous Generation with Randomness")
    print("-" * 70)
    
    topic = "Machine Learning Algorithms"
    
    # Test with different creativity modes
    generator = QuestionGeneratorAgent()
    
    modes_to_test = ["conservative", "balanced", "creative"]
    
    for mode in modes_to_test:
        print(f"\nTesting {mode.upper()} mode:")
        
        questions = generator.generate_questions(
            topic=topic,
            num_questions=2,
            creativity_mode=mode,
            question_types=["multiple_choice", "short_answer"]
        )
        
        print(f"  Generated {len(questions.questions)} questions")
        for q in questions.questions:
            print(f"  - Type: {q.question_type}, Difficulty: {q.difficulty}")
            print(f"    Question: {q.question_text[:80]}...")

if __name__ == "__main__":
    try:
        # Test async functionality
        asyncio.run(test_randomness_modes())
        
        # Test sync functionality
        test_sync_generation()
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"❌ Test failed: {e}")
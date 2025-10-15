#!/usr/bin/env python3
"""
LLM Module Demo Script

This script demonstrates all the LLM module capabilities.
Run with: python -m app.llm.demo
"""

import asyncio
import logging
from app.llm.main import get_llm_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print a section divider."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def demo_knowledge_base():
    """Demonstrate knowledge base operations."""
    print_section("1. Knowledge Base Management")
    
    llm_service = get_llm_service()
    
    # Load sample data
    sample_texts = [
        "Python is a high-level programming language known for simplicity.",
        "FastAPI is a modern web framework for building APIs with Python.",
        "Machine learning enables computers to learn from data."
    ]
    
    metadatas = [
        {"source": "Python Guide", "category": "programming"},
        {"source": "FastAPI Docs", "category": "web"},
        {"source": "ML Basics", "category": "ai"}
    ]
    
    print("Loading sample data into knowledge base...")
    result = llm_service.load_knowledge_base(
        texts=sample_texts,
        metadatas=metadatas
    )
    print(f"✓ Loaded: {result}")
    
    # Get stats
    stats = llm_service.get_knowledge_base_stats()
    print(f"✓ Stats: {stats}")


async def demo_learning_path():
    """Demonstrate learning path generation."""
    print_section("2. Learning Path Generation")
    
    llm_service = get_llm_service()
    
    print("Generating learning path for 'Learn Python web development'...")
    
    try:
        learning_path = await llm_service.agenerate_learning_path(
            goal="Learn Python web development with FastAPI",
            current_level="beginner",
            preferences={"focus": "practical projects"},
            available_time="2 hours per day"
        )
        
        print(f"\n✓ Goal: {learning_path.goal}")
        print(f"✓ Difficulty: {learning_path.difficulty_level}")
        print(f"✓ Total Duration: {learning_path.total_duration}")
        print(f"✓ Number of Steps: {len(learning_path.steps)}")
        
        print("\nSteps:")
        for step in learning_path.steps[:3]:  # Show first 3 steps
            print(f"\n  Step {step.step_number}: {step.title}")
            print(f"  Duration: {step.estimated_duration}")
            print(f"  Description: {step.description[:100]}...")
            print(f"  Resources: {', '.join(step.resources[:2])}")
        
        if len(learning_path.steps) > 3:
            print(f"\n  ... and {len(learning_path.steps) - 3} more steps")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        print("  (This requires a valid OPENAI_API_KEY)")


async def demo_question_generation():
    """Demonstrate question generation."""
    print_section("3. Question Generation")
    
    llm_service = get_llm_service()
    
    print("Generating questions about 'Python Functions'...")
    
    try:
        questions = await llm_service.agenerate_questions(
            topic="Python Functions",
            num_questions=3,
            question_types=["multiple_choice", "short_answer"],
            difficulty="medium"
        )
        
        print(f"\n✓ Topic: {questions.topic}")
        print(f"✓ Total Questions: {questions.total_questions}")
        
        for q in questions.questions:
            print(f"\n  Q{q.question_id}: {q.question_text}")
            print(f"  Type: {q.question_type} | Difficulty: {q.difficulty}")
            
            if q.options:
                print("  Options:")
                for opt in q.options:
                    marker = "✓" if opt.is_correct else " "
                    print(f"    [{marker}] {opt.option_id}. {opt.text}")
            
            print(f"  Correct Answer: {q.correct_answer}")
            print(f"  Explanation: {q.explanation[:100]}...")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        print("  (This requires a valid OPENAI_API_KEY)")


async def demo_chatbot():
    """Demonstrate chatbot functionality."""
    print_section("4. Chatbot Conversation")
    
    llm_service = get_llm_service()
    session_id = "demo_session"
    
    print("Starting conversation with AI tutor...")
    
    messages = [
        "What is Python?",
        "What are its main features?",
        "How do I get started?"
    ]
    
    for i, message in enumerate(messages, 1):
        print(f"\n  User: {message}")
        
        try:
            response = await llm_service.achat(
                message=message,
                session_id=session_id
            )
            print(f"  AI: {response[:200]}...")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            print("    (This requires a valid OPENAI_API_KEY)")
            break
    
    # Show conversation history
    print("\n  Retrieving conversation history...")
    history = llm_service.get_chat_history(session_id)
    print(f"  ✓ History has {len(history)} messages")
    
    # Detailed response
    print("\n  Getting detailed response...")
    try:
        detailed = llm_service.chat_with_details(
            message="Can you summarize our conversation?",
            session_id=session_id
        )
        print(f"  Message: {detailed.message[:150]}...")
        print(f"  Sources: {detailed.sources}")
        print(f"  Confidence: {detailed.confidence}")
        print(f"  Follow-ups: {detailed.follow_up_suggestions}")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Clean up
    llm_service.clear_chat_history(session_id)
    print(f"\n  ✓ Cleared chat history for session: {session_id}")


async def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("  LLM MODULE DEMONSTRATION")
    print("  AI Service - Educational AI Capabilities")
    print("="*80)
    
    print("\nNote: Some features require a valid OPENAI_API_KEY in your .env file")
    print("If you see errors, ensure your API key is configured correctly.\n")
    
    # Demo 1: Knowledge Base
    demo_knowledge_base()
    
    # Demo 2: Learning Path (async)
    await demo_learning_path()
    
    # Demo 3: Question Generation (async)
    await demo_question_generation()
    
    # Demo 4: Chatbot (async)
    await demo_chatbot()
    
    print_section("Demo Complete!")
    print("✓ All LLM module features demonstrated")
    print("\nNext Steps:")
    print("  1. Configure your OPENAI_API_KEY in .env file")
    print("  2. Run: python -m app.llm.load_data (to load sample data)")
    print("  3. Start the service: python run.py")
    print("  4. Visit: http://localhost:8000/docs (for API documentation)")
    print("\nFor more information:")
    print("  - Read: app/llm/README.md")
    print("  - Quick Start: QUICKSTART_LLM.md")
    print("  - Implementation: LLM_IMPLEMENTATION_SUMMARY.md")
    print()


if __name__ == "__main__":
    asyncio.run(main())

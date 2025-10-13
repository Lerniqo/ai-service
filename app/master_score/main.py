from inference import preprocess_data, create_sequences, infer_knowledge
import pandas as pd


def test_infer():
    data = pd.read_csv('sample_data_small.csv')
    df, skill_map, num_skills, skill_difficulty = preprocess_data(data)
    X_cat, X_cont, y, seq_len = create_sequences(df, max_seq_len=100)
    print("Preprocessing and sequence creation successful.")
    print(f"Categorical input shape: {X_cat.shape}")
    print(f"Continuous input shape: {X_cont.shape}")
    print(f"Target shape: {y.shape}")

    result = infer_knowledge(data)

    print("Inference function executed successfully.")
    print("="*60)
    print("TESTING INFER_KNOWLEDGE FUNCTION")
    print("="*60)
    print(f"Number of skills predicted: {len(result)}")
    
    print("\nSkill Mastery Predictions:")
    print("-" * 50)
    
    # Sort predictions by mastery probability (descending)
    sorted_predictions = sorted(result.items(), key=lambda x: x[1], reverse=True)
    
    for skill, prob in sorted_predictions:
        print(f"Skill: {skill:<30} Mastery Probability: {prob:.4f}")
    
    print(f"\nTop 3 Skills by Mastery:")
    for i, (skill, prob) in enumerate(sorted_predictions[:3], 1):
        print(f"{i}. {skill} - {prob:.4f}")
    
    print(f"\nBottom 3 Skills by Mastery:")
    for i, (skill, prob) in enumerate(sorted_predictions[-3:], 1):
        print(f"{i}. {skill} - {prob:.4f}")
        


test_infer()
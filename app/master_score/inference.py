

import pandas as pd
import numpy as np
from tensorflow.keras.preprocessing.sequence import pad_sequences
import tensorflow as tf
from tensorflow import keras
import json
import os

# Load skill mapping from JSON file
skill_mapping_path = os.path.join(os.path.dirname(__file__), 'artifacts', 'skill_mapping.json')
with open(skill_mapping_path, 'r') as f:
    skill_map = json.load(f)

def get_positional_encoding(seq_len, d_model):
    """
    Create sinusoidal positional encoding.
    
    Args:
        seq_len: Sequence length
        d_model: Model dimension
        
    Returns:
        Positional encoding matrix of shape (seq_len, d_model)
    """
    positions = np.arange(seq_len)[:, np.newaxis]
    dimensions = np.arange(d_model)[np.newaxis, :]
    
    angle_rates = 1 / np.power(10000, (2 * (dimensions // 2)) / d_model)
    angle_rads = positions * angle_rates
    
    # Apply sin to even indices, cos to odd indices
    angle_rads[:, 0::2] = np.sin(angle_rads[:, 0::2])
    angle_rads[:, 1::2] = np.cos(angle_rads[:, 1::2])
    
    return angle_rads.astype(np.float32)


@tf.keras.utils.register_keras_serializable()
class PositionalEncoding(tf.keras.layers.Layer):
    """Custom layer for positional encoding."""
    
    def __init__(self, max_seq_len, d_model, **kwargs):
        super(PositionalEncoding, self).__init__(**kwargs)
        self.max_seq_len = max_seq_len
        self.d_model = d_model
        self.pos_encoding = tf.constant(
            get_positional_encoding(max_seq_len, d_model),
            dtype=tf.float32
        )
    
    def call(self, x):
        seq_len = tf.shape(x)[1]
        # Use tf.slice with dynamic seq_len
        pos_enc_slice = tf.slice(self.pos_encoding, [0, 0], [seq_len, self.d_model])
        return x + pos_enc_slice
    
    def get_config(self):
        config = super().get_config()
        config.update({
            'max_seq_len': self.max_seq_len,
            'd_model': self.d_model
        })
        return config

@tf.function(jit_compile=False)
def combined_loss(y_true, y_pred):
    """
    Simplified loss function compatible with XLA compilation.
    
    Args:
        y_true: True labels [skill_id, correctness] shape (batch, seq_len, 2)
        y_pred: Predicted probabilities shape (batch, seq_len, num_skills)
    """
    # Extract skill IDs and correctness
    skill_ids = tf.cast(y_true[:, :, 0], tf.int32)
    correctness = y_true[:, :, 1]
    
    # Create mask for valid interactions (skill_id != -1)
    mask = tf.cast(tf.not_equal(skill_ids, -1), tf.float32)
    
    # Clip skill_ids to valid range [0, num_skills-1]
    num_skills = tf.shape(y_pred)[-1]
    skill_ids_clipped = tf.clip_by_value(skill_ids, 0, num_skills - 1)
    
    # Create one-hot encoding for skill selection
    batch_size = tf.shape(skill_ids)[0]
    seq_len = tf.shape(skill_ids)[1]
    
    # Gather predictions for the relevant skills
    # Use batch indices for gathering
    batch_indices = tf.tile(
        tf.expand_dims(tf.range(batch_size), 1),
        [1, seq_len]
    )
    seq_indices = tf.tile(
        tf.expand_dims(tf.range(seq_len), 0),
        [batch_size, 1]
    )
    
    # Stack indices for gather_nd
    gather_indices = tf.stack([
        batch_indices,
        seq_indices,
        skill_ids_clipped
    ], axis=-1)
    
    # Gather the relevant predictions
    relevant_predictions = tf.gather_nd(y_pred, gather_indices)
    
    # Compute binary crossentropy
    epsilon = 1e-7
    relevant_predictions = tf.clip_by_value(relevant_predictions, epsilon, 1 - epsilon)
    bce = -(correctness * tf.math.log(relevant_predictions) +
            (1 - correctness) * tf.math.log(1 - relevant_predictions))
    
    # Apply mask and compute mean
    masked_bce = bce * mask
    total_loss = tf.reduce_sum(masked_bce) / (tf.reduce_sum(mask) + epsilon)
    
    return total_loss


def create_loss_function():
    """Create the loss function wrapper."""
    def loss_fn(y_true, y_pred):
        return combined_loss(y_true, y_pred)
    return loss_fn


def original_get_positional_encoding(seq_len, d_model):
    """
    Create sinusoidal positional encoding.
    
    Args:
        seq_len: Sequence length
        d_model: Model dimension
        
    Returns:
        Positional encoding matrix of shape (seq_len, d_model)
    """
    positions = np.arange(seq_len)[:, np.newaxis]
    dimensions = np.arange(d_model)[np.newaxis, :]
    
    angle_rates = 1 / np.power(10000, (2 * (dimensions // 2)) / d_model)
    angle_rads = positions * angle_rates
    
    # Apply sin to even indices, cos to odd indices
    angle_rads[:, 0::2] = np.sin(angle_rads[:, 0::2])
    angle_rads[:, 1::2] = np.cos(angle_rads[:, 1::2])
    
    return angle_rads.astype(np.float32)


@tf.keras.utils.register_keras_serializable()
class PositionalEncoding(tf.keras.layers.Layer):
    """Custom layer for positional encoding."""
    
    def __init__(self, max_seq_len, d_model, **kwargs):
        super(PositionalEncoding, self).__init__(**kwargs)
        self.max_seq_len = max_seq_len
        self.d_model = d_model
        self.pos_encoding = tf.constant(
            get_positional_encoding(max_seq_len, d_model),
            dtype=tf.float32
        )
    
    def call(self, x):
        seq_len = tf.shape(x)[1]
        # Use tf.slice with dynamic seq_len
        pos_enc_slice = tf.slice(self.pos_encoding, [0, 0], [seq_len, self.d_model])
        return x + pos_enc_slice
    
    def get_config(self):
        config = super().get_config()
        config.update({
            'max_seq_len': self.max_seq_len,
            'd_model': self.d_model
        })
        return config

@tf.function(jit_compile=False)
def combined_loss(y_true, y_pred):
    """
    Simplified loss function compatible with XLA compilation.
    
    Args:
        y_true: True labels [skill_id, correctness] shape (batch, seq_len, 2)
        y_pred: Predicted probabilities shape (batch, seq_len, num_skills)
    """
    # Extract skill IDs and correctness
    skill_ids = tf.cast(y_true[:, :, 0], tf.int32)
    correctness = y_true[:, :, 1]
    
    # Create mask for valid interactions (skill_id != -1)
    mask = tf.cast(tf.not_equal(skill_ids, -1), tf.float32)
    
    # Clip skill_ids to valid range [0, num_skills-1]
    num_skills = tf.shape(y_pred)[-1]
    skill_ids_clipped = tf.clip_by_value(skill_ids, 0, num_skills - 1)
    
    # Create one-hot encoding for skill selection
    batch_size = tf.shape(skill_ids)[0]
    seq_len = tf.shape(skill_ids)[1]
    
    # Gather predictions for the relevant skills
    # Use batch indices for gathering
    batch_indices = tf.tile(
        tf.expand_dims(tf.range(batch_size), 1),
        [1, seq_len]
    )
    seq_indices = tf.tile(
        tf.expand_dims(tf.range(seq_len), 0),
        [batch_size, 1]
    )
    
    # Stack indices for gather_nd
    gather_indices = tf.stack([
        batch_indices,
        seq_indices,
        skill_ids_clipped
    ], axis=-1)
    
    # Gather the relevant predictions
    relevant_predictions = tf.gather_nd(y_pred, gather_indices)
    
    # Compute binary crossentropy
    epsilon = 1e-7
    relevant_predictions = tf.clip_by_value(relevant_predictions, epsilon, 1 - epsilon)
    bce = -(correctness * tf.math.log(relevant_predictions) +
            (1 - correctness) * tf.math.log(1 - relevant_predictions))
    
    # Apply mask and compute mean
    masked_bce = bce * mask
    total_loss = tf.reduce_sum(masked_bce) / (tf.reduce_sum(mask) + epsilon)
    
    return total_loss


def create_loss_function():
    """Create the loss function wrapper."""
    def loss_fn(y_true, y_pred):
        return combined_loss(y_true, y_pred)
    return loss_fn


def preprocess_data(data: pd.DataFrame) -> pd.DataFrame:
    """
    Load and preprocess data with enhanced feature engineering.
    
    New features:
    - Attempt count per skill
    - Time since last attempt
    - Skill difficulty (based on global correctness rate)
    - Student performance history
    
    Args:
        data: DataFrame containing raw interaction data for a single student

    Returns:
        df: Enhanced preprocessed DataFrame
        skill_map: Dictionary mapping skill names to IDs
        num_skills: Number of unique skills
        skill_difficulty: Dictionary of skill difficulty scores
    """
    # Create base DataFrame
    df = pd.DataFrame()
    df['skill_name'] = data['skill']
    df['start_time'] = data['startTime']
    df['correct'] = data['correct']
    df['end_time'] = data['endTime']
    
    # Clean data
    df.dropna(subset=['skill_name', 'correct', 'start_time', 'end_time'], inplace=True)
    df['correct'] = df['correct'].astype(int)
    df.sort_values(by='start_time', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # --- Enhanced Time Features ---
    df['time_taken'] = df['end_time'] - df['start_time']
    df['time_taken'] = df['time_taken'].clip(0, 300)
    df['time_taken_log'] = np.log1p(df['time_taken'])
    max_log_time = df['time_taken_log'].max()
    df['time_taken_scaled'] = df['time_taken_log'] / max_log_time
    
    # Time since last interaction
    df['time_since_last'] = df['start_time'].diff().fillna(0)
    df['time_since_last'] = df['time_since_last'].clip(0, 86400)  # Cap at 24 hours
    df['time_since_last_scaled'] = np.log1p(df['time_since_last']) / np.log1p(86400)
    
    # --- Skill Encoding ---
    skills = df['skill_name'].unique()
    skill_map = {skill: i + 1 for i, skill in enumerate(skills)}
    num_skills = len(skills)
    df['skill_id'] = df['skill_name'].map(skill_map)
    
    # --- Skill Difficulty Calculation ---
    # Calculate global difficulty (inverse of average correctness)
    skill_stats = df.groupby('skill_id')['correct'].agg(['mean', 'count']).reset_index()
    skill_stats.columns = ['skill_id', 'avg_correctness', 'total_attempts']
    # Difficulty = 1 - correctness rate (higher = harder)
    skill_stats['difficulty'] = 1 - skill_stats['avg_correctness']
    # Add smoothing for skills with few attempts
    skill_stats['difficulty_smoothed'] = (
        (skill_stats['difficulty'] * skill_stats['total_attempts'] + 0.5 * 10) / 
        (skill_stats['total_attempts'] + 10)
    )
    skill_difficulty = dict(zip(skill_stats['skill_id'], skill_stats['difficulty_smoothed']))
    df['skill_difficulty'] = df['skill_id'].map(skill_difficulty)
    
    # --- Attempt Count Features ---
    # Count attempts per skill
    df['attempt_count'] = df.groupby('skill_id').cumcount() + 1
    df['attempt_count_scaled'] = np.log1p(df['attempt_count']) / np.log1p(df['attempt_count'].max())
    
    # Running average correctness for the student
    df['student_correct_cumsum'] = df['correct'].cumsum()
    df['student_total_cumcount'] = np.arange(1, len(df) + 1)
    df['student_avg_correctness'] = df['student_correct_cumsum'] / df['student_total_cumcount']
    
    print("Enhanced data loaded and preprocessed.")
    print(f"Number of unique skills: {num_skills}")
    print(f"Total interactions: {len(df)}")
    
    # Create interaction features (same as before)
    df['interaction_feature'] = df['skill_id'] + (1 - df['correct']) * num_skills
    
    return df, skill_map, num_skills, skill_difficulty

def create_sequences(df, max_seq_len=100):
    """
    Create enhanced sequences with additional features for a single student.
    
    Returns:
        X_cat: Categorical features (interactions)
        X_cont: Continuous features (time, difficulty, attempts, etc.)
        y: Targets
        max_len: Sequence length
    """
    # Process single student data directly (no grouping needed)
    if len(df) <= 1:
        raise ValueError("Need at least 2 interactions to create sequences")
    
    X_cat = []  # Categorical features
    X_cont = []  # Continuous features: [time_taken, time_since_last, difficulty, attempt_count, student_avg]
    y = []  # Target
    
    # Process the entire dataframe as one sequence
    x_cat_seq = df['interaction_feature'].values
    
    # Stack multiple continuous features
    x_cont_seq = np.stack([
        df['time_taken_scaled'].values,
        df['time_since_last_scaled'].values,
        df['skill_difficulty'].values,
        df['attempt_count_scaled'].values,
        df['student_avg_correctness'].values
    ], axis=1)
    
    y_seq_skills = df['skill_id'].values
    y_seq_correctness = df['correct'].values
    y_seq_combined = np.stack([y_seq_skills - 1, y_seq_correctness], axis=1)
    
    # Split into chunks if sequence is longer than max_seq_len
    for i in range(0, len(x_cat_seq), max_seq_len):
        end_index = i + max_seq_len
        if len(x_cat_seq[i:end_index]) > 1:
            X_cat.append(x_cat_seq[i:end_index-1])
            X_cont.append(x_cont_seq[i:end_index-1])
            y.append(y_seq_combined[i+1:end_index])
    
    max_len = max_seq_len - 1
    X_cat_padded = pad_sequences(X_cat, maxlen=max_len, padding='post', value=0)
    X_cont_padded = pad_sequences(X_cont, maxlen=max_len, padding='post', value=0.0, dtype='float32')
    y_padded = pad_sequences(y, maxlen=max_len, padding='post', value=-1)
    
    print(f"Max sequence length: {max_len}")
    print(f"Number of sequences: {len(X_cat_padded)}")
    print(f"Categorical input shape: {X_cat_padded.shape}")
    print(f"Continuous input shape: {X_cont_padded.shape}")
    print(f"Target shape: {y_padded.shape}")
    
    return X_cat_padded, X_cont_padded, y_padded, max_len

def infer_knowledge(data):
    """
    Perform inference to predict knowledge states with enhanced features.
    
    Args:
        model: Trained DKT model
        data: DataFrame containing raw interaction data for a single student

    Returns:
        predictions: Model predictions
    """

    custom_objects = {
        'PositionalEncoding': PositionalEncoding,
        'loss_fn': create_loss_function(),
        'combined_loss': combined_loss
    }
    model = keras.models.load_model(
        '/Users/devinda/VS/sem-5-project/ai-service/app/master_score/artifacts/improved_dkt_model.keras',
        custom_objects=custom_objects
    )

    df, _, _, _ = preprocess_data(data)
    X_cat, X_cont, y, seq_len = create_sequences(df)
    
    # Perform prediction
    result = model.predict([X_cat, X_cont])

    reverse_skill_map = {v: k for k, v in skill_map.items()}

    predictions = dict()

    for i in result:
        for j, k in enumerate(i[-1]):
            skill_name = reverse_skill_map.get(j + 1, f"Skill_{j+1}")
            predictions[skill_name] = float(k) 

    return predictions
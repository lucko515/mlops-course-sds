import os
import pandas as pd

import mlflow
import wandb
import joblib
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

def check_validation_status():
    """
    Check if all data validation checks passed in the previous step.
    
    :return: bool
    """
    # Fetch the most recent run in the project
    api = wandb.Api()
    runs = api.runs("credit-card-fraud-detection")
    latest_run = runs[0]  # Assumes the most recent run is the validation run

    # Check if all_checks_passed is True
    return latest_run.summary.get('all_checks_passed', False)

# Initialize WandB for tracking
wandb.init(project="credit-card-fraud-detection-test-33", name="feature-engineering")

def load_data():
    """
    Load the cleaned dataset from WandB Artifacts.
    
    :return: pandas DataFrame
    """
    artifact = wandb.use_artifact('anicin/credit-card-fraud-detection-test-33/processed_data.csv:latest', type='dataset')
    artifact_dir = artifact.download()

    # Load the dataset
    data = pd.read_csv(os.path.join(artifact_dir, 'processed_data.csv'))
    return data

def save_data(data):
    """
    Save the engineered dataset to WandB as an artifact.
    
    :param data: pandas DataFrame, transformed data
    """
    # Save the transformed data locally
    transformed_data_path = 'engineered_data.csv'
    data.to_csv(transformed_data_path, index=False)
    
    # Log the transformed data as an artifact in WandB
    artifact = wandb.Artifact(name='engineered_data.csv', type='dataset')
    artifact.add_file(transformed_data_path)
    wandb.log_artifact(artifact)
    wandb.log({"engineered_data_shape": data.shape})


def feature_engineering(data):
    """
    Perform feature engineering and data transformation.
    
    :param data: pandas DataFrame, cleaned data
    :return: pandas DataFrame, data with new features and transformations applied
    """
    data['trans_date_trans_time'] = pd.to_datetime(data['trans_date_trans_time'], errors='coerce')

    # Example Feature Engineering: Creating new features
    data['hour'] = data['trans_date_trans_time'].dt.hour
    data['day_of_week'] = data['trans_date_trans_time'].dt.dayofweek

    wandb.log({"new_features": ["hour", "day_of_week"]})

    # Verify and select only existing columns
    categorical_features = ['category', 'state']
    numeric_features = ['amt', 'hour', 'day_of_week']  # Changed 'transactionAmount' to 'amt'

    existing_cat_features = [col for col in categorical_features if col in data.columns]
    existing_num_features = [col for col in numeric_features if col in data.columns]

    # Create a pipeline for transformations
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), existing_num_features),
        ])
    
    pipeline = Pipeline(steps=[('preprocessor', preprocessor)])

    # Apply transformations
    transformed_data = pipeline.fit_transform(data)
    
    # Get feature names after transformation
    feature_names = existing_num_features

    transformed_df = pd.DataFrame(transformed_data, columns=feature_names)

    # Adding the target column
    transformed_df['is_fraud'] = data['is_fraud']

    wandb.log({"transformed_data": wandb.Table(dataframe=transformed_df.head())})
    
    # Log pipeline
    joblib.dump(pipeline, 'preprocessor.pkl')
    artifact = wandb.Artifact('preprocessor', type='model')
    artifact.add_file('preprocessor.pkl')
    wandb.log_artifact(artifact)
    
    # Log transformed feature details
    wandb.log({"transformed_features": feature_names})

    return transformed_df


def main():
    mlflow.start_run()

    # Check if data validation passed
    if not check_validation_status():
        print("Data validation checks did not pass. Aborting feature engineering.")
        wandb.log({"error": "Data validation checks did not pass. Aborting feature engineering."})
        mlflow.end_run()
        return

    # Load data from WandB
    data = load_data()

    # Perform feature engineering and data transformation
    engineered_data = feature_engineering(data)

    # Save the engineered data to WandB
    save_data(engineered_data)
    
    # Log final parameters to MLFlow
    mlflow.log_param("engineered_data_shape", engineered_data.shape)

    mlflow.end_run()

if __name__ == "__main__":
    main()

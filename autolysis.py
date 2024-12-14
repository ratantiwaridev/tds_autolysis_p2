import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from jinja2 import Template
import openai
import numpy as np
from sklearn.cluster import KMeans
import chardet

# Check if AI Proxy token is set
def get_api_token():
    token = os.getenv("AIPROXY_TOKEN")
    if not token:
        raise EnvironmentError("Error: AIPROXY_TOKEN environment variable is not set.")
    return token

# Set the OpenAI API URL to the AI Proxy
openai.api_base = "https://aiproxy.sanand.workers.dev/openai/v1"

openai.api_key = get_api_token()

def load_csv(file_path):
    """
    Load a CSV file with automatic encoding detection.
    """
    encodings = ['utf-8', 'latin-1', 'iso-8859-1']
    for encoding in encodings:
        try:
            return pd.read_csv(file_path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    # Fallback to chardet if predefined encodings fail
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
        detected_encoding = result['encoding']
    try:
        return pd.read_csv(file_path, encoding=detected_encoding)
    except Exception as e:
        raise ValueError(f"Error reading CSV file with detected encoding {detected_encoding}: {e}")

def analyze_csv(file_path):
    """
    Analyze the CSV file and return insights and data for visualizations.
    """
    try:
        data = load_csv(file_path)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

    # Basic analysis
    summary = data.describe(include='all').to_string()
    missing_values = data.isnull().sum().to_dict()
    data_types = data.dtypes.to_dict()
    column_names = data.columns.tolist()

    # Correlation matrix for numerical data
    numeric_data = data.select_dtypes(include=[np.number])
    correlation_matrix = None
    if numeric_data.shape[1] > 1:
        correlation_matrix = numeric_data.corr()

    # Generate a prompt for AI
    prompt = (
        f"You are an expert data analyst. The dataset contains the following columns: {', '.join(column_names)}. "
        f"Here is the summary of the dataset: \n{summary}\n "
        f"Missing values: {missing_values}\nData types: {data_types}\n"
    )

    if correlation_matrix is not None:
        prompt += f"Here is the correlation matrix for numerical columns: \n{correlation_matrix.to_string()}\n"

    prompt += "Please write an engaging narrative analysis of the dataset and suggest 1-3 visualizations that would best represent its key insights."

    # Use OpenAI's ChatCompletion API with gpt-4o-mini model
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system", "content": "You are a data analyst."
            }, {
                "role": "user", "content": prompt
            }]
        )
        narrative = response.choices[0].message['content'].strip()
    except AttributeError:
        print("Error: Response from OpenAI API is malformed.")
        sys.exit(1)
    except Exception as e:
        print(f"Error with AI Proxy: {e}")
        sys.exit(1)

    return data, narrative, correlation_matrix

def generate_visualizations(data, correlation_matrix, output_prefix):
    """
    Generate visualizations based on the dataset and save them as PNG files.
    """
    visualizations = []

    # Example visualization: Bar chart of the first column's value counts (if applicable)
    if len(data.columns) >= 2:
        col = data.columns[0]
        counts = data[col].value_counts().head(10)

        plt.figure(figsize=(10, 6))
        counts.plot(kind='bar', color='skyblue')
        plt.title(f"Top 10 {col} Counts")
        plt.xlabel(col)
        plt.ylabel("Count")
        output_path = f"{output_prefix}_barchart.png"
        plt.savefig(output_path)
        plt.close()

        visualizations.append(output_path)

    # Correlation heatmap
    if correlation_matrix is not None:
        plt.figure(figsize=(10, 8))
        sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap="coolwarm")
        plt.title("Correlation Matrix Heatmap")
        output_path = f"{output_prefix}_heatmap.png"
        plt.savefig(output_path)
        plt.close()

        visualizations.append(output_path)

    # Outlier detection (boxplot for numerical columns)
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        for col in numeric_cols:
            plt.figure(figsize=(10, 6))
            sns.boxplot(x=data[col], color="lightblue")
            plt.title(f"Boxplot for {col}")
            output_path = f"{output_prefix}_{col}_boxplot.png"
            plt.savefig(output_path)
            plt.close()

            visualizations.append(output_path)

    return visualizations

def create_readme(narrative, visualizations):
    """
    Create a README.md file summarizing the analysis and embedding visualizations.
    """
    template = Template(
        """
        # Automated Analysis Report

        {{ narrative }}

        {% for vis in visualizations %}
        ![Visualization](./{{ vis }})
        {% endfor %}
        """
    )

    readme_content = template.render(narrative=narrative, visualizations=visualizations)
    with open("README.md", "w") as f:
        f.write(readme_content)

def main():
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)

    csv_file = sys.argv[1]

    try:
        # Analyze the dataset
        data, narrative, correlation_matrix = analyze_csv(csv_file)

        # Generate visualizations
        output_prefix = os.path.splitext(os.path.basename(csv_file))[0]
        visualizations = generate_visualizations(data, correlation_matrix, output_prefix)

        # Create README.md
        create_readme(narrative, visualizations)

        print("Analysis complete. Results saved to README.md and visualization files.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

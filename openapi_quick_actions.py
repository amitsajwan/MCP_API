import yaml
import os
from typing import List, Dict

class QuickActionsLoader:
    def __init__(self, folder_path: str):
        """
        Initialize the loader with the directory containing OpenAPI files.
        :param folder_path: Path to the directory containing OpenAPI YAML/JSON files.
        """
        self.folder_path = folder_path

    def load_openapi_files(self) -> List[Dict]:
        """
        Load all OpenAPI files from the specified folder.
        :return: A list of parsed OpenAPI documents.
        """
        openapi_docs = []
        if not os.path.exists(self.folder_path):
            raise FileNotFoundError(f"Directory '{self.folder_path}' does not exist.")

        for filename in os.listdir(self.folder_path):
            if filename.endswith((".yaml", ".yml", ".json")):
                file_path = os.path.join(self.folder_path, filename)
                with open(file_path, 'r') as f:
                    try:
                        doc = yaml.safe_load(f)
                        openapi_docs.append(doc)
                    except yaml.YAMLError as e:
                        print(f"Error parsing {filename}: {e}")
        return openapi_docs

    def extract_quick_actions(self, openapi_docs: List[Dict]) -> List[Dict]:
        """
        Extract quick actions from the loaded OpenAPI documents.
        :param openapi_docs: A list of OpenAPI documents.
        :return: A list of quick actions extracted from the documents.
        """
        quick_actions = []
        for doc in openapi_docs:
            paths = doc.get("paths", {})
            for path, methods in paths.items():
                for method, operation in methods.items():
                    if operation.get("x-quick-action"):
                        quick_actions.append({
                            "path": path,
                            "method": method.upper(),
                            "summary": operation.get("summary", ""),
                            "description": operation.get("description", ""),
                            "tags": operation.get("tags", [])
                        })
        return quick_actions

    def get_quick_actions(self) -> List[Dict]:
        """
        Load OpenAPI files and extract quick actions.
        :return: A list of quick actions.
        """
        openapi_docs = self.load_openapi_files()
        return self.extract_quick_actions(openapi_docs)

def get_default_quick_actions() -> List[Dict]:
    """
    Provide default quick actions if no OpenAPI files are found or loaded.
    :return: A list of default quick actions.
    """
    return [
        {
            "path": "/default-path",
            "method": "GET",
            "summary": "Default Action",
            "description": "This is a default quick action.",
            "tags": ["default"]
        }
    ]

if __name__ == "__main__":
    # Define the directory containing OpenAPI YAML/JSON files
    OPENAPI_DIR = "c:/code/MCP_API/openapi_files"  # Update this path as needed

    # Initialize the loader
    loader = QuickActionsLoader(OPENAPI_DIR)

    try:
        # Load quick actions from OpenAPI files
        quick_actions = loader.get_quick_actions()

        # If no quick actions are loaded, use defaults
        if not quick_actions:
            print("No quick actions found. Using default quick actions.")
            quick_actions = get_default_quick_actions()

    except FileNotFoundError as e:
        print(e)
        print("Using default quick actions.")
        quick_actions = get_default_quick_actions()

    # Print the loaded quick actions
    print("Loaded Quick Actions:", quick_actions)

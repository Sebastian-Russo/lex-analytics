import os
from dataclasses import dataclass

import toml # type: ignore


@dataclass
class _ProjectMeta:
    """
    A class to encapsulate project metadata.
    """

    name: str
    version: str


def get_project_meta() -> _ProjectMeta:
    """
    Reads the project name and version from the pyproject.toml file.

    Returns:

        ProjectMeta: The project name and version.
    """

    # Dynamically determine the path to pyproject.toml
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate up to the project root (two levels up from util directory)
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    pyproject_path = os.path.join(project_root, 'pyproject.toml')

    try:
        with open(pyproject_path, 'r', encoding='utf-8') as file:
            pyproject_data = toml.load(file)

            pyproject = pyproject_data.get('project', {})
            name = pyproject.get('name', '')
            version = pyproject.get('version', '')

            if '.' in name:
                name = name.split('.')[1]

            return _ProjectMeta(name, version)
    except FileNotFoundError:
        raise FileNotFoundError('pyproject.toml not found')
    except Exception as e:
        raise Exception(f'Error reading {pyproject_path}: {e}')

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
    pyproject_path = os.path.join(script_dir, 'pyproject.toml') #TODO: make file

    try:
        with open(pyproject_path, 'r') as file:
            pyproject_data = toml.load(file)

            pyproject = pyproject_data.get('project', {})
            name = pyproject.get('name', '')
            if '.' in name:
                name = name.split('.')[1]
                version=pyproject.get('version')

                return _ProjectMeta(name, version)
    except FileNotFoundError:
        raise FileNotFoundError('pyproject.toml not found')
    except Exception as e:
        raise Exception(f'Error reading {pyproject_path}: {e}')

from setuptools import setup
import os
from glob import glob

package_name = 'robot_description'


def collect_data_files(source_directory):
    """Collect files recursively while preserving their package directories."""
    collected_files = []
    for current_directory, _, filenames in os.walk(source_directory):
        if not filenames:
            continue

        destination = os.path.join('share', package_name, current_directory)
        sources = [
            os.path.join(current_directory, filename) for filename in filenames
        ]
        collected_files.append((destination, sources))

    return collected_files


setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'meshes'), glob('meshes/*')),
        (os.path.join('share', package_name, 'config'), glob('config/*'))
    ] + collect_data_files('urdf'),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='author',
    maintainer_email='todo@todo.com',
    description='The ' + package_name + ' package',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)

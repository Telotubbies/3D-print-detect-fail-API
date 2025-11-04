from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'ai_3dprint'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'models'), glob('models/*.pt')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='knn',
    maintainer_email='knn@todo.todo',
    description='TODO: Package description',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'detection = ai_3dprint.detection:main',
            'test = ai_3dprint.test:main',
            'three_d_print = ai_3dprint.three_d_print:main',
            'api_web = ai_3dprint.api_web:main',
        ],
    },
)

# Copyright (c) 2026 Tomás Cárdenas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Check the exported model, gripper coupling and assets without Isaac Sim."""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np
import pytest
import xacro
import yaml


PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / 'urdf' / 'robot_parametrico.xacro'
EXPORT = SOURCE.with_name('robot_parametrico_isaac.urdf')


def expanded(ros_extensions=False):
    """Expand the source with portable mesh references."""
    document = xacro.process_file(str(SOURCE), mappings={
        'include_ros_extensions': str(ros_extensions).lower(),
        'mesh_prefix': '../meshes/',
    })
    return ET.fromstring(document.toxml())


def canonical(element):
    """Ignore formatting and attribute order when comparing XML trees."""
    return ET.canonicalize(ET.tostring(element, encoding='unicode'), strip_text=True)


def test_export_matches_xacro():
    """Reject stale exports and unresolved ROS or Xacro paths."""
    robot = ET.parse(EXPORT).getroot()
    assert canonical(robot) == canonical(expanded())
    assert {node.tag for node in robot} == {'material', 'link', 'joint'}
    for mesh in robot.findall('.//mesh'):
        assert mesh.get('filename').startswith('../meshes/')
        assert mesh.get('scale') == '0.001 0.001 0.001'


def test_link_tree_and_usd_names():
    """Require one connected tree and names that USD can preserve."""
    robot = expanded()
    links = [node.get('name') for node in robot.findall('link')]
    joints = robot.findall('joint')
    names = [node.get('name') for node in joints]
    assert len(links) == len(set(links)) == 16
    assert len(joints) == len(set(names)) == 15
    for name in [robot.get('name'), *links, *names]:
        assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name), name
    parents = {}
    for joint in joints:
        parent = joint.find('parent').get('link')
        child = joint.find('child').get('link')
        assert parent in links and child in links and child not in parents
        parents[child] = parent
    assert set(links) - set(parents) == {'base_link'}
    for link in links:
        visited = set()
        while link in parents:
            assert link not in visited, 'Cycle in link tree'
            visited.add(link)
            link = parents[link]
        assert link == 'base_link'


@pytest.mark.parametrize('position', [-0.04, 0.0, 0.04])
def test_gripper_moves_oppositely_with_one_command(position):
    """Check both jaw displacements and limits over the full input range."""
    robot = expanded()
    left = robot.find("joint[@name='grid_izq']")
    right = robot.find("joint[@name='grid_der']")
    mimic = left.find('mimic')
    assert mimic.attrib == {'joint': 'grid_der', 'multiplier': '-1', 'offset': '0'}
    assert right.find('mimic') is None
    follower = float(mimic.get('multiplier')) * position + float(mimic.get('offset'))
    for joint, value in [(left, follower), (right, position)]:
        limit = joint.find('limit')
        assert float(limit.get('lower')) <= value <= float(limit.get('upper'))
    left_axis = np.fromstring(left.find('axis').get('xyz'), sep=' ')
    right_axis = np.fromstring(right.find('axis').get('xyz'), sep=' ')
    np.testing.assert_allclose(left_axis * follower, -right_axis * position)
    independent = {j.get('name') for j in robot.findall('joint')
                   if j.get('type') != 'fixed' and j.find('mimic') is None}
    assert independent == {'x_joint', 'y_joint', 'z_joint', 'r_joint', 'grid_der'}


def test_ros_extensions_match_model():
    """Require transmissions only for driven joints and valid Gazebo links."""
    robot = expanded(ros_extensions=True)
    independent = {j.get('name') for j in robot.findall('joint')
                   if j.get('type') != 'fixed' and j.find('mimic') is None}
    transmissions = [t.find('joint').get('name') for t in robot.findall('transmission')]
    assert len(transmissions) == len(set(transmissions))
    assert set(transmissions) == independent
    links = {link.get('name') for link in robot.findall('link')}
    assert {g.get('reference') for g in robot.findall('gazebo[@reference]')} == links


def test_meshes_are_complete_binary_stl():
    """Validate every referenced mesh, including collision assets."""
    paths = {(EXPORT.parent / mesh.get('filename')).resolve()
             for mesh in expanded().findall('.//mesh')}
    assert len(paths) == 16
    dtype = np.dtype([('normal', '<f4', (3,)),
                      ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])
    for path in paths:
        assert path.is_file(), str(path)
        assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', path.stem), path.name
        data = path.read_bytes()
        count = int.from_bytes(data[80:84], 'little')
        assert count > 0 and len(data) == 84 + 50 * count, path.name
        triangles = np.frombuffer(data, dtype=dtype, offset=84)['vertices'].astype(float)
        assert np.isfinite(triangles).all(), path.name
        normals = np.cross(triangles[:, 1] - triangles[:, 0],
                           triangles[:, 2] - triangles[:, 0])
        areas = np.linalg.norm(normals, axis=1)
        assert np.all(areas > 0), path.name


def test_inertias_and_joint_limits():
    """Reject zero/invalid inertia tensors and malformed joint limits."""
    robot = expanded()
    for link in robot.findall('link'):
        inertial = link.find('inertial')
        assert float(inertial.find('mass').get('value')) > 0, link.get('name')
        a = {k: float(v) for k, v in inertial.find('inertia').attrib.items()}
        tensor = [[a['ixx'], a['ixy'], a['ixz']],
                  [a['ixy'], a['iyy'], a['iyz']],
                  [a['ixz'], a['iyz'], a['izz']]]
        eigenvalues = np.linalg.eigvalsh(tensor)
        assert np.isfinite(eigenvalues).all() and np.all(eigenvalues > 0), link.get('name')
        assert eigenvalues[2] <= eigenvalues[:2].sum() + 1e-12, link.get('name')
    for joint in robot.findall('joint'):
        if joint.get('type') == 'fixed':
            continue
        axis = np.fromstring(joint.find('axis').get('xyz'), sep=' ')
        assert np.linalg.norm(axis) == pytest.approx(1, abs=1e-6)
        limit = {k: float(v) for k, v in joint.find('limit').attrib.items()}
        assert np.isfinite(list(limit.values())).all()
        assert limit['lower'] < limit['upper']
        assert limit['velocity'] > 0 and limit['effort'] > 0


def test_rviz_uses_current_frames():
    """Ensure RViz uses the model's root and receives a latched description."""
    config = yaml.safe_load((PACKAGE / 'config' / 'display.rviz').read_text())
    manager = config['Visualization Manager']
    assert manager['Global Options']['Fixed Frame'] == 'base_link'
    model = next(d for d in manager['Displays'] if d['Name'] == 'RobotModel')
    assert model['Description Topic']['Durability Policy'] == 'Transient Local'
    assert model['Description Topic']['Value'] == '/robot_description'
    assert not any('wheel' in key or 'motor' in key for key in model['Links'])

#!/usr/bin/env python3
# Description: Convert OBJ to NPY
# Usage: python3 obj-to-npy.py file.obj
# Author: Justin Oros
# Source: https://github.com/JustinOros

import sys
import os
import numpy as np

try:
    import pywavefront
except ImportError:
    print("Please install pywavefront: pip install PyWavefront")
    sys.exit(1)

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <obj-file>") 
    sys.exit(1)

obj_path = sys.argv[1]
if not os.path.isfile(obj_path):
    print(f"File not found: {obj_path}")
    sys.exit(1)

base_name = os.path.splitext(os.path.basename(obj_path))[0]
npy_path = f"{base_name}.npy"

print(f"Loading OBJ: {obj_path}")
scene = pywavefront.Wavefront(obj_path, create_materials=True, collect_faces=True, parse=True)

vertices_list = []
faces_list = []

for name, mesh in scene.meshes.items():
    for material in mesh.materials:
        for face in mesh.faces:
            faces_list.append(face)
        for vertex in scene.vertices:
            vertices_list.append(vertex)

vertices_array = np.array(vertices_list, dtype=np.float32)
faces_array = np.array(faces_list, dtype=np.int32)

print(f"Saving binary NPY: {npy_path}")
np.save(npy_path, {'vertices': vertices_array, 'faces': faces_array})

print("Done!")


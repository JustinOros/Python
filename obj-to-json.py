#!/usr/bin/env python3
# Description: Convert OBJ to JSON
# Usage: python3 obj-to-json.py file.obj
# Author: Justin Oros
# Source: https://github.com/JustinOros

import json
import os
import sys

class OBJExporter:
    def __init__(self, filename):
        self.vertices = []
        self.faces = []
        self.normals = []
        self.parse(filename)

    def parse(self, filename):
        with open(filename, 'r') as f:
            for line in f:
                if line.startswith('v '):
                    parts = line.strip().split()
                    self.vertices.append(list(map(float, parts[1:4])))
                elif line.startswith('vn '):
                    parts = line.strip().split()
                    self.normals.append(list(map(float, parts[1:4])))
                elif line.startswith('f '):
                    face = []
                    for vert in line.strip().split()[1:]:
                        v_idx = vert.split('/')[0]
                        face.append(int(v_idx)-1)
                    self.faces.append(face)

    def export_to_json(self, out_filename):
        data = {
            'vertices': self.vertices,
            'faces': self.faces,
            'normals': self.normals
        }
        with open(out_filename, 'w') as f:
            json.dump(data, f)
        print(f"Exported {out_filename}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <obj-file>")
        sys.exit(1)

    obj_file = sys.argv[1]

    if not os.path.isfile(obj_file):
        print(f"File not found: {obj_file}")
        sys.exit(1)

    base_name = os.path.splitext(obj_file)[0]
    json_file = f"{base_name}.json"

    exporter = OBJExporter(obj_file)
    exporter.export_to_json(json_file)


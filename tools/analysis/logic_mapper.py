import re
import os
import hashlib
import ast
import difflib
from fuzzywuzzy import fuzz

class LogicMapper:
    def __init__(self, files):
        self.files = files
        self.all_elements = []

    def extract_elements(self, filepath):
        if not os.path.exists(filepath):
            return []

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.splitlines(keepends=True)

        results = []

        # We use AST for structural parsing where possible, but keep fallback for top-level assignments
        try:
            tree = ast.parse(content)
            for node in ast.iter_child_nodes(tree):
                name = ""
                node_type = ""
                params = ""

                if isinstance(node, ast.FunctionDef):
                    name = node.name
                    node_type = "function"
                    params = ast.unparse(node.args)
                elif isinstance(node, ast.ClassDef):
                    name = node.name
                    node_type = "class"
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            name = target.id
                            node_type = "variable"
                            params = ast.unparse(node.value)
                            break

                if name:
                    start_line = node.lineno
                    end_line = getattr(node, 'end_lineno', node.lineno)
                    source = "".join(lines[start_line-1:end_line])

                    results.append({
                        'name': name,
                        'type': node_type,
                        'line': start_line,
                        'params': params,
                        'source': source,
                        'source_hash': hashlib.md5(source.strip().encode()).hexdigest(),
                        'filepath': filepath
                    })
        except SyntaxError:
            # Fallback to regex for files with syntax errors (like evolutfinal2.py)
            pattern = re.compile(r'^(?P<indent>)(?P<type>def|class|[a-zA-Z_][a-zA-Z0-9_]*)\s*(?P<extra>.*)')
            for i, line in enumerate(lines):
                if line.startswith((' ', '\t', '\n', '#', 'import ', 'from ', 'if ', 'for ', 'while ', 'with ', 'try:', 'except')):
                    continue
                match = pattern.match(line)
                if match:
                    type_val = match.group('type')
                    extra = match.group('extra')
                    name = ""
                    node_type = ""
                    if type_val == 'def':
                        node_type = 'function'
                        name_match = re.match(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)', extra)
                        if name_match: name = name_match.group(1)
                    elif type_val == 'class':
                        node_type = 'class'
                        name_match = re.match(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)', extra)
                        if name_match: name = name_match.group(1)
                    elif '=' in line:
                        node_type = 'variable'
                        name = type_val

                    if name:
                        snippet = [line]
                        for j in range(i + 1, len(lines)):
                            if lines[j].strip() and not lines[j].startswith((' ', '\t', '#')):
                                if pattern.match(lines[j]) or lines[j].startswith(('def ', 'class ')):
                                    break
                            snippet.append(lines[j])
                        source = "".join(snippet)
                        results.append({
                            'name': name,
                            'type': node_type,
                            'line': i + 1,
                            'params': "Regex Parsed",
                            'source': source,
                            'source_hash': hashlib.md5(source.strip().encode()).hexdigest(),
                            'filepath': filepath
                        })
        return results

    def find_orphans(self, filepath, elements):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        covered = [False] * len(lines)
        for el in elements:
            if el['filepath'] == filepath:
                start = el['line'] - 1
                length = len(el['source'].splitlines())
                for i in range(start, min(start + length, len(lines))):
                    covered[i] = True
        orphans = []
        curr = []
        start = 0
        for i, line in enumerate(lines):
            if not covered[i]:
                if not curr: start = i + 1
                curr.append(line)
            else:
                if curr:
                    if "".join(curr).strip() and not all(l.strip().startswith(('#', 'import ', 'from ')) or not l.strip() for l in curr):
                        orphans.append((start, "".join(curr)))
                    curr = []
        if curr and "".join(curr).strip():
            orphans.append((start, "".join(curr)))
        return orphans

    def generate_report(self, output_path):
        for f in self.files:
            self.all_elements.extend(self.extract_elements(f))

        by_name = {}
        for el in self.all_elements:
            name = el['name']
            if name not in by_name: by_name[name] = []
            by_name[name].append(el)

        families = []
        processed = set()
        names = sorted(by_name.keys())
        for name in names:
            if name in processed: continue
            fam = [name]
            processed.add(name)
            for other in names:
                if other in processed: continue
                if (len(name) > 5 and name in other) or (len(other) > 5 and other in name) or fuzz.ratio(name, other) > 85:
                    fam.append(other)
                    processed.add(other)
            families.append(fam)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# MASTER VARIANTS REPORT\n\n")
            for fam in families:
                f.write(f"## FAMILLE : `{fam[0]}`\n")
                all_v = []
                for n in fam: all_v.extend(by_name[n])
                groups = {}
                for v in all_v:
                    h = v['source_hash']
                    if h not in groups: groups[h] = []
                    groups[h].append(v)
                for idx, h in enumerate(groups.keys()):
                    primary = groups[h][0]
                    f.write(f"### VARIANTE {idx+1} ({h})\n")
                    f.write("Sources: " + ", ".join([f"`{v['filepath']}` (L{v['line']})" for v in groups[h]]) + "\n")
                    f.write("```python\n" + primary['source'] + "\n```\n")

            f.write("# ORPHANS AND INSTRUCTIONS\n")
            for file in self.files:
                f.write(f"## File: {file}\n")
                for line, content in self.find_orphans(file, self.all_elements):
                    f.write(f"### L{line}\n```text\n{content}\n```\n")

if __name__ == "__main__":
    mapper = LogicMapper(['evolutfinal2.py', 'evolutfini3', 'evoluut.py'])
    mapper.generate_report('reports/MASTER_VARIANTS_REPORT.md')

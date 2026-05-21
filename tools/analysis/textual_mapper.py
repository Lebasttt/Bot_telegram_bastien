import re
import os
import hashlib
from fuzzywuzzy import fuzz

def get_status(source):
    source_lower = source.lower()
    source_upper = source.upper()
    status = "Opérationnel"
    if "log(\"stub" in source_lower or "log(f\"stub" in source_lower or "STUB" in source_upper:
        status = "Stub (Simulé / Non-implémenté)"
    elif "pass" in source.split():
        if len(source.splitlines()) < 8:
            status = "Squelette vide (pass)"
        else:
            status = "Implémentation partielle"
    if "simulation" in source_lower or "mock" in source_lower:
        status = "Simulé / Test"
    return status

def get_tools(source):
    tools = set()
    tool_list = ['sqlite3', 'pandas', 'numpy', 'requests', 'httpx', 'playwright', 'spacy', 'nltk', 'scikit-learn', 'psutil', 'networkx', 'statsmodels', 'scipy', 'orjson', 'json', 'pickle', 'jinja2', 'sentence_transformer', 'umap', 'dbscan', 'isolationforest', 'gputil', 'GPUtil', 'matplotlib', 'seaborn', 'libcst', 'black', 'isort', 'shlex', 'cryptography', 'tenacity', 'filelock', 'schedule', 'asyncio']
    for t in tool_list:
        if t.lower() in source.lower():
            tools.add(t)
    return sorted(list(tools))

def get_calls(source):
    calls = set(re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\(', source))
    ignored = {'def', 'if', 'for', 'while', 'print', 'log', 'len', 'range', 'list', 'dict', 'set', 'str', 'int', 'float', 'bool', 'append', 'split', 'replace', 'strip', 'join', 'open', 'read', 'write', 'close', 'enumerate', 'zip', 'getattr', 'setattr', 'hasattr', 'type', 'isinstance', 'self', 'super', 'min', 'max', 'sum', 'sorted', 'any', 'all', 'format', 'time', 'sleep', 'abs', 'round', 'now', 'strftime'}
    return sorted([c for c in calls if c not in ignored and len(c) > 2])[:20]

def normalize_logic(source):
    # Aggressive normalization for comparison: remove comments, docstrings, quotes, spaces, and non-ascii
    source = re.sub(r'#.*$', '', source, flags=re.MULTILINE)
    source = source.replace("'", '"')
    source = source.encode('ascii', 'ignore').decode('ascii')
    source = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
    source = re.sub(r"'''.*?'''", '', source, flags=re.DOTALL)
    return "".join(source.split())

def extract_surgical(filepath):
    results = {}
    if not os.path.exists(filepath): return results
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # Matching top level elements (indent 0)
    # def, class, and large variable blocks
    pattern = re.compile(r'^(?P<indent>)(?P<type>def|class|[a-zA-Z_][a-zA-Z0-9_]*)\s*(?P<extra>.*)')

    for i, line in enumerate(lines):
        if line.startswith((' ', '\t', '\n', '#', 'import ', 'from ', 'if ', 'for ', 'try:', 'except', 'return', 'raise', 'yield')):
            continue

        match = pattern.match(line)
        if match:
            t_val = match.group('type')
            extra = match.group('extra')
            name = ""
            node_type = ""

            if t_val == 'def':
                node_type = 'Fonction'
                name_match = re.match(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)', extra)
                if name_match: name = name_match.group(1)
            elif t_val == 'class':
                node_type = 'Classe'
                name_match = re.match(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)', extra)
                if name_match: name = name_match.group(1)
            elif '=' in line:
                node_type = 'Variable'
                name = t_val

            if name:
                snippet = [line]
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith((' ', '\t', '#')):
                        if pattern.match(lines[j]) or lines[j].startswith(('def ', 'class ')):
                            break
                    snippet.append(lines[j])
                source = "".join(snippet)

                results[name] = {
                    'name': name,
                    'type': node_type,
                    'tools': get_tools(source),
                    'calls': get_calls(source),
                    'status': get_status(source),
                    'purpose': (re.search(r'"""(.*?)"""', source, re.DOTALL).group(1).strip().split('\n')[0] if re.search(r'"""(.*?)"""', source, re.DOTALL) else "Non documenté"),
                    'normalized': normalize_logic(source),
                    'line': i + 1,
                    'filepath': filepath,
                    'raw': source
                }
    return results

def find_instructions(filepath):
    # Specifically extract large comment blocks or directive-heavy sections
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Directives are often in comments or standalone strings
    directives = []

    # Find refactoring specifications
    refac = re.findall(r'(Spécification de refactoring.*?)#', content, re.DOTALL | re.IGNORECASE)
    if refac: directives.append(("Refactoring Spec", refac[0]))

    # Find plachebor instructions
    plache = re.findall(r'(Commentaire "plachebor".*?)Code simuler', content, re.DOTALL | re.IGNORECASE)
    if plache: directives.append(("Gestion Plachebor", plache[0]))

    # Find language matrix
    matrix = re.findall(r'(UNIVERSAL_LANGUAGES = \{.*?\}\n)', content, re.DOTALL)
    if matrix: directives.append(("Matrice Polyglotte", "Mapping de 70+ langages avec leurs commandes dangereuses (trop large pour affichage textuel complet ici)"))

    return directives

files = ['evolutfinal2.py', 'evolutfini3', 'evoluut.py']
scripts_data = {f: extract_surgical(f) for f in files}

all_names = sorted(list(set([name for f in files for name in scripts_data[f].keys()])))

by_family = {}
processed = set()
for name in all_names:
    if name in processed: continue
    fam = [name]
    processed.add(name)
    for other in all_names:
        if other in processed: continue
        type_a = next(scripts_data[f][name]['type'] for f in files if name in scripts_data[f])
        type_b = next(scripts_data[f][other]['type'] for f in files if other in scripts_data[f])
        if type_a == type_b:
            if (len(name) > 5 and name in other) or (len(other) > 5 and other in name) or fuzz.ratio(name, other) > 90:
                fam.append(other)
                processed.add(other)
    by_family[name] = fam

with open('SURGICAL_TEXTUAL_MAP.txt', 'w', encoding='utf-8') as f:
    f.write("============================================================\n")
    f.write("       CARTE CHIRURGICALE DE L'AGENT EVOLUTION (v1.2)\n")
    f.write("============================================================\n\n")
    f.write("RAPPORT ZÉRO CODE - ANALYSE SÉMANTIQUE - DOUBLONS ÉLIMINÉS\n")
    f.write("Chaque composant a été comparé chirurgicalement entre les scripts.\n\n")

    for root_name in sorted(by_family.keys()):
        family = by_family[root_name]
        type_label = scripts_data[next(s for s in files if root_name in scripts_data[s])][root_name]['type']

        f.write(f"[{type_label.upper()}] : {root_name}\n")
        if len(family) > 1:
            f.write(f"Variantes de noms : {', '.join(family[1:])}\n")

        unique_versions = []
        for fname in family:
            for s in files:
                if fname in scripts_data[s]:
                    item = scripts_data[s][fname]
                    found = False
                    for uv in unique_versions:
                        if item['normalized'] == uv['norm']:
                            uv['files'].append(f"{s} (L{item['line']})")
                            found = True
                            break
                    if not found:
                        unique_versions.append({
                            'data': item,
                            'norm': item['normalized'],
                            'files': [f"{s} (L{item['line']})"]
                        })

        for idx, uv in enumerate(unique_versions):
            item = uv['data']
            # If multiple unique versions for the same family, label them
            ver_prefix = f"--- Version {idx+1}" if len(unique_versions) > 1 else "--- Détails"
            f.write(f"{ver_prefix} : {', '.join(uv['files'])}\n")
            if item['purpose'] != "Non documenté" and item['purpose'] != "N/A":
                f.write(f"    Mission : {item['purpose']}\n")
            f.write(f"    Statut  : {item['status']}\n")
            if item['tools']:
                f.write(f"    Outils  : {', '.join(item['tools'])}\n")
            if item['calls']:
                f.write(f"    Appels  : {', '.join(item['calls'])}\n")

        f.write("\n" + "-"*60 + "\n\n")

    f.write("============================================================\n")
    f.write("      INSTRUCTIONS CRITIQUES ET DIRECTIVES D'ÉVOLUTION\n")
    f.write("============================================================\n\n")

    for s in files:
        instr = find_instructions(s)
        if instr:
            f.write(f"SCRIPT : {s}\n")
            for title, content in instr:
                f.write(f"  > {title} :\n")
                # Indent content
                indented = "    " + content.strip().replace('\n', '\n    ')
                f.write(f"{indented}\n\n")

print("Rapport parfait (v1.2) généré.")

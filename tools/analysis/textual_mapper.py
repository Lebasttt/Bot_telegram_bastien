import re
import os
import hashlib
from fuzzywuzzy import fuzz

def get_status(source):
    source_lower = source.lower()
    source_upper = source.upper()
    status = "Opérationnel"
    if "log(\"stub" in source_lower or "log(f\"stub" in source_lower or "STUB" in source_upper:
        status = "Stub (Simulé)"
    elif "pass" in source.split():
        if len(source.splitlines()) < 8:
            status = "Squelette vide"
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
    return sorted([c for c in calls if c not in ignored and len(c) > 2])

def normalize_logic(source):
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
                    'name': name, 'type': node_type, 'tools': get_tools(source),
                    'calls': get_calls(source), 'status': get_status(source),
                    'purpose': (re.search(r'"""(.*?)"""', source, re.DOTALL).group(1).strip().split('\n')[0] if re.search(r'"""(.*?)"""', source, re.DOTALL) else "Non documenté"),
                    'normalized': normalize_logic(source), 'line': i + 1, 'filepath': filepath, 'raw': source
                }
    return results

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

with open('reports/SURGICAL_TEXTUAL_MAP.txt', 'w', encoding='utf-8') as f:
    f.write("============================================================\n")
    f.write("   CARTE CHIRURGICALE DE L'AGENT EVOLUTION (ULTRA-CLEAN)\n")
    f.write("============================================================\n\n")
    f.write("RAPPORT ZÉRO CODE - ZÉRO REDONDANCE - ANALYSE DES DELTAS\n\n")

    for root_name in sorted(by_family.keys()):
        family = by_family[root_name]
        type_label = scripts_data[next(s for s in files if root_name in scripts_data[s])][root_name]['type']
        aliases = [a for a in family if a != root_name]
        alias_str = f" (alias: {', '.join(aliases)})" if aliases else ""
        f.write(f"[{type_label.upper()}] : {root_name}{alias_str}\n")
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
                        unique_versions.append({'data': item, 'norm': item['normalized'], 'files': [f"{s} (L{item['line']})"]})
        pillar = unique_versions[0]['data']
        f.write(f"--- Version pilier (base commune)\n")
        f.write(f"    Mission : {pillar['purpose']}\n")
        f.write(f"    Statut  : {pillar['status']}\n")
        f.write(f"    Outils  : {', '.join(pillar['tools']) if pillar['tools'] else 'Aucun'}\n")
        f.write(f"    Appels  : {', '.join(pillar['calls'][:15]) if pillar['calls'] else 'Aucun'}\n")
        for idx, uv in enumerate(unique_versions[1:]):
            item = uv['data']
            f.write(f"--- Variante {idx+1} : {', '.join(uv['files'])}\n")
            deltas = []
            if item['status'] != pillar['status']: deltas.append(f"Statut : {item['status']}")
            new_tools = set(item['tools']) - set(pillar['tools'])
            rem_tools = set(pillar['tools']) - set(item['tools'])
            if new_tools: deltas.append(f"Ajout outils: {', '.join(new_tools)}")
            if rem_tools: deltas.append(f"Retrait outils: {', '.join(rem_tools)}")
            new_calls = set(item['calls']) - set(pillar['calls'])
            rem_calls = set(pillar['calls']) - set(item['calls'])
            substitutions = []
            for rc in list(rem_calls):
                for nc in list(new_calls):
                    if fuzz.ratio(rc, nc) > 70 or (rc in nc) or (nc in rc):
                        substitutions.append(f"Remplace `{rc}` par `{nc}`")
                        rem_calls.remove(rc)
                        new_calls.remove(nc)
                        break
            if substitutions: deltas.extend(substitutions)
            if new_calls: deltas.append(f"Nouveaux appels: {', '.join(list(new_calls)[:5])}")
            if rem_calls: deltas.append(f"Appels retirés: {', '.join(list(rem_calls)[:5])}")
            if not deltas: deltas.append("Modification de la logique interne (conditions/boucles) sans changement d'outils ou d'appels externes")
            for d in deltas: f.write(f"    Modification : {d}\n")
        identical_to_pillar = unique_versions[0]['files'][1:]
        if identical_to_pillar:
            f.write(f"--- Versions identiques au pilier : {', '.join(identical_to_pillar)}\n")
            f.write(f"    Utilise la version pilier sans modification.\n")
        f.write("\n" + "-"*60 + "\n\n")
    f.write("============================================================\n   INSTRUCTIONS CRITIQUES ET FRAGMENTS ORPHELINS\n============================================================\n\nDIRECTIVE : Remplacement lsof (evoluut.py)\n    Instruction : Ne plus utiliser 'lsof'. Remplacer par psutil.Process().open_files().\n\nDIRECTIVE : Remplacement causalnex (evoluut.py)\n    Instruction : Remplacer par networkx (graphes), statsmodels (régressions) et scipy.stats.\n\nGESTION : Plachebor (evoluut.py)\n    Instruction : Les commentaires 'plachebor' sont des tâches à coder. Une fois fait, supprimer le commentaire.\n\nLOGIQUE : Matrice Polyglotte (evolutfini3)\n    Donnée : Mapping de 70+ langages (Haskell, Solidity, Go, Java, etc.) avec extensions et commandes dangereuses.\n\nFIN DU RAPPORT.\n")

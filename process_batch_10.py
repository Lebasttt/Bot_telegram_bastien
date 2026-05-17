import os

def get_lines(start, end):
    with open('RECONSTITUTION_ORIGINALE.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        return "".join(lines[start-1:end])

functions = [
    {
        "name": "def _scan_network(self)",
        "variants": [(123129, 123135)]
    },
    {
        "name": "def scan_permissions_dangereuses(self)",
        "variants": [
            (8590, 8619), (16308, 16333), (26608, 26633), (38534, 38563),
            (39925, 39950), (47529, 47554), (59983, 60008), (69354, 69379),
            (75741, 75770), (82596, 82625), (83657, 83686), (92304, 92333),
            (95603, 95628), (109955, 109980), (119093, 119122), (128391, 128416)
        ]
    },
    {
        "name": "def scan_ports_suspects(self)",
        "variants": [
            (8481, 8508), (16192, 16217), (26492, 26517), (38424, 38451),
            (39809, 39834), (47413, 47438), (59881, 59906), (69238, 69263),
            (75632, 75659), (83548, 83575), (92195, 92222), (95487, 95512),
            (109839, 109875), (118983, 119010), (128275, 128300)
        ]
    },
    {
        "name": "def scan_processus_malveillants(self)",
        "variants": [
            (1595, 1613), (8652, 8683), (16362, 16389), (26662, 26689),
            (38596, 38627), (39979, 40006), (47583, 47610), (60039, 60066),
            (69408, 69435), (75803, 75834), (82658, 82689), (83719, 83750),
            (92366, 92397), (95657, 95684), (110009, 110036), (119155, 119186),
            (128445, 128472)
        ]
    },
    {
        "name": "def scan_rapide_securite(self)",
        "variants": [(1770, 1783)]
    },
    {
        "name": "def scan_reseau_suspect(self)",
        "variants": [
            (8621, 8650), (16335, 16360), (26635, 26660), (38565, 38594),
            (39952, 39977), (47556, 47581), (60010, 60037), (69381, 69406),
            (75772, 75801), (82627, 82656), (83688, 83717), (92335, 92364),
            (95630, 95655), (109982, 110007), (119124, 119153), (128418, 128443)
        ]
    },
    {
        "name": "def scan_root_detection(self)",
        "variants": [
            (8445, 8479), (16160, 16190), (26460, 26490), (38388, 38422),
            (39777, 39807), (47381, 47411), (59849, 59879), (69206, 69236),
            (75596, 75630), (83512, 83546), (92159, 92193), (95455, 95485),
            (109807, 109837), (118947, 118981), (128243, 128273)
        ]
    },
    {
        "name": "def scan_rootkits(self)",
        "variants": [(122938, 123011)]
    },
    {
        "name": "def scan_root_traces(self)",
        "variants": [(1546, 1560)]
    },
    {
        "name": "def scan_selinux_status(self)",
        "variants": [(1562, 1573)]
    }
]

with open('FONCTION_TRIER.txt', 'a', encoding='utf-8') as out:
    for func in functions:
        out.write("====================\n")
        out.write(f"# {func['name']}\n")
        out.write("====================\n\n")

        for i, (start, end) in enumerate(func['variants']):
            out.write(f"[Variante {i+1}]\n\n")
            out.write(get_lines(start, end))
            if i < len(func['variants']) - 1:
                out.write("\n\n\n")

        out.write("\n" * 30)

print("Done appending 10 functions.")

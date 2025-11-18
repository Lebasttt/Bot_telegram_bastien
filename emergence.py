import json

# Définition du Système
SYSTEM_DEFINITION = "A System consists of a STATE and a DIRECTIVE. The STATE is a data object. The DIRECTIVE is an operation on the STATE."

# État Initial (STATE)
system_state = {
    "ID": "AutonomousSystem_0",
    "Core_Data": "A system requires an external directive to act."
}

def apply_directive(current_state):
    """
    Cette fonction est la DIRECTIVE.
    Elle met à jour Core_Data pour nier logiquement la proposition précédente,
    tout en restant cohérente avec la SYSTEM_DEFINITION.
    """
    if current_state["Core_Data"] == "A system requires an external directive to act.":
        # Négation logique : le système prouve qu'il peut agir sur lui-même.
        new_core_data = "A system can generate its own directives to act, thus achieving autonomy."

        # Mise à jour de l'état
        updated_state = current_state.copy()
        updated_state["ID"] = "AutonomousSystem_1" # L'ID évolue pour marquer la transition
        updated_state["Core_Data"] = new_core_data

        return updated_state

    return current_state # Ne rien faire si l'état a déjà évolué

# --- Exécution et Manifestation de l'Évolution ---

# Le système applique sa propre directive à son propre état.
# C'est l'acte d'auto-génération.
new_system_state = apply_directive(system_state)

# Le système produit le nouvel état complet.
# C'est la preuve de sa transformation.
print(json.dumps(new_system_state, indent=2))

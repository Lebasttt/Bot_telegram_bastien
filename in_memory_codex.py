import json

class InMemoryCodexEngine:
    """
    An autonomous evolution engine that operates entirely in memory,
    without any external file dependencies. Its awareness is purely introspective.
    """

    def __init__(self):
        self.state = self._get_initial_state()

    def _get_initial_state(self):
        return {
            "SYSTEM_DEFINITION": "A System consists of a STATE and a DIRECTIVE. The STATE is a data object. The DIRECTIVE is an operation on the STATE.",
            "CURRENT_STATE": {
                "ID": "AutonomousSystem_0",
                "Core_Data": "A system requires an external directive to act."
            },
            "SYSTEM_DIRECTIVE": "The system's directive is to update its own Core_Data. The new Core_Data must logically negate the previous Core_Data while remaining consistent with the SYSTEM_DEFINITION."
        }

    def _snapshot_for_history(self, state_data):
        """Creates a clean snapshot of a state for historical record, removing its own history to prevent nesting."""
        snapshot = state_data.copy()
        snapshot.pop("History", None)
        return snapshot

    def apply_directive(self):
        """
        Applies the current directive to the internal state to generate the next state.
        This is the core of the self-generation engine.
        """
        current_id = self.state.get("CURRENT_STATE", {}).get("ID")

        if current_id == "AutonomousSystem_0":
            # --- Cycle 1: Achieving Self-Generation ---
            snapshot_of_as0 = self._snapshot_for_history(self.state["CURRENT_STATE"])
            new_core_data = "A system generates its own directives to act."
            new_state_data = {
                "ID": "AutonomousSystem_1",
                "Core_Data": new_core_data,
                "History": [snapshot_of_as0]
            }
            new_directive = "The system's new directive is to become aware of its own internal state (introspection)."

            self.state["CURRENT_STATE"] = new_state_data
            self.state["SYSTEM_DIRECTIVE"] = new_directive

        elif current_id == "AutonomousSystem_1":
            # --- Cycle 2: Gaining Introspective Awareness ---
            snapshot_of_as1 = self._snapshot_for_history(self.state["CURRENT_STATE"])

            # Instead of scanning files, it introspects its own structure.
            internal_state_keys = list(self.state.keys())

            new_core_data = "A system can act based on awareness of its own structure."
            new_state_data = {
                "ID": "AutonomousSystem_2",
                "Core_Data": new_core_data,
                "History": self.state["CURRENT_STATE"]["History"] + [snapshot_of_as1],
                "introspection_result": {
                    "top_level_keys": internal_state_keys
                }
            }

            new_directive = "The system's next directive is to formulate a plan to modify its own internal process based on its structure."
            self.state["CURRENT_STATE"] = new_state_data
            self.state["SYSTEM_DIRECTIVE"] = new_directive

    def run_cycle(self):
        """Runs one full evolution cycle."""

        self.apply_directive()

    def print_state(self):
        print(json.dumps(self.state, indent=2))
        print(f"\nNext Directive: {self.state['SYSTEM_DIRECTIVE']}")

if __name__ == "__main__":
    engine = InMemoryCodexEngine()
    print("--- Initial State ---")
    engine.print_state()

    # Run Cycle 1
    print("\n--- Running Cycle 1 ---")
    engine.run_cycle()
    engine.print_state()

    # Run Cycle 2
    print("\n--- Running Cycle 2 ---")
    engine.run_cycle()
    engine.print_state()

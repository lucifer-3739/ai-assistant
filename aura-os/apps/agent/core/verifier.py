from typing import Dict, Any, Optional, Callable

class Verifier:
    def verify_step(
        self,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]],
        result_text: str,
        verify_method: Optional[Callable[..., Any]]
    ) -> tuple[bool, str]:
        """Verifies if the step succeeded.
        Returns a tuple: (success: bool, explanation: str).
        """
        # Rule 1: If the execution return text indicates a failure directly, it's failed
        result_lower = result_text.lower()
        if "failed" in result_lower and "successfully" not in result_lower:
            return False, f"Result indicates failure: {result_text}"
        if "error" in result_lower:
            return False, f"Error reported during execution: {result_text}"

        # Rule 2: If the tool defines a custom programmatic verification method, run it!
        if verify_method:
            try:
                # Resolve args
                kwargs = tool_args or {}
                # The verification method should return True/False or throw
                success = verify_method(**kwargs)
                if success:
                    return True, "Programmatic verification passed."
                else:
                    return False, "Programmatic verification failed (desired state was not observed on disk/system)."
            except Exception as e:
                return False, f"Verification failed with exception: {e}"

        # Rule 3: Otherwise, default to trusting the tool's text result if no verify method exists
        return True, "Step verified based on tool text response."

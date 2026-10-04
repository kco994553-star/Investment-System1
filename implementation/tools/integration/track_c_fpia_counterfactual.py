"""COUNTERFACTUAL_CODE_IDENTITY_NORMALISED profile helper (FAIL-ONLY evidence; CDR-014 §1/§2).

Loaded only by the hardened child for the counterfactual ``main_block`` profile. It rebinds the
discovered code-identity sites (and the names that importers bound from them) to the values of a
reference tree, in memory, so the unmodified Track C computations can be compared with the
reference. A mismatch is integration interference; a match never upgrades CODE_IDENTITY (which stays
DIVERGED when the trees differ) and is never an equality claim. This is the only FPIA module that
rebinds attributes of imported modules.
"""
import importlib


def apply_pins(pins):
    applied = []
    for pin in pins:
        module = importlib.import_module(pin["module"])
        value = pin["value"]
        if pin["kind"] == "call":
            replacement = (lambda v: (lambda: v))(value)
        else:
            replacement = value
        setattr(module, pin["name"], replacement)
        applied.append(pin["module"] + ":" + pin["name"])
        for importer, local in pin.get("importers", []):
            target = importlib.import_module(importer)
            setattr(target, local, replacement)
            applied.append(importer + ":" + local)
    return applied

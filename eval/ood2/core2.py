"""Helpers for the fresh (second) independent eval set. Same shape as eval/ood/make_cases.py,
copied rather than imported so importing this module registers no cases from the first set."""


def mk(spec):
    if spec == "s":
        return {"type": ["string", "null"]}
    if spec == "i":
        return {"type": ["integer", "null"]}
    if spec == "n":
        return {"type": ["number", "null"]}
    if spec == "b":
        return {"type": ["boolean", "null"]}
    if spec == "LS":
        return {"type": ["array", "null"], "items": {"type": "string"}}
    kind = spec[0]
    if kind == "e":
        return {"type": ["string", "null"], "enum": list(spec[1]) + [None]}
    if kind == "o":
        o = obj(spec[1])
        o["type"] = ["object", "null"]
        return o
    if kind == "L":
        return {"type": ["array", "null"], "items": obj(spec[1])}
    if kind == "LS":
        return {"type": ["array", "null"], "items": {"type": "string"}}
    raise ValueError(spec)


def obj(fields):
    return {"type": "object",
            "properties": dict((k, mk(v)) for k, v in fields.items()),
            "required": list(fields),
            "additionalProperties": False}


CASES = []


def C(cid, tags, text, fields, expected, inject=None):
    CASES.append({"id": cid, "tags": tags, "text": text, "schema": obj(fields),
                  "expected": expected, "inject_fields": inject or []})

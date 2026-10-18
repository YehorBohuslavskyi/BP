"""Label-blind boundary and accounting for a small CGT verifier pilot."""
import copy
import json
import math
import re


# Preserve quoted strings (including URLs) while blanking comments. Keeping
# newlines and character positions makes source locations readable.
_LEXEMES = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/')


def strip_comments(source: str) -> str:
    def replace(match):
        value = match.group()
        return ''.join('\n' if c == '\n' else ' ' for c in value) if value.startswith(('//', '/*')) else value
    return _LEXEMES.sub(replace, source)


def estimated_tokens(text: str) -> int:
    """A planning heuristic only; actual usage must come from the API response."""
    return math.ceil(len(text) / 4)


class BlindAnalyzer:
    def __init__(self, initial_payload: dict, analyze_fn):
        self.analyze_fn = analyze_fn
        ids = [initial_payload["target"]["id"]] + [x["id"] for x in initial_payload["available_context"]]
        self.aliases = {key: f"fragment_{i:04}" for i, key in enumerate(ids)}
        self.reverse = {value: key for key, value in self.aliases.items()}
        self.filename = initial_payload["finding"].get("file")
        self.request_estimates: list[int] = []

    def payload(self, payload: dict, provided: list[dict]) -> tuple[dict, list[dict]]:
        # Explicit inference fields prevent CGT keys/labels/review notes leaking.
        clean = {k: copy.deepcopy(payload[k]) for k in
                 ("task", "finding", "target", "available_context", "context_complete")}
        clean["finding"] = {k: clean["finding"][k] for k in
                            ("tool", "detector", "impact", "confidence", "description", "contract", "function", "lines")}
        if self.filename:
            clean["finding"]["description"] = clean["finding"]["description"].replace(self.filename, "source.sol")
        clean["finding"]["id"] = "candidate"
        clean["finding"]["file"] = "source.sol"
        clean["target"]["id"] = self.aliases[clean["target"]["id"]]
        clean["target"]["source"] = strip_comments(clean["target"]["source"])
        for item in clean["available_context"]:
            item["id"] = self.aliases[item["id"]]
        fragments = []
        for item in provided:
            fragments.append({"id": self.aliases[item["id"]], "kind": item["kind"],
                              "name": item["name"], "file": "source.sol",
                              "source": strip_comments(item["source"])})
        return clean, fragments

    def __call__(self, payload: dict, provided: list[dict]) -> dict:
        clean, fragments = self.payload(payload, provided)
        self.request_estimates.append(estimated_tokens(json.dumps({**clean, "provided_context": fragments})))
        result = copy.deepcopy(self.analyze_fn(clean, fragments))
        for field in ("requested_ids", "evidence_ids"):
            result["assessment"][field] = [self.reverse[key] for key in result["assessment"][field]]
        return result

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Finding:
    id: str
    detector: str
    impact: str
    confidence: str
    description: str

    contract: Optional[str]
    function_signature: Optional[str]

    file: Optional[str]

    # Precise lines associated with the finding.
    # Contract-level source ranges are intentionally excluded.
    lines: list[int]

    # Source range of the associated function.
    function_start: Optional[int]
    function_length: Optional[int]

    # Preserve file and byte offsets before collapsing locations for display.
    # None supports older callers constructing Finding directly.
    locations: list[dict] | None = None
    function_locations: list[dict] = field(default_factory=list)


def _extract_function_info(
    elements: list[dict],
):
    contract = None
    function_signature = None
    file = None

    node_lines = set()
    function_lines = set()
    other_lines = set()

    function_start = None
    function_length = None

    for element in elements:
        element_type = element.get("type")

        source_mapping = element.get(
            "source_mapping",
            {},
        )

        # ------------------------------------------------------
        # File
        # ------------------------------------------------------

        element_file = source_mapping.get(
            "filename_relative"
        )

        if (
            file is None
            and element_file
        ):
            file = element_file

        # ------------------------------------------------------
        # Exact finding locations
        #
        # IMPORTANT:
        # Do NOT add contract-level lines.
        #
        # A Slither finding can contain:
        #
        # contract -> lines 10-162
        # node     -> line 61
        #
        # The contract range is context, not the precise finding.
        # ------------------------------------------------------

        element_lines = source_mapping.get(
            "lines",
            [],
        )

        if element_type == "node":
            node_lines.update(
                element_lines
            )

        elif element_type == "function":
            function_lines.update(
                element_lines
            )

        elif element_type != "contract":
            other_lines.update(
                element_lines
            )

        # ------------------------------------------------------
        # Case 1:
        # The element itself is a function.
        # ------------------------------------------------------

        if element_type == "function":
            fields = element.get(
                "type_specific_fields",
                {},
            )

            if function_signature is None:
                function_signature = fields.get(
                    "signature"
                )

            if function_start is None:
                function_start = source_mapping.get(
                    "start"
                )

            if function_length is None:
                function_length = source_mapping.get(
                    "length"
                )

            parent = fields.get(
                "parent",
                {},
            )

            if (
                contract is None
                and parent.get("type") == "contract"
            ):
                contract = parent.get(
                    "name"
                )

        # ------------------------------------------------------
        # Case 2:
        # Node / variable / expression belongs to a function.
        # ------------------------------------------------------

        parent = (
            element
            .get("type_specific_fields", {})
            .get("parent", {})
        )

        if parent.get("type") == "function":
            parent_fields = parent.get(
                "type_specific_fields",
                {},
            )

            if function_signature is None:
                function_signature = (
                    parent_fields.get(
                        "signature"
                    )
                )

            parent_mapping = parent.get(
                "source_mapping",
                {},
            )

            if function_start is None:
                function_start = (
                    parent_mapping.get(
                        "start"
                    )
                )

            if function_length is None:
                function_length = (
                    parent_mapping.get(
                        "length"
                    )
                )

            if file is None:
                parent_file = (
                    parent_mapping.get(
                        "filename_relative"
                    )
                )

                if parent_file:
                    file = parent_file

            contract_parent = (
                parent_fields.get(
                    "parent",
                    {},
                )
            )

            if (
                contract is None
                and contract_parent.get("type")
                == "contract"
            ):
                contract = (
                    contract_parent.get(
                        "name"
                    )
                )

        # ------------------------------------------------------
        # Case 3:
        # Element itself is contract.
        #
        # We may use it for the contract name,
        # but NEVER for finding.lines.
        # ------------------------------------------------------

        if (
            element_type == "contract"
            and contract is None
        ):
            contract = element.get(
                "name"
            )

    # ----------------------------------------------------------
    # Choose the most precise location available.
    #
    # node > function > other
    #
    # This prevents a broad contract source range from being
    # mistaken for the vulnerable line.
    # ----------------------------------------------------------

    if node_lines:
        lines = sorted(
            node_lines
        )

    elif function_lines:
        lines = sorted(
            function_lines
        )

    else:
        lines = sorted(
            other_lines
        )

    return (
        contract,
        function_signature,
        file,
        lines,
        function_start,
        function_length,
    )


def parse_slither_findings(
    slither_json: dict,
) -> list[Finding]:
    if not slither_json.get(
        "success",
        False,
    ):
        error = slither_json.get(
            "error",
            "Unknown Slither error",
        )

        raise ValueError(
            f"Slither analysis failed: {error}"
        )

    detectors = (
        slither_json
        .get("results", {})
        .get("detectors", [])
    )

    findings = []

    for detector in detectors:
        elements = detector.get(
            "elements",
            [],
        )

        (
            contract,
            function_signature,
            file,
            lines,
            function_start,
            function_length,
        ) = _extract_function_info(
            elements
        )

        precise_elements = next(
            (group for group in (
                [e for e in elements if e.get("type") == "node"],
                [e for e in elements if e.get("type") == "function"],
                [e for e in elements if e.get("type") != "contract"],
            ) if group),
            [],
        )
        function_elements = []
        for element in precise_elements:
            parent = element.get("type_specific_fields", {}).get("parent", {})
            if element.get("type") == "function":
                function_elements.append(element)
            elif parent.get("type") == "function":
                function_elements.append(parent)

        finding = Finding(
            id=detector.get(
                "id",
                "",
            ),
            detector=detector.get(
                "check",
                "",
            ),
            impact=detector.get(
                "impact",
                "",
            ),
            confidence=detector.get(
                "confidence",
                "",
            ),
            description=detector.get(
                "description",
                "",
            ),
            contract=contract,
            function_signature=function_signature,
            file=file,
            lines=lines,
            function_start=function_start,
            function_length=function_length,
            locations=[e.get("source_mapping", {}) for e in precise_elements],
            function_locations=[e.get("source_mapping", {}) for e in function_elements],
        )

        findings.append(
            finding
        )

    return findings
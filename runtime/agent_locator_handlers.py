from __future__ import annotations

"""Focused DOM and locator handler seam extracted from AgentLoop tool methods."""

from typing import Any, Callable

from runtime.dom_locator_contract import rank_locator_candidates, scope_candidates, validate_locator_candidate
from runtime.page_intelligence import build_page_intelligence_packet


async def tool_dom_extract(loop: Any, args: dict[str, Any], *, get_page: Callable[[], Any]) -> dict[str, Any]:
    page = get_page()
    scope = str(args.get("scope") or "page").strip() or "page"
    html = ""
    page_title = ""

    if scope == "page":
        html = await page.content()
    else:
        html = await page.evaluate(
            """
            ({ scope }) => {
              const node = document.querySelector(scope);
              return node ? node.outerHTML : "";
            }
            """,
            {"scope": scope},
        )

    try:
        page_title = str(await page.title() or "")
    except Exception:  # noqa: BLE001
        page_title = ""

    cleaned = loop._clean_markup(html)[:3000]
    try:
        packet = build_page_intelligence_packet(
            html=html,
            url=page.url,
            title=page_title,
        )
        compact_summary = packet.to_compact_summary()
        return {
            "elements": compact_summary,
            "url": page.url,
            "page_intelligence": {
                "headings": list(packet.headings[:5]),
                "ctas": list(packet.ctas[:8]),
                "forms_count": int(packet.forms_count),
                "inputs": list(packet.inputs[:5]),
                "semantic_quality": packet.semantic_quality,
                "ambiguities": list(packet.ambiguities[:3]),
                "risk_flags": list(packet.risk_flags[:3]),
                "sections": list(packet.sections[:5]),
            },
            "_raw_elements": cleaned,
        }
    except Exception:
        return {"elements": cleaned, "url": page.url}


async def tool_locator_find(loop: Any, args: dict[str, Any], *, get_page: Callable[[], Any]) -> dict[str, Any]:
    page = get_page()
    element_data = args.get("element_data") or {}
    candidates = loop._build_locator_candidates(element_data)
    tried: list[dict[str, Any]] = []

    raw_candidates = list(element_data.get("candidates") or [])
    target_text = str(element_data.get("text") or element_data.get("name") or "")
    ranked = rank_locator_candidates(candidates=raw_candidates, target_text=target_text or None)

    for candidate in candidates:
        locator_string = candidate["locator"]
        strategy = candidate["strategy"]

        try:
            locator = loop._resolve_locator(page, locator_string)
            count = await locator.count()
        except Exception as exc:  # noqa: BLE001
            tried.append(
                {
                    "strategy": strategy,
                    "locator": locator_string,
                    "count": 0,
                    "error": str(exc),
                }
            )
            continue

        if count == 1:
            return {
                "found": True,
                "locator": locator_string,
                "strategy": strategy,
                "count": 1,
                "stable": loop._is_stable_locator_strategy(strategy),
                "tried": tried,
                "ranked_candidates": ranked,
            }

        tried.append(
            {
                "strategy": strategy,
                "locator": locator_string,
                "count": count,
            }
        )

    scope_result = scope_candidates(target_text=target_text or None, candidates=raw_candidates) if raw_candidates else {}
    return {
        "found": False,
        "locator": "",
        "strategy": "",
        "count": 0,
        "stable": False,
        "tried": tried,
        "ranked_candidates": ranked,
        "scope_suggestions": scope_result if scope_result else None,
    }


async def tool_locator_validate(loop: Any, args: dict[str, Any], *, get_page: Callable[[], Any]) -> dict[str, Any]:
    page = get_page()
    locator_string = str(args.get("locator") or "").strip()
    expected_value = args.get("expected_value")
    count = 0
    if locator_string:
        try:
            count = await loop._resolve_locator(page, locator_string).count()
        except Exception:  # noqa: BLE001
            count = 0

    matches = [{"element_ref": f"match_{i}", "visible": True} for i in range(count)]
    contract_result = validate_locator_candidate(
        locator_ref=locator_string,
        matches=matches,
        visible_matches=matches,
        page_url=getattr(page, "url", None),
        expected_value=str(expected_value) if expected_value is not None else None,
    )
    return {
        "valid": count == 1,
        "count": count,
        "match_count": contract_result["match_count"],
        "classification": contract_result["classification"],
        "status": contract_result["status"],
    }

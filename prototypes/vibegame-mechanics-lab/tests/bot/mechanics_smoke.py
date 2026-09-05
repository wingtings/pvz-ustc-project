META = {
    "name": "pvz_ustc_mechanics_smoke",
    "purpose": "Verify heater overlap, ice priority, GPA penalties, and the DDL cap.",
    "max_seconds": 12,
}


def _state(snapshot):
    nodes = snapshot.get("nodes", {})
    lab = nodes.get("mechanics-lab", {}).get("runtime", {})
    enemy = nodes.get("enemy", {}).get("runtime", {})
    return lab, enemy


def compact(snapshot, _ctx):
    lab, enemy = _state(snapshot)
    return {
        "frame": snapshot.get("frame"),
        "gpa": lab.get("gpa"),
        "insurance": lab.get("insuranceTriggerCount"),
        "ddl_success": lab.get("ddlSuccessCount"),
        "ddl_blocked": lab.get("ddlBlockedCount"),
        "last_event": lab.get("lastEvent"),
        "heater_count": enemy.get("activeHeaterCount"),
        "speed_multiplier": enemy.get("speedMultiplier"),
        "iced": enemy.get("iced"),
    }


def _fail(reason):
    return ("fail", None, 0, reason)


def decide(snapshot, ctx):
    lab, enemy = _state(snapshot)
    phase = ctx.scratch.setdefault("phase", "initial")

    if not lab or not enemy:
        return _fail("runtime state is missing")

    if phase == "initial":
        if lab.get("gpa") != 100 or enemy.get("speedMultiplier") != 1:
            return _fail("initial GPA or speed multiplier is wrong")
        ctx.scratch["phase"] = "overlap"
        return ("tap", ctx.KEY["place_overlap"], 0.08, "place enemy in two heater zones")

    if phase == "overlap":
        if enemy.get("activeHeaterCount") != 2:
            return _fail("enemy is not inside both heater zones")
        if enemy.get("speedMultiplier") != 0.8:
            return _fail("overlapping heaters stacked or did not apply 0.8")
        ctx.scratch["phase"] = "ice"
        return ("tap", ctx.KEY["toggle_ice"], 0.08, "enable ice while heaters overlap")

    if phase == "ice":
        if not enemy.get("iced") or enemy.get("speedMultiplier") != 0.5:
            return _fail("ice did not take priority over heater slowdown")
        ctx.scratch["phase"] = "insurance"
        return ("tap", ctx.KEY["trigger_insurance"], 0.08, "trigger insurance penalty")

    if phase == "insurance":
        if lab.get("insuranceTriggerCount") != 1 or lab.get("gpa") != 92:
            return _fail("insurance did not subtract exactly 8 GPA")
        ctx.scratch["phase"] = "ddl_to_cap"

    if ctx.scratch["phase"] == "ddl_to_cap":
        count = lab.get("ddlSuccessCount")
        expected_gpa = 92 - 4 * count if isinstance(count, int) else None
        if count is None or lab.get("gpa") != expected_gpa:
            return _fail("DDL success count and GPA diverged")
        if count < 4:
            return ("tap", ctx.KEY["ddl_success"], 0.08, "count a successful DDL departure")
        ctx.scratch["phase"] = "ddl_over_cap"
        return ("tap", ctx.KEY["ddl_success"], 0.08, "attempt a fifth DDL penalty")

    if phase == "ddl_over_cap":
        if lab.get("ddlSuccessCount") != 4 or lab.get("gpa") != 76:
            return _fail("fifth DDL success bypassed the four-event cap")
        if lab.get("lastEvent") != "ddl_success_ignored_at_cap":
            return _fail("cap branch was not observable")
        ctx.scratch["phase"] = "ddl_blocked"
        return ("tap", ctx.KEY["ddl_blocked"], 0.08, "record a blocked DDL event")

    if phase == "ddl_blocked":
        if lab.get("ddlBlockedCount") != 1 or lab.get("gpa") != 76:
            return _fail("blocked DDL event changed GPA")
        if lab.get("lastEvent") != "ddl_blocked_no_penalty":
            return _fail("blocked branch was not observable")
        ctx.scratch["phase"] = "ice_release"
        return ("tap", ctx.KEY["toggle_ice"], 0.08, "release ice inside the heater overlap")

    if phase == "ice_release":
        if enemy.get("iced") or enemy.get("speedMultiplier") != 0.8:
            return _fail("enemy did not return to heater slowdown after ice ended")
        if lab.get("gpa") != 76:
            return _fail("speed-state transition changed GPA")
        return ("done", None, 0, "all mechanism contracts passed")

    return _fail(f"unknown phase: {phase}")

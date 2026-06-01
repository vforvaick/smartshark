"""Scoped Analysis service — scope validation and scoped check execution."""

from app.models.scoped_analysis import ScopeType


def validate_scope(scope_type: ScopeType, scope_params: dict) -> str | None:
    """Validate scope parameters for the given type.

    Returns an error message if invalid, None if valid.
    """
    if not scope_params:
        return "scope_params cannot be empty"

    if scope_type == ScopeType.time_window:
        if "time_start" not in scope_params or "time_end" not in scope_params:
            return "time_window scope requires 'time_start' and 'time_end' in scope_params"
        if not scope_params["time_start"] or not scope_params["time_end"]:
            return "time_window scope requires non-empty 'time_start' and 'time_end'"

    elif scope_type == ScopeType.endpoint:
        if "ip" not in scope_params:
            return "endpoint scope requires 'ip' in scope_params"
        if not scope_params["ip"]:
            return "endpoint scope requires non-empty 'ip'"

    elif scope_type == ScopeType.conversation:
        if "conversation_id" not in scope_params:
            return "conversation scope requires 'conversation_id' in scope_params"
        if not scope_params["conversation_id"]:
            return "conversation scope requires non-empty 'conversation_id'"

    elif scope_type == ScopeType.display_filter:
        if "filter_text" not in scope_params:
            return "display_filter scope requires 'filter_text' in scope_params"
        if not scope_params["filter_text"]:
            return "display_filter scope requires non-empty 'filter_text'"

    elif scope_type == ScopeType.symptom:
        if "description" not in scope_params:
            return "symptom scope requires 'description' in scope_params"
        if not scope_params["description"]:
            return "symptom scope requires non-empty 'description'"

    elif scope_type == ScopeType.playbook:
        if "playbook_name" not in scope_params:
            return "playbook scope requires 'playbook_name' in scope_params"
        if not scope_params["playbook_name"]:
            return "playbook scope requires non-empty 'playbook_name'"

    elif scope_type == ScopeType.combined:
        # Combined requires at least two scope dimensions
        has_time = "time_start" in scope_params and "time_end" in scope_params
        has_endpoint = "ip" in scope_params
        if not (has_time or has_endpoint):
            return "combined scope requires at least time_window or endpoint parameters"

    return None


def scope_boundary_label(scope_type: ScopeType, scope_params: dict) -> str:
    """Produce a human-readable label for the scope boundary."""
    if scope_type == ScopeType.time_window:
        return f"time_window({scope_params.get('time_start')}–{scope_params.get('time_end')})"
    elif scope_type == ScopeType.endpoint:
        return f"endpoint({scope_params.get('ip')})"
    elif scope_type == ScopeType.conversation:
        return f"conversation({scope_params.get('conversation_id')})"
    elif scope_type == ScopeType.display_filter:
        return f"display_filter({scope_params.get('filter_text')})"
    elif scope_type == ScopeType.symptom:
        return f"symptom({scope_params.get('description', '')[:40]})"
    elif scope_type == ScopeType.playbook:
        return f"playbook({scope_params.get('playbook_name')})"
    elif scope_type == ScopeType.combined:
        parts = []
        if "time_start" in scope_params:
            parts.append(f"time:{scope_params['time_start']}–{scope_params.get('time_end')}")
        if "ip" in scope_params:
            parts.append(f"ip:{scope_params['ip']}")
        return f"combined({', '.join(parts)})"
    return str(scope_type)

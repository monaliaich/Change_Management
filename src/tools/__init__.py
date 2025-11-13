"""Tool-call implementations (async functions) that agents register with the Azure SDK.
Common tool calls: `lookup_data`, `check_authorization`, `send_notification`, `generate_report`.
Tool calls must log to the audit trail and operate over CSV-backed data in `src/data`.

"""



__all__ = ["say_hello", "get_number", "echo_message"]

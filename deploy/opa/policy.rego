# Optional OPA policy (POST input to /v1/data/causeway/action/allow)
package causeway.action

default allow = false

allow {
  input.action.kind == "no_action"
}

allow {
  input.action.kind == "dump_pool_stats"
  startswith(input.action.target, "svc:")
}

allow {
  input.action.kind == "fetch_log_template"
}

allow {
  input.action.kind == "compare_deploy_diff"
}

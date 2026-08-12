# ShopAPI Studio tool contract

Use a lowercase stable `tool_id`, semantic `version`, and `contract_version: "1"`.

Declare every port with `name`, `kind`, `schema`, `required`, and `multiple`. Compatible connections require the same kind and schema. Supported kinds are text, audio, subtitle, table, image, video, JSON, and file.

Declare configuration as an object schema with `additionalProperties: false`. Give bounded numeric limits and enumerations where possible. The host reserves `config.enabled`.

Declare a Python entrypoint and bounded timeout. Declare `python_modules`, executables, and models in runtime metadata so Doctor can verify them before execution.

Request the smallest permissions needed. Common permissions are workspace read/write, ShopAPI network and secret access, YouTube network, local compute, and FFmpeg process access. A permission declaration is not approval; the customer approves each run.

Read one JSON request from stdin. Write JSONL events and exactly one result to stdout. Write outputs only inside the node workspace. Return output port names mapped to artifact specifications; never return machine-specific paths as cross-node state.

Use stable error messages, cancellation points, idempotency keys for paid API jobs, bounded retries, and deterministic checkpointing where work is expensive.

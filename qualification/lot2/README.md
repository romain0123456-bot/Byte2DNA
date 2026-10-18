# LOT 2 sandbox qualification

This directory is isolated from the Byte2DNA application. It exercises the small add/multiply contract and a copy of the local POC decision gate. The gate never calls GitHub and cannot merge anything.

The qualification sequence deliberately starts with an incorrect add implementation, observes a failing hosted pull-request check, then fixes the implementation and requires a new check at the new exact SHA. A green check for an older SHA is insufficient. This is a Draft PR qualification; no automatic merge is authorized.

Run `python3 -m unittest discover -s qualification/lot2/tests -v` from the repository root. Standard library only, no secrets, no network, no local model.

Local gate tests use metadata fixtures. Their PASS does not establish GitHub protections, independent GitHub approval identities, LLM concurrency, or a completed merge. Live GitHub evidence is collected separately by the controller. Existing application and LOT5 qualification files are unchanged.

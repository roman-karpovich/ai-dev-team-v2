# Sandbox spike

- Status: Active
- Production mechanism decision: Not yet made

Demonstrate that child processes cannot access the network, sensitive
environment, package installation, source writes, or undeclared paths. Compare
platform mechanisms empirically; CLI safety flags are not evidence of operating
system enforcement.

The minimum useful probe combines an OS-enforced read-only artifact with a
separate writable scratch/output area. It must positively prove access to each
declared dependency, including an allowed localhost Docker service, and
negatively prove that a child cannot write into the source artifact or read the
other review path's sealed result. A permission-mode label from the provider is
an input to the adapter profile, not proof of either result.

Changing permissions with `chmod` while the reviewer runs as the same owner is
not an enforcement boundary: that process can restore the mode. Compare a
read-only mount, container boundary, or distinct ownership boundary and retain
the positive and negative probe evidence in the invocation receipt.
